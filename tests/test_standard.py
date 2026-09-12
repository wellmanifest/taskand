import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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

if __name__ == "__main__":
    unittest.main()
