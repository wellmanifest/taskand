# Standard taskand v1.0 — Kompletna Specyfikacja

> **taskand** to system, w którym wszystko — od komunikatu po kontener z procesem — jest zasobem URI, a ewolucja jest procesem podlegającym walidacji i kwalifikacji w cyfrowym bliźniaku (Digital Twin), nie nagłym bezpośrednim zapisem na produkcji.

---

## Spis treści

1. [Filozofia i zasady nadrzędne](#1-filozofia-i-zasady-nadrzędne)
2. [Jednostki: proces, paczka, zasób URI](#2-jednostki-proces-paczka-zasób-uri)
3. [Typy artefaktów i tryby ewolucji](#3-typy-artefaktów-i-tryby-ewolucji)
4. [Typy paczek (role)](#4-typy-paczek-role)
5. [Schematy URI](#5-schematy-uri)
6. [Standardy komunikacji](#6-standardy-komunikacji)
7. [Ewolucja i pipeline wdrożenia](#7-ewolucja-i-pipeline-wdrożenia)
8. [Poznanie środowiska (roszczenia wiedzy)](#8-poznanie-środowiska-roszczenia-wiedzy)
9. [Digital twin i bramki kwalifikacji](#9-digital-twin-i-bramki-kwalifikacji)
10. [Struktura katalogów paczki](#10-struktura-katalogów-paczki)
11. [Wymagania dla procesów](#11-wymagania-dla-procesów)
12. [Wymagania dla Makefile](#12-wymagania-dla-makefile)
13. [Lista sprawdzająca (conformance checklist)](#13-lista-sprawdzająca-conformance-checklist)

---

## 1. Filozofia i zasady nadrzędne

### 1.1. Wszystko jest zasobem URI

W taskand v1.0 każdy element systemu posiada jednoznaczny identyfikator URI:

- Procesy wykonywalne: `proc://<organizacja>/<zdolność>/<wersja>`
- Sesje stanowe: `session://<typ>/<identyfikator>`
- Niezmienne dane (CAS): `artifact:<nazwa>@sha256:<skrót>`
- Pakiety i kapsuły: `capsule:<nazwa>@<wersja>`
- Środowiska wykonawcze: `runtime://<host>/<executor>`

Żaden element nie może być referencjonowany wyłącznie przez lokalną, ulotną ścieżkę plikową w logice biznesowej. Ścieżka plikowa jest wyłącznie powiązaniem transportowym (binding), zadeklarowanym w `proc-catalog.json`.

### 1.2. Niezależność od środowiska uruchomieniowego

Identyfikator i logika procesu są niezależne od tego, czy wykonawcą jest:
- czysty proces Node.js na hoście,
- kontener OCI / Docker,
- środowisko Firecracker microVM,
- zdalny worker serwerowy.

Tożsamość procesu leży w jego URI, schemacie wejścia/wyjścia oraz sumie kryptograficznej SHA-256 kodu `bin.mjs`.

### 1.3. Fail-Closed Contract

Każdy proces działa w trybie **fail-closed**:
- Brak danych wejściowych, błąd parsowania JSON lub brakujące wymagane pole w schemacie wejściowym skutkuje natychmiastowym zakończeniem z kodem wyjścia `2` (błąd kontraktu).
- Błąd wykonania operacji biznesowej kończy się z kodem `1`.
- Sukces biznesowy kończy się z kodem `0` i poprawnym JSON na stdout.
- Żaden proces nie może zwracać nieustrukturyzowanego tekstu na standardowe wyjście stdout — stdout jest zarezerwowany wyłącznie dla pojedynczego obiektu JSON. Wszystkie komunikaty diagnostyczne trafiają na stderr.

### 1.4. Zero Cross-Package Code Imports

Procesy orkiestrujące nie importują kodu procesów podrzędnych (`import` / `require` z innej paczki jest zabroniony). Współpraca odbywa się wyłącznie przez wywołanie URI za pośrednictwem runnera lub platformy IPC:
```
[Orkiestrator] --(JSON stdin)--> [Runner URI] --(exec bin.mjs)--> [Worker]
      ^                                                              |
      +------------------------(JSON stdout)-------------------------+
```

### 1.5. Niezmienność historii i bezpieczeństwo poświadczeń

- Historia ewolucji jest append-only (`log/conversations.jsonl`, rejestr commitów).
- Poświadczenia, hasła i klucze API **nigdy** nie są utrwalane w obrazach Dockerfile ani commitach repozytorium.
- Sekrety są wstrzykiwane wyłącznie w fazie runtime (zmienne środowiskowe, wolumeny ramfs Vault Agent, BuildKit secret mounts).

---

## 2. Jednostki: proces, paczka, zasób URI

### Proces (`proc://`)
Atomowa jednostka wykonawcza. Jeden proces realizuje dokładnie jedną zdolność. Składa się z:
- `proc.yaml` — deklaracja metadanych, schematów, roli i grantów.
- `bin.mjs` — punkt wejścia ze skrótem SHA-256 zarejestrowanym w katalogu.
- `test.mjs` — automatyczny test kontraktu (weryfikacja wejścia, wyjścia i kodów błędów).

### Paczka / Kapsuła (`capsule:<nazwa>`)
Samowystarczalna jednostka dystrybucyjna i zarządzania uprawnieniami. Definiowana przez:
- `capsule.yaml` — deklaracja roli paczki, listy procesów, delegacji ewolucji i zasad wdrożenia.
- `grants.yaml` — deklaratywna matryca uprawnień i twardych zakazów.
- `proc-catalog.json` — rejestr powiązań URI do plików fizycznych z sumami SHA-256.

---

## 3. Typy artefaktów i tryby ewolucji

| Klasa artefaktu | Tryb ewolucji | Opis |
|---|---|---|
| `process` | `versioned` | Nowa wersja w nowym URI (`v1` -> `v2`). Wersje wcześniejsze są niezmienne. |
| `schema` | `versioned-validated` | Nowa wersja schematu JSON musi zachować zgodność wsteczną lub podbić major. |
| `strategy` | `versioned` | Strategie decyzyjne planistów wersjonowane deklaratywnie w YAML. |
| `skill` | `reviewed` | Umiejętności wymagają zatwierdzenia kwalifikacyjnego. |
| `knowledge` | `append-only` | Rejestr roszczeń i faktów (`claims/`) może być tylko uzupełniany. |
| `twin` | `requalified` | Każda zmiana w środowisku testowym wymaga rekwalifikacji bramek Gate A i Gate B. |

---

## 4. Typy paczek (role)

W manifeście `capsule.yaml` pole `spec.role` przyjmuje jedną z ról:
- `application` — pełna aplikacja użytkowa orkiestrująca zadania i procesy robocze.
- `orchestrator` — paczka zarządcza delegująca zadania do innych URI.
- `worker` — wyspecjalizowany wykonawca pojedynczej dziedziny (np. automatyzacja www).
- `agent` — autonomiczny proces decyzyjny z pętlą wnioskowania.
- `template` — referencyjny szablon do generowania nowych paczek.

---

## 5. Schematy URI

Standard taskand v1.0 definiuje następujące przestrzenie nazw URI:

1. **`proc://<organizacja>/<zdolność>/<wersja>`**
   - Przykład: `proc://taskand.dev/flow/login/v1`
   - Mapowanie: `proc/flow/login/taskand.dev/v1/`
2. **`session://<typ>/<identyfikator>`**
   - Przykład: `session://browser/s-a9b8c7d6`
   - Oznacza aktywny kontekst sesji roboczej.
3. **`artifact:<typ>@sha256:<hash>`**
   - Przykład: `artifact:page-content@sha256:6e7e0414f863758f`
   - Wskaźnik do niezmiennego obiektu CAS (Content Addressable Storage).

---

## 6. Standardy komunikacji

Koperta wykonawcza procesu (Envelope) wejścia i wyjścia:

### Wejście (JSON stdin):
```json
{
  "uri": "proc://taskand.dev/web/navigate/v1",
  "sessionId": "session://browser/s-1234",
  "payload": {
    "url": "https://example.com"
  }
}
```

### Wyjście (JSON stdout):
```json
{
  "ok": true,
  "sessionId": "session://browser/s-1234",
  "artifact": "artifact:page-content@sha256:abc...",
  "status": 200,
  "executionTimeMs": 14
}
```

---

## 7. Ewolucja i pipeline wdrożenia

Pipeline wdrożenia paczki (`make deploy`):
1. **Lokalna walidacja**: `make test` oraz `make conformance` (9/9 punktów).
2. **Weryfikacja kryptograficzna**: `make verify` (spójność sum SHA-256 z katalogiem).
3. **Kwalifikacja w Digital Twin**:
   - **Gate A (Contract & Isolation)**: Uruchomienie w odizolowanym kontenerze piaskownicy, weryfikacja kontraktu fail-closed i braku wycieków poświadczeń.
   - **Gate B (Regression & Invariants)**: Uruchomienie scenariuszy testowych i sprawdzenie niezmienników roszczeń środowiska.
4. **Tagowanie wersji**: Utworzenie niezmiennego tagu w git `capsule-v<wersja>`.
5. **Budowa paczki**: `make pack` generuje dystrybucyjne archiwum `.tgz` w katalogu `dist/`.

---

## 8. Poznanie środowiska (roszczenia wiedzy)

Katalog `claims/` przechowuje deklaracje wiedzy o stanie infrastruktury:
- Stan roszczenia (`status`): `potwierdzona`, `nieznana`, `odrzucona`.
- Reguła walidacji (`rule`): np. `until_resolved` — blokuje wykonanie na produkcji, dopóki stan nie zostanie potwierdzony testem w Digital Twin.

---

## 9. Digital twin i bramki kwalifikacji

- `twin/qualification.yaml` definiuje bramki Gate A i Gate B, limity ponowień (`retries: 3`) oraz kryteria rollbacku.
- `twin/twin.compose.yaml` definiuje odizolowaną piaskownicę kontenerową bez dostępu do sieci produkcyjnej i wrażliwych wolumenów.

---

## 10. Struktura katalogów paczki

```text
<paczka>/
├── capsule.yaml                    # Manifest kapsuły (role, procesy, ewolucja)
├── grants.yaml                     # Polityka uprawnień i lista zakazów
├── proc-catalog.json               # Rejestr powiązań URI -> pliki i sumy SHA-256
├── package.json                    # Konfiguracja ESM ("type": "module")
├── Makefile                        # Standardowe cele: test, pack, verify, run...
├── proc/                           # Drzewo procesów: proc/<zdolność>/<organizacja>/<wersja>/
│   └── <zdolność>/<org>/<ver>/
│       ├── proc.yaml               # Deklaracja interfejsu i roli procesu
│       ├── bin.mjs                 # Wykonywalny plik wejściowy (JSON in -> JSON out)
│       └── test.mjs                # Automatyczny test kontraktu fail-closed
├── schemas/                        # Schematy walidacji JSON
├── claims/                         # Roszczenia wiedzy o środowisku
├── twin/                           # Digital Twin: qualification.yaml, compose
├── strategy/                       # Strategie decyzyjne
├── skills/                         # Deklaracje umiejętności
├── patches/                        # Poprawki git format-patch
└── dist/                           # Zbudowane archiwa .tgz
```

---

## 11. Wymagania dla procesów

1. Wykonywalny plik `bin.mjs` z uprawnieniem wykonywania (`chmod +x`).
2. Bezpieczny shebang: `#!/usr/bin/env node`.
3. Czytanie całego strumienia z stdin przed przetwarzaniem.
4. Zwracanie wyłącznie poprawnego JSON na stdout.
5. Kody wyjścia:
   - `0`: sukces.
   - `1`: błąd wykonania.
   - `2`: błąd kontraktu (brak wejścia, błąd składni JSON, naruszenie schematu).

---

## 12. Wymagania dla Makefile

Każda paczka zgodna ze standardem musi udostępniać następujące cele:

| Cel | Działanie |
|---|---|
| `test` | Uruchamia testy kontraktów wszystkich procesów w paczce |
| `pack` | Tworzy archiwum dystrybucyjne w `dist/` po pomyślnej walidacji konformacji |
| `verify` | Sprawdza sumy SHA-256 plików procesów względem `proc-catalog.json` |
| `run` | Uruchamia wskazany proces przez URI (`make run URI=... PAYLOAD=...`) |
| `observe` | Raportuje stan wykonania w formacie JSONL |
| `extract` | Zwraca manifest kapsuły i katalog procesów |
| `deploy` | Przeprowadza pełną procedurę wdrożenia z kwalifikacją w Digital Twin |
| `rollback` | Przywraca poprzedni zatwierdzony stan |
| `conformance` | Przeprowadza automatyczną walidację 9 punktów listy sprawdzającej |

---

## 13. Lista sprawdzająca (conformance checklist)

1. `capsule.yaml` istnieje, zawiera listę `processes[]` i zdefiniowaną rolę.
2. Co najmniej 1 proces zadeklarowany z plikiem `bin.mjs`.
3. URI każdego procesu odpowiada ścieżce `proc/<zdolność>/<organizacja>/<wersja>/`.
4. `Makefile` implementuje wymagane targety standardu v1.0.
5. `proc-catalog.json` zawiera zweryfikowane hashe SHA-256 plików `bin.mjs` i `proc.yaml`.
6. `grants.yaml` definiuje politykę uprawnień i zakazy (`policy-write`, `git-push`, itp.).
7. Wszystkie procesy posiadają test kontraktu `test.mjs` zachowujący regułę fail-closed.
8. Paczka znajduje się w repozytorium git z mechanizmem wersjonowania.
9. Ewolucja kapsuły definiuje `delegated-to` oraz limit ponowień w Digital Twin (`retries`).
