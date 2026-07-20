# Company-Adaptive OpenClaw

公司級 OpenClaw 自適應導入流程：用固定 schema 與 deterministic scripts 維護 company / department / user / workflow 四層 profile，降低不同 LLM 對執行結果的影響。

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

