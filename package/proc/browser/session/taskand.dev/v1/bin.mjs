#!/usr/bin/env node
// proc://taskand.dev/browser/session/v1 — sesja przeglądarki jako ZASÓB URI
import { readFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';

let input;
try {
  const raw = readFileSync(0, 'utf8').trim();
  input = raw ? JSON.parse(raw) : {};
} catch (e) {
  process.stderr.write('kontrakt fail: niepoprawny JSON na wejściu\n');
  process.exit(2);
}

if (!input.action) {
  process.stderr.write('kontrakt fail: brak wymaganego pola action\n');
  process.exit(2);
}

const sid = 'session://browser/s-' + randomBytes(4).toString('hex');

if (input.action === 'start') {
  const container = 'taskand-browser-' + Date.now();
  const resp = {
    ok: true,
    sessionId: sid,
    runtime: 'docker-playwright',
    image: 'mcr.microsoft.com/playwright:v1.48@sha256:7f9202',
    container: container,
    cookies: '[from broker, purpose-scoped]'
  };
  process.stdout.write(JSON.stringify(resp, null, 2) + '\n');
  process.exit(0);
}

if (input.action === 'stop') {
  if (!input.sessionId) {
    process.stderr.write('kontrakt fail: stop wymaga sessionId\n');
    process.exit(2);
  }
  const resp = {
    ok: true,
    stopped: true,
    sessionId: input.sessionId
  };
  process.stdout.write(JSON.stringify(resp, null, 2) + '\n');
  process.exit(0);
}

process.stderr.write('nieznana akcja: ' + input.action + '\n');
process.exit(2);
