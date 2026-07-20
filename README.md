# Company-Adaptive OpenClaw

公司級 OpenClaw 自適應導入流程：用固定 schema 與 deterministic scripts 維護 company / department / user / workflow 四層 profile，降低不同 LLM 對執行結果的影響。


## Current status

**Alpha / safe MVP.** This repository is safe to install because the first version only creates profile folders, templates, schemas, and deterministic scripts. It does **not** automatically enable OpenClaw runtime hooks or cron jobs.

What works now:

- Manual profile tree installation
- Profile structure validation
- Usage event logging by explicit script call
- Nightly diff generation by explicit script call
- Low-risk diff apply / reject gate
- Profile snapshot and rollback script
- Local OpenClaw skill instructions

Not enabled yet:

- Automatic Discord/message monitoring
- Runtime prompt/profile injection hooks
- Scheduled cron execution
- Production customer wizard

Customer install guidance:

- OK for pilot setup, schema review, and manual testing.
- Do not sell/describe it as fully automatic until hooks + cron pass integration tests.
- To avoid model-dependent behavior, keep all writes routed through scripts; do not ask an LLM to edit profiles directly.

## Modes

- `solo_team`: 小團隊 / 內部使用，不啟用 RLS。
- `client_standard`: 對外 6-15 人團隊，啟用 RLS 與敏感資料邊界。

## Quick install

```bash
python3 scripts/install_profile_tree.py --workspace /path/to/openclaw/workspace --mode solo_team --company-name "Ansai Internal"
python3 scripts/validate_profiles.py --workspace /path/to/openclaw/workspace
```

## Deterministic contract

LLM 不直接改正式 profile；只能產生 schema-bound `profile_diff`。正式寫入由 scripts 驗證、snapshot、apply、rollback。

