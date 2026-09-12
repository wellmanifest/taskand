import { spawnSync } from 'node:child_process';

// Test 1: start sesji
const r1 = spawnSync('node', ['proc/browser/session/taskand.dev/v1/bin.mjs'], {
  input: JSON.stringify({ action: 'start', headless: true })
});
if (r1.status !== 0) {
  console.error('Test 1 fail:', r1.stderr.toString());
  process.exit(1);
}
const res1 = JSON.parse(r1.stdout.toString());
if (!res1.sessionId || !res1.sessionId.startsWith('session://browser/')) {
  console.error('Test 1 invalid output:', res1);
  process.exit(1);
}

// Test 2: stop sesji
const r2 = spawnSync('node', ['proc/browser/session/taskand.dev/v1/bin.mjs'], {
  input: JSON.stringify({ action: 'stop', sessionId: res1.sessionId })
});
if (r2.status !== 0) {
  console.error('Test 2 fail:', r2.stderr.toString());
  process.exit(1);
}

// Test 3: fail-closed na pustym wejściu (exit 2)
const r3 = spawnSync('node', ['proc/browser/session/taskand.dev/v1/bin.mjs'], { input: '' });
if (r3.status !== 2) {
  console.error('Test 3 fail: oczekiwano exit 2, otrzymano', r3.status);
  process.exit(1);
}

console.log('proc://taskand.dev/browser/session/v1: testy kontraktu ✓ (fail-closed zachowany)');
