#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = "python3"

def run(args, cwd=ROOT):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)

def main():
    tmp = Path(tempfile.mkdtemp(prefix="company-adaptive-test-"))
    try:
        run([PY, "scripts/install_profile_tree.py", "--workspace", str(tmp), "--mode", "solo_team", "--company-name", "TestCo"])
        run([PY, "scripts/validate_profiles.py", "--workspace", str(tmp)])
        run([PY, "scripts/log_interaction_event.py", "--workspace", str(tmp), "--sender-id", "123", "--channel-id", "c1", "--task-type", "test", "--correction-signal", "請用表格"])
        run([PY, "scripts/log_interaction_event.py", "--workspace", str(tmp), "--sender-id", "123", "--channel-id", "c1", "--task-type", "test", "--correction-signal", "下次用表格"])
        run([PY, "scripts/nightly_learn.py", "--workspace", str(tmp)])
        pending = list((tmp/"adaptive-openclaw/diffs/pending").glob("*.json"))
        assert pending, "expected pending diff"
        run([PY, "scripts/apply_profile_diff.py", "--workspace", str(tmp)] + [str(p) for p in pending])
        applied = list((tmp/"adaptive-openclaw/diffs/applied").glob("*.json"))
        assert applied, "expected applied diff"
        # Forbidden diff must reject.
        forbidden = tmp/"forbidden.json"
        forbidden.write_text(json.dumps({
            "target_type":"user_profile",
            "target_id":"discord:123",
            "operation":"set_field",
            "path":"permission_scope.can_read",
            "value":["all_sensitive"],
            "risk_level":"high",
            "confidence":0.99,
            "evidence_count":1,
            "evidence_summary":"test",
            "source_event_ids":[],
            "auto_apply":True
        }), encoding="utf-8")
        run([PY, "scripts/apply_profile_diff.py", "--workspace", str(tmp), str(forbidden)])
        rejected = list((tmp/"adaptive-openclaw/diffs/rejected").glob("forbidden.json"))
        assert rejected, "expected forbidden diff rejected"
        run([PY, "scripts/self_repair_check.py", "--workspace", str(tmp)])
        run([PY, "scripts/generate_adoption_report.py", "--workspace", str(tmp)])
        run([PY, "scripts/rollback_profile.py", "--workspace", str(tmp)])
        run([PY, "scripts/validate_profiles.py", "--workspace", str(tmp)])
        print("PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
