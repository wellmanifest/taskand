.PHONY: test bundle-check conformance verify pack new-pkg help

help:
	@echo "wellmanifest/taskand — Standard taskand v1.0"
	@echo "  make test          Uruchomienie testów jednostkowych i audytu konformacji"
	@echo "  make bundle-check  Weryfikacja integralności standardu bundle.json"
	@echo "  make conformance   Weryfikacja 9/9 punktów referencyjnej paczki"
	@echo "  make verify        Weryfikacja sum SHA-256 w referencyjnej paczce"
	@echo "  make pack          Zbudowanie archiwum dystrybucyjnego paczki"
	@echo "  make new-pkg DIR=  Wygenerowanie nowego pakietu taskand"

test: bundle-check conformance
	python3 -B -m unittest discover -s tests -v

bundle-check:
	python3 -B operations/bundle.py --check

conformance:
	node operations/conformance.mjs package

verify:
	node operations/catalog.mjs --verify package

pack:
	cd package && make pack

new-pkg:
	bash operations/new_package.sh $(DIR)
