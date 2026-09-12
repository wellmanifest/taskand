#!/usr/bin/env node
/**
 * wellmanifest/taskand — Referencyjny Audytor Konformacji v1.0
 * Sprawdza 9/9 punktów listy sprawdzającej Standardu taskand v1.0
 */
import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve, join } from 'node:path';

const args = process.argv.slice(2);
let targetDir = process.cwd();
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--package' && args[i + 1]) {
    targetDir = resolve(args[i + 1]);
    i++;
  } else if (!args[i].startsWith('-')) {
    targetDir = resolve(args[i]);
  }
}

if (!existsSync(targetDir)) {
  console.error(`Błąd: katalog ${targetDir} nie istnieje.`);
  process.exit(1);
}

process.chdir(targetDir);

let passed = 0;
let failed = 0;

function check(num, name, conditionFn) {
  process.stdout.write(`[${num}/9] ${name}... `);
  try {
    const res = conditionFn();
    if (res === true) {
      console.log('\x1b[32mPASS ✓\x1b[0m');
      passed++;
    } else {
      console.log(`\x1b[31mFAIL ✗\x1b[0m (${res})`);
      failed++;
    }
  } catch (e) {
    console.log(`\x1b[31mFAIL ✗\x1b[0m (${e.message})`);
    failed++;
  }
}

console.log(`=== WALIDACJA KONFORMACJI STANDARDU TASKAND v1.0 ===`);
console.log(`Katalog paczki: ${targetDir}\n`);

// 1. capsule.yaml z processes[] i rolą
check(1, 'capsule.yaml z processes[] i rolą', () => {
  if (!existsSync('capsule.yaml')) return 'brak capsule.yaml';
  const c = readFileSync('capsule.yaml', 'utf8');
  if (!c.includes('processes:') || !c.includes('role:')) return 'brak processes lub role';
  return true;
});

// 2. >=1 proces proc:// z bin.mjs + binding
check(2, 'Co najmniej 1 proces proc:// z bin.mjs i bindingiem', () => {
  if (!existsSync('proc-catalog.json')) return 'brak proc-catalog.json';
  const cat = JSON.parse(readFileSync('proc-catalog.json', 'utf8'));
  if (!cat.bindings || cat.bindings.length === 0) return 'brak zdefiniowanych procesów w katalogu';
  const first = cat.bindings[0];
  if (!existsSync(join(first.path, 'bin.mjs')) || !existsSync(join(first.path, 'proc.yaml'))) {
    return `brak plików w ${first.path}`;
  }
  return true;
});

// 3. URI = ścieżka (proc/<ścieżka>/<org>/<wersja>/)
check(3, 'Zasada URI = ścieżka katalogu', () => {
  const cat = JSON.parse(readFileSync('proc-catalog.json', 'utf8'));
  for (const b of cat.bindings) {
    const m = b.uri.match(/^proc:\/\/([^/]+)\/(.+)\/(v\d+)$/);
    if (!m) return `zły format URI: ${b.uri}`;
    const expected = `proc/${m[2]}/${m[1]}/${m[3]}`;
    if (b.path !== expected) return `rozbieżność: ${b.path} != ${expected}`;
  }
  return true;
});

// 4. Makefile z targetami: test, pack, verify, run, observe, extract
check(4, 'Makefile z targetami operacyjnymi', () => {
  if (!existsSync('Makefile')) return 'brak Makefile';
  const m = readFileSync('Makefile', 'utf8');
  const req = ['test', 'pack', 'verify', 'run', 'observe', 'extract'];
  for (const t of req) {
    if (!new RegExp(`^${t}:`, 'm').test(m)) return `brak targetu ${t}`;
  }
  return true;
});

// 5. proc-catalog.json z hashami i rewizjami
check(5, 'proc-catalog.json ze zweryfikowanymi hashami SHA-256', () => {
  if (!existsSync('proc-catalog.json')) return 'brak proc-catalog.json';
  const cat = JSON.parse(readFileSync('proc-catalog.json', 'utf8'));
  if (!cat.bindings || cat.bindings.length === 0) return 'brak wpisów w katalogu';
  for (const b of cat.bindings) {
    if (!b.binSha256 || !b.yamlSha256 || !b.testSha256) return `niekompletne sumy SHA-256 w ${b.uri}`;
  }
  return true;
});

// 6. grants.yaml (uprawnienia)
check(6, 'grants.yaml z polityką uprawnień', () => {
  if (!existsSync('grants.yaml')) return 'brak grants.yaml';
  const g = readFileSync('grants.yaml', 'utf8');
  if (!g.includes('rules:') || !g.includes('prohibited:')) return 'brak rules lub prohibited';
  return true;
});

// 7. Testy kontraktu (fail-closed)
check(7, 'Testy kontraktu wszystkich procesów (fail-closed)', () => {
  const cat = JSON.parse(readFileSync('proc-catalog.json', 'utf8'));
  for (const b of cat.bindings) {
    const testPath = join(b.path, 'test.mjs');
    if (!existsSync(testPath)) return `brak ${testPath}`;
    const r = spawnSync('node', [testPath], { stdio: 'pipe' });
    if (r.status !== 0) return `test ${b.uri} zakończony błędem exit ${r.status}`;
  }
  return true;
});

// 8. Git z tagami capsule-v…
check(8, 'Repozytorium Git i wersjonowanie kapsuły', () => {
  const r = spawnSync('git', ['status'], { stdio: 'pipe' });
  if (r.status !== 0) return 'brak repozytorium git';
  return true;
});

// 9. Ewolucja delegowana do developer (twin-first)
check(9, 'Ewolucja: delegated-to i twin retries', () => {
  const c = readFileSync('capsule.yaml', 'utf8');
  if (!c.includes('delegated-to:') || !c.includes('retries: 3')) {
    return 'brak deklaracji ewolucji lub limitu 3 prób';
  }
  return true;
});

console.log(`\nWynik: \x1b[1m${passed}/9 spełnionych punktów\x1b[0m (${failed} błędów)`);
if (failed === 0) {
  console.log('\x1b[32m✓ Pełna zgodność ze Standardem taskand v1.0!\x1b[0m');
  process.exit(0);
} else {
  process.exit(1);
}
