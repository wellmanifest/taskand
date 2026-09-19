---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "mcp-runtime-reliability",
  "kind": "information",
  "version": 1,
  "title": "Stabilne uruchamianie i odbiór Taskand MCP",
  "status": "proposed",
  "owner": "wellmanifest/taskand",
  "scope": "repository",
  "updated": "2026-09-19",
  "source_revision": "e1c6072065489ac1b907b4fd4de6c45494601320",
  "priority": "P2",
  "evidence": [
    "repo://semcod/taskand-glm53@8f2ee69f7cdb91af2a3fce8e90abc33d0e1131a5/packages/taskand-mcp/README.md",
    "repo://subactor/search@51de4e9c07ff90c80309ff91664181e767a6fd09/tests/test_mcp.py",
    "receipt:mcp-repair-20260919.local-startup-canary",
    "https://modelcontextprotocol.io/specification/2025-11-25/basic/transports"
  ]
}
---

# Stabilne uruchamianie i odbiór Taskand MCP

<!-- docs:section summary -->
## Cel i stan

Serwer MCP używany przez Taskand lub host LLM powinien działać niezależnie
od cyklu życia worktree. Poniższa procedura oddziela instalację, transport,
narzędzia i rzeczywiste wykonanie zadania.

<!-- docs:section details -->
## Instalacja i diagnoza

Używać przypiętego wheel/artefaktu i jawnego interpretera z trwałej instalacji
operatora. Konfiguracja wskazuje absolutny executable, osobne argv, dozwolony
root i minimalne środowisko. Nie uruchamiać z usuwanego worktree ani pobierać
najnowszych zależności przy każdym starcie. Sekrety dostarcza uprawniony runtime,
nie argumenty LLM, repozytorium lub log. Nie kopiować całego środowiska hosta.

Sprawdzić kolejno istnienie cwd, executable, docelowego interpretera shebang,
wersję Python i zależności. Zakończenie procesu przed initialize daje wtórny
broken pipe; zwiększenie timeoutu nie naprawia brakującego pliku.

Incydent 2026-09-19: redup wskazywał nieistniejący Python 3.11, koru nieistniejącą
instalację 3.12 pod /opt, search usunięty worktree ticket-006. Dwa pierwsze
środowiska naprawiono przez `uv venv --allow-existing` z istniejącym interpreterem
tej samej linii minor; pakiety zachowano. Search zainstalowano z dokładnego
scalonego commitu, poza worktree. To lokalna naprawa, nie przenośny deployment:
produkcyjny rollout powinien odtworzyć środowisko z locka i ponownie je sprawdzić.

W stdio stdout przenosi komunikaty MCP, a diagnostyka trafia na stderr.
Adapter obsługuje sesję MCP; nie zmienia procesowego kontraktu Taskand
„jedno JSON wejście → jedno JSON wyjście” w samym workerze.
[Specyfikacja transportu](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

Operator rozdziela czas startu, deadline wywołania, limit wyników i budżet
całego zadania. Po timeout/cancel sprawdza status skutku przed ponowieniem.
Dla lokalnego adaptera Taskand maksymalny timeout procesu wynosi 300 s;
budżet klienta powinien uwzględniać narzut adaptera. Nie oznacza to możliwości
przerwania zdalnego procesu ani wsparcia trwałych jobów.

<!-- docs:section validation -->
## Odbiór

Wymagane osobne dowody: initialize, tools/list ze schematami, dozwolona
bezpieczna operacja, odmowa bez grantu, błędne argumenty, timeout, ponowne
połączenie i zgodność tożsamości release. Sam proces, port lub HTTP 200
nie wystarczają. Po zmianie konfiguracji sprawdzić katalog rzeczywistej sesji.

Lokalnie: 6/6 zimnych prób transportu i bezpiecznych wywołań oraz 4 testy
search przeszły. Nie uruchomiono pytest redup/koru (brak pytest); nie badano
ich operacji efektowych. Pełny test delegacji pozostaje przed pilotem.

Dokumenty sprawdza `.governance/check_docs.py --docs-root /trusted/docs --root .`.
Używać `--prepare --format v2 --scope repository --kind information --id ID
--deliverable PATH`, a po zapisie i git add: `--complete --base SHA
--prepared-plan RECEIPT --deliverable PATH`. Pin Docs:
`19efafbeb18923cfd51cc69bd519330488500137`. Chronione CI nie zostało podłączone
przez ten lokalny adapter i nie należy deklarować jego egzekwowania.

<!-- docs:section risks -->
## Odpowiedzialność i rollback

Właściciel wdrożenia zachowuje poprzedni artefakt i konfigurację, uruchamia
canary nowego runtime, następnie przełącza klientów. Nie usuwa nieznanych
środowisk ani worktree. Standard nie instaluje demonów; runtime HOME pozostaje
w semcod/subactor. Docelowy klient Taskand powinien stosować tę samą procedurę.
