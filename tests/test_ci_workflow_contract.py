from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
full = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
branch = (ROOT / ".github/workflows/branch-check.yml").read_text(encoding="utf-8")

for text in ("branches: [main]", "pull_request:", "workflow_dispatch:", "cancel-in-progress: true", "python3 scripts/run_tests.py"):
    assert text in full, f"full CI missing: {text}"
for text in ("branches-ignore: [main]", "pull-requests: read", "gh api --method GET", "if: needs.detect-open-pr.outputs.exists != 'true'", "bash scripts/check_push.sh"):
    assert text in branch, f"branch CI missing: {text}"
assert "python3 scripts/run_tests.py" not in branch
print("CI workflow contract checks passed")
