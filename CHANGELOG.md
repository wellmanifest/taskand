# Changelog

All notable changes to the taskand standard are documented in this file.

## [1.0.0] - 2026-09-12

### Added
- Initial specification of **Standard taskand v1.0** (13 normative sections).
- Machine policy `policy.json` with 10 requirements (TKD-001 to TKD-010).
- JSON Schemas: `capsule.v1.json`, `grants.v1.json`, `proc.v1.json`, `catalog.v1.json`, `envelope.v1.json`.
- Operational tools:
  - `operations/conformance.mjs` (automated 9/9 checklist auditor).
  - `operations/runner.mjs` (universal URI runner with zero code imports).
  - `operations/catalog.mjs` (SHA-256 process catalog generator and verifier).
  - `operations/new_package.sh` (9/9 conforming package generator).
  - `operations/bundle.py` (standard bundle hash tracker).
- Reference package implementation in `package/`:
  - `proc://taskand.dev/flow/login/v1` (orchestrator).
  - `proc://taskand.dev/browser/session/v1` (worker).
  - `proc://taskand.dev/web/navigate/v1` (worker).
  - `proc://taskand.dev/web/analyze/v1` (worker).
  - Digital Twin configuration (`twin/qualification.yaml`, `twin/twin.compose.yaml`).
  - Knowledge claims (`claims/`).
  - Strict permissions and prohibited baseline (`grants.yaml`).
- Architecture documentation for secrets management (`docs/secrets.md`) and Digital Twin (`docs/digital-twin.md`).
