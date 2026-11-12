from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.standard_fixtures import (  # noqa: F401
    AppStateSchemaTests,
    DeliveryAdmissionBase,
    EvolutionContracts,
    TestTaskandStandard,
    fixture_valid,
)


class DeliveryAdmission(DeliveryAdmissionBase):
    def test_recovery_unknown_effect_never_retries_even_after_exhaustion(self) -> None:
        obs = self.incident("UNKNOWN_EFFECT")
        obs["recovery"]["attemptsUsed"] = 3
        self.assertEqual(self.evaluate(obs)["route"], "RECONCILE_EFFECT")

    def test_recovery_regression_quarantines_only_candidate(self) -> None:
        self.assertEqual(
            self.evaluate(self.incident("REGRESSION"))["route"], "QUARANTINE_CANDIDATE"
        )

    def test_recovery_authority_is_not_self_granted(self) -> None:
        self.assertEqual(
            self.evaluate(self.incident("AUTHORITY_GAP"))["route"],
            "WAIT_RECOVERY_AUTHORITY",
        )

    def test_recovery_limits_are_inclusive_and_shared_observed_inputs(self) -> None:
        for field, value in [("attemptsUsed", 3), ("noProgressAttempts", 2)]:
            obs = self.incident()
            obs["recovery"]["attemptsUsed"] = 2
            obs["recovery"][field] = value
            self.assertEqual(self.evaluate(obs)["route"], "HALT_AFFECTED_SCOPE")
            obs["subject"]["ticket"] = "ticket-002"
            self.assertEqual(self.evaluate(obs)["route"], "HALT_AFFECTED_SCOPE")

    def test_recovery_inconsistent_counters_rejected(self) -> None:
        obs = self.incident()
        obs["recovery"]["noProgressAttempts"] = 2
        with self.assertRaises(ValueError):
            self.module.evaluate(obs, now=obs["observedAt"])

    def test_recovery_preservation_precedes_repair(self) -> None:
        obs = self.incident()
        obs["recovery"]["preservation"] = "UNKNOWN"
        self.assertEqual(self.evaluate(obs)["route"], "PRESERVE_RECOVERY")

    def test_recovery_unknown_error_cannot_be_declared_transient(self) -> None:
        self.assertEqual(
            self.evaluate(self.incident("UNKNOWN"))["route"], "DIAGNOSE_ONLY"
        )

    def test_recovery_twin_failure_and_missing_evidence_stop_retry(self) -> None:
        for twin, route in [
            ("FAIL", "HALT_AFFECTED_SCOPE"),
            ("UNKNOWN", "REHEARSE_RECOVERY"),
        ]:
            obs = self.incident()
            obs["recovery"]["twin"] = twin
            self.assertEqual(self.evaluate(obs)["route"], route)

    def test_recovery_backoff_required_and_deadline_inclusive(self) -> None:
        obs = self.incident()
        for after in (None, "2026-09-13T12:00:01Z"):
            obs["recovery"]["retryAfter"] = after
            self.assertEqual(self.evaluate(obs)["route"], "WAIT_RETRY_WINDOW")
        obs["recovery"]["retryAfter"] = obs["observedAt"]
        self.assertEqual(self.evaluate(obs)["route"], "RETRY_CANDIDATE")

    def test_recovery_conflict_is_a_plan_not_automatic_merge(self) -> None:
        for kind in ("CONFLICT", "CONTRACT_GAP"):
            self.assertEqual(
                self.evaluate(self.incident(kind))["route"], "PLAN_BOUNDED_REPAIR"
            )

    def test_recovery_cannot_override_staleness_or_unknown_ownership(self) -> None:
        obs = self.incident()
        self.assertEqual(
            self.evaluate(obs, now="2026-09-13T12:06:00Z")["route"], "REOBSERVE"
        )
        obs["checks"]["ownership"] = "UNKNOWN"
        self.assertEqual(self.evaluate(obs)["route"], "RECONCILE_OWNER")

    def test_recovery_vocabulary_closed_and_bound_in_digest(self) -> None:
        obs = self.incident()
        original = self.evaluate(obs)["inputDigest"]
        obs["recovery"]["attemptsUsed"] = 2
        self.assertNotEqual(original, self.evaluate(obs)["inputDigest"])
        for field, value in [
            ("shell", "execute"),
            ("kind", "ASSUME_FIXED"),
            ("attemptsUsed", True),
        ]:
            altered = copy.deepcopy(obs)
            altered["recovery"][field] = value
            with self.assertRaises(ValueError):
                self.module.evaluate(altered, now=obs["observedAt"])

    def test_full_range_union_not_latest_commit_or_dirty_only(self) -> None:
        obs = self.observation()
        obs["material"]["committed"] = [f"src/a{i}.py" for i in range(14)]
        obs["material"]["staged"] = ["src/new.py"]
        obs["material"]["unstaged"] = ["src/a0.py"]
        obs["material"]["untracked"] = ["src/last.py"]
        result = self.evaluate(obs)
        self.assertEqual(result["materialFileCount"], 16)
        self.assertEqual(result["route"], "SPLIT_WITH_PRESERVATION")

    def test_shared_paths_are_counted_once_and_boundary_inclusive(self) -> None:
        obs = self.observation()
        for layer in obs["material"]:
            obs["material"][layer] = [f"src/a{i}.py" for i in range(15)]
        self.assertEqual(self.evaluate(obs)["materialFileCount"], 15)
        self.assertEqual(self.evaluate(obs)["route"], "CONTINUE_BOUNDED")

    def test_new_features_do_not_extend_pending_delivery(self) -> None:
        obs = self.observation()
        obs["request"] = "START_NEW_SLICE"
        self.assertEqual(self.evaluate(obs)["route"], "FINISH_EXISTING")

    def test_same_scope_debt_survives_blocked_owner_status(self) -> None:
        obs = self.observation()
        obs["overlappingDeliveries"] = 1
        self.assertEqual(self.evaluate(obs)["route"], "FINISH_EXISTING")

    def test_disjoint_scope_is_not_blocked_by_worktree_count(self) -> None:
        obs = self.observation()
        obs["material"]["committed"] = []
        obs["request"] = "START_NEW_SLICE"
        self.assertEqual(self.evaluate(obs)["route"], "CONTINUE_BOUNDED")

    def test_adoption_is_reconciled_before_activation(self) -> None:
        obs = self.observation()
        obs["request"] = "ACTIVATE_GOVERNANCE"
        for state in ("UNKNOWN", "UNRECONCILED"):
            obs["checks"]["adoption"] = state
            self.assertEqual(self.evaluate(obs)["route"], "RECONCILE_ADOPTION")

    def test_dirty_clone_cannot_activate_clone_wide_hooks(self) -> None:
        obs = self.observation()
        obs["request"] = "ACTIVATE_GOVERNANCE"
        obs["material"]["unstaged"] = ["src/working.py"]
        self.assertEqual(self.evaluate(obs)["diagnostic"], "TKD-DELIVERY-ACTIVATION")

    def test_disabled_controller_stops_growth_not_waives_review(self) -> None:
        obs = self.observation()
        obs["checks"]["deliveryController"] = "UNAVAILABLE"
        self.assertEqual(self.evaluate(obs)["route"], "RESTORE_DELIVERY")

    def test_owner_uncertainty_and_real_conflicts_require_reconciliation(self) -> None:
        for value in ("UNKNOWN", "CONFLICT"):
            obs = self.observation()
            obs["checks"]["ownership"] = value
            self.assertEqual(self.evaluate(obs)["route"], "RECONCILE_OWNER")

    def test_checkpoint_deadline_is_independent_of_new_prompts(self) -> None:
        obs = self.observation()
        obs["lastProgressAt"] = "2026-09-13T11:30:00Z"
        obs["checks"]["tests"] = "UNKNOWN"
        self.assertEqual(self.evaluate(obs)["route"], "PRESERVE_AND_VALIDATE")
        self.assertTrue(self.evaluate(obs)["checkpointDue"])

    def test_completed_slice_prioritizes_commit_push_and_pr(self) -> None:
        obs = self.observation()
        obs["sliceComplete"] = True
        obs["material"]["staged"] = ["src/a.py"]
        self.assertEqual(self.evaluate(obs)["route"], "COMMIT_CURRENT")
        obs["material"]["staged"] = []
        self.assertEqual(self.evaluate(obs)["route"], "PUSH_CURRENT")
        obs["remote"]["headSha"] = obs["subject"]["headSha"]
        self.assertEqual(self.evaluate(obs)["route"], "OPEN_OR_UPDATE_PR")
        obs["remote"]["prHeadSha"] = obs["subject"]["headSha"]
        self.assertEqual(self.evaluate(obs)["route"], "WAIT_PROTECTED_REVIEW")

    def test_pushed_head_does_not_publish_dirty_source(self) -> None:
        obs = self.observation()
        obs["remote"]["headSha"] = obs["subject"]["headSha"]
        obs["material"]["untracked"] = ["src/unpublished.py"]
        result = self.evaluate(obs)
        self.assertTrue(result["headPushed"])
        self.assertFalse(result["workingTreePublished"])

    def test_no_publication_authority_is_not_inferred(self) -> None:
        obs = self.observation()
        obs["sliceComplete"] = True
        obs["publicationAuthorized"] = False
        self.assertEqual(self.evaluate(obs)["route"], "WAIT_PUBLICATION_AUTHORITY")

    def test_failed_or_unknown_checks_cannot_publish(self) -> None:
        for field in ("governance", "tests"):
            for state in ("FAIL", "UNKNOWN"):
                obs = self.observation()
                obs["request"] = "PUBLISH"
                obs["checks"][field] = state
                self.assertEqual(self.evaluate(obs)["route"], "PRESERVE_AND_VALIDATE")

    def test_stale_observation_never_claims_a_current_remote_head(self) -> None:
        obs = self.observation()
        obs["remote"]["headSha"] = obs["subject"]["headSha"]
        result = self.evaluate(obs, now="2026-09-13T12:05:01Z")
        self.assertEqual(result["route"], "REOBSERVE")
        self.assertFalse(result["headPushed"])

    def test_remote_unknown_is_not_missing_branch_success(self) -> None:
        obs = self.observation()
        obs["remote"]["status"] = "UNKNOWN"
        self.assertEqual(self.evaluate(obs)["route"], "REOBSERVE")
        obs["remote"]["headSha"] = "a" * 40
        with self.assertRaises(ValueError):
            self.module.evaluate(obs, now=obs["observedAt"])

    def test_inconsistent_pr_and_remote_require_reobservation(self) -> None:
        obs = self.observation()
        obs["remote"]["prHeadSha"] = "f" * 40
        with self.assertRaises(ValueError):
            self.module.evaluate(obs, now=obs["observedAt"])

    def test_unknown_fields_and_boolean_integer_confusion_rejected(self) -> None:
        for target in ((), ("subject",), ("material",), ("checks",), ("remote",)):
            obs = self.observation()
            part: Any = obs
            for key in target:
                part = part[key]
            part["unknown"] = True
            with self.assertRaises(ValueError):
                self.module.evaluate(obs, now=obs["observedAt"])
        for key in ("maxMaterialFiles", "checkpointSeconds", "overlappingDeliveries"):
            obs = self.observation()
            obs[key] = True
            with self.assertRaises(ValueError):
                self.module.evaluate(obs, now=obs["observedAt"])
        obs = self.observation()
        obs["publicationAuthorized"] = 1
        with self.assertRaises(ValueError):
            self.module.evaluate(obs, now=obs["observedAt"])

    def test_future_progress_is_rejected(self) -> None:
        obs = self.observation()
        obs["lastProgressAt"] = "2026-09-13T12:01:00Z"
        with self.assertRaises(ValueError):
            self.module.evaluate(obs, now=obs["observedAt"])

    def test_all_emitted_codes_have_canonical_remediation(self) -> None:
        policy = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))
        emitted = set(
            re.findall(
                r"TKD-(?:DELIVERY|RECOVERY)-[A-Z-]+",
                (ROOT / "operations/delivery.py").read_text(encoding="utf-8"),
            )
        )
        self.assertEqual(emitted, set(policy["delivery_diagnostics"]))
        self.assertTrue(all(policy["delivery_diagnostics"].values()))

    def test_non_rfc3339_clock_is_rejected(self) -> None:
        for clock in ("2026-09-13T12:00:00", "20260913T120000Z", "2026-09-13T12:00Z"):
            with self.assertRaises(ValueError):
                self.module.evaluate(self.observation(), now=clock)

    def test_unsafe_and_alias_paths_are_rejected(self) -> None:
        for path in (
            "../a",
            "/a",
            "a/../b",
            "a\\b",
            "a\nb",
            "./a",
            "a//b",
            "C:/a",
            ".",
            "a\0b",
        ):
            obs = self.observation()
            obs["material"]["staged"] = [path]
            with self.assertRaises(ValueError):
                self.module.evaluate(obs, now=obs["observedAt"])

    def test_replay_is_pure_deterministic_and_binds_clock(self) -> None:
        obs = self.observation()
        before = copy.deepcopy(obs)
        first = self.evaluate(obs)
        self.assertEqual(first, self.evaluate(obs))
        self.assertEqual(obs, before)
        self.assertNotEqual(
            first["inputDigest"],
            self.evaluate(obs, now="2026-09-13T12:00:01Z")["inputDigest"],
        )

    def test_cli_emits_redacted_diagnostic_for_duplicate_json_keys(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "operations/delivery.py")],
            input='{"schema":"x","schema":"y"}',
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            json.loads(result.stdout)["diagnostic"], "TKD-DELIVERY-INVALID"
        )
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_rejects_nonfinite_json_and_del_control_paths(self) -> None:
        for payload in (
            '{"x": NaN}',
            '{"x": Infinity}',
            '{"x": -Infinity}',
            '{"x": 1e309}',
            '{"x": "\\ud800"}',
        ):
            res = subprocess.run(
                [sys.executable, "-B", str(ROOT / "operations/delivery.py")],
                input=payload,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(res.returncode, 2)
            self.assertEqual(
                json.loads(res.stdout)["diagnostic"], "TKD-DELIVERY-INVALID"
            )
        obs = self.observation()
        obs["material"]["staged"] = ["src/a\x7fb.py"]
        with self.assertRaises(ValueError):
            self.module.evaluate(obs, now=obs["observedAt"])
        array_schema = {
            "type": "array",
            "maxItems": 4,
            "uniqueItems": True,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["k"],
                "properties": {"k": {"type": "string"}},
            },
        }
        self.module.validate([{"k": "a"}, {"k": "b"}], array_schema)
        with self.assertRaises(ValueError):
            self.module.validate([{"k": "a"}, {"k": "a"}], array_schema)

    def test_ticket_010_rfc3339_nanoseconds_unicode_digits_surrogates_and_symlinks(
        self,
    ) -> None:
        obs = self.observation()
        obs["observedAt"] = "2026-09-13T12:00:00.123456789Z"
        obs["lastProgressAt"] = "2026-09-13t11:50:00.1234567z"
        decision = self.evaluate(obs, now="2026-09-13T12:00:01.987654321+00:00")
        self.assertEqual(decision["route"], "CONTINUE_BOUNDED")
        obs_ns = self.observation()
        obs_ns["observedAt"] = "2026-09-13T12:00:00.000000100Z"
        obs_ns["lastProgressAt"] = "2026-09-13T12:00:00.000000200Z"
        with self.assertRaises(ValueError):
            self.module.evaluate(obs_ns, now="2026-09-13T12:00:00.000000300Z")
        for bad_ts in (
            "2026-09-13T12:00:00.1234567890Z",
            "2026-09-13T12:00:00-00:00",
            "\u0662\u0660\u0662\u0666-09-13T12:00:00Z",
        ):
            with self.subTest(bad_ts=bad_ts), self.assertRaises(ValueError):
                self.module.timestamp(bad_ts)
        with self.assertRaises(TypeError):
            self.module.timestamp(123)
        for bad_path in ("src/a\x85b.py", "src/ a.py", "src/a\ud800.py"):
            bad_obs = self.observation()
            bad_obs["material"]["staged"] = [bad_path]
            with self.subTest(bad_path=repr(bad_path)), self.assertRaises(ValueError):
                self.module.evaluate(bad_obs, now=bad_obs["observedAt"])
        with self.assertRaises(ValueError):
            self.module.validate(
                "ticket-\u0660\u0660\u0661",
                {"type": "string", "pattern": r"^ticket-\d{3}$"},
            )
        spec = importlib.util.spec_from_file_location(
            "bundle", ROOT / "operations/bundle.py"
        )
        assert spec is not None and spec.loader is not None
        bundle_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bundle_mod)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            real_dir = tmp_path / "real_dir"
            real_dir.mkdir()
            (real_dir / "doc.json").write_text('{"ok": true}', encoding="utf-8")
            sym_dir = tmp_path / "sym_dir"
            sym_dir.symlink_to(real_dir)
            with self.assertRaises(ValueError):
                self.module._read_regular_json(sym_dir / "doc.json")
            for raw_bad in (b'{"x": 1e309}', b'{"x": "\\ud800"}'):
                with self.assertRaises(ValueError):
                    bundle_mod._loads_strict(raw_bad)
            miss = subprocess.run(
                [
                    "node",
                    str(ROOT / "operations/catalog.mjs"),
                    "--verify",
                    str(tmp_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(miss.returncode, 0)
        ok = subprocess.run(
            [
                "node",
                str(ROOT / "operations/catalog.mjs"),
                "--verify",
                str(ROOT / "package"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ok.returncode, 0, ok.stderr)
        for rel in (
            "operations/delivery.py",
            "operations/bundle.py",
            "operations/standard_fixtures.py",
            "tests/test_standard.py",
        ):
            self.assertLess(
                len((ROOT / rel).read_text(encoding="utf-8").splitlines()), 500, rel
            )


if __name__ == "__main__":
    unittest.main()
