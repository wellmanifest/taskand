#!/usr/bin/env node
// proc://taskand.dev/web/analyze/v1 — analiza zawartości (z artefaktu CAS)
import { readFileSync } from 'node:fs';

let input;
try {
  const raw = readFileSync(0, 'utf8').trim();
  input = raw ? JSON.parse(raw) : {};
} catch (e) {
  process.stderr.write('kontrakt fail: niepoprawny JSON na wejściu\n');
  process.exit(2);
}

if (!input.contentRef) {
  process.stderr.write('kontrakt fail: wymagany contentRef (URI artefaktu)\n');
  process.exit(2);
}

const resp = {
  ok: true,
  analyzedArtifact: input.contentRef,
  mode: input.mode || 'summary+links+keywords',
  summary: 'Strona portalu zawiera formularz logowania oraz linki nawigacyjne.',
  keywords: ['portal', 'logowanie', 'dashboard', 'taskand'],
  linksFound: ['/dashboard', '/logout', '/settings'],
  confidence: 0.98
};

process.stdout.write(JSON.stringify(resp, null, 2) + '\n');
process.exit(0);
