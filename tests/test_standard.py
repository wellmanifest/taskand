import json
import hashlib
import re
from datetime import datetime
import unittest
import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fixture_valid(value, schema, root):
    """Offline fixture checker for the keywords used here, not a JSON Schema runtime."""
    if '$ref' in schema:
        if not schema['$ref'].startswith('#/$defs/'):
            raise AssertionError('Unexpected external schema retrieval')
        return fixture_valid(value, root['$defs'][schema['$ref'].split('/')[-1]], root)
    if 'oneOf' in schema and sum(fixture_valid(value, part, root) for part in schema['oneOf']) != 1:
        return False
    if 'const' in schema and value != schema['const']: return False
    if 'enum' in schema and value not in schema['enum']: return False
    kind = schema.get('type')
    if kind == 'object':
        if not isinstance(value, dict): return False
        if not set(schema.get('required', [])) <= value.keys(): return False
        if schema.get('additionalProperties') is False and not value.keys() <= schema['properties'].keys(): return False
        if any(not fixture_valid(v, schema['properties'][k], root) for k, v in value.items() if k in schema.get('properties', {})): return False
    elif kind == 'array':
        if not isinstance(value, list) or len(value) > schema.get('maxItems', float('inf')): return False
        if schema.get('uniqueItems') and len({json.dumps(v, sort_keys=True) for v in value}) != len(value): return False
        if any(not fixture_valid(v, schema['items'], root) for v in value): return False
    elif kind == 'string':
        if not isinstance(value, str) or len(value) < schema.get('minLength', 0): return False
        if 'pattern' in schema and not re.search(schema['pattern'], value): return False
        if schema.get('format') == 'date-time':
            try:
                if 'T' not in value or datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None: return False
            except ValueError: return False
    elif kind == 'integer':
        if type(value) is not int or not schema.get('minimum', -float('inf')) <= value <= schema.get('maximum', float('inf')): return False
    elif kind == 'null' and value is not None: return False
    elif kind == 'boolean' and type(value) is not bool: return False
    return True


class EvolutionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / 'schemas/envelope.v2.json').read_text())

    def ref(self, name='test'):
        return {'uri': 'urn:test:' + name, 'digest': 'sha256:' + 'a' * 64}

    def request(self):
        return {'schema': 'taskand.task-request/v1', 'id': 'urn:test:request', 'kind': 'COMMAND',
                'correlationRef': 'urn:test:correlation', 'causationRef': None,
                'operation': self.ref('operation'), 'payload': self.ref('payload'),
                'dsl': {'mode': 'REQUEST_ONLY', 'artifact': self.ref('dsl'), 'schema': self.ref('schema'), 'grammar': self.ref('grammar')},
                'contextRefs': [], 'authorityRef': 'authorization:test', 'idempotencyKey': 'test-only',
                'budget': {'maxSteps': 3, 'maxAttempts': 2, 'maxChildren': 0, 'maxDepth': 0, 'deadline': '2026-09-13T12:00:00Z'}}

    def event(self):
        return {'specversion': '1.0', 'id': 'test', 'source': 'proc://test/observer/v1', 'type': 'taskand.execution.observed.v1',
                'time': '2026-09-13T12:00:00Z', 'datacontenttype': 'application/json',
                'dataschema': 'urn:taskand:schema:envelope:v2#log-data',
                'correlationid': 'urn:test:correlation', 'requestref': 'urn:test:request',
                'data': {'schema': 'taskand.log-event/v1', 'eventRef': 'urn:test:event', 'subjectRef': 'proc://test/worker/v1',
                         'result': 'BLOCKED', 'code': 'MISSING_TWIN', 'evidenceRefs': [self.ref('evidence')]}}

    def valid(self, obj):
        return fixture_valid(obj, self.schema, self.schema)

    def test_request_and_event_are_disjoint(self):
        self.assertTrue(self.valid(self.request()))
        self.assertTrue(self.valid(self.event()))
        self.assertFalse(fixture_valid(self.event(), self.schema['$defs']['taskRequest'], self.schema))
        self.assertFalse(fixture_valid(self.request(), self.schema['$defs']['logEvent'], self.schema))

    def test_every_layer_closed_and_versioned(self):
        for target in ((), ('dsl',), ('dsl', 'artifact'), ('budget',), ('operation',)):
            obj = self.request(); part = obj
            for key in target: part = part[key]
            part['unrecognized'] = True
            self.assertFalse(self.valid(obj), target)
        obj = self.request(); obj['schema'] = 'taskand.task-request/v2'
        self.assertFalse(self.valid(obj))

    def test_dsl_grammar_and_digest_required(self):
        for field in ('artifact', 'schema', 'grammar'):
            obj = self.request(); del obj['dsl'][field]
            self.assertFalse(self.valid(obj))
        obj = self.request(); obj['dsl']['mode'] = 'EXECUTE'
        self.assertFalse(self.valid(obj))
        obj = self.request(); obj['payload']['digest'] = 'latest'
        self.assertFalse(self.valid(obj))

    def test_cloud_event_does_not_carry_nested_extensions_or_authority(self):
        obj = self.event(); obj['taskand'] = {'authorize': True}
        self.assertFalse(self.valid(obj))
        obj = self.event(); obj['data']['authorityRef'] = 'authorization:forged'
        self.assertFalse(self.valid(obj))
        obj = self.event(); obj['correlationid'] = {'id': 'urn:test:x'}
        self.assertFalse(self.valid(obj))

    def test_budgets_and_reference_syntax(self):
        for key, value in [('maxAttempts', 0), ('maxChildren', 33), ('maxDepth', True), ('deadline', 'yesterday')]:
            obj = self.request(); obj['budget'][key] = value
            self.assertFalse(self.valid(obj), key)
        obj = self.request(); obj['contextRefs'] = [self.ref(), self.ref()]
        self.assertFalse(self.valid(obj))
        obj = self.request(); obj['operation']['uri'] = 'not a URI'
        self.assertFalse(self.valid(obj))

    def test_bundle_contains_complete_normative_graph(self):
        bundle = json.loads((ROOT / 'bundle.json').read_text())
        for path in (ROOT / 'schemas').glob('*.json'):
            self.assertIn(path.relative_to(ROOT).as_posix(), bundle['files'])
        for path in ['docs/information/evolution.md', 'docs/standard.md', 'operations/bundle.py']:
            self.assertIn(path, bundle['files'])
        for path, digest in bundle['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)

    def test_fixture_checker_covers_all_used_keywords(self):
        supported = {'$schema', '$id', '$anchor', '$defs', '$ref', 'title', 'oneOf', 'type', 'const', 'enum',
                     'properties', 'required', 'additionalProperties', 'items', 'uniqueItems', 'maxItems',
                     'minLength', 'pattern', 'format', 'minimum', 'maximum'}
        def check(schema):
            self.assertLessEqual(schema.keys(), supported)
            for key in ('$defs', 'properties'):
                for child in schema.get(key, {}).values(): check(child)
            for child in schema.get('oneOf', []): check(child)
            if 'items' in schema: check(schema['items'])
        check(self.schema)

class TestTaskandStandard(unittest.TestCase):
    def test_policy_schema(self):
        policy_path = ROOT / "policy.json"
        self.assertTrue(policy_path.exists(), "policy.json must exist")
        policy = json.loads(policy_path.read_text())
        self.assertEqual(policy.get("standard"), "wellmanifest/taskand")
        self.assertEqual(policy.get("home"), "wellmanifest")
        self.assertGreaterEqual(len(policy.get("requirements", [])), 9)

    def test_schemas_exist(self):
        schemas = [
            "capsule.v1.json",
            "grants.v1.json",
            "proc.v1.json",
            "catalog.v1.json",
            "envelope.v1.json"
        ]
        for s in schemas:
            sp = ROOT / "schemas" / s
            self.assertTrue(sp.exists(), f"Schema {s} must exist")
            content = json.loads(sp.read_text())
            self.assertIn("title", content)

    def test_bundle_manifest(self):
        bundle_path = ROOT / "bundle.json"
        self.assertTrue(bundle_path.exists(), "bundle.json must exist")
        bundle = json.loads(bundle_path.read_text())
        self.assertEqual(bundle.get("standard"), "wellmanifest/taskand")
        self.assertIn("files", bundle)


class DeliveryAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('delivery', ROOT / 'operations/delivery.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.schema = json.loads((ROOT / 'schemas/delivery-observation.v1.json').read_text())

    def observation(self):
        return {'schema': 'taskand.delivery-observation/v1',
                'subject': {'repository': 'fixture/taskand', 'ticket': 'ticket-001',
                            'headSha': 'a' * 40, 'baseSha': 'b' * 40,
                            'intentDigest': 'sha256:' + 'c' * 64,
                            'policyDigest': 'sha256:' + 'd' * 64,
                            'workspaceDigest': 'sha256:' + 'e' * 64},
                'observedAt': '2026-09-13T12:00:00Z',
                'lastProgressAt': '2026-09-13T11:50:00Z',
                'maxObservationAgeSeconds': 300, 'checkpointSeconds': 1800,
                'maxMaterialFiles': 15,
                'material': {'committed': ['src/a.py'], 'staged': [], 'unstaged': [], 'untracked': []},
                'checks': {'ownership': 'VERIFIED', 'adoption': 'VERIFIED',
                           'governance': 'PASS', 'tests': 'PASS', 'deliveryController': 'READY'},
                'remote': {'status': 'OBSERVED', 'headSha': None, 'prHeadSha': None},
                'overlappingDeliveries': 0, 'sliceComplete': False,
                'publicationAuthorized': True, 'request': 'CONTINUE_SLICE', 'recovery': None}

    def incident(self, kind='TRANSIENT'):
        obs = self.observation()
        obs['recovery'] = {'fingerprint': 'sha256:' + 'f' * 64, 'kind': kind,
                           'attemptsUsed': 1, 'maxAttempts': 3,
                           'noProgressAttempts': 1, 'maxNoProgressAttempts': 2,
                           'preservation': 'VERIFIED', 'twin': 'PASS',
                           'retryAfter': '2026-09-13T12:00:00Z'}
        return obs

    def test_recovery_unknown_effect_never_retries_even_after_exhaustion(self):
        obs = self.incident('UNKNOWN_EFFECT'); obs['recovery']['attemptsUsed'] = 3
        self.assertEqual(self.evaluate(obs)['route'], 'RECONCILE_EFFECT')

    def test_recovery_regression_quarantines_only_candidate(self):
        self.assertEqual(self.evaluate(self.incident('REGRESSION'))['route'], 'QUARANTINE_CANDIDATE')

    def test_recovery_authority_is_not_self_granted(self):
        self.assertEqual(self.evaluate(self.incident('AUTHORITY_GAP'))['route'], 'WAIT_RECOVERY_AUTHORITY')

    def test_recovery_limits_are_inclusive_and_shared_observed_inputs(self):
        for field, value in [('attemptsUsed', 3), ('noProgressAttempts', 2)]:
            obs = self.incident(); obs['recovery']['attemptsUsed'] = 2
            obs['recovery'][field] = value
            self.assertEqual(self.evaluate(obs)['route'], 'HALT_AFFECTED_SCOPE')
            obs['subject']['ticket'] = 'ticket-002'
            self.assertEqual(self.evaluate(obs)['route'], 'HALT_AFFECTED_SCOPE')

    def test_recovery_inconsistent_counters_rejected(self):
        obs = self.incident(); obs['recovery']['noProgressAttempts'] = 2
        with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])

    def test_recovery_preservation_precedes_repair(self):
        obs = self.incident(); obs['recovery']['preservation'] = 'UNKNOWN'
        self.assertEqual(self.evaluate(obs)['route'], 'PRESERVE_RECOVERY')

    def test_recovery_unknown_error_cannot_be_declared_transient(self):
        self.assertEqual(self.evaluate(self.incident('UNKNOWN'))['route'], 'DIAGNOSE_ONLY')

    def test_recovery_twin_failure_and_missing_evidence_stop_retry(self):
        for twin, route in [('FAIL', 'HALT_AFFECTED_SCOPE'), ('UNKNOWN', 'REHEARSE_RECOVERY')]:
            obs = self.incident(); obs['recovery']['twin'] = twin
            self.assertEqual(self.evaluate(obs)['route'], route)

    def test_recovery_backoff_required_and_deadline_inclusive(self):
        obs = self.incident()
        for after in (None, '2026-09-13T12:00:01Z'):
            obs['recovery']['retryAfter'] = after
            self.assertEqual(self.evaluate(obs)['route'], 'WAIT_RETRY_WINDOW')
        obs['recovery']['retryAfter'] = obs['observedAt']
        self.assertEqual(self.evaluate(obs)['route'], 'RETRY_CANDIDATE')

    def test_recovery_conflict_is_a_plan_not_automatic_merge(self):
        for kind in ('CONFLICT', 'CONTRACT_GAP'):
            self.assertEqual(self.evaluate(self.incident(kind))['route'], 'PLAN_BOUNDED_REPAIR')

    def test_recovery_cannot_override_staleness_or_unknown_ownership(self):
        obs = self.incident()
        self.assertEqual(self.evaluate(obs, now='2026-09-13T12:06:00Z')['route'], 'REOBSERVE')
        obs['checks']['ownership'] = 'UNKNOWN'
        self.assertEqual(self.evaluate(obs)['route'], 'RECONCILE_OWNER')

    def test_recovery_vocabulary_closed_and_bound_in_digest(self):
        obs = self.incident(); original = self.evaluate(obs)['inputDigest']
        obs['recovery']['attemptsUsed'] = 2
        self.assertNotEqual(original, self.evaluate(obs)['inputDigest'])
        for field, value in [('shell', 'execute'), ('kind', 'ASSUME_FIXED'), ('attemptsUsed', True)]:
            altered = copy.deepcopy(obs); altered['recovery'][field] = value
            with self.assertRaises(ValueError): self.module.evaluate(altered, now=obs['observedAt'])

    def evaluate(self, obs=None, now='2026-09-13T12:00:00Z'):
        obj = obs if obs is not None else self.observation()
        self.assertTrue(fixture_valid(obj, self.schema, self.schema))
        result = self.module.evaluate(obj, now=now)
        self.assertFalse(result['grantsAuthority'])
        self.assertEqual(result['effects'], [])
        self.assertFalse(result['mergeVerified'])
        return result

    def test_full_range_union_not_latest_commit_or_dirty_only(self):
        obs = self.observation()
        obs['material']['committed'] = ['src/a%d.py' % i for i in range(14)]
        obs['material']['staged'] = ['src/new.py']
        obs['material']['unstaged'] = ['src/a0.py']
        obs['material']['untracked'] = ['src/last.py']
        result = self.evaluate(obs)
        self.assertEqual(result['materialFileCount'], 16)
        self.assertEqual(result['route'], 'SPLIT_WITH_PRESERVATION')

    def test_shared_paths_are_counted_once_and_boundary_inclusive(self):
        obs = self.observation()
        for layer in obs['material']:
            obs['material'][layer] = ['src/a%d.py' % i for i in range(15)]
        self.assertEqual(self.evaluate(obs)['materialFileCount'], 15)
        self.assertEqual(self.evaluate(obs)['route'], 'CONTINUE_BOUNDED')

    def test_new_features_do_not_extend_pending_delivery(self):
        obs = self.observation(); obs['request'] = 'START_NEW_SLICE'
        self.assertEqual(self.evaluate(obs)['route'], 'FINISH_EXISTING')

    def test_same_scope_debt_survives_blocked_owner_status(self):
        obs = self.observation(); obs['overlappingDeliveries'] = 1
        self.assertEqual(self.evaluate(obs)['route'], 'FINISH_EXISTING')

    def test_disjoint_scope_is_not_blocked_by_worktree_count(self):
        obs = self.observation(); obs['material']['committed'] = []
        obs['request'] = 'START_NEW_SLICE'
        self.assertEqual(self.evaluate(obs)['route'], 'CONTINUE_BOUNDED')

    def test_adoption_is_reconciled_before_activation(self):
        obs = self.observation(); obs['request'] = 'ACTIVATE_GOVERNANCE'
        for state in ('UNKNOWN', 'UNRECONCILED'):
            obs['checks']['adoption'] = state
            self.assertEqual(self.evaluate(obs)['route'], 'RECONCILE_ADOPTION')

    def test_dirty_clone_cannot_activate_clone_wide_hooks(self):
        obs = self.observation(); obs['request'] = 'ACTIVATE_GOVERNANCE'
        obs['material']['unstaged'] = ['src/working.py']
        self.assertEqual(self.evaluate(obs)['diagnostic'], 'TKD-DELIVERY-ACTIVATION')

    def test_disabled_controller_stops_growth_not_waives_review(self):
        obs = self.observation(); obs['checks']['deliveryController'] = 'UNAVAILABLE'
        self.assertEqual(self.evaluate(obs)['route'], 'RESTORE_DELIVERY')

    def test_owner_uncertainty_and_real_conflicts_require_reconciliation(self):
        for value in ('UNKNOWN', 'CONFLICT'):
            obs = self.observation(); obs['checks']['ownership'] = value
            self.assertEqual(self.evaluate(obs)['route'], 'RECONCILE_OWNER')

    def test_checkpoint_deadline_is_independent_of_new_prompts(self):
        obs = self.observation(); obs['lastProgressAt'] = '2026-09-13T11:30:00Z'
        obs['checks']['tests'] = 'UNKNOWN'
        self.assertEqual(self.evaluate(obs)['route'], 'PRESERVE_AND_VALIDATE')
        self.assertTrue(self.evaluate(obs)['checkpointDue'])

    def test_completed_slice_prioritizes_commit_push_and_pr(self):
        obs = self.observation(); obs['sliceComplete'] = True
        obs['material']['staged'] = ['src/a.py']
        self.assertEqual(self.evaluate(obs)['route'], 'COMMIT_CURRENT')
        obs['material']['staged'] = []
        self.assertEqual(self.evaluate(obs)['route'], 'PUSH_CURRENT')
        obs['remote']['headSha'] = obs['subject']['headSha']
        self.assertEqual(self.evaluate(obs)['route'], 'OPEN_OR_UPDATE_PR')
        obs['remote']['prHeadSha'] = obs['subject']['headSha']
        self.assertEqual(self.evaluate(obs)['route'], 'WAIT_PROTECTED_REVIEW')

    def test_pushed_head_does_not_publish_dirty_source(self):
        obs = self.observation(); obs['remote']['headSha'] = obs['subject']['headSha']
        obs['material']['untracked'] = ['src/unpublished.py']
        result = self.evaluate(obs)
        self.assertTrue(result['headPushed'])
        self.assertFalse(result['workingTreePublished'])

    def test_no_publication_authority_is_not_inferred(self):
        obs = self.observation(); obs['sliceComplete'] = True
        obs['publicationAuthorized'] = False
        self.assertEqual(self.evaluate(obs)['route'], 'WAIT_PUBLICATION_AUTHORITY')

    def test_failed_or_unknown_checks_cannot_publish(self):
        for field in ('governance', 'tests'):
            for state in ('FAIL', 'UNKNOWN'):
                obs = self.observation(); obs['request'] = 'PUBLISH'
                obs['checks'][field] = state
                self.assertEqual(self.evaluate(obs)['route'], 'PRESERVE_AND_VALIDATE')

    def test_stale_observation_never_claims_a_current_remote_head(self):
        obs = self.observation(); obs['remote']['headSha'] = obs['subject']['headSha']
        result = self.evaluate(obs, now='2026-09-13T12:05:01Z')
        self.assertEqual(result['route'], 'REOBSERVE')
        self.assertFalse(result['headPushed'])

    def test_remote_unknown_is_not_missing_branch_success(self):
        obs = self.observation(); obs['remote']['status'] = 'UNKNOWN'
        self.assertEqual(self.evaluate(obs)['route'], 'REOBSERVE')
        obs['remote']['headSha'] = 'a' * 40
        with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])

    def test_inconsistent_pr_and_remote_require_reobservation(self):
        obs = self.observation(); obs['remote']['prHeadSha'] = 'f' * 40
        with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])

    def test_unknown_fields_and_boolean_integer_confusion_rejected(self):
        for target in ((), ('subject',), ('material',), ('checks',), ('remote',)):
            obs = self.observation(); part = obs
            for key in target: part = part[key]
            part['unknown'] = True
            with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])
        for key in ('maxMaterialFiles', 'checkpointSeconds', 'overlappingDeliveries'):
            obs = self.observation(); obs[key] = True
            with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])
        obs = self.observation(); obs['publicationAuthorized'] = 1
        with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])

    def test_future_progress_is_rejected(self):
        obs = self.observation(); obs['lastProgressAt'] = '2026-09-13T12:01:00Z'
        with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])

    def test_all_emitted_codes_have_canonical_remediation(self):
        policy = json.loads((ROOT / 'policy.json').read_text())
        emitted = set(re.findall(r'TKD-(?:DELIVERY|RECOVERY)-[A-Z-]+', (ROOT / 'operations/delivery.py').read_text()))
        self.assertEqual(emitted, set(policy['delivery_diagnostics']))
        self.assertTrue(all(policy['delivery_diagnostics'].values()))

    def test_non_rfc3339_clock_is_rejected(self):
        for clock in ('2026-09-13T12:00:00', '20260913T120000Z', '2026-09-13T12:00Z'):
            with self.assertRaises(ValueError): self.module.evaluate(self.observation(), now=clock)

    def test_unsafe_and_alias_paths_are_rejected(self):
        for path in ('../a', '/a', 'a/../b', 'a\\b', 'a\nb', './a', 'a//b', 'C:/a', '.', 'a\0b'):
            obs = self.observation(); obs['material']['staged'] = [path]
            with self.assertRaises(ValueError): self.module.evaluate(obs, now=obs['observedAt'])

    def test_replay_is_pure_deterministic_and_binds_clock(self):
        obs = self.observation(); before = copy.deepcopy(obs)
        first = self.evaluate(obs)
        self.assertEqual(first, self.evaluate(obs))
        self.assertEqual(obs, before)
        self.assertNotEqual(first['inputDigest'], self.evaluate(obs, now='2026-09-13T12:00:01Z')['inputDigest'])

    def test_cli_emits_redacted_diagnostic_for_duplicate_json_keys(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'operations/delivery.py')],
                                input='{"schema":"x","schema":"y"}', text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['diagnostic'], 'TKD-DELIVERY-INVALID')
        self.assertNotIn('Traceback', result.stderr)

if __name__ == "__main__":
    unittest.main()
