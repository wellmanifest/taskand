# Ticket 009: Harden delivery evaluator and bundle regular-file verification

- **ID**: ticket-009
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

Harden `operations/delivery.py`, `operations/bundle.py`, and `tests/test_standard.py` (regenerating `bundle.json`) while keeping all owned Python modules strictly under 500 lines:
- Cache and load `schemas/delivery-observation.v1.json` via `O_NOFOLLOW | O_NONBLOCK` regular-file verification with duplicate-key and non-finite JSON constant rejection.
- Harden `validate()` to support composite `uniqueItems` checks without `TypeError`, enforce `additionalProperties` cleanly, reject `NaN`/`Infinity` on CLI/API paths (`allow_nan=False`), reject `DEL` (`0x7f`) control characters in material paths, and remove unreachable duplicate `not known` branch in `evaluate()`.
- Harden `operations/bundle.py` with descriptor-relative `O_DIRECTORY | O_NOFOLLOW` regular-file reads, strict JSON parsing, and atomic `bundle.json` writes.

## Acceptance criteria

- [x] AC-01: `operations/delivery.py` rejects non-finite JSON constants, composite duplicate items, symlinked schema files, and control-character paths while caching the bundled schema.
- [x] AC-02: `operations/bundle.py` enforces symlink-free regular-file reads, strict JSON parsing, and regenerated `bundle.json` passes `operations/bundle.py --check`.
- [x] AC-03: Unit tests, `ruff`, `./project/governance-check.sh`, and `wellman check` pass with all owned Python modules under 500 lines.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
