from __future__ import annotations

import argparse
import sys

import validate


def main() -> int:
    parser = argparse.ArgumentParser(prog="openenv")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Run repository validation checks")

    args = parser.parse_args()

    if args.command == "validate":
        return validate.main()

    parser.error(f"unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())