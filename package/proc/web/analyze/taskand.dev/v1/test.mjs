import { spawnSync } from 'node:child_process';

const r1 = spawnSync('node', ['proc/web/analyze/taskand.dev/v1/bin.mjs'], {
  input: JSON.stringify({ contentRef: 'artifact:page-content@sha256:abc12345' })
});
if (r1.status !== 0) {
  console.error('Test fail:', r1.stderr.toString());
  process.exit(1);
}
const res = JSON.parse(r1.stdout.toString());
if (!res.keywords || res.keywords.length === 0) {
  console.error('Brak słów kluczowych');
  process.exit(1);
}

const r2 = spawnSync('node', ['proc/web/analyze/taskand.dev/v1/bin.mjs'], { input: '{}' });
if (r2.status !== 2) {
  console.error('Test kontrakt fail: oczekiwano exit 2');
  process.exit(1);
}

console.log('proc://taskand.dev/web/analyze/v1: testy kontraktu ✓ (fail-closed zachowany)');
