#!/usr/bin/env python3
"""List every /trace/home/* quota as a Markdown table.

Rows with a 25 GB hard limit come first, then the rest; each block is
sorted alphabetically by path.

Usage:
    TRACE_API_PASSWORD=... python scripts/home_quotas_table.py
    TRACE_API_PASSWORD=... python scripts/home_quotas_table.py --csv home_quotas.csv
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.vast_client import get_all_quotas

HOME_PREFIX = '/trace/home/'
# Accept either decimal (25 GB) or binary (25 GiB) limits
LIMITS_25G = {25 * 10**9, 25 * 2**30}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--csv', help='Also write rows to this CSV file')
    args = parser.parse_args()

    rows = [q for q in get_all_quotas() if (q['path'] or '').startswith(HOME_PREFIX)]
    for q in rows:
        q['at_25g'] = q['hard_limit'] in LIMITS_25G
    rows.sort(key=lambda q: (not q['at_25g'], q['path'].lower()))

    print(f"| Path | Name | Hard limit | Used | % | 25 GB |")
    print(f"|---|---|---|---|---|---|")
    for q in rows:
        print(f"| {q['path']} | {q['name']} | {q['hard_limit_fmt']} | "
              f"{q['used_effective_fmt']} | {q['usage_pct']} | {'yes' if q['at_25g'] else 'no'} |")

    at_25 = sum(q['at_25g'] for q in rows)
    print(f"\n{len(rows)} home quotas: {at_25} at 25 GB, {len(rows) - at_25} other", file=sys.stderr)

    if args.csv:
        fields = ['path', 'name', 'hard_limit', 'hard_limit_fmt',
                  'used_effective', 'used_effective_fmt', 'usage_pct', 'at_25g']
        with open(args.csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {args.csv}", file=sys.stderr)


if __name__ == '__main__':
    main()
