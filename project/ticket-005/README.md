# Ticket 005: Taskand MCP reuse and stable runtime guidance

- **ID**: ticket-005
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-19

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user request 2026-09-19 authorizes repairing
local MCP startup and documenting Taskand reuse in the owning Wellmanifest
standards. Intake: Taskand Planfile PLF-005. This ticket owns only Taskand
integration and runtime guidance, not product code or authority policy.
No schema change, production deployment or secret access.

Publication continuation: user explicitly authorized the proposed protected
PR/review/merge path on 2026-09-19. Intake PLF-007 follows completed local
PLF-005. Dependency ticket-006 was independently reviewed and merged in PR #5.
The new accepted base is that observed merge, not an unreviewed local adoption.

2026-09-19 continuation: user explicitly authorized Docs adoption and metadata
repair. Dependency ticket-006 supplies the pinned local checker. This slice
repairs evolution metadata, refreshes its bundle and patch version, and adds
the two indexed MCP guides. Existing normative contract semantics are unchanged.

## Acceptance criteria

- [x] AC-01: Describe both MCP directions, concrete tools, grants and missing adoption.
- [x] AC-02: Document reproducible startup repair and bounded conformance tests.
- [x] AC-03: Documentation and managed governance checks pass.

## Tracking boundary

Current boundary: local material delivery validated on dependency ticket-006.
Both Docs completion checks and managed governance passed; make test passed
bundle validation, 9 legacy conformance cases and 46 unit tests. The original
blocker below is historical and resolved by the explicitly authorized adoption.
At the initial local boundary there was no push, PR or merge. Publication now
proceeds through the protected Validator; no protected CI rollout or Taskand
MCP client implementation is included.

2026-09-19: Documentation generation stopped before material writes because
wellmanifest/docs 19efafbeb18923cfd51cc69bd519330488500137 --prepare failed:
missing .governance/docs.json; managed SNAPSHOT_MIGRATION.md is not resolved
through a trusted managed-copy inventory; evolution.md has unqualified evidence
references. Next: authorize bounded Docs adoption/metadata repair in the owning
governance and integration scopes, then rerun prepare. No lease was acquired,
no documentation generated, no commit or remote effect. The host MCP repair is
separate, locally verified under PLF-005. At that boundary this ticket was not delivered.

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
