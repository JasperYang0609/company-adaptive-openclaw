#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
LOG = SCRIPTS / "log_skill_lifecycle.py"
REPORT = SCRIPTS / "generate_skill_lifecycle_report.py"
SCHEMA_PATH = ROOT / "schemas" / "skill_lifecycle_event.schema.json"
sys.path.insert(0, str(SCRIPTS))

from skill_lifecycle import (  # noqa: E402
    EVENT_FIELDS,
    LifecycleError,
    analyze_store,
    append_event,
    build_event,
    event_store,
    load_or_create_lifecycle_salt,
)


class SkillLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="company-adaptive-lifecycle-")
        self.workspace = Path(self.tmp.name)
        self.salt = load_or_create_lifecycle_salt(self.workspace)
        self.journey = "jrn_" + "1" * 32

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def event(
        self,
        stage: str,
        *,
        journey: str | None = None,
        attempt: int = 0,
        reason: str = "none",
        duration: str = "not_recorded",
        output: str = "none",
        skill: str = "summary-backup",
    ) -> dict:
        return build_event(
            salt=self.salt,
            journey_id=journey or self.journey,
            skill_key=skill,
            stage=stage,
            attempt=attempt,
            source="direct_request",
            reason_code=reason,
            duration_bucket=duration,
            output_kind=output,
        )

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(LOG), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def run_report(self, output: Path | None = None) -> subprocess.CompletedProcess[str]:
        args = [
            sys.executable,
            str(REPORT),
            "--workspace",
            str(self.workspace),
        ]
        if output is not None:
            args += ["--output", str(output)]
        return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)

    def store_lines(self) -> list[dict]:
        path = event_store(self.workspace)
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def test_schema_and_writer_use_exact_privacy_allowlist(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), EVENT_FIELDS)
        self.assertEqual(set(schema["properties"]), EVENT_FIELDS)

        event = self.event("shown")
        self.assertEqual(set(event), EVENT_FIELDS)
        forbidden = {
            "sender_id",
            "user_id",
            "channel_id",
            "session_key",
            "message_id",
            "content",
            "prompt",
            "error_text",
            "stack_trace",
            "customer_name",
            "path",
        }
        self.assertTrue(forbidden.isdisjoint(event))

    def test_all_seven_stages_record_and_aggregate_without_raw_canaries(self) -> None:
        raw_canaries = [
            "synthetic-user-123",
            "synthetic-channel-456",
            "synthetic-session-secret",
            "private prompt payload",
        ]

        records = [
            (self.journey, "shown", []),
            (self.journey, "selected", []),
            (self.journey, "started", []),
            (self.journey, "completed", ["--duration-bucket", "10s_60s", "--output-kind", "file"]),
            (self.journey, "corrected", ["--reason-code", "user_correction"]),
            ("jrn_" + "2" * 32, "started", []),
            ("jrn_" + "2" * 32, "failed", ["--reason-code", "tool_error", "--duration-bucket", "1s_10s"]),
            ("jrn_" + "3" * 32, "shown", []),
            ("jrn_" + "3" * 32, "abandoned", ["--reason-code", "user_cancelled"]),
        ]
        for journey, stage, extra in records:
            result = self.run_cli(
                "record",
                "--workspace",
                str(self.workspace),
                "--skill-key",
                "summary-backup",
                "--stage",
                stage,
                "--journey-id",
                journey,
                "--source",
                "direct_request",
                *extra,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["stage"], stage)

        store_text = event_store(self.workspace).read_text(encoding="utf-8")
        for canary in raw_canaries:
            self.assertNotIn(canary, store_text)

        output = self.workspace / "lifecycle-report.json"
        result = self.run_report(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        report_text = output.read_text(encoding="utf-8")
        report = json.loads(report_text)
        for stage in ("shown", "selected", "started", "completed", "failed", "abandoned", "corrected"):
            self.assertGreaterEqual(report["skills"]["summary-backup"]["journeys_by_stage"][stage], 1)
        self.assertEqual(report["coverage"], "explicit_adapter_only")
        self.assertNotIn(self.journey, report_text)
        self.assertNotIn("event_id", report_text)
        self.assertNotIn("journey_id", report_text)
        for canary in raw_canaries:
            self.assertNotIn(canary, report_text)

    def test_duplicate_tuple_is_idempotent_and_not_rewritten(self) -> None:
        first = self.event("shown")
        self.assertEqual(append_event(self.workspace, first), "written")
        replay = dict(first)
        replay["timestamp"] = "2026-08-06T00:00:01Z"
        self.assertEqual(append_event(self.workspace, replay), "duplicate")
        self.assertEqual(len(self.store_lines()), 1)

    def test_impossible_and_terminal_transitions_fail_closed(self) -> None:
        with self.assertRaisesRegex(LifecycleError, "requires a prior started"):
            append_event(self.workspace, self.event("completed", output="text"))

        append_event(self.workspace, self.event("started"))
        with self.assertRaisesRegex(LifecycleError, "bounded failure reason"):
            self.event("failed")
        append_event(
            self.workspace,
            self.event("failed", reason="validation_failed", duration="lt_1s"),
        )
        with self.assertRaisesRegex(LifecycleError, "already terminal"):
            append_event(self.workspace, self.event("started", attempt=1))

    def test_unknown_sensitive_fields_are_rejected_before_store_write(self) -> None:
        event = self.event("shown")
        event["content"] = "private prompt payload"
        with self.assertRaisesRegex(LifecycleError, "field contract mismatch"):
            append_event(self.workspace, event)
        path = self.workspace / "adaptive-openclaw/events/skill_lifecycle_events.jsonl"
        self.assertFalse(path.exists())

    def test_report_counts_malformed_duplicate_and_transition_anomaly(self) -> None:
        path = event_store(self.workspace)
        shown = self.event("shown")
        impossible = self.event("completed", attempt=1, output="text")
        path.write_bytes(
            (json.dumps(shown, separators=(",", ":")) + "\n").encode()
            + (json.dumps(shown, separators=(",", ":")) + "\n").encode()
            + b'{"broken":\n'
            + (json.dumps(impossible, separators=(",", ":")) + "\n").encode()
        )
        report = analyze_store(path)
        self.assertEqual(report["stats"]["accepted_events"], 1)
        self.assertEqual(report["stats"]["invalid_lines"], 1)
        self.assertEqual(report["stats"]["duplicate_events"], 1)
        self.assertEqual(report["stats"]["transition_anomalies"], 1)

    def test_concurrent_duplicate_append_writes_at_most_once(self) -> None:
        journey = "jrn_" + "4" * 32
        args = (
            "record",
            "--workspace",
            str(self.workspace),
            "--skill-key",
            "summary-backup",
            "--stage",
            "shown",
            "--journey-id",
            journey,
            "--source",
            "recommendation",
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.run_cli(*args), range(8)))
        self.assertTrue(all(result.returncode == 0 for result in results), [r.stderr for r in results])
        statuses = [json.loads(result.stdout)["status"] for result in results]
        self.assertEqual(statuses.count("written"), 1)
        self.assertEqual(statuses.count("duplicate"), 7)
        self.assertEqual(len(self.store_lines()), 1)

    def test_store_and_report_symlinks_fail_closed(self) -> None:
        events_dir = self.workspace / "adaptive-openclaw/events"
        events_dir.mkdir(parents=True, exist_ok=True)
        outside = self.workspace / "outside.jsonl"
        outside.write_text("", encoding="utf-8")
        (events_dir / "skill_lifecycle_events.jsonl").symlink_to(outside)
        with self.assertRaisesRegex(LifecycleError, "safely open"):
            append_event(self.workspace, self.event("shown"))

        clean_workspace = Path(tempfile.mkdtemp(dir=self.workspace))
        report_link = clean_workspace / "report.json"
        report_link.symlink_to(outside)
        proc = subprocess.run(
            [
                sys.executable,
                str(REPORT),
                "--workspace",
                str(clean_workspace),
                "--output",
                str(report_link),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("symlink", proc.stderr)

    def test_lifecycle_salt_symlink_fails_closed(self) -> None:
        workspace = self.workspace / "salt-symlink-workspace"
        config = workspace / "adaptive-openclaw/config"
        config.mkdir(parents=True)
        outside = self.workspace / "outside-salt"
        outside.write_bytes(b"X" * 32)
        (config / "skill_lifecycle_salt").symlink_to(outside)
        with self.assertRaisesRegex(LifecycleError, "safely open lifecycle salt"):
            load_or_create_lifecycle_salt(workspace)

    def test_cli_refuses_terminal_stage_without_existing_journey(self) -> None:
        result = self.run_cli(
            "record",
            "--workspace",
            str(self.workspace),
            "--skill-key",
            "summary-backup",
            "--stage",
            "completed",
            "--output-kind",
            "text",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires a prior started", result.stderr)


if __name__ == "__main__":
    unittest.main()
