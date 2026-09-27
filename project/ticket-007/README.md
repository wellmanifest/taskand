# Ticket 007: add standard Apache-2.0 LICENSE file

- **ID**: ticket-007
- **Owner**: human:tom
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

1. Add the standard Apache License Version 2.0 (`LICENSE`) file to the root of the repository.
2. Update `.governance/manifest.json` to register `LICENSE` under `governance.ownedPaths`.
3. Resolve autodiagnosis hygiene item: `NO_LICENSE` in `wellmanifest/taskand`.
4. Verify standard test suite and conformance pass cleanly (`pytest tests/test_standard.py`).

## Acceptance criteria

- [x] AC-01: Standard Apache-2.0 `LICENSE` file is present in repository root.
- [x] AC-02: `.governance/manifest.json` lists `LICENSE` in governance ownedPaths.
- [x] AC-03: Governance checks pass (`./project/governance-check.sh` -> `GOV-PASS`).
- [x] AC-04: Test suite `pytest tests/test_standard.py` passes cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
