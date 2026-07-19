#!/usr/bin/env python3

import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_with_timeout.py <seconds> <command> [args...]", file=sys.stderr)
        return 64
    try:
        timeout = float(sys.argv[1])
    except ValueError:
        print(f"invalid timeout: {sys.argv[1]}", file=sys.stderr)
        return 64
    if timeout <= 0:
        print("timeout must be greater than zero", file=sys.stderr)
        return 64
    try:
        completed = subprocess.run(sys.argv[2:], timeout=timeout, check=False)
        return completed.returncode
    except subprocess.TimeoutExpired:
        print(f"command timed out after {timeout:g} seconds: {' '.join(sys.argv[2:])}", file=sys.stderr)
        return 124
    except OSError as error:
        print(f"could not execute {sys.argv[2]}: {error}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    raise SystemExit(main())
