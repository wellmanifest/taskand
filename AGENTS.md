# taskand manufacturing standard

HOME wellmanifest; SHAPE domain_pack. This repository owns the normative
taskand v1.0 standard specification, schemas, machine policy, reference
conformance checker, and the canonical reference package.

All system entities are URI resources (`proc://`, `session://`, `artifact:`).
Processes must execute fail-closed through JSON stdin/stdout with exit codes:
- 0: Success
- 1: Runtime execution error
- 2: Schema / contract mismatch

No process may import code across package boundaries (`zero cross-package imports`).
Credentials, secrets and tokens must never be persisted in Dockerfiles, Git commits,
or images; they are injected solely at runtime.

Evolution of packages must undergo qualification in the Digital Twin sandbox
(Gate A for contract & isolation, Gate B for regression & environment invariants)
before deployment.

When modifying the standard:
- Update `VERSION`, `policy.json`, and run `python3 operations/bundle.py` to regenerate `bundle.json`.
- Validate that all reference processes pass `make test` and `make conformance` (9/9).
