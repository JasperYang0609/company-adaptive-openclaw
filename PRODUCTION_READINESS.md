# Production Readiness Plan

Goal: turn `company-adaptive-openclaw` from a safe manual MVP into a customer-deliverable automatic package.

## Production definition

A production customer-deliverable version must satisfy all of these:

- Install wizard can create a company profile tree for a 6-15 person team.
- Runtime can identify sender and load only relevant company / department / user / workflow profile snippets.
- Interaction logger records events without storing secrets or sensitive raw details.
- Nightly job can generate profile/workflow diffs from events.
- Diff application is deterministic and schema-gated.
- High-risk fields are denied or pending, never auto-applied.
- Rollback restores the previous profile tree.
- Same fixture events produce the same applied profile results across supported LLMs, or differences stay pending.
- Customer can disable hooks/cron and fall back to manual mode.

## Milestones

### v0.2 — Deterministic core hardening

Deliverables:

- Complete JSON schemas for company / department / user / workflow profiles.
- Add tests for install, validate, event logging, diff generation, apply, reject, rollback.
- Add fixture datasets based on anonymized Like Group / Mifiya patterns.
- Add dry-run mode for all state-changing scripts.

Exit criteria:

- `python3 scripts/run_tests.py` passes.
- Forbidden diff test is rejected.
- Rollback test passes.

### v0.3 — Hook logger canary

Deliverables:

- OpenClaw plugin hook that observes inbound/agent end events and writes usage events.
- Hook must be configurable and disabled by default.
- Redaction rules before event write.
- Local canary mode for this OpenClaw only.

Exit criteria:

- 100 test messages produce expected usage events.
- No raw secrets or sensitive details stored in events.
- Disabling plugin stops event logging cleanly.

### v0.4 — Runtime profile loader canary

Deliverables:

- Runtime profile snippet selector.
- Token budget cap.
- Sender/channel/workflow relevance scoring.
- Injection disabled by default; canary allowlist only.

Exit criteria:

- Same request loads deterministic profile snippets.
- Irrelevant profiles are not loaded.
- Context injection stays under configured token budget.

### v0.5 — Nightly cron canary

Deliverables:

- Scheduled nightly learning command.
- Self-repair report.
- Adoption report.
- Apply only low-risk diffs.
- Failure leaves profile tree unchanged.

Exit criteria:

- 7 consecutive nightly canary runs pass.
- No high-risk write occurs.
- Failed run does not mutate profiles.

### v0.9 — Client pilot release

Deliverables:

- `client_standard` install wizard.
- RLS starter matrix.
- Customer onboarding questionnaire.
- Department pinned-prompt generator.
- Admin commands: show/reset/export profile.

Exit criteria:

- Pilot install on one non-critical customer workspace.
- Customer can review generated profiles.
- Manual disable / rollback verified.

### v1.0 — Production release

Deliverables:

- Versioned release tag.
- Installation guide.
- Operator safety guide.
- Troubleshooting guide.
- Upgrade/rollback guide.

Exit criteria:

- Full test suite pass.
- Canary logs reviewed.
- No known high-risk blocker.

## Release policy

- v0.x can be installed for pilot/manual testing only.
- v1.0 is the first version that may be described as a customer-deliverable automatic system.
- Hooks and cron must remain opt-in even after v1.0.
- Any write to identity, permission, RLS, secrets, external sends, or system config remains deny-by-default.

### v1.2 — Channel Onboarding Agent

Goal: make newly created customer Discord channels/threads self-onboarding.

Acceptance criteria:

- Channel/thread profiles are installed and validated by default.
- A deterministic script can create a redacted channel profile from channel id/name/category, creator id, creator role/position, permission boundary, and initial description.
- Runtime hints can detect a channel profile and steer the assistant to offer role-aware options instead of asking for a prompt.
- Nightly learning can update low-risk channel recommendations from usage events.
- Identity, permission, RLS, secrets, and sensitive raw details remain deny-by-default and must not auto-apply.
