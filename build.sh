#!/usr/bin/env bash
# Build gate: run the test suite, then snapshot architectural quality metrics.
#
#   ./build.sh            run tests + quality snapshot
#
# Outputs:
#   .quality/dashboard.md   current metrics vs previous run, offender lists
#   .quality/history.jsonl  one summary line per run (aggregatable)
#   .quality/runs/          full per-run detail JSON
#
# Exit code is the test suite's exit code — quality metrics are informational
# (trend data for deciding when the next batch of work should be a cleanup).
#
# To run after every commit, install as a post-commit hook:
#   ln -sf ../../build.sh .git/hooks/post-commit
set -o pipefail
cd "$(dirname "$0")"
mkdir -p .quality

echo "== tests =="
poetry run pytest -q 2>&1 | tee .quality/last_test_output.txt
TEST_EXIT=${PIPESTATUS[0]}

echo
echo "== quality snapshot =="
poetry run python scripts/quality_check.py --test-exit "$TEST_EXIT"

if [ "$TEST_EXIT" -ne 0 ]; then
    echo
    echo "BUILD FAILED: test suite exited $TEST_EXIT"
fi
exit "$TEST_EXIT"
