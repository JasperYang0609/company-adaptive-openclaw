#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
import uuid

from common import root
from telemetry_privacy import dumps_json_line, normalize_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--sender-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--task-type", default="unknown")
    parser.add_argument("--correction-signal", default="")
    parser.add_argument("--success-signal", default="")
    parser.add_argument("--artifact-delivered", action="store_true")
    args = parser.parse_args()

    event = {
        "event_id": "evt_" + uuid.uuid4().hex[:12],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "platform": "discord",
        "sender_id": normalize_text(args.sender_id),
        "channel_id": normalize_text(args.channel_id),
        "task_type": normalize_text(args.task_type),
        "correction_signal": normalize_text(args.correction_signal),
        "success_signal": normalize_text(args.success_signal),
        "artifact_delivered": bool(args.artifact_delivered),
    }
    path = root(args.workspace) / "events" / "usage_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = dumps_json_line(event)
    with path.open("a", encoding="utf-8", errors="strict") as handle:
        handle.write(line + "\n")
    print(event["event_id"])


if __name__ == "__main__":
    main()
