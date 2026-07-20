# Deterministic Contract

To avoid model-dependent behavior:

1. LLM output is advisory only unless it validates as `profile_diff`.
2. All profile writes go through `apply_profile_diff.py`.
3. High-risk paths are denied even when `auto_apply=true`.
4. Every write snapshots the previous profile tree.
5. Validation must pass after writes or rollback is automatic.
6. Nightly jobs failing validation must not modify profiles.
