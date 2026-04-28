# SaldeoSMART MCP Server

Read-only MCP server dla [SaldeoSMART](https://www.saldeosmart.pl/) — pozwala Claude'owi czytać dokumenty, faktury i kontrahentów z Twojego konta.

## Co umie


| Tool               | Co robi                                                                                  |
| ------------------ | ---------------------------------------------------------------------------------------- |
| `list_companies`   | Listuje firmy w Saldeo (klientów biura)                                                 |
| `list_contractors` | Listuje kontrahentów dla wybranej firmy                                                 |
| `list_documents`   | Pobiera dokumenty kosztowe (z polityką: ostatnie 10 dni / OCR / oznaczone do wysłania) |
| `search_documents` | Szuka konkretnego dokumentu po ID, numerze, NIP lub GUID                                 |
| `list_invoices`    | Listuje faktury sprzedażowe wystawione w Saldeo                                         |

## Wymagania

Do uruchomienia serwera (production):

- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** ≥ 24 — obraz buduje się z `docker/Dockerfile`. Demon dockerowy musi działać.
- **GNU Make** — do uruchamiania `make build`/`make run`. Na macOS/Linux jest standardowo; Windows: WSL albo `make` z chocolatey.
- **Konto SaldeoSMART z dostępem API** — token generujesz w **Ustawienia konta → API**.
- **Claude Desktop** (jeśli chcesz spiąć z Claude'em).

Dodatkowo do pracy nad kodem (tylko deweloperzy):

- **[`uv`](https://docs.astral.sh/uv/)** — odpala testy/lint w lokalnym `.venv`. Sam ogarnia Pythona ≥ 3.10 z `pyproject.toml`. Nie trzeba go mieć żeby zbudować obraz — uv siedzi w warstwie buildera Dockerfile'a.
- **Node.js + npx** — opcjonalne, do MCP Inspectora (`make inspector`).

> ⚠️ Aby dostać token API, w niektórych planach trzeba napisać do `api@saldeosmart.pl` i poprosić o aktywację.

## Build obrazu

```bash
git clone <ten-repo>
cd saldeosmart-mcp
make build          # = docker build -f docker/Dockerfile -t saldeosmart-mcp:latest .
```

### Struktura obrazu

Dockerfile (`docker/Dockerfile`) jest dwustopniowy:

1. **`builder`** — bazuje na `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`. Tutaj `uv sync --frozen --no-dev` rozwiązuje i instaluje zależności z `uv.lock` w izolowanym `.venv`, a następnie kompiluje bytecode. Cache uv-a siedzi w mount cache'u BuildKitu, więc kolejne buildy są szybkie.
2. **`runtime`** — bazuje na czystym `python:3.12-slim-bookworm`. Kopiuje gotowy `.venv` z buildera, zakłada nieuprzywilejowanego użytkownika `mcp` i ustawia `ENTRYPOINT ["saldeosmart-mcp"]`.

Detale runtime'u:

- `PATH="/app/.venv/bin:$PATH"` — `saldeosmart-mcp` (console-script z `pyproject.toml`) jest na PATH.
- `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1` — żeby Python nie psuł stdio (transport MCP) i nie zaśmiecał obrazu plikami `.pyc`.
- `SALDEO_LOG_DIR=/var/log/saldeosmart` + `VOLUME` na ten katalog — patrz [Logi](#logi).
- `USER mcp` — kontener nie chodzi z roota.

Gotowy obraz: Python 3.12-slim + `.venv` z `fastmcp`, `httpx`, `pydantic`, `pydantic-settings` + kod pakietu. Rozmiar: ~234 MB.

Inne przydatne cele Makefile'a:

```bash
make help           # lista wszystkich celów
make run            # uruchom serwer w kontenerze (wymaga SALDEO_USERNAME / SALDEO_API_TOKEN w env)
make inspector      # MCP Inspector przeciwko obrazowi
make test           # pytest lokalnie (potrzebuje uv)
make lint           # ruff + mypy lokalnie (potrzebuje uv)
make sync           # uv sync --extra dev — zainstaluj dev dependencies
make clean          # docker image rm saldeosmart-mcp:latest
```

Tag obrazu / ścieżkę do Dockerfile'a możesz nadpisać:

```bash
IMAGE=saldeosmart-mcp:dev make build
```

## Konfiguracja Claude Desktop

Otwórz `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Dodaj wpis:

```json
{
  "mcpServers": {
    "saldeosmart": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "SALDEO_USERNAME=twoj-login",
        "-e", "SALDEO_API_TOKEN=twoj-token-z-ustawien",
        "-e", "SALDEO_BASE_URL=https://saldeo.brainshare.pl",
        "saldeosmart-mcp:latest"
      ]
    }
  }
}
```

Flagi `-i` i `--rm` są wymagane: MCP używa stdio, więc kontener musi mieć podpięte stdin (`-i`), a nie ma sensu zostawiać zatrzymanych kontenerów po sesji (`--rm`). Forma `-e KEY=value` ustawia zmienną w kontenerze niezależnie od shell-a hosta — credentials siedzą w `claude_desktop_config.json`, nie w `~/.zshrc`/`~/.bashrc`.

> 🔒 Jeśli wolisz nie trzymać tokenu w configu Claude'a, zrób plik `~/saldeosmart.env` (`chmod 600`) z liniami `KEY=VALUE` i podmień `-e ...` na `"--env-file", "/Users/ty/saldeosmart.env"`. Plik łatwo trzymać poza repo i rotować bez ruszania configu Claude'a.

Jeśli Claude Desktop zgłosi, że nie znajduje `docker`, podaj absolutną ścieżkę z `which docker` zamiast samej nazwy.

Dla testów użyj `https://saldeo-test.brainshare.pl` jako `SALDEO_BASE_URL`.

Restart Claude Desktop. Powinieneś zobaczyć ikonkę narzędzi 🔧 w polu czatu.

## Test lokalny (bez Claude'a)

```bash
export SALDEO_USERNAME=twoj-login
export SALDEO_API_TOKEN=twoj-token
make run            # = docker run --rm -i -e SALDEO_USERNAME -e SALDEO_API_TOKEN ... saldeosmart-mcp:latest
```

Serwer wystartuje i będzie czekać na wiadomości MCP na stdin/stdout.

Z [MCP Inspectorem](https://github.com/modelcontextprotocol/inspector):

```bash
make inspector
```

## Testy

```bash
make sync           # raz, żeby założyć .venv z dev deps
make test           # pytest
make lint           # ruff + mypy
```

Pokrywają najbardziej zdradliwą część — algorytm podpisu MD5 i kodowanie XML→gzip→base64.

## Logi

W obrazie logi domyślnie lądują pod `/var/log/saldeosmart/saldeosmart.log` (rotacja dobowa, 7 dni). Żeby je trzymać poza kontenerem, podmontuj wolumen:

```bash
docker run --rm -i \
    -e SALDEO_USERNAME=... -e SALDEO_API_TOKEN=... \
    -v saldeosmart-logs:/var/log/saldeosmart \
    saldeosmart-mcp:latest
```

## Architektura

- `client.py` — niskopoziomowy klient HTTP. Obsługuje:
  - sygnaturę `req_sig` (MD5 z posortowanych parametrów + URL-encode + token)
  - kodowanie payloadu XML (`gzip` → `base64` → param `command`)
  - automatyczną dekompresję odpowiedzi (gzip via httpx)
  - parsowanie błędów Saldeo (`<STATUS>ERROR</STATUS>`)
- `server.py` — warstwa MCP. Każdy `@mcp.tool` to czysta funkcja Pythona z typami i docstringiem; FastMCP sam buduje JSON Schema i opisy dla Claude'a.

## Limity API (uwaga!)

Spec mówi:

- **20 żądań na minutę** per użytkownik
- **Brak równoczesnych żądań** — kolejne wysyłaj dopiero po odpowiedzi na poprzednie
- Max payload: ~70 MB po kodowaniu base64

Jeśli planujesz odpytywać dużo, zastanów się nad cache'em po stronie serwera.

## Co dalej

Ten serwer jest **read-only**. Jeśli kiedyś będziesz chciał:

- dodawać dokumenty (`document/add`) — wymaga przesyłania plików jako `attmnt_X` (już wstępnie obsłużone w `client.post_command`)
- aktualizować kontrahentów (`contractor/merge`)
- zlecać OCR (`document/recognize`)

…to wzorzec jest gotowy: nowe `@mcp.tool` w `server.py` + budowanie odpowiedniego XML-a + `client.post_command(...)`.

## Licencja

MIT. Nie jest to oficjalny produkt SaldeoSMART/BrainShare.
