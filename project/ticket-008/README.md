# Ticket 008: application state lifecycle schema and closed-loop resume contract

- **ID**: ticket-008
- **Owner**: agent:claude
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-06

## Goal and scope

Standardize Universal Application State Lifecycle Schema (`schemas/app-state.v1.json`) and closed-loop resume verification assertions for stateful applications (GUI, TUI, Browser, Daemons) within `taskand` task execution graphs. Reconcile historical merged ticket statuses.

## Acceptance criteria

- [x] AC-01: Standardize JSON Schema `schemas/app-state.v1.json` supporting application kinds `gui_x11`, `tui_terminal`, `browser_cdp`, and `service_daemon`.
- [x] AC-02: Document application state lifecycle contract and closed-loop assertions in `docs/information/app-state-contract.md`.
- [x] AC-03: Register schema in `operations/bundle.py`, regenerate `bundle.json`, and verify with `tests/test_standard.py`.
- [x] AC-04: Reconcile historical merged tickets to DONE.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
