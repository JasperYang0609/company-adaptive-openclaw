#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from collections import Counter

from common import root
from telemetry_privacy import iter_valid_jsonl, load_or_create_export_salt, pseudonymous_alias


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    adaptive_root = root(args.workspace)
    source = adaptive_root / "events" / "usage_events.jsonl"
    salt = load_or_create_export_salt(adaptive_root)
    counts: Counter[str] = Counter()
    valid_lines = 0
    invalid_lines = 0

    for _line_number, event, _error_type in iter_valid_jsonl(source):
        if event is None:
            invalid_lines += 1
            continue
        valid_lines += 1
        alias = pseudonymous_alias("sender", event.get("sender_id"), salt)
        counts[alias] += 1

    output = adaptive_root / "reports" / "adoption" / f"{time.strftime('%Y%m%d')}_adoption.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"- {alias}: {count}" for alias, count in counts.most_common()) or "- No valid events"
    output.write_text(
        "# Adoption Report\n\n"
        f"- Valid events: {valid_lines}\n"
        f"- Invalid lines skipped: {invalid_lines}\n"
        "- Privacy: pseudonymous aliases; raw sender identifiers excluded\n\n"
        "## Usage by pseudonymous sender\n\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    print(output)
    print(f"valid_events={valid_lines} invalid_lines={invalid_lines}")


if __name__ == "__main__":
    main()
