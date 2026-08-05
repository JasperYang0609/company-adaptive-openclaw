#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from common import root
from telemetry_privacy import iter_valid_jsonl, load_or_create_export_salt, pseudonymous_alias

CATEGORY_FIELDS = (
    "platform",
    "surface_type",
    "event_action",
    "task_type",
)

ALLOWED_SUCCESS_STATES = {
    "sent",
    "failed",
    "success",
    "completed",
    "delivered",
    "not_delivered",
}


def bounded_category(value) -> str:
    text = str(value or "unknown").strip().lower()
    if 1 <= len(text) <= 64 and all(char.isascii() and (char.isalnum() or char in "._-") for char in text):
        return text
    return "other"



def safe_event(event: dict, salt: bytes) -> dict:
    exported = {
        "event_id": str(event.get("event_id", "unknown"))[:80],
        "timestamp": str(event.get("timestamp", ""))[:40],
    }
    for field in CATEGORY_FIELDS:
        if field in event:
            exported[field] = bounded_category(event[field])
    success = str(event.get("success_signal", "")).strip().lower()
    if success:
        exported["success_status"] = success if success in ALLOWED_SUCCESS_STATES else "recorded"
    if "correction_signal" in event:
        exported["has_correction_signal"] = bool(event.get("correction_signal"))
    if "artifact_delivered" in event:
        exported["artifact_delivered"] = bool(event.get("artifact_delivered"))
    exported["sender_alias"] = pseudonymous_alias("sender", event.get("sender_id"), salt)
    exported["channel_alias"] = pseudonymous_alias("channel", event.get("channel_id"), salt)
    if event.get("parent_channel_id"):
        exported["parent_channel_alias"] = pseudonymous_alias(
            "parent_channel", event.get("parent_channel_id"), salt
        )
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description="Export pseudonymous Company Adaptive usage events")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output", help="Output JSON path; defaults to adaptive-openclaw/reports/exports/")
    args = parser.parse_args()

    adaptive_root = root(args.workspace)
    source = adaptive_root / "events" / "usage_events.jsonl"
    salt = load_or_create_export_salt(adaptive_root)

    events: list[dict] = []
    invalid_lines: list[dict] = []
    for line_number, event, error_type in iter_valid_jsonl(source):
        if event is None:
            invalid_lines.append({"line": line_number, "error": error_type})
            continue
        events.append(safe_event(event, salt))

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else adaptive_root
        / "reports"
        / "exports"
        / f"{time.strftime('%Y%m%d_%H%M%S')}_usage_events_safe.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "company-adaptive-usage-export/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy": "pseudonymous; raw identifiers and content summaries excluded",
        "stats": {
            "exported_events": len(events),
            "invalid_lines": len(invalid_lines),
        },
        "invalid_line_summary": invalid_lines,
        "events": events,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"output={output}")
    print(f"exported_events={len(events)} invalid_lines={len(invalid_lines)}")


if __name__ == "__main__":
    main()
