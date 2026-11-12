#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, posix, resolve } from 'node:path';

const procs = [
  { uri: 'proc://taskand.dev/flow/login/v1', path: 'proc/flow/login/taskand.dev/v1' },
  { uri: 'proc://taskand.dev/browser/session/v1', path: 'proc/browser/session/taskand.dev/v1' },
  { uri: 'proc://taskand.dev/web/navigate/v1', path: 'proc/web/navigate/taskand.dev/v1' },
  { uri: 'proc://taskand.dev/web/analyze/v1', path: 'proc/web/analyze/taskand.dev/v1' }
];

const args = process.argv.slice(2);
const updateMode = args.includes('--generate');
const verifyOnly = args.includes('--verify');
const targetArg = args.find(a => !a.startsWith('--')) || '.';
const pkgDir = resolve(targetArg);
const catalogPath = join(pkgDir, 'proc-catalog.json');

function resolveBindingDir(relPath) {
  if (
    typeof relPath !== 'string' ||
    !relPath ||
    relPath.startsWith('/') ||
    relPath.includes('\\') ||
    posix.normalize(relPath) !== relPath ||
    relPath.split('/').includes('..')
  ) {
    throw new Error(`Nieprawidłowa ścieżka procesu w katalogu: ${relPath}`);
  }
  return join(pkgDir, relPath);
}

if (updateMode || (!verifyOnly && !existsSync(catalogPath))) {
  const catalog = {
    version: 1,
    standard: 'taskand-v1.0',
    generatedAt: new Date().toISOString(),
    bindings: procs.map(p => {
      const procDir = resolveBindingDir(p.path);
      const binContent = readFileSync(join(procDir, 'bin.mjs'));
      const yamlContent = readFileSync(join(procDir, 'proc.yaml'));
      const testContent = readFileSync(join(procDir, 'test.mjs'));
      return {
        uri: p.uri,
        path: p.path,
        binSha256: createHash('sha256').update(binContent).digest('hex'),
        yamlSha256: createHash('sha256').update(yamlContent).digest('hex'),
        testSha256: createHash('sha256').update(testContent).digest('hex')
      };
    })
  };
  writeFileSync(catalogPath, JSON.stringify(catalog, null, 2) + '\n');
  console.log('✓ proc-catalog.json zaktualizowany (' + procs.length + ' procesów)');
  process.exit(0);
}

// Tryb weryfikacji hashy
try {
  const catalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
  let errCount = 0;

  for (const b of catalog.bindings) {
    const procDir = resolveBindingDir(b.path);
    const binFile = join(procDir, 'bin.mjs');
    const yamlFile = join(procDir, 'proc.yaml');
    const testFile = join(procDir, 'test.mjs');
    if (!existsSync(binFile) || !existsSync(yamlFile) || (b.testSha256 && !existsSync(testFile))) {
      console.error(`Brak pliku w wiązaniu: ${b.path}`);
      errCount++;
      continue;
    }
    const curBinHash = createHash('sha256').update(readFileSync(binFile)).digest('hex');
    const curYamlHash = createHash('sha256').update(readFileSync(yamlFile)).digest('hex');

    if (curBinHash !== b.binSha256) {
      console.error(`Błąd hash dla ${b.uri} bin.mjs: oczekiwano ${b.binSha256}, otrzymano ${curBinHash}`);
      errCount++;
    }
    if (curYamlHash !== b.yamlSha256) {
      console.error(`Błąd hash dla ${b.uri} proc.yaml: oczekiwano ${b.yamlSha256}, otrzymano ${curYamlHash}`);
      errCount++;
    }
    if (b.testSha256) {
      const curTestHash = createHash('sha256').update(readFileSync(testFile)).digest('hex');
      if (curTestHash !== b.testSha256) {
        console.error(`Błąd hash dla ${b.uri} test.mjs: oczekiwano ${b.testSha256}, otrzymano ${curTestHash}`);
        errCount++;
      }
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
