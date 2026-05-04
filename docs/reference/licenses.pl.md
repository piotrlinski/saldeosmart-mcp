---
title: Licencje zależności
description: Generowana automatycznie lista wszystkich zależności runtime i ich licencji.
---

# Licencje zależności

!!! info "Ta strona referencyjna jest dostępna tylko w języku angielskim"
    Inwentarz licencji zależności jest generowany z metadanych pakietów
    (po angielsku) i odświeżany przy każdym buildzie dokumentacji. Aby
    przeczytać pełną listę, użyj przełącznika języka u góry strony i
    przejdź na wersję angielską: [Third-party licenses](licenses.md).

W skrócie:

- **Licencja projektu**: MIT.
- **Zależności runtime** (instalowane razem z `pip install saldeosmart-mcp`):
  wyłącznie licencje permisywne (MIT, BSD, Apache-2.0, ISC, PSF, Public
  Domain) plus jedna zależność na licencji MPL-2.0 (`certifi`) — wszystkie
  zgodne z dystrybucją MIT.
- **Brak silnych licencji copyleft** (GPL/AGPL/LGPL) wśród zależności
  runtime.
- **Narzędzia developerskie i dokumentacyjne** (np. `codespell` GPL-2.0)
  nie są dystrybuowane razem z paczką — używamy ich tylko podczas buildu.
