# Ticket 006: Adopt pinned Docs gate for MCP guidance

- **ID**: ticket-006
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-19

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user explicitly approved expanding Docs
adoption and metadata repair on 2026-09-19. PLF-005 continuation.
This ticket owns the governance adapter and pin; existing integration tickets
own documentation/index/metadata. The initial delivery was local only.

Publication continuation, 2026-09-19: the user answered "kontynuuj" to the
explicit proposal to publish the four existing Wellmanifest slices through
protected PR/review/merge, leaving runtime ticket-029 with its current owner.
This authorizes push and PR plus invocation of the independently deployed
Validator, not self-approval or direct merge. No protected policy/CI changes.

## Acceptance criteria

- [x] AC-01: Immutable Docs execution, independently bound managed copies and negative canaries pass (7 tests).
- [x] AC-02: Managed governance passes; protected CI adoption remains separately reported.

Local validation: full existing managed inventory matches its independently
bound lock; historical merged adoption reservation reconciled from GitHub
read-back plus managed Git ancestry/patch verification, without closure edits.
The Docs adapter is an explicit local entry point, not a deployed protected CI
gate. Existing product metadata is repaired by the dependent integration ticket.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
