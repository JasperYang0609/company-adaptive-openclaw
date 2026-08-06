"""Privacy-minimal Skill lifecycle telemetry primitives.

This module intentionally has no fields for sender, channel, session, message,
content, customer name, path, stack trace, or free-form error text.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from common import root
from telemetry_privacy import dumps_json_line

SCHEMA = "company-adaptive-skill-lifecycle/v1"
INSTRUMENTATION = "explicit_adapter"
STAGES = (
    "shown",
    "selected",
    "started",
    "completed",
    "failed",
    "abandoned",
    "corrected",
)
SOURCES = ("recommendation", "direct_request", "agent_route", "automation", "unknown")
REASON_CODES = (
    "none",
    "user_cancelled",
    "superseded",
    "timeout",
    "preflight_blocked",
    "unsupported",
    "permission_denied",
    "validation_failed",
    "tool_error",
    "provider_error",
    "delivery_failed",
    "user_correction",
    "unknown_failure",
)
DURATION_BUCKETS = (
    "not_recorded",
    "lt_1s",
    "1s_10s",
    "10s_60s",
    "1m_5m",
    "5m_30m",
    "gte_30m",
)
OUTPUT_KINDS = ("none", "text", "file", "external_write", "notification", "mixed")
EVENT_FIELDS = {
    "schema",
    "instrumentation",
    "event_id",
    "journey_id",
    "timestamp",
    "skill_key",
    "stage",
    "attempt",
    "source",
    "reason_code",
    "duration_bucket",
    "output_kind",
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
JOURNEY_RE = re.compile(r"^jrn_[0-9a-f]{32}$")
EVENT_ID_RE = re.compile(r"^lce_[0-9a-f]{16}$")
TERMINAL_STAGES = {"completed", "failed", "abandoned"}
FAILURE_REASONS = {
    "timeout",
    "preflight_blocked",
    "unsupported",
    "permission_denied",
    "validation_failed",
    "tool_error",
    "provider_error",
    "delivery_failed",
    "unknown_failure",
}
ABANDON_REASONS = {"user_cancelled", "superseded", "timeout"}


class LifecycleError(ValueError):
    pass


def new_journey_id() -> str:
    return "jrn_" + secrets.token_hex(16)


def event_id_for(
    salt: bytes,
    journey_id: str,
    skill_key: str,
    stage: str,
    attempt: int,
) -> str:
    payload = f"skill-lifecycle:{journey_id}:{skill_key}:{stage}:{attempt}".encode("ascii")
    return "lce_" + hmac.new(salt, payload, hashlib.sha256).hexdigest()[:16]


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def validate_slug(value: object, label: str) -> str:
    if not isinstance(value, str) or not SLUG_RE.fullmatch(value):
        raise LifecycleError(f"{label} must be a lowercase bounded slug")
    return value


def validate_timestamp(value: object) -> str:
    if not isinstance(value, str) or len(value) > 40:
        raise LifecycleError("timestamp is invalid")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleError("timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise LifecycleError("timestamp must include a timezone")
    return value


def validate_reason(stage: str, reason: str) -> None:
    if stage in {"shown", "selected", "started", "completed"} and reason != "none":
        raise LifecycleError(f"reason_code must be none for stage {stage}")
    if stage == "failed" and reason not in FAILURE_REASONS:
        raise LifecycleError("failed requires a bounded failure reason_code")
    if stage == "abandoned" and reason not in ABANDON_REASONS:
        raise LifecycleError("abandoned requires user_cancelled, superseded, or timeout")
    if stage == "corrected" and reason != "user_correction":
        raise LifecycleError("corrected requires reason_code user_correction")


def validate_event(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LifecycleError("event must be a JSON object")
    unknown = set(value) - EVENT_FIELDS
    missing = EVENT_FIELDS - set(value)
    if unknown or missing:
        raise LifecycleError(
            f"event field contract mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if value.get("schema") != SCHEMA:
        raise LifecycleError("unsupported lifecycle schema")
    if value.get("instrumentation") != INSTRUMENTATION:
        raise LifecycleError("unsupported instrumentation mode")
    if not isinstance(value.get("event_id"), str) or not EVENT_ID_RE.fullmatch(value["event_id"]):
        raise LifecycleError("event_id must be an opaque lifecycle id")
    if not isinstance(value.get("journey_id"), str) or not JOURNEY_RE.fullmatch(value["journey_id"]):
        raise LifecycleError("journey_id must be an opaque lifecycle id")
    validate_timestamp(value.get("timestamp"))
    validate_slug(value.get("skill_key"), "skill_key")
    stage = value.get("stage")
    source = value.get("source")
    reason = value.get("reason_code")
    duration = value.get("duration_bucket")
    output = value.get("output_kind")
    if stage not in STAGES:
        raise LifecycleError("stage is not allowed")
    if source not in SOURCES:
        raise LifecycleError("source is not allowed")
    if reason not in REASON_CODES:
        raise LifecycleError("reason_code is not allowed")
    if duration not in DURATION_BUCKETS:
        raise LifecycleError("duration_bucket is not allowed")
    if output not in OUTPUT_KINDS:
        raise LifecycleError("output_kind is not allowed")
    attempt = value.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or not 0 <= attempt <= 999:
        raise LifecycleError("attempt must be an integer from 0 to 999")
    if stage in {"shown", "selected", "started"} and (duration != "not_recorded" or output != "none"):
        raise LifecycleError(f"stage {stage} cannot claim duration or output")
    validate_reason(stage, reason)
    return dict(value)


def build_event(
    *,
    salt: bytes,
    journey_id: str,
    skill_key: str,
    stage: str,
    attempt: int = 0,
    source: str = "unknown",
    reason_code: str = "none",
    duration_bucket: str = "not_recorded",
    output_kind: str = "none",
) -> dict[str, Any]:
    event = {
        "schema": SCHEMA,
        "instrumentation": INSTRUMENTATION,
        "event_id": event_id_for(salt, journey_id, skill_key, stage, attempt),
        "journey_id": journey_id,
        "timestamp": utc_timestamp(),
        "skill_key": skill_key,
        "stage": stage,
        "attempt": attempt,
        "source": source,
        "reason_code": reason_code,
        "duration_bucket": duration_bucket,
        "output_kind": output_kind,
    }
    return validate_event(event)


def semantic_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key != "timestamp"}


def transition_error(prior: list[dict[str, Any]], event: dict[str, Any]) -> str | None:
    skill_keys = {str(item["skill_key"]) for item in prior}
    if skill_keys and skill_keys != {event["skill_key"]}:
        return "journey_id cannot span multiple skill_key values"

    operational: str | None = None
    terminal: str | None = None
    for item in prior:
        stage = str(item["stage"])
        if stage == "corrected":
            continue
        operational = stage
        if stage in TERMINAL_STAGES:
            terminal = stage

    stage = event["stage"]
    if stage == "corrected":
        return None if prior else "corrected requires an existing journey event"
    if terminal:
        return f"journey is already terminal at {terminal}"
    if stage == "shown":
        if operational is not None:
            return "shown must be the first operational stage"
    elif stage == "selected":
        if operational not in (None, "shown", "selected"):
            return "selected cannot follow the current operational stage"
    elif stage == "started":
        if operational not in (None, "shown", "selected"):
            return "started cannot follow the current operational stage"
    elif stage in {"completed", "failed"}:
        if operational != "started":
            return f"{stage} requires a prior started event"
    elif stage == "abandoned":
        if operational not in {"shown", "selected", "started"}:
            return "abandoned requires a non-terminal journey"
    return None


def ensure_private_directory(path: Path) -> None:
    if os.path.lexists(path):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise LifecycleError(f"telemetry directory is unsafe: {path.name}")
    else:
        path.mkdir(mode=0o700, parents=False)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def event_store(workspace: str | Path) -> Path:
    adaptive_root = root(workspace)
    workspace_root = adaptive_root.parent
    if not workspace_root.is_dir():
        raise LifecycleError("workspace must be a directory")
    ensure_private_directory(adaptive_root)
    events = adaptive_root / "events"
    ensure_private_directory(events)
    return events / "skill_lifecycle_events.jsonl"


def load_or_create_lifecycle_salt(workspace: str | Path) -> bytes:
    """Create/read the lifecycle HMAC salt under a private lock without partial-read races."""
    adaptive_root = event_store(workspace).parent.parent
    config = adaptive_root / "config"
    ensure_private_directory(config)
    salt_path = config / "skill_lifecycle_salt"
    lock_path = config / ".skill_lifecycle_salt.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        lock_fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise LifecycleError("cannot safely open lifecycle salt lock") from exc
    try:
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise LifecycleError("lifecycle salt lock is not a regular file")
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if os.path.lexists(salt_path):
            try:
                salt_fd = os.open(salt_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            except OSError as exc:
                raise LifecycleError("cannot safely open lifecycle salt") from exc
            try:
                if not stat.S_ISREG(os.fstat(salt_fd).st_mode):
                    raise LifecycleError("lifecycle salt is not a regular file")
                os.fchmod(salt_fd, 0o600)
                chunks: list[bytes] = []
                while chunk := os.read(salt_fd, 4096):
                    chunks.append(chunk)
                salt = b"".join(chunks)
            finally:
                os.close(salt_fd)
        else:
            salt = secrets.token_bytes(32)
            create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            try:
                salt_fd = os.open(salt_path, create_flags, 0o600)
            except OSError as exc:
                raise LifecycleError("cannot safely create lifecycle salt") from exc
            try:
                os.fchmod(salt_fd, 0o600)
                written = 0
                while written < len(salt):
                    written += os.write(salt_fd, salt[written:])
                os.fsync(salt_fd)
            finally:
                os.close(salt_fd)
        if len(salt) != 32:
            raise LifecycleError("lifecycle salt must be exactly 32 bytes")
        return salt
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


@contextmanager
def locked_store(path: Path) -> Iterator[None]:
    lock_path = path.parent / ".skill_lifecycle.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise LifecycleError("cannot safely open lifecycle lock") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise LifecycleError("lifecycle lock is not a regular file")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def read_store_bytes(path: Path) -> bytes:
    if not os.path.lexists(path):
        return b""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise LifecycleError("cannot safely open lifecycle event store") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise LifecycleError("lifecycle event store is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(fd, 1024 * 1024):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def parse_line(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LifecycleError("invalid lifecycle JSONL line") from exc
    return validate_event(value)


def strict_existing_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    by_journey: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line_number, raw in enumerate(read_store_bytes(path).splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            event = parse_line(raw)
        except LifecycleError as exc:
            raise LifecycleError(f"existing lifecycle store is invalid at line {line_number}") from exc
        prior_same_id = seen.get(event["event_id"])
        if prior_same_id is not None:
            if semantic_event(prior_same_id) != semantic_event(event):
                raise LifecycleError(f"conflicting lifecycle event_id at line {line_number}")
            continue
        anomaly = transition_error(by_journey[event["journey_id"]], event)
        if anomaly:
            raise LifecycleError(f"existing lifecycle transition is invalid at line {line_number}: {anomaly}")
        seen[event["event_id"]] = event
        by_journey[event["journey_id"]].append(event)
        events.append(event)
    return events


def append_event(workspace: str | Path, event: dict[str, Any]) -> str:
    event = validate_event(event)
    path = event_store(workspace)
    with locked_store(path):
        existing = strict_existing_events(path)
        for prior in existing:
            if prior["event_id"] != event["event_id"]:
                continue
            if semantic_event(prior) == semantic_event(event):
                return "duplicate"
            raise LifecycleError("event id collision or idempotency payload mismatch")
        journey_events = [item for item in existing if item["journey_id"] == event["journey_id"]]
        anomaly = transition_error(journey_events, event)
        if anomaly:
            raise LifecycleError(anomaly)

        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags, 0o600)
        except OSError as exc:
            raise LifecycleError("cannot safely append lifecycle event") from exc
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise LifecycleError("lifecycle event store is not a regular file")
            encoded = (dumps_json_line(event) + "\n").encode("utf-8", errors="strict")
            written = 0
            while written < len(encoded):
                written += os.write(fd, encoded[written:])
            os.fsync(fd)
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
    return "written"


def analyze_store(path: Path) -> dict[str, Any]:
    invalid_lines = 0
    duplicate_events = 0
    transition_anomalies = 0
    seen: dict[str, dict[str, Any]] = {}
    by_journey: dict[str, list[dict[str, Any]]] = defaultdict(list)
    accepted: list[dict[str, Any]] = []

    if os.path.lexists(path):
        raw_data = read_store_bytes(path)
    else:
        raw_data = b""
    for raw in raw_data.splitlines():
        if not raw.strip():
            continue
        try:
            event = parse_line(raw)
        except LifecycleError:
            invalid_lines += 1
            continue
        prior = seen.get(event["event_id"])
        if prior is not None:
            duplicate_events += 1
            continue
        seen[event["event_id"]] = event
        journey_events = by_journey[event["journey_id"]]
        anomaly = transition_error(journey_events, event)
        if anomaly:
            transition_anomalies += 1
            continue
        journey_events.append(event)
        accepted.append(event)

    stage_journeys: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    reason_counts: dict[str, Counter[str]] = defaultdict(Counter)
    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for event in accepted:
        skill = event["skill_key"]
        stage_journeys[skill][event["stage"]].add(event["journey_id"])
        reason_counts[skill][event["reason_code"]] += 1
        source_counts[skill][event["source"]] += 1

    skills: dict[str, Any] = {}
    for skill in sorted(stage_journeys):
        skills[skill] = {
            "journeys_by_stage": {
                stage: len(stage_journeys[skill].get(stage, set())) for stage in STAGES
            },
            "reason_events": dict(sorted(reason_counts[skill].items())),
            "source_events": dict(sorted(source_counts[skill].items())),
        }
    return {
        "schema": "company-adaptive-skill-lifecycle-report/v1",
        "coverage": "explicit_adapter_only",
        "privacy": "aggregate categorical counts; no raw identifiers, content, event ids, or journey ids",
        "stats": {
            "accepted_events": len(accepted),
            "unique_journeys": len({event["journey_id"] for event in accepted}),
            "invalid_lines": invalid_lines,
            "duplicate_events": duplicate_events,
            "transition_anomalies": transition_anomalies,
        },
        "skills": skills,
    }
