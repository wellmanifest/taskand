"""Pure reference evaluator; no Git, network, lease, approval or effect authority."""

from __future__ import annotations

import argparse
import errno
import functools
import hashlib
import json
import math
import os
import re
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas/delivery-observation.v1.json"
)
MAX_OBSERVATION_BYTES = 1_048_576
_NS_PER_SECOND = 1_000_000_000
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_RFC3339_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[Tt](\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?([Zz]|[+-]\d{2}:\d{2})$",
    re.ASCII,
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def _reject_nonfinite_json(token: str) -> NoReturn:
    raise ValueError(f"Non-finite JSON constant: {token}")


def _parse_finite_float(token: str) -> float:
    val = float(token)
    if not math.isfinite(val):
        raise ValueError(f"Non-finite JSON float: {token}")
    return val


def _has_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)


def _reject_surrogates(value: Any) -> None:
    stack = [value]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            if _has_surrogate(cur):
                raise ValueError("Lone UTF-16 surrogate in JSON input")
        elif isinstance(cur, dict):
            for key, item in cur.items():
                if isinstance(key, str) and _has_surrogate(key):
                    raise ValueError("Lone UTF-16 surrogate in JSON key")
                stack.append(item)
        elif isinstance(cur, list):
            stack.extend(cur)


def _check_no_symlink_path(path: str | Path) -> Path:
    raw_path = os.fspath(path)
    if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
        raise ValueError("Expected regular schema file without symlinks")
    path_obj = Path(raw_path)
    cur = Path(path_obj.anchor) if path_obj.is_absolute() else Path.cwd()
    walk_parts = path_obj.parts[1:] if path_obj.is_absolute() else path_obj.parts
    if not path_obj.is_absolute():
        if len(cur.parts) > 2 and cur.is_symlink():
            raise ValueError("Expected regular schema file without symlinks")
        for anc in cur.parents:
            if len(anc.parts) > 2 and anc.is_symlink():
                raise ValueError("Expected regular schema file without symlinks")
    for part in walk_parts:
        if part in ("", "."):
            continue
        if part == "..":
            cur = cur.parent
            continue
        cur = cur / part
        if len(cur.parts) > 2 and cur.is_symlink():
            raise ValueError("Expected regular schema file without symlinks")
    abs_path = Path(os.path.abspath(raw_path))
    if abs_path.is_symlink():
        raise ValueError("Expected regular schema file without symlinks")
    for anc in abs_path.parents:
        if len(anc.parts) > 2 and anc.is_symlink():
            raise ValueError("Expected regular schema file without symlinks")
    return abs_path


def _read_regular_json(path: Path, max_bytes: int = MAX_OBSERVATION_BYTES) -> Any:
    abs_path = _check_no_symlink_path(path)
    try:
        before = os.lstat(abs_path)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.EISDIR):
            raise ValueError("Expected regular schema file without symlinks") from exc
        raise
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("Expected regular schema file without symlinks")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(abs_path, flags)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.EISDIR):
            raise ValueError("Expected regular schema file without symlinks") from exc
        raise
    try:
        st = os.fstat(fd)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise ValueError("Expected regular schema file without symlinks")
        if (before.st_dev, before.st_ino) != (st.st_dev, st.st_ino):
            raise ValueError("Schema file inode changed during open")
        if st.st_size > max_bytes:
            raise ValueError("Schema exceeds byte limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("Schema exceeds byte limit")
            chunks.append(chunk)
    finally:
        os.close(fd)
    decoded = json.loads(
        b"".join(chunks).decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_nonfinite_json,
        parse_float=_parse_finite_float,
    )
    _reject_surrogates(decoded)
    return decoded


@functools.lru_cache(maxsize=1)
def _bundled_schema() -> dict[str, Any]:
    schema = _read_regular_json(SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise TypeError("Bundled schema root must be a JSON object")
    return schema


def _parse_rfc3339(value: Any) -> tuple[datetime, int]:
    if not isinstance(value, str):
        raise TypeError("Expected an offset-aware timestamp")
    match = _RFC3339_RE.fullmatch(value)
    if match is None:
        raise ValueError("Expected an offset-aware timestamp")
    date_part, time_part, frac_part, offset_part = match.groups()
    if offset_part == "-00:00":
        raise ValueError("Unknown local offset -00:00 is not permitted")
    normalized_offset = "+00:00" if offset_part in ("Z", "z") else offset_part
    base = datetime.fromisoformat(f"{date_part}T{time_part}{normalized_offset}")
    if base.tzinfo is None:
        raise ValueError("Expected an offset-aware timestamp")
    nanos = int(frac_part.ljust(9, "0")) if frac_part else 0
    epoch_ns = ((base - _UNIX_EPOCH) // timedelta(seconds=1)) * _NS_PER_SECOND + nanos
    return base.replace(microsecond=nanos // 1000), epoch_ns


def timestamp(value: Any) -> datetime:
    dt, _ = _parse_rfc3339(value)
    return dt


def _timestamp_ns(value: Any) -> int:
    _, epoch_ns = _parse_rfc3339(value)
    return epoch_ns


def _canonical_item_key(item: Any) -> str:
    return json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate(value: Any, schema: dict[str, Any]) -> None:
    """Validate only this bundled closed schema vocabulary, without remote refs."""
    if not isinstance(schema, dict):
        raise TypeError("Schema node must be a JSON object")
    supported = {
        "$schema",
        "$id",
        "title",
        "type",
        "additionalProperties",
        "required",
        "properties",
        "enum",
        "const",
        "pattern",
        "format",
        "minimum",
        "maximum",
        "oneOf",
        "items",
        "maxItems",
        "uniqueItems",
        "minLength",
    }
    if set(schema) - supported:
        raise ValueError("Unsupported bundled schema keyword")
    if "oneOf" in schema:
        matches = 0
        for part in schema["oneOf"]:
            try:
                validate(value, part)
                matches += 1
            except ValueError:
                pass
        if matches != 1:
            raise ValueError("Expected exactly one transport variant")
    if "const" in schema and value != schema["const"]:
        raise ValueError("Unsupported schema family")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("Unknown vocabulary value")
    kind = schema.get("type")
    expected = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    if kind and (kind not in expected or type(value) is not expected[kind]):
        raise ValueError("Invalid transport type")
    if kind == "object":
        required = set(schema.get("required", ()))
        properties = schema.get("properties", {})
        if any(_has_surrogate(k) for k in value if isinstance(k, str)):
            raise ValueError("Lone UTF-16 surrogate in object key")
        if not required <= value.keys():
            raise ValueError("Missing or unknown observation field")
        if (
            schema.get("additionalProperties") is False
            and not value.keys() <= properties.keys()
        ):
            raise ValueError("Missing or unknown observation field")
        for key, child in properties.items():
            if key in value:
                validate(value[key], child)
    elif kind == "array":
        if len(value) > schema["maxItems"]:
            raise ValueError("Observation array exceeds its bound")
        for child in value:
            validate(child, schema["items"])
        if schema.get("uniqueItems") and len(
            {_canonical_item_key(item) for item in value}
        ) != len(value):
            raise ValueError("Duplicate material path")
    elif kind == "string":
        if _has_surrogate(value):
            raise ValueError("Lone UTF-16 surrogate in string value")
        if len(value) < schema.get("minLength", 0):
            raise ValueError("Empty reference")
        if "pattern" in schema and not re.fullmatch(
            schema["pattern"], value, flags=re.ASCII
        ):
            raise ValueError("Invalid reference syntax")
        if schema.get("format") == "date-time":
            timestamp(value)
    elif kind == "integer" and not schema["minimum"] <= value <= schema["maximum"]:
        raise ValueError("Invalid observation bound")


def recovery_route(
    incident: dict[str, Any], current: datetime | int
) -> tuple[str, str]:
    """Route observed incidents, never perform a repair or reset their ledger."""
    kind = incident["kind"]
    if kind == "UNKNOWN_EFFECT":
        return "RECONCILE_EFFECT", "TKD-RECOVERY-EFFECT"
    if kind == "REGRESSION":
        return "QUARANTINE_CANDIDATE", "TKD-RECOVERY-REGRESSION"
    if kind == "AUTHORITY_GAP":
        return "WAIT_RECOVERY_AUTHORITY", "TKD-RECOVERY-AUTHORITY"
    if (
        incident["attemptsUsed"] >= incident["maxAttempts"]
        or incident["noProgressAttempts"] >= incident["maxNoProgressAttempts"]
    ):
        return "HALT_AFFECTED_SCOPE", "TKD-RECOVERY-EXHAUSTED"
    if incident["preservation"] != "VERIFIED":
        return "PRESERVE_RECOVERY", "TKD-RECOVERY-PRESERVATION"
    if kind == "UNKNOWN":
        return "DIAGNOSE_ONLY", "TKD-RECOVERY-UNKNOWN"
    if incident["twin"] == "FAIL":
        return "HALT_AFFECTED_SCOPE", "TKD-RECOVERY-TWIN-FAILED"
    if incident["twin"] != "PASS":
        return "REHEARSE_RECOVERY", "TKD-RECOVERY-TWIN"
    if kind == "TRANSIENT":
        if incident["retryAfter"] is None:
            return "WAIT_RETRY_WINDOW", "TKD-RECOVERY-BACKOFF"
        if isinstance(current, int):
            not_ready = current < _timestamp_ns(incident["retryAfter"])
        else:
            not_ready = current < timestamp(incident["retryAfter"])
        if not_ready:
            return "WAIT_RETRY_WINDOW", "TKD-RECOVERY-BACKOFF"
        return "RETRY_CANDIDATE", "TKD-RECOVERY-RETRY"
    return "PLAN_BOUNDED_REPAIR", "TKD-RECOVERY-PLAN"


def _is_unsafe_material_path(path: str) -> bool:
    posix = PurePosixPath(path)
    return bool(
        "\\" in path
        or posix.as_posix() != path
        or path == "."
        or path.startswith("/")
        or ".." in posix.parts
        or any(part != part.strip() for part in posix.parts)
        or any(
            ord(c) < 32
            or ord(c) == 127
            or 0x80 <= ord(c) <= 0x9F
            or 0xD800 <= ord(c) <= 0xDFFF
            for c in path
        )
        or re.match(r"^[a-zA-Z]:", path)
    )


def evaluate(observation: dict[str, Any], *, now: str) -> dict[str, Any]:
    validate(observation, _bundled_schema())
    current_ns = _timestamp_ns(now)
    observed_ns = _timestamp_ns(observation["observedAt"])
    progress_ns = _timestamp_ns(observation["lastProgressAt"])
    if progress_ns > observed_ns:
        raise ValueError("Publication progress cannot occur after observation")
    incident = observation["recovery"]
    if incident and incident["noProgressAttempts"] > incident["attemptsUsed"]:
        raise ValueError("No-progress attempts cannot exceed all attempts")
    material = set().union(*observation["material"].values())
    if any(_is_unsafe_material_path(path) for path in material):
        raise ValueError("Material paths must be canonical repository-relative paths")
    dirty = set().union(
        *(observation["material"][key] for key in ("staged", "unstaged", "untracked"))
    )
    checks, remote = observation["checks"], observation["remote"]
    known = remote["status"] == "OBSERVED"
    if not known and (remote["headSha"] or remote["prHeadSha"]):
        raise ValueError("Unknown remote observation cannot claim a SHA")
    if remote["prHeadSha"] and remote["prHeadSha"] != remote["headSha"]:
        raise ValueError("Inconsistent remote branch and PR observations; reobserve")
    age_ns = current_ns - observed_ns
    max_age_ns = observation["maxObservationAgeSeconds"] * _NS_PER_SECOND
    due = (current_ns - progress_ns) >= (
        observation["checkpointSeconds"] * _NS_PER_SECOND
    )
    request = observation["request"]
    fresh = 0 <= age_ns <= max_age_ns
    pushed = fresh and known and remote["headSha"] == observation["subject"]["headSha"]
    pr_matches = (
        fresh and known and remote["prHeadSha"] == observation["subject"]["headSha"]
    )
    verified = checks["governance"] == checks["tests"] == "PASS"

    if age_ns < 0 or age_ns > max_age_ns:
        route, code = "REOBSERVE", "TKD-DELIVERY-STALE"
    elif checks["ownership"] != "VERIFIED":
        route, code = "RECONCILE_OWNER", "TKD-DELIVERY-OWNER"
    elif checks["adoption"] != "VERIFIED":
        route, code = "RECONCILE_ADOPTION", "TKD-DELIVERY-ADOPTION"
    elif incident:
        route, code = recovery_route(incident, current_ns)
    elif not known:
        route, code = "REOBSERVE", "TKD-DELIVERY-REMOTE"
    elif observation["overlappingDeliveries"]:
        route, code = "FINISH_EXISTING", "TKD-DELIVERY-OVERLAP"
    elif len(material) > observation["maxMaterialFiles"]:
        route, code = "SPLIT_WITH_PRESERVATION", "TKD-DELIVERY-BUDGET"
    elif (
        checks["deliveryController"] != "READY" and observation["publicationAuthorized"]
    ):
        route, code = "RESTORE_DELIVERY", "TKD-DELIVERY-CONTROLLER"
    elif request == "START_NEW_SLICE" and material:
        route, code = "FINISH_EXISTING", "TKD-DELIVERY-PENDING"
    elif request == "ACTIVATE_GOVERNANCE" and (dirty or not verified):
        route, code = "RECONCILE_ADOPTION", "TKD-DELIVERY-ACTIVATION"
    elif due or observation["sliceComplete"] or request == "PUBLISH":
        if not verified:
            route, code = "PRESERVE_AND_VALIDATE", "TKD-DELIVERY-VALIDATION"
        elif not observation["publicationAuthorized"]:
            route, code = "WAIT_PUBLICATION_AUTHORITY", "TKD-DELIVERY-AUTHORITY"
        elif dirty:
            route, code = "COMMIT_CURRENT", "TKD-DELIVERY-UNCOMMITTED"
        elif not pushed:
            route, code = "PUSH_CURRENT", "TKD-DELIVERY-UNPUSHED"
        elif not pr_matches:
            route, code = "OPEN_OR_UPDATE_PR", "TKD-DELIVERY-NO-PR"
        else:
            route, code = "WAIT_PROTECTED_REVIEW", "TKD-DELIVERY-REVIEW"
    else:
        route, code = "CONTINUE_BOUNDED", "TKD-DELIVERY-BOUNDED"

    inputs = {"observation": observation, "evaluatedAt": now}
    digest = hashlib.sha256(
        json.dumps(
            inputs, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema": "taskand.delivery-decision/v1",
        "inputDigest": "sha256:" + digest,
        "evaluatedAt": now,
        "subject": observation["subject"],
        "route": route,
        "diagnostic": code,
        "grantsAuthority": False,
        "effects": [],
        "materialFileCount": len(material),
        "checkpointDue": due,
        "workingTreeDirty": bool(dirty),
        "headPushed": pushed,
        "workingTreePublished": pushed and not dirty,
        "prMatchesHead": pr_matches,
        "mergeVerified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--now", help="Explicit replay clock (RFC3339)")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_OBSERVATION_BYTES + 1)
        if len(raw) > MAX_OBSERVATION_BYTES:
            raise ValueError("Observation exceeds 1 MiB")
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite_json,
            parse_float=_parse_finite_float,
        )
        _reject_surrogates(data)
        result = evaluate(data, now=args.now or datetime.now(UTC).isoformat())
    except (ValueError, TypeError, RecursionError):
        print(
            json.dumps(
                {
                    "schema": "taskand.delivery-decision/v1",
                    "route": "REOBSERVE",
                    "diagnostic": "TKD-DELIVERY-INVALID",
                    "grantsAuthority": False,
                    "effects": [],
                }
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
