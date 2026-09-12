import { spawnSync } from 'node:child_process';

const r1 = spawnSync('node', ['proc/flow/login/taskand.dev/v1/bin.mjs'], {
  input: JSON.stringify({ task: { site: 'portal.example.com', credentialRef: 'secret:portal/auth' } })
});
if (r1.status !== 0) {
  console.error('Test flow fail:', r1.stderr.toString());
  process.exit(1);
}
const res = JSON.parse(r1.stdout.toString());
if (!res.ok || !res.pageArtifact || !res.analysis) {
  console.error('Test flow: niepoprawna odpowiedź:', res);
  process.exit(1);
}

const r2 = spawnSync('node', ['proc/flow/login/taskand.dev/v1/bin.mjs'], { input: '{}' });
if (r2.status !== 2) {
  console.error('Test kontrakt fail: oczekiwano exit 2');
  process.exit(1);
}

console.log('proc://taskand.dev/flow/login/v1: testy kontraktu ✓ (cały łańcuch URI przeszedł pomyślnie)');
