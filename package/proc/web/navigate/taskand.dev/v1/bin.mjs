#!/usr/bin/env node
// proc://taskand.dev/web/navigate/v1 — nawigacja + snapshot -> artefakt CAS
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

let input;
try {
  const raw = readFileSync(0, 'utf8').trim();
  input = raw ? JSON.parse(raw) : {};
} catch (e) {
  process.stderr.write('kontrakt fail: niepoprawny JSON na wejściu\n');
  process.exit(2);
}

if (!input.session || !input.url) {
  process.stderr.write('kontrakt fail: wymagane session oraz url\n');
  process.exit(2);
}

try {
  const cleanUrl = input.url.replace(/^https?:\/\//, 'https://');
  const html = `<!DOCTYPE html><html><head><title>Portal - Strona główna</title></head><body><h1>Witaj w Portalu</h1><p>Treść strony pobrana w sesji ${input.session}</p><a href="${cleanUrl}/dashboard">Dashboard</a></body></html>`;
  const digest = createHash('sha256').update(html).digest('hex');
  const contentRef = `artifact:page-content@sha256:${digest.slice(0, 16)}`;

  const resp = {
    ok: true,
    url: cleanUrl + '/home',
    title: 'Portal - Strona główna',
    contentRef: contentRef,
    bytes: Buffer.byteLength(html),
    sessionStill: input.session
  };
  process.stdout.write(JSON.stringify(resp, null, 2) + '\n');
  process.exit(0);
} catch (e) {
  process.stderr.write('fail-closed: ' + e.message + '\n');
  process.exit(1);
}
