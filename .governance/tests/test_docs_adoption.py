"""Regression canaries for the pinned consumer entry point (stdlib only)."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("docs_adapter", ROOT / ".governance/check_docs.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class DocsAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = tempfile.TemporaryDirectory()
        cls.checker = adapter.export_checker(Path(os.environ["DOCS_SOURCE"]), Path(cls.runtime.name))

    @classmethod
    def tearDownClass(cls):
        cls.runtime.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("remote", "add", "origin", "https://github.com/wellmanifest/canary.git")
        self.write(".governance/docs.json", json.dumps({
            "schema": "wellmanifest.docs/adoption/v1", "repository": "wellmanifest/canary",
            "standard": "wellmanifest/docs", "source_revision": adapter.DOCS_REVISION,
            "policy_sha256": adapter.POLICY_SHA}))
        self.write("docs/README.md", "# Documentation\n")
        self.git("add", ".")
        self.git("-c", "user.name=Canary", "-c", "user.email=canary@example.invalid",
                 "-c", "core.hooksPath=/dev/null", "commit", "-qm", "isolated fixture")
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def check(self, *args):
        result = subprocess.run([sys.executable, "-I", str(self.checker), "--root", str(self.root),
            "--standard-revision", adapter.DOCS_REVISION, *args], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def prepare(self):
        return self.check("--prepare", "--format", "v2", "--scope", "repository",
            "--kind", "information", "--id", "mcp-canary",
            "--deliverable", "docs/INFORMATION/MCP_CANARY.md")

    def test_published_managed_inventory_matches_actual_consumer(self):
        self.assertIn(".governance/docs/SNAPSHOT_MIGRATION.md", adapter.managed_inventory(ROOT))

    def test_missing_and_wrong_adoption_fail_before_generation(self):
        for content in ["{}", '{"source_revision":"' + "0" * 40 + '"}']:
            self.write(".governance/docs.json", content)
            code, result = self.prepare()
            self.assertNotEqual(code, 0)
            self.assertFalse(result["ok"])
            self.assertFalse((self.root / "docs/INFORMATION/MCP_CANARY.md").exists())

    def test_missing_index_blocks_prepare(self):
        (self.root / "docs/README.md").unlink()
        self.assertNotEqual(self.prepare()[0], 0)

    def test_wrong_destination_blocks_prepare(self):
        code, _ = self.check("--prepare", "--format", "v2", "--scope", "repository",
            "--kind", "information", "--id", "mcp-canary", "--deliverable", "REPORT.md")
        self.assertNotEqual(code, 0)

    def test_completion_requires_real_deliverable_and_matching_plan(self):
        code, prepared = self.prepare()
        self.assertEqual(code, 0)
        self.write("prepared.json", json.dumps(prepared))
        args = ("--complete", "--base", self.base, "--prepared-plan", str(self.root / "prepared.json"),
                "--deliverable", "docs/INFORMATION/MCP_CANARY.md")
        self.assertNotEqual(self.check(*args)[0], 0)
        meta = dict(schema="wellmanifest.docs/document/v2", id="mcp-canary", kind="information",
            version=1, title="MCP canary", status="proposed", owner="wellmanifest/canary",
            scope="repository", updated="2026-09-19", source_revision=self.base,
            priority="P2", evidence=["repo://wellmanifest/canary@" + self.base + "/docs/README.md"])
        body = "\n".join("<!-- docs:section " + section + " -->\n## " + section + "\n\nCanary evidence.\n"
                         for section in ["summary", "details", "validation", "risks"])
        self.write("docs/INFORMATION/MCP_CANARY.md", "---\n" + json.dumps(meta) + "\n---\n# MCP canary\n" + body)
        self.write("docs/README.md", "[MCP canary](INFORMATION/MCP_CANARY.md)\n")
        self.git("add", "docs")
        code, result = self.check(*args)
        self.assertEqual(code, 0, result)
        prepared["plan"]["id"] = "wrong"
        self.write("prepared.json", json.dumps(prepared))
        self.assertNotEqual(self.check(*args)[0], 0)

    def test_symlinks_and_pin_overrides_fail_closed(self):
        target = self.root / "link"
        target.symlink_to(self.root / ".governance/docs.json")
        with self.assertRaises(ValueError):
            adapter.safe_bytes(self.root, "link")
        with self.assertRaises(ValueError):
            adapter.run(["--docs-root", ".", "--standard-revision", "0" * 40])
        with self.assertRaises(ValueError):
            adapter.run(["--docs-root", ".", "--managed-copies=unsafe.json"])

    def test_unpinned_governance_cannot_exclude_documents(self):
        with self.assertRaises(ValueError):
            self.write(".governance/manifest.lock.json", "{}")
            adapter.managed_inventory(self.root)


if __name__ == "__main__":
    unittest.main()
