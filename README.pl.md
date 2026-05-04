# SaldeoSMART MCP Server

[![CI](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml)
[![Docs](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/docs-deploy.yml/badge.svg)](https://piotrlinski.github.io/saldeosmart-mcp/pl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-2a6db2.svg)](https://mypy-lang.org/)

Serwer [Model Context Protocol](https://modelcontextprotocol.io/) udostępniający
REST API [SaldeoSMART](https://www.saldeosmart.pl/) jako typowane,
przyjazne LLM narzędzia — odczyt dokumentów, faktur, kontrahentów,
pracowników, wyciągów bankowych; tworzenie, aktualizacja, scalanie
i synchronizacja danych księgowych — z dowolnego klienta MCP
(Claude Desktop, Claude Code, Cursor, Zed, MCP Inspector).

## :rocket: Szybki start (30 sekund)

```bash
# Zbuduj obraz
git clone https://github.com/piotrlinski/saldeosmart-mcp.git
cd saldeosmart-mcp && make build

# Uruchom — wskaż klientowi MCP poniższe polecenie:
docker run --rm -i \
  -e SALDEO_USERNAME=twój-login \
  -e SALDEO_API_TOKEN=twój-token \
  saldeosmart-mcp:latest
```

Bez Dockera:

```bash
uvx --from git+https://github.com/piotrlinski/saldeosmart-mcp \
    saldeosmart-mcp --username twój-login --api-token twój-token
```

[**Pełna dokumentacja →**](https://piotrlinski.github.io/saldeosmart-mcp/pl/) ·
[Wersja angielska](https://piotrlinski.github.io/saldeosmart-mcp/) ·
[Katalog narzędzi](https://piotrlinski.github.io/saldeosmart-mcp/reference/tools/) ·
[Konfiguracja klienta MCP](https://piotrlinski.github.io/saldeosmart-mcp/pl/how-to/) ·
[Współtworzenie](CONTRIBUTING.md)

## Najważniejsze cechy

- :material-tools: **43 narzędzia** opakowujące każdy udokumentowany endpoint REST SaldeoSMART.
- :material-shield-lock: **Prywatność** — tokeny `SecretStr`, redakcja URL-i w logach, blokada równoległych żądań.
- :material-test-tube: **Ścisłe typowanie** — modele Pydantic v2, CI z mypy w trybie strict.
- :material-translate: **English + Polski** — dwujęzyczna dokumentacja.
- :material-source-branch: **Licencja MIT**, projekt nie jest powiązany z SaldeoSMART/BrainShare.

## Wymagania

- Konto SaldeoSMART z włączonym dostępem do API
  ([wygeneruj token](https://piotrlinski.github.io/saldeosmart-mcp/pl/tutorials/quickstart/#warunki-wstepne)).
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24
  lub [`uv`](https://docs.astral.sh/uv/) ≥ 0.4.
- Klient zgodny z MCP.

## :warning: Narzędzia zapisu modyfikują dane księgowe

Każde narzędzie `merge_*`, `add_*`, `update_*`, `delete_*`, `recognize_*`,
`sync_*` i `create_*` zmienia dane na koncie SaldeoSMART klienta. Przed
udostępnieniem ich autonomicznemu agentowi przejrzyj
[katalog narzędzi](https://piotrlinski.github.io/saldeosmart-mcp/reference/tools/).

## Limity API

- 20 zapytań na minutę na użytkownika.
- Brak współbieżnych zapytań — klient serializuje wywołania przez `threading.Lock`.
- Maksymalny rozmiar payloadu: ~70 MB po zakodowaniu base64.

## Rozwój projektu

```bash
make sync          # uv sync --extra dev
make test          # pytest
make lint          # ruff + mypy
make docs-serve    # podgląd dokumentacji na http://127.0.0.1:8000
```

Procedura współtworzenia: [`CONTRIBUTING.md`](CONTRIBUTING.md) (zasady warstw
architektury i kontrakt docstringów dla LLM). Ścieżka zgłaszania luk
bezpieczeństwa: [`SECURITY.md`](SECURITY.md). Historia zmian:
[`CHANGELOG.md`](CHANGELOG.md).

## Licencja

[MIT](LICENSE) — pełny tekst w pliku. Projekt nie jest oficjalnym produktem
SaldeoSMART/BrainShare.
