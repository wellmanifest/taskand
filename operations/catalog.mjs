#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';

const procs = [
  { uri: 'proc://taskand.dev/flow/login/v1', path: 'proc/flow/login/taskand.dev/v1' },
  { uri: 'proc://taskand.dev/browser/session/v1', path: 'proc/browser/session/taskand.dev/v1' },
  { uri: 'proc://taskand.dev/web/navigate/v1', path: 'proc/web/navigate/taskand.dev/v1' },
  { uri: 'proc://taskand.dev/web/analyze/v1', path: 'proc/web/analyze/taskand.dev/v1' }
];

const updateMode = process.argv.includes('--generate');

if (updateMode || !existsSync('proc-catalog.json')) {
  const catalog = {
    version: 1,
    standard: 'taskand-v1.0',
    generatedAt: new Date().toISOString(),
    bindings: procs.map(p => {
      const binContent = readFileSync(p.path + '/bin.mjs');
      const yamlContent = readFileSync(p.path + '/proc.yaml');
      const testContent = readFileSync(p.path + '/test.mjs');
      return {
        uri: p.uri,
        path: p.path,
        binSha256: createHash('sha256').update(binContent).digest('hex'),
        yamlSha256: createHash('sha256').update(yamlContent).digest('hex'),
        testSha256: createHash('sha256').update(testContent).digest('hex')
      };
    })
  };
  writeFileSync('proc-catalog.json', JSON.stringify(catalog, null, 2) + '\n');
  console.log('✓ proc-catalog.json zaktualizowany (' + procs.length + ' procesów)');
  process.exit(0);
}

// Tryb weryfikacji hashy
try {
  const catalog = JSON.parse(readFileSync('proc-catalog.json', 'utf8'));
  let errCount = 0;

  for (const b of catalog.bindings) {
    if (!existsSync(b.path + '/bin.mjs')) {
      console.error(`Brak pliku: ${b.path}/bin.mjs`);
      errCount++;
      continue;
    }
    const curBinHash = createHash('sha256').update(readFileSync(b.path + '/bin.mjs')).digest('hex');
    const curYamlHash = createHash('sha256').update(readFileSync(b.path + '/proc.yaml')).digest('hex');

    if (curBinHash !== b.binSha256) {
      console.error(`Błąd hash dla ${b.uri} bin.mjs: oczekiwano ${b.binSha256}, otrzymano ${curBinHash}`);
      errCount++;
    }
    if (curYamlHash !== b.yamlSha256) {
      console.error(`Błąd hash dla ${b.uri} proc.yaml: oczekiwano ${b.yamlSha256}, otrzymano ${curYamlHash}`);
      errCount++;
    }
  }

  if (errCount > 0) {
    console.error(`✗ Weryfikacja katalogu nie powiodła się: ${errCount} błędów.`);
    process.exit(1);
  }

  console.log(`catalog ✓ (${catalog.bindings.length} procesów zweryfikowanych pomyślnie)`);
  process.exit(0);
} catch (e) {
  console.error('Błąd odczytu katalogu:', e.message);
  process.exit(1);
}
