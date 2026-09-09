#!/bin/sh
set -eu
repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo_root"
python3 -m compileall -q scripts tests
python3 scripts/run_tests.py
python3 tests/test_ci_workflow_contract.py
