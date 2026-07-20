from __future__ import annotations
import json, shutil, time
from pathlib import Path

SAFE_ROOT = "adaptive-openclaw"
FORBIDDEN_PATH_HINTS = [
    "identity", "department", "permission", "rls", "api", "token", "password", "secret", "credential",
    "salary", "payroll", "customer_pii", "medical", "contract", "external_send", "gateway", "cron"
]

def root(workspace: str | Path) -> Path:
    return Path(workspace).expanduser().resolve() / SAFE_ROOT

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def snapshot(workspace: str | Path) -> Path:
    r = root(workspace)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = r / "history" / "profiles" / ts
    dest = base
    i = 1
    while dest.exists():
        i += 1
        dest = r / "history" / "profiles" / f"{ts}_{i}"
    for name in ["profiles"]:
        src = r / name
        if src.exists():
            shutil.copytree(src, dest / name)
    return dest

def is_forbidden_diff(diff: dict) -> bool:
    if diff.get("risk_level") in {"high", "forbidden"}:
        return True
    path = str(diff.get("path", "")).lower()
    return any(h in path for h in FORBIDDEN_PATH_HINTS)
