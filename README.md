# SaldeoSMART MCP Server

Read-only MCP server dla [SaldeoSMART](https://www.saldeosmart.pl/) — pozwala Claude'owi czytać dokumenty, faktury i kontrahentów z Twojego konta.

## Co umie

| Tool | Co robi |
|---|---|
| `list_companies` | Listuje firmy w Saldeo (klientów biura) |
| `list_contractors` | Listuje kontrahentów dla wybranej firmy |
| `list_documents` | Pobiera dokumenty kosztowe (z polityką: ostatnie 10 dni / OCR / oznaczone do wysłania) |
| `search_documents` | Szuka konkretnego dokumentu po ID, numerze, NIP lub GUID |
| `list_invoices` | Listuje faktury sprzedażowe wystawione w Saldeo |

## Wymagania

- Python 3.10+
- Konto SaldeoSMART z dostępem API (token generujesz w **Ustawienia konta → API**)
- Claude Desktop

> ⚠️ Aby dostać token API, w niektórych planach trzeba napisać do `api@saldeosmart.pl` i poprosić o aktywację.

## Instalacja

```bash
git clone <ten-repo>
cd saldeosmart-mcp
pip install -e .
```

Albo z `uv`:

```bash
uv pip install -e .
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
      "command": "python",
      "args": ["-m", "saldeosmart_mcp.server"],
      "env": {
        "SALDEO_USERNAME": "twoj-login",
        "SALDEO_API_TOKEN": "twoj-token-z-ustawien",
        "SALDEO_BASE_URL": "https://saldeo.brainshare.pl"
      }
    }
  }
}
```

Dla testów użyj `https://saldeo-test.brainshare.pl` jako `SALDEO_BASE_URL`.

Restart Claude Desktop. Powinieneś zobaczyć ikonkę narzędzi 🔧 w polu czatu.

## Test lokalny (bez Claude'a)

```bash
export SALDEO_USERNAME=twoj-login
export SALDEO_API_TOKEN=twoj-token
python -m saldeosmart_mcp.server
```

Serwer powinien wystartować i czekać na wiadomości MCP na stdin/stdout.

Możesz też użyć [MCP Inspectora](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector python -m saldeosmart_mcp.server
```

## Testy

```bash
pip install pytest
pytest tests/
```

Pokrywają najbardziej zdradliwą część — algorytm podpisu MD5 i kodowanie XML→gzip→base64.

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
