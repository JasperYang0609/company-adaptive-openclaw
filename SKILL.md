---
name: company-adaptive-openclaw
description: "Set up and maintain company, department, user, and workflow profiles for adaptive OpenClaw deployments."
---

# Company-Adaptive OpenClaw

Use when installing, auditing, or improving OpenClaw usage adaptation for a company or small team.

## Runtime rule

Do not directly edit official profiles from free-form reasoning. Use deterministic scripts:

- install: `scripts/install_profile_tree.py`
- validate: `scripts/validate_profiles.py`
- apply diff: `scripts/apply_profile_diff.py`
- rollback: `scripts/rollback_profile.py`
- nightly learning: `scripts/nightly_learn.py`
- self repair: `scripts/self_repair_check.py`

## Four profile layers

- Company: org, data sources, RLS/safety rules.
- Department: channels, common workflows, pinned prompts, sensitive boundaries.
- User: response preferences, common tasks, correction history.
- Workflow: trigger examples, required inputs, data sources, output format, validation, failure report.

## Safety

- Low-risk preferences may auto-apply after schema validation.
- Identity, department, permissions, RLS, secrets, sensitive raw details, external sends, and system config changes never auto-apply.
- If uncertain, produce a pending diff, not a profile write.
