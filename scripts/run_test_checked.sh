#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "usage: run_test_checked.sh <seconds> <test-binary> [args...]" >&2
    exit 64
fi

timeout_seconds="$1"
shift
test_log="$(mktemp -t ernos-test.XXXXXX)"
cleanup() {
    rm -f "$test_log"
}
trap cleanup EXIT

set +e
python3 scripts/run_with_timeout.py "$timeout_seconds" "$@" 2>&1 | tee "$test_log"
test_status=${PIPESTATUS[0]}
set -e

if [ "$test_status" -ne 0 ]; then
    echo "test process failed with exit code $test_status: $*" >&2
    exit "$test_status"
fi
if grep -qE 'FAIL:|[1-9][0-9]* FAILED!?|TESTS FAILED' "$test_log"; then
    echo "test output reported a failure despite a zero exit code: $*" >&2
    exit 1
fi
