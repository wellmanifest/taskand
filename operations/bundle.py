"""Build or verify the exact, portable standard adoption projection."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import math
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
MAX_BUNDLE_FILE_BYTES = 4_194_304
FILES = (
    "VERSION",
    "policy.json",
    "schemas/capsule.v1.json",
    "schemas/grants.v1.json",
    "schemas/proc.v1.json",
    "schemas/catalog.v1.json",
    "schemas/envelope.v1.json",
    "schemas/envelope.v2.json",
    "schemas/delivery-observation.v1.json",
    "schemas/browser-command.v1.json",
    "schemas/browser-session.v1.json",
    "schemas/app-state.v1.json",
    "docs/standard.md",
    "docs/secrets.md",
    "docs/digital-twin.md",
    "docs/information/evolution.md",
    "docs/information/taskand-evolution.md",
    "operations/bundle.py",
    "operations/delivery.py",
    "operations/standard_fixtures.py",
    "operations/catalog.mjs",
    "operations/new_package.sh",
    "operations/conformance.mjs",
    "operations/runner.mjs",
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(token: str) -> NoReturn:
    raise ValueError(f"Non-finite JSON constant: {token}")


def _parse_finite_float(token: str) -> float:
    val = float(token)
    if not math.isfinite(val):
        raise ValueError(f"Non-finite JSON float: {token}")
    return val


def _reject_surrogates(value: Any) -> None:
    stack = [value]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            if any(0xD800 <= ord(ch) <= 0xDFFF for ch in cur):
                raise ValueError("Lone UTF-16 surrogate in JSON input")
        elif isinstance(cur, dict):
            for key, item in cur.items():
                if isinstance(key, str) and any(
                    0xD800 <= ord(ch) <= 0xDFFF for ch in key
                ):
                    raise ValueError("Lone UTF-16 surrogate in JSON key")
                stack.append(item)
        elif isinstance(cur, list):
            stack.extend(cur)


def _read_regular_bytes(
    root_dir: Path, relpath: str, max_bytes: int = MAX_BUNDLE_FILE_BYTES
) -> bytes:
    parts = PurePosixPath(relpath).parts
    if not parts or parts[0] == "/" or ".." in parts or "." in parts:
        raise ValueError(f"Invalid bundle relative path: {relpath}")
    dir_flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = (
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        cur_fd = os.open(root_dir, dir_flags)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValueError(f"Symlink or non-directory root: {root_dir}") from exc
        raise
    try:
        for segment in parts[:-1]:
            try:
                next_fd = os.open(segment, dir_flags, dir_fd=cur_fd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise ValueError(
                        f"Symlink or non-directory segment in {relpath}"
                    ) from exc
                raise
            os.close(cur_fd)
            cur_fd = next_fd
        try:
            file_fd = os.open(parts[-1], file_flags, dir_fd=cur_fd)
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.EISDIR):
                raise ValueError(
                    f"Symlink or directory rejected for {relpath}"
                ) from exc
            raise
    finally:
        os.close(cur_fd)
    try:
        st = os.fstat(file_fd)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise ValueError(f"Expected regular file for {relpath}")
        if st.st_size > max_bytes:
            raise ValueError(f"Bundled file exceeds byte limit: {relpath}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(file_fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"Bundled file exceeds byte limit: {relpath}")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(file_fd)


def _loads_strict(raw: bytes) -> Any:
    decoded = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_nonfinite_json,
        parse_float=_parse_finite_float,
    )
    _reject_surrogates(decoded)
    return decoded


def _atomic_write_text(target: Path, content: str) -> None:
    try:
        st = os.lstat(target)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise ValueError("bundle.json target must be a regular non-symlink file")
    except FileNotFoundError:
        pass
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".bundle.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, target)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    version = _read_regular_bytes(ROOT, "VERSION").decode("utf-8").strip()
    policy = _loads_strict(_read_regular_bytes(ROOT, "policy.json"))
    if policy["version"] != version:
        raise ValueError("Policy and release versions differ")
    discovered_schemas = {
        path.relative_to(ROOT).as_posix() for path in (ROOT / "schemas").glob("*.json")
    }
    if discovered_schemas - set(FILES):
        raise ValueError("Normative schema omitted from bundle")
    result = {
        "schema": "wellmanifest.taskand/bundle/v1",
        "standard": "wellmanifest/taskand",
        "version": version,
        "files": {
            name: hashlib.sha256(_read_regular_bytes(ROOT, name)).hexdigest()
            for name in FILES
        },
    }
    target = ROOT / "bundle.json"
    if args.check:
        if not target.exists() and not target.is_symlink():
            raise ValueError(
                "bundle.json missing; run operations/bundle.py to generate"
            )
        if _loads_strict(_read_regular_bytes(ROOT, "bundle.json")) != result:
            raise ValueError(
                "Standard bundle drift; regenerate within the material change"
            )
    else:
        _atomic_write_text(target, json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Standard bundle: verified" if args.check else "Standard bundle: built")


if __name__ == "__main__":
    main()
