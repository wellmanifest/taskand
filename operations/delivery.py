"""Pure reference evaluator; no Git, network, lease, approval or effect authority."""
from __future__ import annotations

import argparse
import errno
import functools
import hashlib
import json
import os
import re
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas/delivery-observation.v1.json"
)
MAX_OBSERVATION_BYTES = 1_048_576
_RFC3339_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
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


def _read_regular_json(path: Path, max_bytes: int = MAX_OBSERVATION_BYTES) -> Any:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.EISDIR):
            raise ValueError("Expected regular schema file without symlinks") from exc
        raise
    try:
        st = os.fstat(fd)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise ValueError("Expected regular schema file without symlinks")
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
    return json.loads(
        b"".join(chunks).decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_nonfinite_json,
    )


@functools.lru_cache(maxsize=1)
def _bundled_schema() -> dict[str, Any]:
    schema = _read_regular_json(SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise TypeError("Bundled schema root must be a JSON object")
    return schema


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
        raise ValueError("Expected an offset-aware timestamp")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Expected an offset-aware timestamp")
    return result


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
        if len(value) < schema.get("minLength", 0):
            raise ValueError("Empty reference")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise ValueError("Invalid reference syntax")
        if schema.get("format") == "date-time":
            timestamp(value)
    elif kind == "integer" and not schema["minimum"] <= value <= schema["maximum"]:
        raise ValueError("Invalid observation bound")


def recovery_route(incident: dict[str, Any], current: datetime) -> tuple[str, str]:
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
        if incident["retryAfter"] is None or current < timestamp(
            incident["retryAfter"]
        ):
            return "WAIT_RETRY_WINDOW", "TKD-RECOVERY-BACKOFF"
        return "RETRY_CANDIDATE", "TKD-RECOVERY-RETRY"
    return "PLAN_BOUNDED_REPAIR", "TKD-RECOVERY-PLAN"


def _is_unsafe_material_path(path: str) -> bool:
    posix = PurePosixPath(path)
    return bool(
        posix.as_posix() != path
        or path == "."
        or path.startswith("/")
        or ".." in posix.parts
        or any(ord(c) < 32 or ord(c) == 127 for c in path)
        or re.match(r"^[a-zA-Z]:", path)
    )


def evaluate(observation: dict[str, Any], *, now: str) -> dict[str, Any]:
    validate(observation, _bundled_schema())
    current = timestamp(now)
    observed = timestamp(observation["observedAt"])
    progress = timestamp(observation["lastProgressAt"])
    if progress > observed:
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
    age = (current - observed).total_seconds()
    due = (current - progress).total_seconds() >= observation["checkpointSeconds"]
    request = observation["request"]
    fresh = 0 <= age <= observation["maxObservationAgeSeconds"]
    pushed = fresh and known and remote["headSha"] == observation["subject"]["headSha"]
    pr_matches = (
        fresh and known and remote["prHeadSha"] == observation["subject"]["headSha"]
    )
    verified = checks["governance"] == checks["tests"] == "PASS"

    if age < 0 or age > observation["maxObservationAgeSeconds"]:
        route, code = "REOBSERVE", "TKD-DELIVERY-STALE"
    elif checks["ownership"] != "VERIFIED":
        route, code = "RECONCILE_OWNER", "TKD-DELIVERY-OWNER"
    elif checks["adoption"] != "VERIFIED":
        route, code = "RECONCILE_ADOPTION", "TKD-DELIVERY-ADOPTION"
    elif incident:
        route, code = recovery_route(incident, current)
    elif not known:
        route, code = "REOBSERVE", "TKD-DELIVERY-REMOTE"
    elif observation["overlappingDeliveries"]:
        route, code = "FINISH_EXISTING", "TKD-DELIVERY-OVERLAP"
    elif len(material) > observation["maxMaterialFiles"]:
        route, code = "SPLIT_WITH_PRESERVATION", "TKD-DELIVERY-BUDGET"
    elif (
        checks["deliveryController"] != "READY"
        and observation["publicationAuthorized"]
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

    # Bind the clock as well as the observation: replay at another time differs.
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
        )
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
    return 0  # Successful evaluation, not permission or an applied effect.


if __name__ == "__main__":
    sys.exit(main())
