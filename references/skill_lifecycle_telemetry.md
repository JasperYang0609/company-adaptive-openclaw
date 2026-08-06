# Privacy-minimal Skill Lifecycle Telemetry

This contract measures explicitly instrumented Skill journeys without collecting raw users, channels, sessions, messages, prompts, customer names, paths, stack traces, or error text.

## Coverage boundary

Coverage is `explicit_adapter_only`.

An event exists only when an owned adapter or operator explicitly calls `scripts/log_skill_lifecycle.py`. This Repository does not patch OpenClaw Core and does not observe every Skill recommendation or execution automatically. Therefore:

- absence of an event does **not** prove that a Skill was not shown or used;
- counts are not a denominator for all OpenClaw traffic;
- adoption/conversion rates are valid only within an adapter that also records its own `shown` population;
- Core-wide automatic instrumentation remains an upstream OpenClaw concern.

## Privacy contract

The raw lifecycle JSONL is privacy-minimal at collection time. Its exact allowlist is defined by `schemas/skill_lifecycle_event.schema.json`:

- opaque random `journey_id`;
- deterministic opaque `event_id` scoped by the local telemetry salt;
- UTC timestamp;
- canonical non-sensitive `skill_key` slug;
- bounded stage, attempt, source, reason, duration bucket, and output kind.

Never put a user, customer, channel, session, message, ticket, project, or secret into `skill_key` or any categorical field. Use a stable public Skill identifier such as `summary-backup`.

The generated report contains aggregate counts only. It excludes event IDs, journey IDs, raw content, and free-form error data.

## Stages

- `shown`: an owned adapter visibly offered the Skill.
- `selected`: the user or deterministic route selected it.
- `started`: execution began after required preflight.
- `completed`: execution completed under the adapter's acceptance rule.
- `failed`: terminal failure with a bounded failure reason.
- `abandoned`: terminal cancellation/supersession/timeout.
- `corrected`: user correction observed for an existing journey; this may follow completion.

`completed` and `failed` require `started`. `abandoned` requires a prior non-terminal stage. A journey cannot restart after a terminal event. Replayed `(journey, skill, stage, attempt)` events are idempotent.

## Adapter example

```bash
JOURNEY="$(python3 scripts/log_skill_lifecycle.py new-journey)"

python3 scripts/log_skill_lifecycle.py record \
  --workspace /path/to/workspace \
  --journey-id "$JOURNEY" \
  --skill-key summary-backup \
  --stage shown \
  --source recommendation

python3 scripts/log_skill_lifecycle.py record \
  --workspace /path/to/workspace \
  --journey-id "$JOURNEY" \
  --skill-key summary-backup \
  --stage started \
  --source recommendation

python3 scripts/log_skill_lifecycle.py record \
  --workspace /path/to/workspace \
  --journey-id "$JOURNEY" \
  --skill-key summary-backup \
  --stage completed \
  --source recommendation \
  --duration-bucket 10s_60s \
  --output-kind file
```

Generate an aggregate report:

```bash
python3 scripts/generate_skill_lifecycle_report.py --workspace /path/to/workspace
```

## Failure behavior

- New writes validate exact fields and lifecycle transitions, lock the store, and fail closed.
- Exact semantic retries return `duplicate` and do not append another line.
- A writer refuses to append when the existing store is malformed or transition-invalid; do not silently rewrite production telemetry.
- Reporting is read-only and fail-soft for malformed, duplicate, and transition-anomalous legacy lines; each category is counted.
- Symlinked event stores and report outputs are rejected.

## Operational boundary

The CLI does not install or enable hooks, modify Gateway/Cron, send notifications, migrate old telemetry, or upload reports. Production adapters require a separate privacy and rollout decision.
