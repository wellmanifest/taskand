# Ticket 010: Harden RFC3339 nanosecond timestamps, float overflow, UTF-8 surrogates, and modularize test suite

- **ID**: ticket-010
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-12

## Session authorization

- `SESSION_EXECUTION_AUTHORIZATION`: Autonomous execution, testing, and protected publication requested by the repository owner.

## Goal and scope

Harden `operations/delivery.py` and `operations/bundle.py` and modularize `tests/test_standard.py` (`operations/standard_fixtures.py`) so every Python module stays `< 500` lines after `ruff format`, regenerating `bundle.json`:

1. **RFC 3339 nanosecond & ASCII timestamp normalization (`operations/delivery.py`)**: Enforce `re.ASCII` on `_RFC3339_RE`, accept 1..9 fractional digits (normalizing 7..9 nanosecond digits cleanly for `datetime.fromisoformat`) and lowercase `t`/`z`, while rejecting `> 9` fractional digits, RFC 3339 §4.3 unknown local offset `-00:00`, and Unicode digits (`\u0662`).
2. **Float overflow, UTF-16 surrogates, ASCII schema patterns, & symlink-parent hardening**: Reject `1e309`/`-1e309` via `parse_float` and lone UTF-16 surrogates (`\ud800`..`\udfff`) in `operations/delivery.py` and `operations/bundle.py`; enforce `flags=re.ASCII` on `validate()` `pattern` checks; reject C1 controls, backslashes, lone surrogates, and whitespace-padded segments in `_is_unsafe_material_path()`; and enforce symlink-ancestor + `(st_dev, st_ino)` parity in `_read_regular_json()`.
3. **Catalog verification & `< 500`-line modularization**: Fix `operations/catalog.mjs` to honor positional package directory arguments (`make verify` / `node operations/catalog.mjs --verify package`), fail closed when `--verify` is passed on a missing catalog, and verify `testSha256` alongside `binSha256` and `yamlSha256`; extract `operations/standard_fixtures.py`, regenerate `bundle.json`, and mark merged `ticket-009` as `DONE`.

## Acceptance criteria

- [x] AC-01: `ruff check --no-cache`, `python3 operations/bundle.py --check`, `make test`, `./project/governance-check.sh --base origin/main`, and `wellman check` pass with 0 errors and all Python modules stay `< 500` lines after `ruff format`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
