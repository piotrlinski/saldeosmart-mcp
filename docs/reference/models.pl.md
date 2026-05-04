---
title: Modele
description: Modele Pydantic dla każdego wejścia i odpowiedzi przekraczającego granicę MCP.
---

# Modele

!!! info "Ta strona referencyjna jest dostępna tylko w języku angielskim"
    Modele Pydantic są generowane automatycznie z docstringów (po angielsku),
    aby zachować spójność z kontraktem narzędzi MCP. Aby przeczytać pełny opis
    modeli, użyj przełącznika języka u góry strony i przejdź na wersję
    angielską: [Models](models.md).

Strona angielska zawiera:

- Wspólne typy walidowane: `IsoDate`, `Nip`, `Pesel`, `VatNumber`, `Year`, `Month`.
- Modele wejść zapisu (`*Input`) z ograniczeniami pól.
- Modele odpowiedzi odczytu (`Document`, `Invoice`, `Contractor`, …) z metodami
  `from_xml`.

W razie wątpliwości skonsultuj się z [katalogiem narzędzi](tools/index.md),
który dla każdego narzędzia wskazuje konkretny model wejścia i odpowiedzi.
