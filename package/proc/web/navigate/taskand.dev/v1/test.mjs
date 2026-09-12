import { spawnSync } from 'node:child_process';

const r1 = spawnSync('node', ['proc/web/navigate/taskand.dev/v1/bin.mjs'], {
  input: JSON.stringify({ session: 'session://browser/s-test', url: 'example.com' })
});
if (r1.status !== 0) {
  console.error('Test fail:', r1.stderr.toString());
  process.exit(1);
}
const res = JSON.parse(r1.stdout.toString());
if (!res.contentRef || !res.contentRef.startsWith('artifact:page-content@sha256:')) {
  console.error('Brak poprawnego contentRef:', res);
  process.exit(1);
}

// Test fail-closed
const r2 = spawnSync('node', ['proc/web/navigate/taskand.dev/v1/bin.mjs'], { input: '{}' });
if (r2.status !== 2) {
  console.error('Test kontrakt fail: oczekiwano exit 2');
  process.exit(1);
}

console.log('proc://taskand.dev/web/navigate/v1: testy kontraktu ✓ (fail-closed zachowany)');
