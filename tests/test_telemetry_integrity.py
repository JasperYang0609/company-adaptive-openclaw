#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from telemetry_privacy import dumps_json_line  # noqa: E402


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="company-adaptive-telemetry-") as tmp_dir:
        workspace = Path(tmp_dir)
        adaptive_root = workspace / "adaptive-openclaw"
        source = adaptive_root / "events" / "usage_events.jsonl"
        source.parent.mkdir(parents=True, exist_ok=True)
        raw_sender = "synthetic-user-123"
        raw_channel = "synthetic-channel-456"
        raw_content = "synthetic private content that must not be exported"
        valid_event = {
            "event_id": "evt_valid",
            "timestamp": "2026-08-05T00:00:00+0000",
            "platform": "discord",
            "sender_id": raw_sender,
            "channel_id": raw_channel,
            "parent_channel_id": "synthetic-parent-789",
            "task_type": "development",
            "content_summary": raw_content,
            "correction_signal": "格式",
        }
        with source.open("wb") as handle:
            handle.write((json.dumps(valid_event) + "\n").encode("utf-8"))
            handle.write(b'{"sender_id":"\\ud800","channel_id":"bad"}\n')
            handle.write(b'{"sender_id":')
            handle.write(b"\n")
            handle.write(b'\xff\xfe\n')

        report_result = run(
            "python3", "scripts/generate_adoption_report.py", "--workspace", str(workspace)
        )
        assert "valid_events=1 invalid_lines=3" in report_result.stdout
        report = next((adaptive_root / "reports" / "adoption").glob("*_adoption.md"))
        report_text = report.read_text(encoding="utf-8")
        assert raw_sender not in report_text
        assert raw_channel not in report_text
        assert "Invalid lines skipped: 3" in report_text
        assert "usr_" in report_text

        export_path = adaptive_root / "reports" / "exports" / "safe.json"
        export_result = run(
            "python3",
            "scripts/export_usage_events.py",
            "--workspace",
            str(workspace),
            "--output",
            str(export_path),
        )
        assert "exported_events=1 invalid_lines=3" in export_result.stdout
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        serialized = json.dumps(payload, ensure_ascii=False)
        assert raw_sender not in serialized
        assert raw_channel not in serialized
        assert raw_content not in serialized
        assert "格式" not in serialized
        assert payload["stats"] == {"exported_events": 1, "invalid_lines": 3}
        exported_event = payload["events"][0]
        assert exported_event["sender_alias"].startswith("usr_")
        assert exported_event["channel_alias"].startswith("chn_")
        assert "content_summary" not in exported_event
        assert "correction_signal" not in exported_event
        assert exported_event["has_correction_signal"] is True

        second_export = adaptive_root / "reports" / "exports" / "safe-2.json"
        run(
            "python3",
            "scripts/export_usage_events.py",
            "--workspace",
            str(workspace),
            "--output",
            str(second_export),
        )
        payload_2 = json.loads(second_export.read_text(encoding="utf-8"))
        assert payload_2["events"][0]["sender_alias"] == exported_event["sender_alias"]

        salt_path = adaptive_root / "config" / "telemetry_export_salt"
        assert len(salt_path.read_bytes()) >= 16
        assert salt_path.stat().st_mode & 0o077 == 0

        normalized_line = dumps_json_line({"sender_id": "synthetic-\ud800-user"})
        assert "\\ud800" not in normalized_line.lower()
        assert "\uFFFD" in normalized_line
        json.loads(normalized_line)

    print("PASS test_telemetry_integrity")


if __name__ == "__main__":
    main()
