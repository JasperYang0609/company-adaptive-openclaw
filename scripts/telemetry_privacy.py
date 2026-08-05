from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any, Iterator


SURROGATE_MIN = 0xD800
SURROGATE_MAX = 0xDFFF


def normalize_text(value: Any) -> str:
    """Return valid Unicode scalar text, replacing lone surrogate code points."""
    text = str(value or "")
    return "".join("\uFFFD" if SURROGATE_MIN <= ord(char) <= SURROGATE_MAX else char for char in text)


def normalize_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {normalize_text(key): normalize_json_value(item) for key, item in value.items()}
    return value


def contains_lone_surrogate(value: Any) -> bool:
    if isinstance(value, str):
        return any(SURROGATE_MIN <= ord(char) <= SURROGATE_MAX for char in value)
    if isinstance(value, list):
        return any(contains_lone_surrogate(item) for item in value)
    if isinstance(value, dict):
        return any(contains_lone_surrogate(key) or contains_lone_surrogate(item) for key, item in value.items())
    return False


def dumps_json_line(value: Any) -> str:
    line = json.dumps(normalize_json_value(value), ensure_ascii=False, separators=(",", ":"))
    # Validate the exact serialized representation before appending it to JSONL.
    json.loads(line)
    line.encode("utf-8", errors="strict")
    return line


def iter_valid_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any] | None, str | None]]:
    if not path.exists():
        return
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                decoded = raw_line.decode("utf-8", errors="strict")
                parsed = json.loads(decoded)
                if not isinstance(parsed, dict):
                    raise ValueError("event is not a JSON object")
                if contains_lone_surrogate(parsed):
                    raise ValueError("event contains a lone Unicode surrogate")
                yield line_number, parsed, None
            except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
                yield line_number, None, type(exc).__name__


def load_or_create_export_salt(adaptive_root: Path) -> bytes:
    salt_path = adaptive_root / "config" / "telemetry_export_salt"
    salt_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        salt = salt_path.read_bytes()
    except FileNotFoundError:
        salt = secrets.token_bytes(32)
        try:
            fd = os.open(salt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(salt)
        except FileExistsError:
            salt = salt_path.read_bytes()
    try:
        os.chmod(salt_path, 0o600)
    except OSError:
        pass
    if len(salt) < 16:
        raise ValueError("telemetry export salt must be at least 16 bytes")
    return salt


def pseudonymous_alias(kind: str, raw_value: Any, salt: bytes) -> str:
    value = normalize_text(raw_value).strip() or "unknown"
    digest = hmac.new(salt, f"{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    prefix = {"sender": "usr", "channel": "chn", "parent_channel": "chn"}.get(kind, "id")
    return f"{prefix}_{digest}"
