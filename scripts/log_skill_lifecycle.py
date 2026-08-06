#!/usr/bin/env python3
"""Write privacy-minimal, explicitly instrumented Skill lifecycle events."""
from __future__ import annotations

import argparse
import json
import sys

from skill_lifecycle import (
    DURATION_BUCKETS,
    OUTPUT_KINDS,
    REASON_CODES,
    SOURCES,
    STAGES,
    LifecycleError,
    append_event,
    build_event,
    new_journey_id,
    load_or_create_lifecycle_salt,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new-journey", help="generate an opaque, non-identifying journey id")
    new.add_argument("--json", action="store_true", help="emit a JSON object instead of only the id")

    record = sub.add_parser("record", help="append one lifecycle event")
    record.add_argument("--workspace", required=True)
    record.add_argument("--skill-key", required=True)
    record.add_argument("--stage", required=True, choices=STAGES)
    record.add_argument("--journey-id", help="opaque jrn_ id; generated for a first-stage event when omitted")
    record.add_argument("--attempt", type=int, default=0)
    record.add_argument("--source", choices=SOURCES, default="unknown")
    record.add_argument("--reason-code", choices=REASON_CODES, default="none")
    record.add_argument("--duration-bucket", choices=DURATION_BUCKETS, default="not_recorded")
    record.add_argument("--output-kind", choices=OUTPUT_KINDS, default="none")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "new-journey":
        journey_id = new_journey_id()
        if args.json:
            print(json.dumps({"journey_id": journey_id}, sort_keys=True))
        else:
            print(journey_id)
        return 0

    journey_id = args.journey_id or new_journey_id()
    try:
        salt = load_or_create_lifecycle_salt(args.workspace)
        event = build_event(
            salt=salt,
            journey_id=journey_id,
            skill_key=args.skill_key,
            stage=args.stage,
            attempt=args.attempt,
            source=args.source,
            reason_code=args.reason_code,
            duration_bucket=args.duration_bucket,
            output_kind=args.output_kind,
        )
        status = append_event(args.workspace, event)
    except (LifecycleError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "status": status,
                "event_id": event["event_id"],
                "journey_id": event["journey_id"],
                "stage": event["stage"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
