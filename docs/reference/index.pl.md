---
title: Dokumentacja API
description: Generowane automatycznie referencje narzędzi MCP, modeli, kodów błędów i wersji API.
---

# Dokumentacja API

!!! info "Strony referencyjne pozostają w języku angielskim"
    Strony w tej sekcji są generowane z docstringów w kodzie źródłowym
    (po angielsku), aby zachować spójność z kontraktem narzędzi MCP, do
    którego LLM-y mają się odnosić jako do jednego źródła prawdy.

    Strony **przewodników**, **samouczków** i **koncepcji** są dostępne
    również w polskiej wersji językowej. Aby przełączyć się na angielską
    wersję dokumentacji API, użyj przełącznika języka u góry strony.

Wszystko, co znajdziesz w tej sekcji:

- [**Tools**](tools/index.md) — każde narzędzie `@mcp.tool` zarejestrowane
  w instancji FastMCP, pogrupowane według zasobu Saldeo (documents,
  invoices, contractors, …).
- [**Models**](models.md) — modele Pydantic wejść i odpowiedzi z ograniczeniami
  pól i walidatorami.
- [**Configuration**](configuration.md) — zmienne środowiskowe i flagi CLI.
- [**Error codes**](error-codes.md) — kody zwracane przez Saldeo i
  syntetyczne kody klienta wraz z wskazówkami diagnostycznymi.
- [**API versions**](api-versions.md) — która wersja REST API SaldeoSMART
  jest obecnie celem każdego narzędzia.
- [**Changelog**](changelog.md) — historia wydań (Keep a Changelog, SemVer).
