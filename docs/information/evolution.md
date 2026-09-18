---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "taskand-evolution",
  "kind": "information",
  "version": 3,
  "title": "Taskand jako standard systemu ewolucyjnego",
  "status": "draft",
  "owner": "wellmanifest/taskand",
  "created": "2026-09-13",
  "updated": "2026-09-13",
  "review_after": "2026-10-13",
  "source_revision": "388e0cc7fee92506e7cb94ab8b7479005ceffc18",
  "affected_repositories": ["wellmanifest/taskand"],
  "evidence": ["policy.json", "schemas/envelope.v2.json", "schemas/delivery-observation.v1.json", "operations/delivery.py", "operations/bundle.py", "tests/test_standard.py"]
}
---

# Ewolucja komplementarna — profil evolution-v1

<!-- docs:section purpose -->
## Zakres i status

Normatywne rozszerzenie standardu 1.1.0, lokalnie przygotowane w ticket-001.
Profil jest opt-in. Nie zmienia historycznego `taskand-v1`, nie zaświadcza,
że wdrożenie glm53 już go realizuje, i nie zastępuje governance repozytorium.
Runtime usług należy do semcod/subactor; wellmanifest przechowuje standard.

Komplementarność jest relacją celu, pytań, odpowiedzi i dowodów, nie nakazem
nieskończonego wykonania. Każda iteracja ma bounded intent, warunek zakończenia,
budżet i prawo użytkownika do zatrzymania. Odpowiedź może wskazać kolejne pytania,
ale nie zleca ich automatycznie. Sukces dotyczy kryterium i dokładnej wersji.

<!-- docs:section content -->
## Kontrakty i adresowanie

| Warstwa | Adres / wersja | Obowiązek |
| --- | --- | --- |
| Standard | VERSION 1.1.0 + immutable source SHA + bundle digest | Adopcja jawna, pełny graf normatywnych referencji. |
| Koperta | `urn:taskand:schema:envelope:v2` | Zamknięte, rozłączne profile request i log; brak cichego fallbacku do v1. |
| Zadanie C/Q | `…:v2#task-request`, `taskand.task-request/v1` | Referencje do operacji, payloadu, DSL, gramatyki i schema z digestami. |
| Log | `…:v2#log-event`, data `taskand.log-event/v1` | CloudEvents 1.0; fakty, korelacja i dowody, nigdy autoryzacja. |
| DSL | artifact + schema + grammar jako URI/SHA-256 | Wersja języka niezależna od procesu, zadania, modelu LLM i CloudEvents. |
| Proces / twin / prompt | stała tożsamość URN, konkretna rewizja i digest | Resolver odróżnia tożsamość, adres pobrania i alias bieżącej wersji. |

URN jest URI identyfikującym zasób, nie automatycznie działającym endpointem.
Każda referencja wymaga resolvera, kontroli dostępu i sprawdzenia SHA-256 dokładnych
bajtów UTF-8/artefaktu. Sam poprawny prefiks ani hash nie dowodzi istnienia,
wierności modelu lub authority. Nie pobiera się dowolnych URL schematów:
kontroler używa przypiętej, zaufanej mapy rejestru, zapobiegając SSRF.

Koperta przenosi DSL przez referencję, nie dowolny tekst do wykonania. Resolver
weryfikuje zamknięty model payloadu i AST oraz request-only GBNF dokładnej wersji.
Nie wystarczy JSON mode dostawcy LLM ani wyciągnięcie pierwszego JSON z prozy.
NL i opisy z rejestru są danymi niezaufanymi; nie mogą zmienić reguł kompilatora.
Inny DSL do logowania opisuje fakty, a nie komendy. Replay logu jest bezskutkowy.

JSON Schema opisuje transport. Semantyka C/Q, emits/rejects i authority pochodzi
z właściwego rejestru operacji oraz kontrolera. Query nie ma efektów. Komenda
ma jeden skutek i receipt. `authorityRef` jest wskaźnikiem do niezależnie
zweryfikowanej zgody, nie zgodą udzieloną przez tekst modelu.

## Cykl pracy

```text
NL → promptRef → kompilator DSL + rejestry → request-only → controller preconditions
                                                            │
                                       brak dowodu ──────────┤
                                           ↓                ↓
                                      BLOCKED       model/twin + scenariusz
                                                            ↓
                                            Gate A → Gate B → kandydat
                                                            ↓
                                    independent approval exact-head → apply
                                                            ↓
                                         receipt → obserwacja → nowy intent
```

1. Trusted intake przydziela requestId i promptRef. Rejestruje autora, zgodę na
   przechowywanie treści, korelację, causation i HMAC lub bezpieczny digest.
   Surowe prompty i sekrety nie trafiają do publicznych logów/Git.
2. Kompilator rozwiązuje każdą zależność do istniejącego obiektu i rewizji.
   Brak referencji, nieznany model urządzenia i niepełne pokrycie mają jawny stan
   UNKNOWN/PARTIAL; nie wolno ich zastępować domysłem ani sukcesem.
3. Planista proponuje AST zgodny z gramatyką i zamkniętym schematem. Walidator
   deterministyczny sprawdza graf DAG, URI, hashe, scope i limity.
4. Kontroler odczytuje bieżącą zgodę, lease/fencing, deadline i idempotency key.
   Powtórzenie tego samego żądania zwraca istniejący receipt; ten sam klucz z
   innym digestem jest konfliktem. Restart nie odtwarza wykonanych efektów.
5. Najpierw kwalifikuje się scenariusz w odizolowanym bliźniaku. Gate A sprawdza
   kontrakt i izolację; Gate B regresję na przypiętym korpusie. Nowy proces bez
   poprzednika również potrzebuje kryteriów i testów, nie pustej regresji.
6. Nowa wersja pozostaje kandydatem do niezależnej kwalifikacji. Publikacja lub
   wdrożenie korzysta z dedykowanego kontrolera i zgody dokładnego HEAD.
7. Receipt wiąże input, plan, twin, model LLM, testy, kod i wynik. Graf live
   przedstawia fakty, również timeout/UNKNOWN. Odpowiedź HTTP 200 nie jest sukcesem.
8. Obserwacje mogą uzasadnić następną, osobno ograniczoną iterację. Zmiana intencji,
   polityki, bazy lub modelu unieważnia zależne dowody zgodnie z ich bindings.

## Bliźniaki i ponowne użycie

Rejestr modeli przechowuje tożsamość, rewizję, typ, właściciela, źródło obserwacji,
datę, pokrycie, niepewność i URI artefaktów. Typy obejmują sieć, urządzenie,
usługę, stronę WWW i jawny syntetyczny profil testowego użytkownika. Model nie
dziedziczy uprawnień ani tożsamości realnego człowieka. Wymagane są ACL, retencja,
usuwanie zgodne z polityką i redakcja; same pliki 0600 nie rozwiązują prywatności.

Kompozycja wskazuje dokładne rewizje składowych, tworzy acykliczny graf i nie
zmienia starych modeli. Nowe obserwacje tworzą nową rewizję z parent i dowodami.
Wspólne zadania mogą ulepszyć model, ale istniejący test pozostaje przypięty do
starego digestu; upgrade zależności wymaga ponownej kwalifikacji.

Identyczne podsieci i IP wymagają osobnego namespace/sieci testowej: nie wolno
ogłaszać tych samych adresów w realnym LAN. Zgodność adresacji nie jest
zgodnością routingu, firmware czy zachowania. Nieznane urządzenie reprezentuje
model częściowy z obserwowanymi portami/protokołami i listą braków. Dalsze
rozpoznanie musi mieścić się w autoryzowanym zakresie.

Dockerfile/OCI to jeden z runtime modeli. Nie emuluje automatycznie kernela,
sprzętu mobilnego ani urządzenia. Browser w kontenerze może odtwarzać UI WWW;
pełny desktop/mobile wymaga właściwego emulatora/VM i jawnej macierzy pokrycia.
Bliźniak WWW nie wysyła brakującej odpowiedzi do produkcji; syntetyczna odpowiedź
jest oznaczona i nie stanowi dowodu prawdziwego backendu.

## Autonomia, multiplikacja i self-update

```dsl
DOCUMENT TASKAND_EVOLUTION
VERSION 2
MODE STRICT

RULE TKD-EVO-001 TYPE REQUIRED
WHEN CAPABILITY_REQUESTED
DO RESOLVE QUALIFIED_REUSABLE_URI_AND_TWIN_REVISION
FORBID INVENT_REFERENCE_OR_REGENERATE_COMPATIBLE_EXISTING_CAPABILITY
ASSERT REUSE_DECISION_HAS_EVIDENCE

RULE TKD-EVO-002 TYPE REQUIRED
WHEN CHILD_REQUESTED
DO REQUIRE ATOMIC_VERSION_ALLOCATION_AND_CURRENT_FENCING_TOKEN
DO REQUIRE CHILD_SCOPE_SUBSET_OF_PARENT AND CHILD_GRANTS_SUBSET_OF_PARENT
DO REQUIRE SHARED_BUDGET_DECREASES AND DEADLINE_NOT_EXTENDED
FORBID COPY_SECRETS_IDENTITY_OR_APPROVAL_TO_CHILD
NEXT VALIDATION OR BLOCKED

RULE TKD-EVO-003 TYPE REQUIRED
WHEN RECOVERY_PROPOSED
DO CLASSIFY TRANSIENT_FAILURE OR CONTRACT_GAP OR AUTHORITY_GAP
DO RETRY_TRANSIENT_FAILURE_WITHIN_BUDGET_AND_IDEMPOTENCY
DO CREATE_BOUNDED_REPAIR_INTENT_FOR_CONTRACT_GAP
FORBID SELF_GRANT_AUTHORITY_OR_DISABLE_FAILED_GATE
NEXT PLAN OR BLOCKED

RULE TKD-EVO-004 TYPE REQUIRED
WHEN SELF_UPDATE_PROPOSED
DO REQUIRE USER_AUTHORIZED_DELIVERY AND QUALIFIED_IMMUTABLE_CANDIDATE
DO REQUIRE INDEPENDENT_EXACT_HEAD_APPROVAL_AND_CONTROLLER_RECEIPT
FORBID WORKER_GIT_PUSH_SELF_RESTART_OR_POLICY_WRITE
NEXT PUBLICATION OR BLOCKED
```

Bloki DSL są normatywnym zapisem, nie interpreterem ani dowodem egzekwowania.
Runtime musi implementować controller preconditions; same prompty nie wystarczą.

`maxChildren`, `maxDepth`, `maxAttempts`, `maxSteps` i deadline są wspólnym
budżetem drzewa, nie nowym budżetem dla każdego potomka. Równoległe rezerwacje
muszą być atomowe; unikalność folderu sprawdzana przez exists() nie wystarcza.
Rozproszona multiplikacja wymaga kontrolera współdzielonego między węzłami.
Awaria store, parsera logów lub lease blokuje skutek, nie resetuje cooldownu.

Taskand może przygotować następną wersję własnego kodu jako kandydat: osobny ticket,
worktree i branch, przypięty standard, testy, snapshot, PR oraz niezależny review.
Nie może sam nadać sobie zgody na merge. Zakazy `git-push`, `self-restart` i
`policy-write` dla workera w TKD-006 pozostają w mocy; osobno upoważniony
kontroler publikacji/restartu nie jest tym workerem. Wdrożenie wymaga canary i
weryfikowalnego rollbacku do poprzedniej niezmiennej wersji, bez utraty zdarzeń.

## Zgodność z pozostałymi standardami

### TKD-013: zatrzymanie narastania niewypchniętej pracy

Obserwację `taskand.delivery-observation/v1` adresuje
`urn:taskand:schema:delivery-observation:v1`. Zamknięty schemat należy do
normatywnego bundle; referencyjny, bezskutkowy evaluator to
`operations/delivery.py`. Wynik `taskand.delivery-decision/v1` wiąże SHA bazy
i HEAD, digests intencji, polityki, workspace oraz zegar ewaluacji. Katalog
kodów i bezpiecznych remediacji znajduje się w `policy.json/delivery_diagnostics`.
Nie jest to nowy kontroler Git ani zastępstwo adopcji New-project.

```dsl
RULE TKD-EVO-005 TYPE REQUIRED
WHEN TASK_CONTINUED OR MATERIAL_MILESTONE OR NEW_SLICE_REQUESTED
DO OBSERVE ACCEPTED_BASE_TO_HEAD AND INDEX AND WORKING_TREE AND_UNTRACKED_SOURCE
DO COUNT UNIQUE_MATERIAL_PATHS_ACROSS_ALL_LAYERS
DO CHECK CURRENT_INTENT_BUDGET AND_PUBLICATION_PROGRESS_DEADLINE
DO PRIORITIZE FINISH_EXISTING OR PRESERVE_AND_VALIDATE OR SPLIT_WITH_PRESERVATION
FORBID RESET_PROGRESS_DEADLINE_ON_NEW_PROMPT_CHECKPOINT_OR_AGENT_RESTART
FORBID GROW_SAME_SCOPE_WHILE_REQUIRED_DELIVERY_REMAINS_UNRESOLVED
ASSERT LOCAL_COMMIT PUSH PR MERGE AND_DEPLOYMENT_REMAIN_DISTINCT

RULE TKD-EVO-006 TYPE REQUIRED
WHEN GOVERNANCE_ADOPTION_OR_CLONE_WIDE_HOOK_ACTIVATION_REQUESTED
DO INVENTORY EVERY_REGISTERED_CHECKOUT INDEX_WORKING_LAYERS TICKET_BINDINGS AND_LIVE_MOUNTS
DO CLASSIFY LEGACY_HISTORY_AND_NEW_DELTA_SEPARATELY_WITH_EXACT_BASE_EVIDENCE
DO QUALIFY IMMUTABLE_ADOPTION_AND_PROTECTED_DELIVERY_ROUTE_BEFORE_ACTIVATION
FORBID RELABEL_OLD_COMMITS_AS_NEW_TICKET OR_ENABLE_HOOKS_THAT_STRAND_EXISTING_WORK
FORBID DISABLE_GATES_OR_REWRITE_PUBLISHED_HISTORY_TO_REPAIR_ADOPTION
NEXT RECONCILE_ADOPTION OR VALIDATION

RULE TKD-EVO-007 TYPE REQUIRED
WHEN MULTIPLE_DELIVERIES_EXIST
DO RESOLVE ACTUAL_SCOPE_INTERSECTION AND_WRITER_AUTHORITY
DO COUNT BLOCKED_UNMERGED_MATERIAL_AS_DELIVERY_DEBT_NOT_ACTIVE_WRITE_AUTHORITY
DO SERIALIZE_OVERLAPPING_INTEGRATION_AND_RETEST_EXACT_MERGED_CANDIDATE
DO ALLOW_DISJOINT_AUTHORIZED_WORK_WITHIN_REPOSITORY_WIP_LIMITS
FORBID EQUATE_AGENT_COUNT_OR_WORKTREE_COUNT_WITH_ACTUAL_WRITE_CONFLICT
FORBID CLOSE_TICKET_OR_DELETE_CHECKOUT_WITHOUT_VERIFIED_TERMINAL_EVIDENCE
```

Źródłem obserwacji MUSI być adapter kontrolera odczytujący Git, istniejące
rejestry ticketów/lease, chroniony profil publikacji i zdalne SHA. Dane podane
przez LLM lub sam plik JSON nie są dowodem. `maxMaterialFiles` pochodzi z
zaakceptowanej polityki/intencji; zakres nie może pomijać starszych commitów.
Wyłączenie zarządzanego payloadu adopcji wymaga już zweryfikowanego dowodu
niezmiennej adopcji, a nie nazwy katalogu `.governance`. `lastProgressAt`
wiąże ostatni potwierdzony etap dostawy, nie ostatnią wiadomość, heartbeat
czy zapis snapshotu. Przy braku takiego etapu używa się początku pracy.

`overlappingDeliveries` obejmuje pozostałe nierozstrzygnięte delty w tym samym
zakresie, także odłożone jako BLOCKED; nie jest liczbą wszystkich worktree.
Historyczny wspólny commit nie jest nowym writerem. Dowody testów muszą wiązać
również staged, unstaged i untracked bytes przez workspace digest — zielony
test starego HEAD nie wystarcza. Pola `checks` są obserwacjami sprawdzanymi
przez adapter, nie deklaracjami uprawnień.

| Obserwacja | Wskazywany następny krok |
| --- | --- |
| Nieuzgodniona adopcja / stare gałęzie bez ticketów | RECONCILE_ADOPTION przed aktywacją hooków. |
| Suma zakresu przekracza limit | SPLIT_WITH_PRESERVATION, bez podnoszenia limitu. |
| Poprzedni zakres czeka na dostawę | FINISH_EXISTING zamiast kolejnej funkcji. |
| Minął checkpoint, brak testów dokładnego snapshotu | PRESERVE_AND_VALIDATE. |
| Gotowy zakres, lokalne zmiany | COMMIT_CURRENT z istniejącymi bramkami. |
| Commit nieobecny zdalnie / brak pasującego PR | PUSH_CURRENT / OPEN_OR_UPDATE_PR. |
| Pasujący PR już istnieje | WAIT_PROTECTED_REVIEW, bez ponownego PR i self-merge. |
| Chroniony executor jest niedostępny | RESTORE_DELIVERY; zabezpieczenie pracy pozostaje dozwolone. |

Uruchomienie offline: `python3 -B operations/delivery.py --now <RFC3339>`
czyta jeden JSON ze stdin. Kod 0 oznacza poprawne wyliczenie trasy, **nie zgodę
na efekt**; kod 2 oznacza niepoprawne wejście. Kontroler musi odczytać `route`,
ponownie zweryfikować pełne bramki, intencję, ownership/fencing, testy i zdalny
stan bezpośrednio przed skutkiem. Evaluator nie uruchamia Git, nie instaluje
hooków, nie zbiera danych użytkownika i nigdy nie potwierdza merge.

To lokalna implementacja referencyjna profilu opt-in. Włączenie jej do intake,
checkpointów i kontrolera Taskand/New-project wymaga oddzielnej, przypiętej
adopcji z canary. Samo dodanie reguł ani udany test nie oznacza, że działają
już w `taskand-glm53` lub pozostałych projektach.

### TKD-014: trudne incydenty i wykrywanie regresji podczas pracy

```dsl
RULE TKD-EVO-008 TYPE REQUIRED
WHEN FAILURE_OR_REGRESSION_OBSERVED
DO RESOLVE INCIDENT_ID FROM REPOSITORY_ID ACCEPTED_OUTCOME EFFECT_SCOPE AND_STABLE_FAILURE_CODE
DO PRESERVE EXACT_HEAD INDEX_WORKING_UNTRACKED_BYTES AND_UNIQUE_HISTORY
DO BIND RAW_EVIDENCE_REF PARSER_VERSION OBSERVATION_DIGEST AND_TWIN_REVISION
DO RECONCILE UNKNOWN_EFFECT_OUTCOME_BY_IDEMPOTENCY_KEY_BEFORE_RETRY
FORBID INTERPRET_TIMEOUT_PARSE_FAILURE_OR_MISSING_RECEIPT_AS_NO_EFFECT
NEXT DIAGNOSE_ONLY OR RECONCILE_EFFECT OR PLAN_BOUNDED_REPAIR

RULE TKD-EVO-009 TYPE REQUIRED
WHEN REPAIR_ATTEMPT_PROPOSED
DO RESERVE SHARED_ATTEMPT_AND_TIME_BUDGET_ATOMICALLY_BEFORE_EFFECT
DO REQUIRE QUALIFIED_ISOLATED_TWIN_AND_EXACT_CANDIDATE_REGRESSION_CHECKS
DO REOBSERVE INTENT BASE HEAD WORKSPACE LEASE POLICY AND_REMOTE_RECEIPTS_BEFORE_EFFECT
DO HALT_AFFECTED_SCOPE WHEN ATTEMPTS_EXHAUSTED OR_NO_PROGRESS_LIMIT_REACHED OR_TWIN_FAILED
FORBID RESET_INCIDENT_BUDGET_ON_PROMPT_TICKET_WORKTREE_CHILD_NODE_OR_PROCESS_RESTART
FORBID REPAIR_TARGET_BY_WRITING_UNOWNED_STANDARD_OR_SELF_GRANTING_AUTHORITY
NEXT BOUNDED_REPAIR OR HALT_AFFECTED_SCOPE OR WAIT_RECOVERY_AUTHORITY

RULE TKD-EVO-010 TYPE REQUIRED
WHEN INCIDENT_STATE_OR_VALIDATION_EVIDENCE_CHANGES
DO RECONCILE EVENT_CURSOR_WITH_PERIODIC_FULL_OBSERVATION
DO INVALIDATE DEPENDENT_EVIDENCE_WHEN_SUBJECT_BINDINGS_CHANGE
DO FREEZE_AFFECTED_CANDIDATE_PROMOTION_WHEN_REGRESSION_CONFIRMED
DO DEDUPLICATE_ESCALATION_BY_INCIDENT_AND_MISSING_DECISION
DO CONTINUE_DISJOINT_AUTHORIZED_WORK_WHEN_WITHIN_WIP_LIMIT
FORBID WATCHER_EVENT_OR_LLM_SUMMARY_AS_LOCK_APPROVAL_OR_TERMINAL_RECEIPT
NEXT REOBSERVE OR QUARANTINE_CANDIDATE OR WAIT_RECOVERY_AUTHORITY
```

Referencja rozszerza **nieopublikowany** `delivery-observation/v1` o wymagane
pole `recovery`: `null` oznacza potwierdzony brak otwartego incydentu; nie wolno
używać go, gdy rejestr incydentów jest niedostępny. Obiekt przenosi fingerprint,
klasę awarii, liczniki prób i braku postępu, limity, potwierdzenie zachowania
danych, wynik bliźniaka oraz `retryAfter`. Brak pola jest błędem kontraktu.
Po pierwszej publikacji niezgodna zmiana wymaga nowej wersji/adresu schematu.

Fingerprint wiąże stabilną tożsamość przyczyny i zakresu, a nie losowy requestId,
numer próby lub HEAD. Kolejne obserwacje wiążą zmieniające się SHA osobno.
Rejestr utrzymuje też wspólny budżet zaakceptowanego celu, aby nowy fingerprint
nie odnowił budżetu drzewa. Adapter MUSI pobrać liczniki z trwałego rejestru
przez CAS/fencing; caller ani LLM nie mogą je wyzerować. Referencyjny evaluator
jedynie sprawdza i interpretuje ich obserwację — nie implementuje tego store.

Limit prób i braku postępu jest osiągnięty przy `used >= limit`. Polityka
wdrożenia ustala również wspólny deadline i limit czasu/kosztu. Postęp oznacza
usunięcie konkretnego findingu z dowodem albo potwierdzony etap dostawy, nie
nowy log, commit trackingowy, snapshot czy powtórzony test z tym samym błędem.
Powtórny start wymaga nowej obserwacji i uzasadnionej, jawnie ograniczonej decyzji;
cooldown sam nie resetuje budżetu. Wygasły deadline również blokuje skutki.

| Klasa / obserwacja | Trasa referencyjna | Granica |
| --- | --- | --- |
| Wynik push/merge/deploy nieznany | RECONCILE_EFFECT | Odczyt receiptu i faktycznego celu; żadnego ślepego powtórzenia. |
| Potwierdzona regresja | QUARANTINE_CANDIDATE | Zatrzymanie promocji kandydata, nie usunięcie jego danych. |
| Brak uprawnienia | WAIT_RECOVERY_AUTHORITY | Jedno pytanie o konkretny efekt i brakującą decyzję. |
| Limit prób / brak postępu | HALT_AFFECTED_SCOPE | Stop dotkniętego writera i potomków; pozostałe zakresy osobno. |
| Nieznany format/niepełny log | DIAGNOSE_ONLY | UNKNOWN i bezpieczna referencja do oryginału, bez domyślnego sukcesu. |
| Brak lub błąd bliźniaka | REHEARSE_RECOVERY / HALT_AFFECTED_SCOPE | Wynik dotyczy dokładnego modelu, scenariusza i kandydata. |
| Błąd przejściowy, testy i backoff | RETRY_CANDIDATE | Propozycja dla kontrolera; nadal pełne preconditions. |
| Konflikt / luka kontraktu | PLAN_BOUNDED_REPAIR | Naprawa celu w jego repo; zmiana standardu wyłącznie w jego HOME. |

Docelowy obserwator łączy eventy Git/CI/lease z okresowym pełnym odczytem;
monitoruje wiek niewypchniętej pracy, rozmiar delty, przecięcia zakresów,
zmianę bazy/HEAD, stale approval, błędy testów i brak postępu. Utrata eventów,
przerwa lub niedostępny rejestr dają UNKNOWN i wymuszają resynchronizację.
Widok live ma pokazywać czas obserwacji i jej opóźnienie, nie obiecywać stałej
aktualności. Kontroler odczytuje stan ponownie tuż przed skutkiem — watcher
nie zamyka wyścigu między odczytem i zapisem.

W obcym projekcie adapter używa jego identyfikatora repozytorium, pinów,
ticket-lifecycle, testów i chronionego profilu publikacji. Taskand nie tworzy
równoległego źródła prawdy ticketów ani globalnej zgody na wszystkie repo.
Naprawa samego Taskand jest oddzielnym zakresem i zależnością, nie ukrytym
poszerzeniem zadania klienta. Pierwsze wdrożenie powinno być read-only, potem
kontrolowany pilot jednej klasy napraw, dopiero po dowodach szersza automatyzacja.

Nie jest to działający watchdog ani automatyczny naprawiacz Git. Lokalne testy
sprawdzają zamknięte wejście, kolejność tras i brak efektów; nie dowodzą
trwałości rejestru, reakcji live, atomowych limitów lub wykonania naprawy.

### Granice odpowiedzialności

| Standard | Kontrolowany obszar |
| --- | --- |
| `new-project` | Dystrybucja pinów, admission work-start, intent, budżety, hooki i governance. |
| `ticket-lifecycle` | Identyfikacja i zakres pracy, zależności, WIP, handoff i terminalne receipts. |
| `worktrees` | Kanoniczna lokalizacja i inwentaryzacja; nie zgoda na kasowanie. |
| `git-lifecycle` | Commit, publikacja, zachowanie obu warstw zmian, recovery i cleanup. |
| `taskand` | Kolejność ewolucji, wspólne budżety potomków i użycie powyższych bramek przez scheduler. |

Efektową egzekucję i niezależny review zapewniają wdrożone kontrolery, nie
dokumenty. Pełna ochrona przed regresją wymaga testów jednostkowych,
kontraktowych i integracyjnych na dokładnym wyniku scalenia z bieżącym main,
ponowienia po zmianie bazy, zamrożenia HEAD podczas review oraz canary/rollback
przy wdrożeniu. Bezkonfliktowy merge tekstowy nie potwierdza zgodności zachowania.

### Zgodność historycznych profili

- `new-project`: bounded intent, worktree, lease i niezależny review są potrzebne
  także systemowi samodoskonalącemu się; błąd bramy nie upoważnia do jej wyłączenia.
- `taskand-v1` używa capsule i proc-catalog; glm53 stosuje genome i rejestry
  organizmów. To różne profile. Nie można deklarować zgodności przez podobne nazwy.
- Schemat envelope v1 miał obiekt rozszerzenia `taskand` na poziomie CloudEvents.
  Zachowujemy go historycznie; v2 umieszcza złożone dane w `data`, a rozszerzenia
  korelacji są tekstem. Niezgodna migracja wymaga nowego adresu kontraktu.
- Dotychczasowy bundle pomijał kopertę i dokumenty normatywne. Nowy generator
  obejmuje cały aktualny katalog schematów oraz normatywny dokument i narzędzia;
  nowy pominięty schemat powoduje błąd, nie cichą niepełną adopcję.
- Rosnący fencing token jest wymogiem bezpieczeństwa. Starszy kontroler
  zwiększający tylko leaseRevision wymaga naprawy/adaptera, nie osłabienia standardu.
- 9/9 starego audytora paczki nie sprawdza pełnego evolution-v1. Testy schematów
  nie dowodzą egzekwowania budżetów, izolacji, retencji ani niezależnego approval.
- Przegląd `wellmanifest/dsl/spec/DSL_STANDARD.md` i kontraktu
  `wellmanifest/logs` 0.3.0 potwierdził oddzielanie semantyki, transportu i authority.
  Logi mają własny request-only GBNF, Protobuf i zamkniętą projekcję JSON.
  Nowy profil taskand nie deklaruje automatycznej zgodności z tym modelem logów:
  jego adopcja wymaga osobnego, przypiętego adaptera i testów zgodności.
  Nie przeprowadzono pełnej walidacji wszystkich repozytoriów wellmanifest.

<!-- docs:section references -->
## Źródła i weryfikacja

`make test` sprawdza stary profil, bundle i nowe pozytywne/negatywne fixtures.
`make verify` ma istniejący błąd katalogu roboczego. Równoważne wywołanie
`node ../operations/catalog.mjs --verify` z katalogu `package/` potwierdziło
4 bindingi; nie uznajemy samego targetu Makefile za naprawiony.
Walidator fixtures w testach obsługuje tylko słowa kluczowe użyte w tym schemacie;
nie jest implementacją całego JSON Schema ani kontrolerem aplikacji.

Walidacja kontynuacji 2026-09-13: 46/46 testów standardu, w tym 36 przypadków
`DeliveryAdmission` (12 nowych dla recovery), konformacja starej paczki 9/9
i bundle PASS. Liczniki są danymi wejściowymi: test po zmianie ticketa nie
jest dowodem ich trwałości w jeszcze niezaimplementowanym store. Kontrola
pełnego lokalnego zakresu względem zaakceptowanej bazy ma zero błędów po
pominięciu dwóch niewymaganych aliasów seed `project.sh` i `project.bat`.
Ich kopie zachowano; właściwe `project/governance-check.*` pozostają niezmienione.
Limit 15 plików materialnych nie został zwiększony.

Oddzielny worktree guard zwraca `GOV-WORKTREE-OVERLAP-001` dla istniejących
kopii adopcji w primary i ticket-001. To blokuje commit; PASS bramki zakresu
nie jest PASS wszystkich bramek. Profil 1.1.0 i ta referencja pozostają
lokalnym kandydatem. Nie wykonano ich publikacji ani adopcji kontroli dostawy
w glm53; źródłowe testy nie dowodzą działania adaptera w schedulerze.

CloudEvents:
[specyfikacja 1.0.2](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md)
i [format JSON 1.0.2](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/formats/json-format.md).
Złożony obiekt rozszerzenia nie jest dozwolonym typem atrybutu kontekstu.
Wersja CloudEvents nie określa wersji payloadu domenowego.
