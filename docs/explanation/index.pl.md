# Koncepcje

Materiały tłumaczące, dlaczego kod ma taką strukturę. Przydatne podczas
utrzymywania projektu, audytu bezpieczeństwa lub wdrażania nowego
współtwórcy.

Zorientowane na zadania przepisy znajdziesz w [przewodnikach](../how-to/index.md).
Generowane automatycznie referencje API — w sekcji
[Dokumentacja](../reference/index.md).

## Co tu jest

- [**Architektura**](architecture.md) — stos warstw, reguła kierunku importów,
  cykl życia wywołania narzędzia.
- [**Podpisywanie żądań**](request-signing.md) — algorytm MD5 wymagany przez
  Saldeo, z diagramem sekwencji.
- [**Współbieżność**](concurrency.md) — dlaczego każde żądanie idzie przez
  pojedynczą `threading.Lock` (Saldeo zabrania równoległych żądań na użytkownika).
- [**Bezpieczeństwo i prywatność**](security-and-privacy.md) — tokeny
  `SecretStr`, redakcja URL-i w logach, polityka „tylko odczyt" testu dymnego,
  założenia dotyczące powierzchni ataku.
- [**Decyzje projektowe**](design-decisions.md) — bieżący dziennik
  nieoczywistych wyborów: dlaczego FastMCP, dlaczego MD5 (specyfikacja
  Saldeo), dlaczego jeden model Pydantic na kierunek, dlaczego podział
  `_runtime`/`_builders`, oraz czego świadomie nie robimy.
