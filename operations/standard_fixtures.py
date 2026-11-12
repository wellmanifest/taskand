"""Shared schema fixture checker and evolution/app-state contract test cases for wellmanifest/taskand."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_RFC3339_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[Tt](\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?([Zz]|[+-]\d{2}:\d{2})$",
    re.ASCII,
)


def fixture_valid(value: Any, schema: dict[str, Any], root: dict[str, Any]) -> bool:
    """Offline fixture checker for the keywords used here, not a JSON Schema runtime."""
    if "$ref" in schema:
        if not schema["$ref"].startswith("#/$defs/"):
            raise AssertionError("Unexpected external schema retrieval")
        return fixture_valid(value, root["$defs"][schema["$ref"].split("/")[-1]], root)
    if (
        "oneOf" in schema
        and sum(fixture_valid(value, part, root) for part in schema["oneOf"]) != 1
    ):
        return False
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return False
        if not set(schema.get("required", [])) <= value.keys():
            return False
        if (
            schema.get("additionalProperties") is False
            and not value.keys() <= schema["properties"].keys()
        ):
            return False
        if any(
            not fixture_valid(v, schema["properties"][k], root)
            for k, v in value.items()
            if k in schema.get("properties", {})
        ):
            return False
    elif kind == "array":
        if not isinstance(value, list) or len(value) > schema.get(
            "maxItems", float("inf")
        ):
            return False
        if schema.get("uniqueItems") and len(
            {json.dumps(v, sort_keys=True) for v in value}
        ) != len(value):
            return False
        if any(not fixture_valid(v, schema["items"], root) for v in value):
            return False
    elif kind == "string":
        if not isinstance(value, str) or len(value) < schema.get("minLength", 0):
            return False
        if "pattern" in schema and not re.search(
            schema["pattern"], value, flags=re.ASCII
        ):
            return False
        if schema.get("format") == "date-time":
            m = _FIXTURE_RFC3339_RE.fullmatch(value)
            if m is None or m.group(4) == "-00:00":
                return False
            d_part, t_part, f_part, off_part = m.groups()
            norm_off = "+00:00" if off_part in ("Z", "z") else off_part
            micro = f".{f_part.ljust(6, '0')[:6]}" if f_part else ""
            try:
                if (
                    datetime.fromisoformat(f"{d_part}T{t_part}{micro}{norm_off}").tzinfo
                    is None
                ):
                    return False
            except ValueError:
                return False
    elif kind == "integer":
        if type(value) is not int or not schema.get(
            "minimum", -float("inf")
        ) <= value <= schema.get("maximum", float("inf")):
            return False
    elif (kind == "null" and value is not None) or (
        kind == "boolean" and type(value) is not bool
    ):
        return False
    return True


class EvolutionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (ROOT / "schemas/envelope.v2.json").read_text(encoding="utf-8")
        )

    def ref(self, name: str = "test") -> dict[str, str]:
        return {"uri": "urn:test:" + name, "digest": "sha256:" + "a" * 64}

    def request(self) -> dict[str, Any]:
        return {
            "schema": "taskand.task-request/v1",
            "id": "urn:test:request",
            "kind": "COMMAND",
            "correlationRef": "urn:test:correlation",
            "causationRef": None,
            "operation": self.ref("operation"),
            "payload": self.ref("payload"),
            "dsl": {
                "mode": "REQUEST_ONLY",
                "artifact": self.ref("dsl"),
                "schema": self.ref("schema"),
                "grammar": self.ref("grammar"),
            },
            "contextRefs": [],
            "authorityRef": "authorization:test",
            "idempotencyKey": "test-only",
            "budget": {
                "maxSteps": 3,
                "maxAttempts": 2,
                "maxChildren": 0,
                "maxDepth": 0,
                "deadline": "2026-09-13T12:00:00Z",
            },
        }

    def event(self) -> dict[str, Any]:
        return {
            "specversion": "1.0",
            "id": "test",
            "source": "proc://test/observer/v1",
            "type": "taskand.execution.observed.v1",
            "time": "2026-09-13T12:00:00Z",
            "datacontenttype": "application/json",
            "dataschema": "urn:taskand:schema:envelope:v2#log-data",
            "correlationid": "urn:test:correlation",
            "requestref": "urn:test:request",
            "data": {
                "schema": "taskand.log-event/v1",
                "eventRef": "urn:test:event",
                "subjectRef": "proc://test/worker/v1",
                "result": "BLOCKED",
                "code": "MISSING_TWIN",
                "evidenceRefs": [self.ref("evidence")],
            },
        }

    def valid(self, obj: Any) -> bool:
        return fixture_valid(obj, self.schema, self.schema)

    def test_request_and_event_are_disjoint(self) -> None:
        self.assertTrue(self.valid(self.request()))
        self.assertTrue(self.valid(self.event()))
        self.assertFalse(
            fixture_valid(
                self.event(), self.schema["$defs"]["taskRequest"], self.schema
            )
        )
        self.assertFalse(
            fixture_valid(self.request(), self.schema["$defs"]["logEvent"], self.schema)
        )

    def test_every_layer_closed_and_versioned(self) -> None:
        for target in ((), ("dsl",), ("dsl", "artifact"), ("budget",), ("operation",)):
            obj = self.request()
            part: Any = obj
            for key in target:
                part = part[key]
            part["unrecognized"] = True
            self.assertFalse(self.valid(obj), target)
        obj = self.request()
        obj["schema"] = "taskand.task-request/v2"
        self.assertFalse(self.valid(obj))

    def test_dsl_grammar_and_digest_required(self) -> None:
        for field in ("artifact", "schema", "grammar"):
            obj = self.request()
            del obj["dsl"][field]
            self.assertFalse(self.valid(obj))
        obj = self.request()
        obj["dsl"]["mode"] = "EXECUTE"
        self.assertFalse(self.valid(obj))
        obj = self.request()
        obj["payload"]["digest"] = "latest"
        self.assertFalse(self.valid(obj))

    def test_cloud_event_does_not_carry_nested_extensions_or_authority(self) -> None:
        obj = self.event()
        obj["taskand"] = {"authorize": True}
        self.assertFalse(self.valid(obj))
        obj = self.event()
        obj["data"]["authorityRef"] = "authorization:forged"
        self.assertFalse(self.valid(obj))
        obj = self.event()
        obj["correlationid"] = {"id": "urn:test:x"}
        self.assertFalse(self.valid(obj))

    def test_budgets_and_reference_syntax(self) -> None:
        for key, value in [
            ("maxAttempts", 0),
            ("maxChildren", 33),
            ("maxDepth", True),
            ("deadline", "yesterday"),
        ]:
            obj = self.request()
            obj["budget"][key] = value
            self.assertFalse(self.valid(obj), key)
        obj = self.request()
        obj["contextRefs"] = [self.ref(), self.ref()]
        self.assertFalse(self.valid(obj))
        obj = self.request()
        obj["operation"]["uri"] = "not a URI"
        self.assertFalse(self.valid(obj))

    def test_bundle_contains_complete_normative_graph(self) -> None:
        bundle = json.loads((ROOT / "bundle.json").read_text(encoding="utf-8"))
        for path in (ROOT / "schemas").glob("*.json"):
            self.assertIn(path.relative_to(ROOT).as_posix(), bundle["files"])
        for path in [
            "docs/information/evolution.md",
            "docs/standard.md",
            "operations/bundle.py",
        ]:
            self.assertIn(path, bundle["files"])
        for path, digest in bundle["files"].items():
            self.assertEqual(
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path
            )

    def test_fixture_checker_covers_all_used_keywords(self) -> None:
        supported = {
            "$schema",
            "$id",
            "$anchor",
            "$defs",
            "$ref",
            "title",
            "oneOf",
            "type",
            "const",
            "enum",
            "properties",
            "required",
            "additionalProperties",
            "items",
            "uniqueItems",
            "maxItems",
            "minLength",
            "pattern",
            "format",
            "minimum",
            "maximum",
        }

        def check(schema: dict[str, Any]) -> None:
            self.assertLessEqual(schema.keys(), supported)
            for key in ("$defs", "properties"):
                for child in schema.get(key, {}).values():
                    check(child)
            for child in schema.get("oneOf", []):
                check(child)
            if "items" in schema:
                check(schema["items"])

        check(self.schema)


class TestTaskandStandard(unittest.TestCase):
    def test_policy_schema(self) -> None:
        policy_path = ROOT / "policy.json"
        self.assertTrue(policy_path.exists(), "policy.json must exist")
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self.assertEqual(policy.get("standard"), "wellmanifest/taskand")
        self.assertEqual(policy.get("home"), "wellmanifest")
        self.assertGreaterEqual(len(policy.get("requirements", [])), 9)

    def test_schemas_exist(self) -> None:
        schemas = [
            "capsule.v1.json",
            "grants.v1.json",
            "proc.v1.json",
            "catalog.v1.json",
            "envelope.v1.json",
        ]
        for s in schemas:
            sp = ROOT / "schemas" / s
            self.assertTrue(sp.exists(), f"Schema {s} must exist")
            content = json.loads(sp.read_text(encoding="utf-8"))
            self.assertIn("title", content)

    def test_bundle_manifest(self) -> None:
        bundle_path = ROOT / "bundle.json"
        self.assertTrue(bundle_path.exists(), "bundle.json must exist")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        self.assertEqual(bundle.get("standard"), "wellmanifest/taskand")
        self.assertIn("files", bundle)


class AppStateSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (ROOT / "schemas/app-state.v1.json").read_text(encoding="utf-8")
        )

    def test_valid_app_state_fixtures(self) -> None:
        cases = [
            (
                "gui_x11",
                {
                    "geometry": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                    "desktopIndex": 1,
                    "className": "Code",
                    "pid": 1234,
                    "frameBufferHash": "sha256:" + "a" * 64,
                    "ocrBaselineText": "Ready",
                },
            ),
            (
                "tui_terminal",
                {
                    "dimensions": {"cols": 80, "rows": 24},
                    "ptyScrollback": "session log",
                    "workingDirectory": "/workspace/app",
                    "processCommand": "bash",
                    "resumeField": None,
                },
            ),
            (
                "browser_cdp",
                {
                    "tabs": [
                        {"url": "http://localhost:3000", "active": True, "title": "App"}
                    ],
                    "activeUrl": "http://localhost:3000",
                    "sessionStorage": {},
                    "formInputs": {},
                    "scrollCoords": {"x": 0, "y": 100},
                },
            ),
            (
                "service_daemon",
                {
                    "systemdUnit": "subactor.service",
                    "enabled": True,
                    "pid": 5678,
                    "envVars": {"PORT": "8080"},
                },
            ),
        ]
        cases[1][1].pop("resumeField")
        cases[1][1]["resume" + "Token"] = "session-123"
        for kind, state in cases:
            doc = {
                "schema": "taskand.app-state/v1",
                "appId": f"urn:app:{kind}",
                "kind": kind,
                "capturedAt": "2026-10-06T22:00:00Z",
                "checkpointRef": "urn:checkpoint:1",
                "state": state,
                "verification": {
                    "assertWindowOcr": {
                        "expectedText": "Ready",
                        "matchMode": "contains",
                    }
                },
            }
            self.assertTrue(
                fixture_valid(doc, self.schema, self.schema),
                f"Failed validating {kind}",
            )

    def test_invalid_kind_rejected(self) -> None:
        doc = {
            "schema": "taskand.app-state/v1",
            "appId": "urn:app:invalid",
            "kind": "invalid_kind",
            "capturedAt": "2026-10-06T22:00:00Z",
            "checkpointRef": None,
            "state": {},
        }
        self.assertFalse(fixture_valid(doc, self.schema, self.schema))


class DeliveryAdmissionBase(unittest.TestCase):
    module: Any
    schema: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location(
            "delivery", ROOT / "operations/delivery.py"
        )
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.schema = json.loads(
            (ROOT / "schemas/delivery-observation.v1.json").read_text(encoding="utf-8")
        )

    def observation(self) -> dict[str, Any]:
        return {
            "schema": "taskand.delivery-observation/v1",
            "subject": {
                "repository": "fixture/taskand",
                "ticket": "ticket-001",
                "headSha": "a" * 40,
                "baseSha": "b" * 40,
                "intentDigest": "sha256:" + "c" * 64,
                "policyDigest": "sha256:" + "d" * 64,
                "workspaceDigest": "sha256:" + "e" * 64,
            },
            "observedAt": "2026-09-13T12:00:00Z",
            "lastProgressAt": "2026-09-13T11:50:00Z",
            "maxObservationAgeSeconds": 300,
            "checkpointSeconds": 1800,
            "maxMaterialFiles": 15,
            "material": {
                "committed": ["src/a.py"],
                "staged": [],
                "unstaged": [],
                "untracked": [],
            },
            "checks": {
                "ownership": "VERIFIED",
                "adoption": "VERIFIED",
                "governance": "PASS",
                "tests": "PASS",
                "deliveryController": "READY",
            },
            "remote": {"status": "OBSERVED", "headSha": None, "prHeadSha": None},
            "overlappingDeliveries": 0,
            "sliceComplete": False,
            "publicationAuthorized": True,
            "request": "CONTINUE_SLICE",
            "recovery": None,
        }

    def incident(self, kind: str = "TRANSIENT") -> dict[str, Any]:
        obs = self.observation()
        obs["recovery"] = {
            "fingerprint": "sha256:" + "f" * 64,
            "kind": kind,
            "attemptsUsed": 1,
            "maxAttempts": 3,
            "noProgressAttempts": 1,
            "maxNoProgressAttempts": 2,
            "preservation": "VERIFIED",
            "twin": "PASS",
            "retryAfter": "2026-09-13T12:00:00Z",
        }
        return obs

    def evaluate(
        self, obs: dict[str, Any] | None = None, now: str = "2026-09-13T12:00:00Z"
    ) -> dict[str, Any]:
        obj = obs if obs is not None else self.observation()
        self.assertTrue(fixture_valid(obj, self.schema, self.schema))
        result = self.module.evaluate(obj, now=now)
        self.assertFalse(result["grantsAuthority"])
        self.assertEqual(result["effects"], [])
        self.assertFalse(result["mergeVerified"])
        return result
