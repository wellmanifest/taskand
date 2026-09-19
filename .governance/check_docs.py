"""Pinned local Docs gate. CI must independently select this adapter and its inputs.

Usage: python3 .governance/check_docs.py --docs-root /trusted/docs --root .
       --prepare --format v2 --scope repository --kind information --id ...
       --deliverable docs/INFORMATION/....md
Completion additionally requires --base, --complete and --prepared-plan.
No fetch, generation, Git mutation, publication or approval is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

DOCS_REVISION = "19efafbeb18923cfd51cc69bd519330488500137"
POLICY_SHA = "fac05e720ec49370ba393e817a4a03b895d7ed33828e09b3420f9fcfb09264b0"
GOVERNANCE_LOCK_SHA = "5d70a186f2fc4fcb5429d91ff9ad389a9f071d70aa37edd46f6019ff0d469c0f"


def safe_bytes(root, name):
    path = root / name
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("DOCS_ADAPTER_PATH")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("DOCS_ADAPTER_SYMLINK")
    return path.read_bytes()


def managed_inventory(root):
    raw = safe_bytes(root, ".governance/manifest.lock.json")
    if hashlib.sha256(raw).hexdigest() != GOVERNANCE_LOCK_SHA:
        raise ValueError("DOCS_ADAPTER_GOVERNANCE_PIN")
    lock = json.loads(raw)
    # The full pre-existing published inventory is bound above, not taken
    # from a candidate document or a caller-supplied exclusion list.
    for name, digest in lock["managedFiles"].items():
        if hashlib.sha256(safe_bytes(root, name)).hexdigest() != digest:
            raise ValueError("DOCS_ADAPTER_MANAGED_DRIFT:" + name)
    return {name: digest for name, digest in lock["managedFiles"].items()
            if name.startswith(".governance/docs/") and name.endswith(".md")}


def export_checker(source, destination):
    # Read immutable Git objects, never execute the provider's dirty checkout.
    listing = subprocess.check_output(
        ["git", "-C", str(source), "ls-tree", "-r", "-z", DOCS_REVISION, "--", "docs/standard"])
    count = 0
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        header, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        name = raw_name.decode()
        if mode not in {"100644", "100755"} or kind != "blob" or ".." in Path(name).parts:
            raise ValueError("DOCS_ADAPTER_SOURCE_TYPE")
        if not name.startswith("docs/standard/"):
            raise ValueError("DOCS_ADAPTER_SOURCE_PATH")
        data = subprocess.check_output(["git", "-C", str(source), "cat-file", "blob", oid])
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        count += 1
    policy = destination / "docs/standard/policy.json"
    if count == 0 or hashlib.sha256(policy.read_bytes()).hexdigest() != POLICY_SHA:
        raise ValueError("DOCS_ADAPTER_POLICY_PIN")
    return destination / "docs/standard/check.py"


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-root", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args, forwarded = parser.parse_known_args(argv)
    # Standard and exclusions cannot be replaced through forwarding.
    forbidden = {"--standard-revision", "--managed-copies", "--fleet", "--namespace", "--root"}
    if any(arg.split("=", 1)[0] in forbidden for arg in forwarded):
        raise ValueError("DOCS_ADAPTER_OVERRIDE")
    root = args.root.absolute()
    inventory = managed_inventory(root)
    with tempfile.TemporaryDirectory(prefix="wellmanifest-docs-") as temporary:
        directory = Path(temporary)
        checker = export_checker(args.docs_root, directory)
        copies = directory / "managed-copies.json"
        copies.write_text(json.dumps(inventory))
        return subprocess.run(
            [sys.executable, "-I", str(checker), "--root", str(root),
             "--standard-revision", DOCS_REVISION, "--managed-copies", str(copies), *forwarded],
            check=False, timeout=120).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(2)
