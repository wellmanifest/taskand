"""Pure reference evaluator; no Git, network, lease, approval or effect authority."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas/delivery-observation.v1.json"


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        raise ValueError("Expected an offset-aware timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Expected an offset-aware timestamp")
    return result


def validate(value, schema):
    """Validate only this bundled closed schema vocabulary, without remote refs."""
    supported = {"$schema", "$id", "title", "type", "additionalProperties", "required",
                 "properties", "enum", "const", "pattern", "format", "minimum",
                 "maximum", "oneOf", "items", "maxItems", "uniqueItems", "minLength"}
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
    expected = {"object": dict, "array": list, "string": str, "integer": int,
                "boolean": bool, "null": type(None)}
    if kind and (kind not in expected or type(value) is not expected[kind]):
        raise ValueError("Invalid transport type")
    if kind == "object":
        if set(value) != set(schema["required"]):
            raise ValueError("Missing or unknown observation field")
        for key, child in schema["properties"].items():
            validate(value[key], child)
    elif kind == "array":
        if len(value) > schema["maxItems"]:
            raise ValueError("Observation array exceeds its bound")
        for child in value:
            validate(child, schema["items"])
        if schema.get("uniqueItems") and len(value) != len(set(value)):
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


def recovery_route(incident, current):
    """Route observed incidents, never perform a repair or reset their ledger."""
    kind = incident["kind"]
    if kind == "UNKNOWN_EFFECT":
        return "RECONCILE_EFFECT", "TKD-RECOVERY-EFFECT"
    if kind == "REGRESSION":
        return "QUARANTINE_CANDIDATE", "TKD-RECOVERY-REGRESSION"
    if kind == "AUTHORITY_GAP":
        return "WAIT_RECOVERY_AUTHORITY", "TKD-RECOVERY-AUTHORITY"
    if (incident["attemptsUsed"] >= incident["maxAttempts"]
            or incident["noProgressAttempts"] >= incident["maxNoProgressAttempts"]):
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
        if incident["retryAfter"] is None or current < timestamp(incident["retryAfter"]):
            return "WAIT_RETRY_WINDOW", "TKD-RECOVERY-BACKOFF"
        return "RETRY_CANDIDATE", "TKD-RECOVERY-RETRY"
    return "PLAN_BOUNDED_REPAIR", "TKD-RECOVERY-PLAN"


def evaluate(observation, *, now):
    validate(observation, json.loads(SCHEMA_PATH.read_text()))
    current = timestamp(now)
    observed = timestamp(observation["observedAt"])
    progress = timestamp(observation["lastProgressAt"])
    if progress > observed:
        raise ValueError("Publication progress cannot occur after observation")
    incident = observation["recovery"]
    if incident and incident["noProgressAttempts"] > incident["attemptsUsed"]:
        raise ValueError("No-progress attempts cannot exceed all attempts")
    material = set().union(*observation["material"].values())
    if any(PurePosixPath(path).as_posix() != path or path == "." or any(ord(c) < 32 for c in path)
           or re.match(r"^[a-zA-Z]:", path) for path in material):
        raise ValueError("Material paths must be canonical repository-relative paths")
    dirty = set().union(*(observation["material"][key]
                          for key in ("staged", "unstaged", "untracked")))
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
    pr_matches = fresh and known and remote["prHeadSha"] == observation["subject"]["headSha"]
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
    elif checks["deliveryController"] != "READY" and observation["publicationAuthorized"]:
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
        elif not known:
            route, code = "REOBSERVE", "TKD-DELIVERY-REMOTE"
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
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema": "taskand.delivery-decision/v1", "inputDigest": "sha256:" + digest,
            "evaluatedAt": now, "subject": observation["subject"], "route": route,
            "diagnostic": code, "grantsAuthority": False, "effects": [],
            "materialFileCount": len(material), "checkpointDue": due,
            "workingTreeDirty": bool(dirty), "headPushed": pushed,
            "workingTreePublished": pushed and not dirty, "prMatchesHead": pr_matches,
            "mergeVerified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--now", help="Explicit replay clock (RFC3339)")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError("Observation exceeds 1 MiB")
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON field")
                result[key] = value
            return result
        data = json.loads(raw, object_pairs_hook=unique_object)
        result = evaluate(data, now=args.now or datetime.now(timezone.utc).isoformat())
    except (ValueError, TypeError, RecursionError):
        print(json.dumps({"schema": "taskand.delivery-decision/v1", "route": "REOBSERVE",
                          "diagnostic": "TKD-DELIVERY-INVALID", "grantsAuthority": False,
                          "effects": []}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0  # Successful evaluation, not permission or an applied effect.


if __name__ == "__main__":
    sys.exit(main())
