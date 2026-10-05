#!/usr/bin/env python3
"""List every per-user quota under /trace/home as a Markdown table.

/trace/home is a single VAST directory quota; each user's limit is a
user quota attached to it. Rows with a 25 GB hard limit come first,
then the rest; each block is sorted alphabetically by user.

Usage:
    read -s TRACE_API_PASSWORD; export TRACE_API_PASSWORD
    python3 scripts/home_quotas_table.py
    python3 scripts/home_quotas_table.py --csv home_quotas.csv
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.vast_client import get_vast_client
from modules.formatting import format_bytes, calculate_percentage

HOME_PATH = '/trace/home'
# Accept either decimal (25 GB) or binary (25 GiB) limits
LIMITS_25G = {25 * 10**9, 25 * 2**30}


def get_home_user_quotas(client):
    home = [q for q in client.quotas.get() if (q.get('path') or '').rstrip('/') == HOME_PATH]
    if not home:
        sys.exit(f"No directory quota found at {HOME_PATH}")
    home = home[0]

    data = client.userquotas.get()
    entries = data['results'] if isinstance(data, dict) else data

    # User quotas link back to their directory quota by id; fall back to
    # quota_system_id if this VAST version doesn't expose quota_id.
    linked = [e for e in entries if e.get('quota_id') == home.get('id')]
    if not linked and home.get('quota_system_id') is not None:
        linked = [e for e in entries if e.get('quota_system_id') == home.get('quota_system_id')]
    if not linked:
        print(f"Warning: could not link user quotas to {HOME_PATH}; showing all "
              f"{len(entries)} user quotas", file=sys.stderr)
        linked = entries

    return [e for e in linked if not e.get('entity', {}).get('is_group', False)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--csv', help='Also write rows to this CSV file')
    args = parser.parse_args()

    rows = []
    for e in get_home_user_quotas(get_vast_client()):
        entity = e.get('entity', {})
        hard = e.get('hard_limit') or 0
        used = e.get('used_capacity') or 0
        rows.append({
            'user': entity.get('name') or entity.get('identifier') or f"id:{e.get('id')}",
            'identifier_type': entity.get('identifier_type'),
            'hard_limit': hard,
            'hard_limit_fmt': format_bytes(hard) if hard else 'none',
            'used_capacity': used,
            'used_capacity_fmt': format_bytes(used),
            'usage_pct': f"{calculate_percentage(used, hard):.1f}" if hard else '',
            'at_25g': hard in LIMITS_25G,
        })
    rows.sort(key=lambda r: (not r['at_25g'], str(r['user']).lower()))

    print("| User | Hard limit | Used | % | 25 GB |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['user']} | {r['hard_limit_fmt']} | {r['used_capacity_fmt']} | "
              f"{r['usage_pct']} | {'yes' if r['at_25g'] else 'no'} |")

    at_25 = sum(r['at_25g'] for r in rows)
    print(f"\n{len(rows)} home user quotas: {at_25} at 25 GB, {len(rows) - at_25} other",
          file=sys.stderr)

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['user'])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {args.csv}", file=sys.stderr)


if __name__ == '__main__':
    main()
