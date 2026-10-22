#!/usr/bin/env python3
"""Build/verify a committed product candidate; never publish or move refs."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/plane-devflow/scripts'))
from product_release import manifest, verify_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--candidate', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = manifest(ROOT, args.commit, candidate=args.candidate)
    # Source identity is committed, independent of dirty working files.
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    else:
        print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
