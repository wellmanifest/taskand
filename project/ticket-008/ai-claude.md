# Agent Plan: Ticket 008

## Overview
Standardize Universal Application State Lifecycle Schema (`schemas/app-state.v1.json`) and closed-loop resume verification assertions for stateful applications (GUI, TUI, Browser, Daemons) within `taskand` task execution graphs.

## Execution Steps
1. Create `schemas/app-state.v1.json` validating application kinds: `gui_x11`, `tui_terminal`, `browser_cdp`, and `service_daemon`.
2. Document application state lifecycle contract in `docs/information/app-state-contract.md`.
3. Add `schemas/app-state.v1.json` to `operations/bundle.py` and regenerate `bundle.json`.
4. Add unit test suite `AppStateSchemaTests` to `tests/test_standard.py`.
5. Reconcile merged historical tickets 004, 005, 006, 007 to DONE.
6. Verify governance check and test suite.
