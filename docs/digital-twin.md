# Digital Twin i Bramki Kwalifikacji (Gate A & Gate B)

Piaskownica Digital Twin zapewnia pełną izolację testowanych procesów przed ich wdrożeniem na produkcję.

## Architektura Piaskownicy
- **twin/twin.compose.yaml**: Zdefiniowane środowisko testowe w odciętej sieci (`internal: true`).
- **twin/qualification.yaml**: Deklaratywna konfiguracja bramek kwalifikacyjnych.

## Bramki Kwalifikacji

### Gate A: Contract & Isolation
1. Weryfikacja formatu wejścia i wyjścia JSON (zgodność ze schematem).
2. Sprawdzenie reguły fail-closed: błędny JSON wejściowy musi natychmiast zwrócić kod wyjścia `2`.
3. Sprawdzenie braku wycieków poświadczeń w logach stderr/stdout.

### Gate B: Regression & Environmental Invariants
1. Uruchomienie scenariuszy testowych pod obciążeniem.
2. Sprawdzenie roszczeń wiedzy (`claims/`): upewnienie się, że stan bazy, wolumenów i usług zewnętrznych nie został uszkodzony.
3. Test automatycznego wycofania zmian (Rollback drill) w przypadku wystąpienia błędu.
