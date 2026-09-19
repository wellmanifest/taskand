---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "taskand-mcp-reuse",
  "kind": "information",
  "version": 2,
  "title": "Dobór MCP i kierunki integracji Taskand",
  "status": "proposed",
  "owner": "wellmanifest/taskand",
  "scope": "repository",
  "updated": "2026-09-19",
  "source_revision": "e1c6072065489ac1b907b4fd4de6c45494601320",
  "priority": "P2",
  "evidence": [
    "repo://semcod/taskand-glm53@8f2ee69f7cdb91af2a3fce8e90abc33d0e1131a5/packages/taskand-mcp/README.md",
    "repo://semcod/redup@c0afd9f4f63e774ec9b0e0018efc2dfbbd2716a0/src/redup/mcp/handlers.py",
    "repo://semcod/koru@f837788088540da1dc72736a44bb8c2011d8364d/src/koruapi/mcp_server_planfile.py",
    "repo://subactor/search@51de4e9c07ff90c80309ff91664181e767a6fd09/src/subactor_search/mcp_server.py"
  ]
}
---

# Dobór MCP i kierunki integracji Taskand

<!-- docs:section summary -->
## Cel i stan

Taskand powinien reużywać istniejące MCP zamiast ponownie implementować wyszukiwanie,
analizę kodu i obsługę zadań. To wskazówki pilotażu, nie nowy schemat ani dowód
wdrożenia klienta MCP w glm53.

<!-- docs:section details -->
## Dwa kierunki i dobór narzędzi

LLM → serwer MCP Taskand → gateway → proces URI: lokalny adapter udostępnia
`list_processes`, `describe_process`, `call_process`. URI pozostaje argumentem;
nie trzeba tworzyć osobnego narzędzia MCP dla każdego procesu. Odkrywalność
publicznego katalogu nie jest uprawnieniem do wykonania.

Taskand → klient MCP → zewnętrzny serwer: wymaga osobnego procesu-adaptera,
rejestracji URI i grantów. Konfiguracja MCP w hoście LLM nie konfiguruje Taskand.
Nie importować kodu innych paczek bezpośrednio do orkiestratora.

| Potrzeba | Reużywany serwer i narzędzia | Granica pilotażu |
| --- | --- | --- |
| Kontekst projektu | subactor-search: `search_projects`, `list_projects`, `index_status` | Odczyt indeksu; zachować cytowania, wiek i luki pokrycia. Nie przedstawiać snapshotu jako live. |
| Duplikacja i kandydaci refaktoryzacji | redup: `project_info`, `analyze_project`, `compare_scans` | Przypięty root, limity plików/wyników; brak automatycznego stosowania sugestii. |
| Katalog i plan pracy | koru: `koru_list_tickets`, `koru_ide_command_scenario_schema` | Sprawdzić faktyczne efekty konkretnej wersji, nie ufać nazwie narzędzia. |
| Delegowanie wykonania | koru: `koru_run_ticket`, `koru_job_status` | Dopiero z grantem efektowym, ticketem, izolacją i lease. Nie uruchamiać w canary odczytowym. |

Dla każdego nowego bindingu operator zapisuje wersjonowane URI, właściciela,
rewizję artefaktu serwera, dokładną nazwę narzędzia, digest kontraktu wejścia/wyjścia,
mapowanie argumentów, root danych, timeout, limity, klasę efektu i referencję
grantu. To lista kryteriów rejestracji, nie pola do dopisania do zamkniętego
`proc.yaml` bez osobnej zmiany schematu. Nie rejestrować fikcyjnych URI.

Start: wyszukiwanie → ograniczona analiza redup → kandydat zmian → testy →
niezależna walidacja. Zapis i publikacja pozostają u kontrolerów repozytorium.
[Granice agentów](https://github.com/wellmanifest/agent/blob/c9db0a22ce213365e1c5abf79111bc9ce3e29ed9/docs/INFORMATION/MCP_CLIENT_BOUNDARIES.md)
są przypięte do dokładnej rewizji towarzyszącego przewodnika.
[Obsługa runtime](MCP_RUNTIME_RELIABILITY.md) opisuje stabilne uruchamianie.

<!-- docs:section validation -->
## Dowody i kryteria odbioru

Obserwacja 2026-09-19: initialize, tools/list i bezpieczne wywołanie przeszły
dla redup (8 narzędzi), koru (36) i search (3), po dwa zimne starty.
Nie testowano wykonania ticketu, pulpitu ani przepływu Taskand → MCP.
Brak dodatków AST/semantic redup ogranicza dostępne analizy.

Adapter Taskand przeszedł 9 testów fixture; live pokazał 29 procesów i odmowę
codegen dla gościa. To dowód transportu, nie przyspieszenia developmentu.
Pilot powinien porównać te same zadania: czas całkowity, koszt/tokeny,
zaakceptowane wyniki, retry i regresje, z delegacją oraz bez niej.

<!-- docs:section risks -->
## Ograniczenia i kolejny krok

Gateway zgłaszał `MISMATCH_OR_INVALID`; przed efektem wymagane jest potwierdzenie
tożsamości runtime. Kontrola tylko zewnętrznego URI nie dowodzi grantów
tranzytywnych. Timeout oznacza możliwy nieznany wynik, nie zgodę na retry.
Właściciel runtime glm53 implementuje klienta i kwalifikuje jeden odczytowy
binding. Wycofanie pilota oznacza wyłączenie tego bindingu, nie usuwanie danych.
