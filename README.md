# Wellmanifest taskand — Standard taskand v1.0

Standard architektury, wytwarzania i walidacji procesów autonomicznych identyfikowanych przez URI (`proc://`, `session://`, `artifact:`). HOME `wellmanifest`, SHAPE `domain_pack`.

- [Specyfikacja Standardu taskand v1.0](docs/standard.md)
- [Polityka maszynowa (TKD-001 do TKD-010)](policy.json)
- [Indeks dokumentacji](docs/README.md)
- [Architektura zarządzania sekretami](docs/secrets.md)
- [Cyfrowy Bliźniak i bramki kwalifikacyjne](docs/digital-twin.md)
- [Schematy JSON](schemas/)
- [Referencyjna paczka procesów](package/)

---

## Filozofia: Wszystko jest zasobem URI

Standard **taskand** definiuje uniwersalny paradygmat:
1. **URI jako tożsamość**: Każdy proces, sesja i artefakt posiada jednoznaczny identyfikator URI (`proc://`, `session://`, `artifact:`).
2. **Niezależność od wykonawcy**: Kontenery OCI, microVM i procesy hosta są jedynie mechanizmem uruchomieniowym.
3. **Fail-Closed Contract**: Komunikacja oparta wyłącznie o JSON stdin → JSON stdout. Kody wyjścia: `0` (sukces), `1` (błąd wykonania), `2` (naruszenie kontraktu).
4. **Zero Cross-Package Imports**: Orkiestracja odbywa się wyłącznie przez wywołania URI runnera — import kodu z innych pakietów jest zabroniony.
5. **Kwalifikacja w Digital Twin**: Żadna nowa wersja nie trafia na produkcję bez przejścia bramek Gate A (kontrakt) i Gate B (regresja).
6. **Zero Secrets at Rest**: Poświadczenia i hasła nigdy nie są zapisywane w obrazach ani commitach (patrz [docs/secrets.md](docs/secrets.md)).
7. **Deterministyczna Jakość i Algorytmy**: Integracja z procesami jakości kodu [`semcod/algocode`](https://github.com/semcod/algocode) w architekturze komunikacji DSL (`Human` -> `LLM` -> `Algorithm`) według standardu [`wellmanifest/nl-dsl-llm`](https://github.com/wellmanifest/nl-dsl-llm).

---

## 🛠️ Szybki start i narzędzia operacyjne

```bash
# 1. Sprawdź integralność standardu i uruchom testy
make test

# 2. Przeprowadź audyt 9/9 punktów konformacji referencyjnej paczki
make conformance

# 3. Sprawdź sumy kryptograficzne SHA-256 procesów
make verify

# 4. Spakuj paczkę referencyjną do dystrybucyjnego .tgz
make pack

# 5. Wygeneruj nową paczkę zgodną w 100% ze standardem
make new-pkg DIR=packages/moj-pakiet
```

---

## 📂 Struktura repozytorium standardu

```text
wellmanifest/taskand/
├── VERSION                         # Wersja standardu (1.0.0)
├── policy.json                     # Maszynowa polityka wymagań (TKD-001..TKD-010)
├── bundle.json                     # Kryptograficzne przypięcie plików standardu (SHA-256)
├── AGENTS.md                       # Kontrakt postępowania dla agentów autonomicznych
├── CHANGELOG.md                    # Dziennik zmian specyfikacji
├── Makefile                        # Operacyjne cele: test, conformance, bundle-check, pack
├── schemas/                        # Normatywne schematy JSON
│   ├── capsule.v1.json             # Schemat manifestu kapsuły
│   ├── grants.v1.json              # Schemat polityki uprawnień
│   ├── proc.v1.json                # Schemat deklaracji procesu
│   ├── catalog.v1.json             # Schemat katalogu procesów
│   ├── envelope.v1.json            # Schemat koperty IPC wejścia/wyjścia
│   └── browser-session.v1.json     # Schemat sesji przeglądarki
├── docs/                           # Dokumentacja i specyfikacja
│   ├── standard.md                 # Kompletna specyfikacja Standardu v1.0 (13 sekcji)
│   ├── secrets.md                  # Wzorce zarządzania poświadczeniami i Vault
│   ├── digital-twin.md             # Specyfikacja bramek Gate A i Gate B
│   └── README.md                   # Spis treści dokumentacji
├── operations/                     # Narzędzia referencyjne
│   ├── conformance.mjs             # Audytor listy sprawdzającej 9/9
│   ├── runner.mjs                  # Uniwersalny runner procesów URI
│   ├── catalog.mjs                 # Generator i weryfikator sum SHA-256 katalogu
│   ├── new_package.sh              # Generator nowych paczek
│   └── bundle.py                   # Weryfikator spójności bundle.json
├── tests/                          # Testy jednostkowe standardu
│   └── test_standard.py
└── package/                        # Referencyjna paczka taskand
    ├── capsule.yaml
    ├── grants.yaml
    ├── proc-catalog.json
    ├── Makefile
    ├── proc/
    │   ├── flow/login/taskand.dev/v1/
    │   ├── browser/session/taskand.dev/v1/
    │   ├── web/navigate/taskand.dev/v1/
    │   └── web/analyze/taskand.dev/v1/
    ├── twin/
    └── claims/
```

---

## 📋 Lista sprawdzająca (9/9 punktów konformacji)

| Punkt | Wymóg | Narzędzie weryfikacji |
|---|---|---|
| 1 | `capsule.yaml` z processes[] i rolą | `operations/conformance.mjs` |
| 2 | Co najmniej 1 proces proc:// z `bin.mjs` i bindingiem | `operations/conformance.mjs` |
| 3 | Zasada URI = ścieżka katalogu | `operations/conformance.mjs` |
| 4 | `Makefile` z pełnym zestawem targetów operacyjnych | `operations/conformance.mjs` |
| 5 | `proc-catalog.json` ze zweryfikowanymi hashami SHA-256 | `operations/catalog.mjs` |
| 6 | `grants.yaml` z polityką uprawnień i twardymi zakazami | `operations/conformance.mjs` |
| 7 | Testy kontraktu wszystkich procesów (fail-closed exit 0/1/2) | `proc/**/test.mjs` |
| 8 | Repozytorium Git i wersjonowanie kapsuły | `git status` / `git tag` |
| 9 | Ewolucja z delegacją kontrolera i limitem ponowień w Digital Twin | `capsule.yaml` |
