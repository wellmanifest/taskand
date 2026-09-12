# Zarządzanie Sekretami i Poświadczeniami w Standardzie taskand v1.0

Dokument definiuje architekturę bezpieczeństwa poświadczeń, tokenów i haseł w procesach i kontenerach.

## Zasada Złota (Zero Secrets at Rest)
Klucze API, tokeny, hasła do baz danych i certyfikaty **pod żadnym pozorem nie mogą być utrwalane w obrazach Dockerfile, skryptach, repozytorium git ani plikach pamięci trwałej**.

## 4 Wzorce Bezpieczeństwa

### 1. Wstrzykiwanie w Runtime (dla procesów i kontenerów)
- Hasła przekazywane są wyłącznie przez zmienne środowiskowe w momencie uruchomienia:
  ```bash
  docker run --env-file .env -e API_KEY="${API_KEY}" proc-image
  ```
- Plik `.env` jest bezwzględnie dopisany do `.gitignore`.
- Nigdy nie używaj instrukcji `ENV SECRET=...` w pliku Dockerfile.

### 2. Vault Agent Sidecar (dla środowisk rozproszonych)
- Kontener pomocniczy pobiera sekrety z HashiCorp Vault lub AWS Secrets Manager.
- Zapisuje je w pamięci RAM (`tmpfs` zamontowanym w `/vault/secrets`).
- Proces główny czyta hasło z pamięci RAM — dysk nie rejestruje żadnego śladu.

### 3. BuildKit Secret Mounts (podczas budowania obrazów)
- Gdy instalacja zależności wymaga autoryzacji:
  ```dockerfile
  RUN --mount=type=secret,id=token \
      TOKEN=$(cat /run/secrets/token) && curl -H "Authorization: Bearer $TOKEN" https://pkg.org
  ```
- Sekret nie pozostaje w żadnej warstwie obrazu wynikowego.

### 4. Bezpieczny Montaż Read-Only
- Dla narzędzi CLI hosta (np. GitHub CLI):
  ```yaml
  volumes:
    - "${HOME}/.config/gh:/root/.config/gh:ro"
  ```
- Prawa dostępu do plików na hoście muszą być ograniczone do właściciela (`chmod 600`).
