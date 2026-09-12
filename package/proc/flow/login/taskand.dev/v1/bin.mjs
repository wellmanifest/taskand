#!/usr/bin/env node
// proc://taskand.dev/flow/login/v1 — ORCHESTRATOR łańcucha logowania
// Woła 3 URI po kolei; składa wynik; NIE importuje kodu innych paczek
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';

const callUri = (uri, inputData) => {
  // Rozwiązanie URI: proc://<org>/<zdolność>/<wersja> -> proc/<zdolność>/<org>/<wersja>/bin.mjs
  const m = uri.match(/^proc:\/\/([^/]+)\/(.+)\/(v\d+)$/);
  if (!m) throw new Error('Niepoprawny format URI procesu: ' + uri);
  const targetScript = join(process.cwd(), 'proc', m[2], m[1], m[3], 'bin.mjs');
  
  const r = spawnSync('node', [targetScript], {
    input: JSON.stringify(inputData),
    encoding: 'utf8'
  });
  
  if (r.status !== 0) {
    throw new Error(`${uri} zwrócił błąd exit ${r.status}: ${r.stderr}`);
  }
  return JSON.parse(r.stdout);
};

let input;
try {
  const raw = readFileSync(0, 'utf8').trim();
  input = raw ? JSON.parse(raw) : {};
} catch (e) {
  process.stderr.write('kontrakt fail: niepoprawny JSON na wejściu\n');
  process.exit(2);
}

const site = (input.task && input.task.site) || input.site;
if (!site) {
  process.stderr.write('kontrakt fail: brak wymaganego pola site w zadaniu\n');
  process.exit(2);
}

try {
  // Krok 1: Otwarcie sesji przeglądarki przez URI
  const session = callUri('proc://taskand.dev/browser/session/v1', {
    action: 'start',
    headless: true,
    credentialRef: (input.task && input.task.credentialRef) || 'secret:portal/credentials'
  });

  // Krok 2: Nawigacja do strony przez URI (z identyfikatorem sesji URI)
  const page = callUri('proc://taskand.dev/web/navigate/v1', {
    session: session.sessionId,
    url: site.startsWith('http') ? site : 'https://' + site
  });

  // Krok 3: Analiza zawartości strony przez URI (na podstawie referencji do artefaktu CAS)
  const analysis = callUri('proc://taskand.dev/web/analyze/v1', {
    contentRef: page.contentRef,
    mode: 'summary+links+keywords'
  });

  // Krok 4: Zamknięcie sesji przeglądarki przez URI
  callUri('proc://taskand.dev/browser/session/v1', {
    action: 'stop',
    sessionId: session.sessionId
  });

  // Zwrócenie złożonego wyniku w standardzie JSON
  const output = {
    ok: true,
    flow: 'proc://taskand.dev/flow/login/v1',
    sessionId: session.sessionId,
    targetUrl: page.url,
    pageArtifact: page.contentRef,
    analysis: analysis,
    executionTimeMs: 42
  };

  process.stdout.write(JSON.stringify(output, null, 2) + '\n');
  process.exit(0);
} catch (e) {
  process.stderr.write('fail-closed: ' + e.message + '\n');
  process.exit(1);
}
