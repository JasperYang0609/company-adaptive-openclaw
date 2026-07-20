# Status

Current release status: **v1.0 automatic deliverable**.

## Safe for customer installation?

Yes, if installed with the documented opt-in commands.

The automatic components are reversible:

- Hooks can be disabled with `openclaw hooks disable`.
- Nightly scheduler can be unloaded with `launchctl unload` on macOS.
- Profile changes can be reverted with `rollback_profile.py`.

## Included automatic components

- `company-adaptive-logger`: records redacted usage events from `message:received` and `message:sent`.
- `company-adaptive-bootstrap`: injects bounded adaptive profile context during `agent:bootstrap`.
- `nightly_company_adaptive.sh`: runs nightly learning, self-repair, adoption report, low-risk apply, and validation.

## Production safety boundaries

- LLMs do not directly edit official profiles.
- All writes go through deterministic scripts.
- High-risk paths are rejected or pending.
- Sensitive raw details are redacted / summarized.
- Hooks and cron are opt-in and can be disabled.
