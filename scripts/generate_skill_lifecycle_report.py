#!/usr/bin/env python3
"""Generate an aggregate-only report from privacy-minimal Skill lifecycle events."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

from common import root
from skill_lifecycle import LifecycleError, STAGES, analyze_store


def default_output(workspace: str) -> Path:
    day = dt.datetime.now().astimezone().date().isoformat().replace("-", "")
    return root(workspace) / "reports" / "adoption" / f"{day}_skill_lifecycle.json"


def write_atomic(path: Path, payload: dict) -> None:
    if path.is_symlink():
        raise LifecycleError("report output symlink is not allowed")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    adaptive_root = root(args.workspace)
    source = adaptive_root / "events" / "skill_lifecycle_events.jsonl"
    output = Path(args.output).expanduser().absolute() if args.output else default_output(args.workspace)
    try:
        payload = analyze_store(source)
        payload["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        # Keep stage keys stable even when a skill has no event for a stage.
        for summary in payload["skills"].values():
            summary["journeys_by_stage"] = {
                stage: summary["journeys_by_stage"].get(stage, 0) for stage in STAGES
            }
        write_atomic(output, payload)
    except (LifecycleError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"output={output}")
    print(
        "accepted_events={accepted_events} invalid_lines={invalid_lines} "
        "duplicate_events={duplicate_events} transition_anomalies={transition_anomalies}".format(
            **payload["stats"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
