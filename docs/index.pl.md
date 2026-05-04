---
title: SaldeoSMART MCP
description: Serwer Model Context Protocol dla SaldeoSMART — odczyt i modyfikacja danych księgowych z dowolnego klienta AI obsługującego MCP.
hide:
  - navigation
---

# SaldeoSMART MCP

[![CI](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/piotrlinski/saldeosmart-mcp/blob/master/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-2a6db2.svg)](https://mypy-lang.org/)

Serwer [Model Context Protocol](https://modelcontextprotocol.io/) udostępniający
REST API [SaldeoSMART](https://www.saldeosmart.pl/) jako typowane,
przyjazne LLM narzędzia. Odczyt dokumentów, faktur, kontrahentów, pracowników,
wyciągów bankowych; tworzenie, aktualizacja, scalanie i synchronizacja danych
księgowych — z dowolnego klienta zgodnego z MCP (Claude Desktop, Claude Code,
Cursor, Zed, MCP Inspector lub własny SDK).

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Szybki start**

    ---

    Uruchom serwer w Dockerze, podłącz Claude Desktop i wykonaj pierwsze
    wywołanie narzędzia w pięć minut.

    [:octicons-arrow-right-24: Zacznij](tutorials/quickstart.md)

-   :material-book-open-variant:{ .lg .middle } **Przewodniki**

    ---

    Instalacja przez `uvx` lub Docker, konfiguracja każdego klienta MCP,
    diagnostyka uwierzytelniania, dodawanie nowego narzędzia.

    [:octicons-arrow-right-24: Przeglądaj](how-to/index.md)

-   :material-api:{ .lg .middle } **Dokumentacja API**

    ---

    Generowany automatycznie katalog narzędzi MCP, modeli wejścia/wyjścia,
    kodów błędów, konfiguracji oraz wersji REST API SaldeoSMART.

    [:octicons-arrow-right-24: Referencje](reference/index.md)

-   :material-school:{ .lg .middle } **Koncepcje**

    ---

    Dlaczego FastMCP, jak działa podpisywanie żądań, model współbieżności
    i podejście do bezpieczeństwa.

    [:octicons-arrow-right-24: Więcej](explanation/index.md)

</div>

## Po co to powstało

Biura rachunkowe i ich klienci spędzają dużo czasu na czynnościach
mechanicznych — przekazywaniu dokumentów, uzgadnianiu kontrahentów,
oznaczaniu wymiarów, synchronizacji deklaracji podatkowych. SaldeoSMART
udostępnia kompletne REST API dla tych operacji, ale ręczne podłączenie LLM
do tego API jest żmudne i podatne na błędy (podpisywane żądania, payloady
XML w gzip+base64, błędy per element w batchu). Ten serwer to ten cały
kabel zrobiony raz, dobrze: każdy udokumentowany endpoint jest dostępny
jako typowane narzędzie MCP z docstringiem, na podstawie którego LLM może
działać.

## Najważniejsze cechy

- :material-tools: **43 narzędzia** — każdy udokumentowany endpoint REST SaldeoSMART, pogrupowany według dziedziny.
- :material-shield-lock: **Prywatność** — tokeny `SecretStr`, redakcja URL-i w logach, blokada równoległych żądań.
- :material-test-tube: **Ścisłe typowanie** — modele Pydantic v2, CI z mypy strict.
- :material-translate: **Polski + English** — pełna dwujęzyczna dokumentacja (ta strona).
- :material-source-branch: **Licencja MIT**, projekt nie jest powiązany z SaldeoSMART/BrainShare.

## W skrócie

```bash
# Uruchomienie w Dockerze
docker run --rm -i \
  -e SALDEO_USERNAME=twój-login \
  -e SALDEO_API_TOKEN=twój-token \
  ghcr.io/piotrlinski/saldeosmart-mcp:latest

# Lub przez uvx (bez demona Dockera)
uvx saldeosmart-mcp \
  --username twój-login \
  --api-token twój-token
```

Następnie wskaż klientowi MCP powyższe polecenie. Pełna konfiguracja:
[Konfiguracja Claude Desktop](how-to/configure-claude-desktop.md).

!!! warning "Uwaga — narzędzia zapisu modyfikują dane księgowe"
    Każde narzędzie `merge_*`, `add_*`, `update_*`, `delete_*`,
    `recognize_*`, `sync_*` i `create_*` zmienia dane na koncie klienta.
    Zanim udostępnisz je autonomicznemu agentowi, przejrzyj
    [katalog narzędzi](reference/tools/index.md).

!!! info "Strony referencyjne pozostają w języku angielskim"
    Katalog narzędzi, modeli, kodów błędów i wersji API jest generowany
    z docstringów w kodzie źródłowym (po angielsku), aby zachować spójność
    z kontraktem narzędzi MCP. Strony przewodników, samouczków i koncepcji
    są tłumaczone na polski.
