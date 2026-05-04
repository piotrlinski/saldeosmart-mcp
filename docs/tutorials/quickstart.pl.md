# Szybki start

W pięć minut uruchomisz serwer SaldeoSMART MCP w Dockerze, a Twój klient
Claude Desktop wywoła jego narzędzia.

## Warunki wstępne

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24, demon uruchomiony.
- Konto SaldeoSMART z włączonym dostępem do API. Token wygenerujesz w
  **Konfiguracja → Konto → API → Generuj token**. W niektórych planach
  trzeba najpierw napisać do `api@saldeosmart.pl`, by włączyli API.
- Zainstalowany [Claude Desktop](https://claude.ai/download).

!!! info "Tylko użytkownicy biura rachunkowego mogą generować tokeny"
    Portal API jest dostępny wyłącznie dla użytkowników *biura rachunkowego*.
    Klienci biura nie wygenerują tokenu — należy poprosić biuro o
    udostępnienie dostępu do API z konta biura.

## 1. Zbuduj obraz

```bash
git clone https://github.com/piotrlinski/saldeosmart-mcp.git
cd saldeosmart-mcp
make build
```

Buduje to dwuetapowy `docker/Dockerfile`:

1. **builder** — `uv sync --frozen --no-dev` względem `uv.lock`, kompilacja bytecodu.
2. **runtime** — Python 3.12-slim, nieuprzywilejowany użytkownik `mcp`, ~234 MB.

## 2. Skonfiguruj Claude Desktop

Otwórz `claude_desktop_config.json`:

- **macOS** — `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows** — `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux** — `~/.config/Claude/claude_desktop_config.json`

Dodaj wpis `saldeosmart` w `mcpServers`:

```json
{
  "mcpServers": {
    "saldeosmart": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "SALDEO_USERNAME=twój-login",
        "-e", "SALDEO_API_TOKEN=twój-token",
        "saldeosmart-mcp:latest"
      ]
    }
  }
}
```

Uruchom Claude Desktop ponownie.

## 3. Sprawdź

W nowej rozmowie zapytaj Claude'a:

> Wymień narzędzia SaldeoSMART, do których masz dostęp.

Powinieneś zobaczyć 43 narzędzia pogrupowane według zasobu: `list_companies`,
`list_documents`, `merge_contractors` itd.

## Następne kroki

- [**Pierwsze wywołanie narzędzia**](first-tool-call.md) — wywołaj prawdziwy endpoint odczytu.
- [Konfiguracja innych klientów](../how-to/configure-other-clients.md) — Cursor, Claude Code, Zed, MCP Inspector.
- [Katalog narzędzi](../reference/tools/index.md) — każde narzędzie, każdy parametr.

## Rozwiązywanie problemów

??? failure "Claude Desktop pisze `command not found: docker`"
    Zamień `"command": "docker"` na pełną ścieżkę z polecenia
    `which docker` (np. `/usr/local/bin/docker`). Claude Desktop uruchamia
    serwery MCP bez dziedziczenia `PATH` z powłoki.

??? failure "Lista narzędzi jest pusta"
    Sprawdź plik logów — domyślnie `/var/log/saldeosmart/saldeosmart.log`
    wewnątrz kontenera. Najczęstszą przyczyną jest brak lub nieprawidłowy
    token. Zobacz [Diagnostyka uwierzytelniania](../how-to/debug-auth.md).
