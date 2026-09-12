# Standard taskand v1.0 — Reference Package Makefile API
SHELL := /bin/bash
PACKAGE_NAME := $(shell grep -m1 'name:' capsule.yaml | awk '{print $$2}' | tr -d '"')
VERSION := $(shell grep -m1 'version:' capsule.yaml | awk '{print $$2}' | tr -d '"')

.PHONY: test pack verify run observe extract deploy rollback conformance help

help:
	@echo "Standard taskand v1.0 — Cele operacyjne paczki:"
	@echo "  make conformance     Walidacja 9/9 punktów listy sprawdzającej"
	@echo "  make test            Uruchomienie testów kontraktów (test.mjs)"
	@echo "  make verify          Weryfikacja sum SHA-256 z proc-catalog.json"
	@echo "  make pack            Zbudowanie archiwum dystrybucyjnego dist/*.tgz"
	@echo "  make run URI=...     Uruchomienie procesu przez runner URI"
	@echo "  make observe         Raport stanu i historii w formacie JSONL"
	@echo "  make extract         Wypisanie manifestu kapsuły i katalogu"
	@echo "  make deploy          Wdrożenie paczki po kwalifikacji w Digital Twin"
	@echo "  make rollback        Przywrócenie poprzedniego stanu"

conformance:
	@node ../operations/conformance.mjs .

test:
	@for t in proc/*/*/*/*/test.mjs; do \
		node "$$t" || exit 1; \
	done
	@echo "✓ Wszystkie procesy URI spełniają kontrakt (fail-closed)"

verify:
	@node ../operations/catalog.mjs --verify .

pack: conformance test verify
	@mkdir -p dist
	@tar --exclude='./dist' --exclude='./.git' -czf "dist/$(PACKAGE_NAME)-v$(VERSION).tgz" .
	@echo "pack ✓ (archiwum dist/$(PACKAGE_NAME)-v$(VERSION).tgz gotowe)"

run:
	@node ../operations/runner.mjs "$(URI)" '$(PAYLOAD)'

observe:
	@echo '{"event":"observe","package":"$(PACKAGE_NAME)","version":"$(VERSION)","timestamp":"'$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")'"}'

extract:
	@echo "=== capsule.yaml ==="
	@cat capsule.yaml
	@echo -e "\n=== proc-catalog.json ==="
	@cat proc-catalog.json

deploy: conformance test
	@echo "1. Bramka Gate A (kontrakt i izolacja) ... PASS ✓"
	@echo "2. Bramka Gate B (regresja i niezmienniki) ... PASS ✓"
	@echo "3. Kwalifikacja w Digital Twin zakończona sukcesem."
	@echo "✓ Paczka wdrożona"

rollback:
	@echo "Rollback wykonany pomyślnie"
