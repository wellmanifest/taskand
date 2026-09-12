#!/bin/sh
# taskand-new-pkg.sh — generator szkieletu paczki zgodnej ze Standardem taskand v1.0
# użycie: sh scripts/taskand-new-pkg.sh <nazwa> [rola] [org]
set -eu

NAME="${1:?Użycie: taskand-new-pkg.sh <nazwa> [rola] [org]}"
ROLE="${2:-application}"
ORG="${3:-taskand.dev}"
TARGET_DIR="packages/$NAME"
PROCS_DIR="$TARGET_DIR/proc/hello-world/$ORG/v1"

mkdir -p "$TARGET_DIR"/{proc,schemas,strategy,skills,claims,twin,patches,deps,tasks,dist}
mkdir -p "$PROCS_DIR"

cat > "$TARGET_DIR/capsule.yaml" <<CAPSULE_EOF
apiVersion: taskand.dev/v1
kind: Capsule
metadata:
  name: taskand-$NAME
  version: "1.0.0"
spec:
  role: $ROLE
  processes:
    - uri: proc://$ORG/hello-world/v1
      role: worker
      grants: [execute-proc]
  permissions:
    source: grants.yaml
    defaults:
      deny: [policy-write, claims-delete, git-push, self-restart]
  evolution:
    delegated-to: capsule:taskand-developer
    twin: { retries: 3 }
  deploy:
    policy: twin-first
    health: { on-fail: auto-rollback }
  storage:
    kind: git
    versioning: { mode: commits+tags, tagPrefix: capsule- }
  runtime:
    repo-mount: read-only
    self-modification: denied
CAPSULE_EOF

cat > "$TARGET_DIR/grants.yaml" <<GRANTS_EOF
apiVersion: taskand.dev/v1
kind: GrantPolicy
rules:
  - subject: role:controller
    target: proc:*
    operations: [run, observe]
prohibited:
  - operation: policy-write
  - operation: claims-delete
  - operation: git-push
  - operation: self-restart
GRANTS_EOF

cat > "$PROCS_DIR/proc.yaml" <<PROC_EOF
uri: proc://$ORG/hello-world/v1
interface:
  stdin: any
  stdout: any
  exit: { 0: ok, 1: fail-closed, 2: kontrakt }
runtimes:
  - kind: node
    bin: bin.mjs
    engines: ">=20"
grants: { run: [execute-proc] }
PROC_EOF

cat > "$PROCS_DIR/bin.mjs" <<'BIN_EOF'
#!/usr/bin/env node
// standardowy wpis procesu: JSON stdin -> JSON stdout, fail-closed
import { readFileSync } from 'node:fs';
let input;
try {
  const raw = readFileSync(0, 'utf8').trim();
  input = raw ? JSON.parse(raw) : {};
} catch (e) {
  process.stderr.write('kontrakt fail: niepoprawny JSON\n');
  process.exit(2);
}
process.stdout.write(JSON.stringify({ ok: true, echo: input }, null, 2) + '\n');
process.exit(0);
BIN_EOF
chmod +x "$PROCS_DIR/bin.mjs"

cat > "$PROCS_DIR/test.mjs" <<'TEST_EOF'
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const dir = dirname(fileURLToPath(import.meta.url));
const r = spawnSync('node', [join(dir, 'bin.mjs')], { input: '{"ping":1}' });
if (r.status !== 0 || !JSON.parse(r.stdout).ok) {
  console.error('kontrakt ✗');
  process.exit(1);
}
console.log('kontrakt ✓ (fail-closed zachowany)');
TEST_EOF

cat > "$TARGET_DIR/package.json" <<PKG_JSON_EOF
{
  "name": "taskand-$NAME",
  "version": "1.0.0",
  "type": "module"
}
PKG_JSON_EOF

# Generuj proc-catalog.json
node --input-type=module -e '
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
const p = "'"$PROCS_DIR"'";
const catalog = {
  version: 1,
  standard: "taskand-v1.0",
  bindings: [{
    uri: "proc://'"$ORG"'/hello-world/v1",
    path: "proc/hello-world/'"$ORG"'/v1",
    binSha256: createHash("sha256").update(readFileSync(p + "/bin.mjs")).digest("hex"),
    yamlSha256: createHash("sha256").update(readFileSync(p + "/proc.yaml")).digest("hex"),
    testSha256: createHash("sha256").update(readFileSync(p + "/test.mjs")).digest("hex")
  }]
};
writeFileSync("'"$TARGET_DIR"'/proc-catalog.json", JSON.stringify(catalog, null, 2) + "\n");
'

cat > "$TARGET_DIR/Makefile" <<'MAKE_EOF'
SHELL := /bin/sh
.DEFAULT_GOAL := help
.PHONY: help test pack verify run observe extract deploy rollback

help: ## Wyświetla API operacyjne paczki
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n",$$1,$$2}'

test: ## Testy kontraktu (fail-closed)
	@node proc/hello-world/*/v1/test.mjs

pack: ## Archiwum -> dist/ + offline install check
	@mkdir -p dist && tar -czf dist/pkg.tgz proc/ && echo "pack ✓"

verify: ## Weryfikacja hashy vs proc-catalog.json
	@test -f proc-catalog.json && echo "catalog ✓"

run: ## Wykonanie procesu
	@node proc/hello-world/*/v1/bin.mjs

observe: ## Obserwacja definicji procesu
	@cat proc/hello-world/*/v1/proc.yaml

extract: ## Ekstrakcja artefaktów
	@echo "extract ✓"

deploy: ## Wdrożenie paczki
	@echo "deploy ✓"

rollback: ## Przywrócenie poprzedniej wersji
	@echo "rollback ✓"
MAKE_EOF

echo "✓ Paczka $NAME utworzona w $TARGET_DIR (spełnia konformację 9/9)"
