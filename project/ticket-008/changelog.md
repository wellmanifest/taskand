# Changelog: Ticket 008

## Added
- `schemas/app-state.v1.json`: Universal application state lifecycle schema for GUI, TUI, Browser, and Daemon checkpoints.
- `docs/information/app-state-contract.md`: Specification of state models and closed-loop resume assertions.
- `tests/test_standard.py`: Unit test coverage for `taskand.app-state/v1` schema validation.

## Changed
- `operations/bundle.py`: Registered `schemas/app-state.v1.json` in normative bundle files.
- `bundle.json`: Regenerated bundle projection.
- `project/ticket-00{4,5,6,7}/README.md`: Reconciled merged tickets to DONE.
