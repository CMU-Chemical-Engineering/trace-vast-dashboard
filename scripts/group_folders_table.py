#!/usr/bin/env python3
"""List every /trace/group/<group>/* entry as a Markdown table.

Sorted by group folder, then group-readable entries before unreadable
ones, then by name. A directory counts as group readable only if it has
both g+r and g+x (needed to list and enter it).

Usage:
    python3 scripts/group_folders_table.py
    python3 scripts/group_folders_table.py --root /trace/group --csv group_folders.csv
"""

import argparse
import csv
import grp
import os
import pwd
import stat
import sys


def _owner(uid):
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def _group(gid):
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def scan(root):
    rows = []
    for group_dir in sorted(os.scandir(root), key=lambda d: d.name):
        if not group_dir.is_dir(follow_symlinks=False):
            continue
        try:
            entries = list(os.scandir(group_dir.path))
        except PermissionError:
            print(f"Cannot read {group_dir.path}", file=sys.stderr)
            continue
        for entry in entries:
            st = entry.stat(follow_symlinks=False)
            mode = st.st_mode
            is_dir = stat.S_ISDIR(mode)
            readable = bool(mode & stat.S_IRGRP) and (not is_dir or bool(mode & stat.S_IXGRP))
            gname = _group(st.st_gid)
            rows.append({
                'group_folder': group_dir.name,
                'name': entry.name,
                'type': 'dir' if is_dir else 'link' if stat.S_ISLNK(mode) else 'file',
                'mode': stat.filemode(mode),
                'owner': _owner(st.st_uid),
                'group': gname,
                'group_matches': gname == group_dir.name,
                'group_readable': readable,
            })
    rows.sort(key=lambda r: (r['group_folder'], not r['group_readable'], r['name'].lower()))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', default='/trace/group', help='Group root (default /trace/group)')
    parser.add_argument('--csv', help='Also write rows to this CSV file')
    args = parser.parse_args()

    rows = scan(args.root)

    print("| Group folder | Entry | Type | Mode | Owner | Group | Group matches | Group readable |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['group_folder']} | {r['name']} | {r['type']} | `{r['mode']}` | {r['owner']} | "
              f"{r['group']} | {'yes' if r['group_matches'] else 'no'} | "
              f"{'yes' if r['group_readable'] else 'no'} |")

    unreadable = sum(not r['group_readable'] for r in rows)
    print(f"\n{len(rows)} entries: {len(rows) - unreadable} group readable, {unreadable} not",
          file=sys.stderr)

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['group_folder'])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {args.csv}", file=sys.stderr)


if __name__ == '__main__':
    main()
