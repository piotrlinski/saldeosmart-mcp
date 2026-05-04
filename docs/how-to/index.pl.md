# Przewodniki

Zorientowane na zadania przepisy odpowiadające na konkretne pytania, które
pojawią się po uruchomieniu serwera. Każdy przewodnik odpowiada dokładnie na
jedno pytanie. Aby poznać projekt od strony użytkownika, zacznij od
[samouczków](../tutorials/index.md).

## Konfiguracja

- [Instalacja serwera](install.md) — `uvx`, `pip` lub Docker.
- [Konfiguracja Claude Desktop](configure-claude-desktop.md)
- [Konfiguracja Claude Code](configure-claude-code.md)
- [Konfiguracja Cursor](configure-cursor.md)
- [Konfiguracja innych klientów](configure-other-clients.md) — Zed, MCP Inspector, własny SDK.

## Eksploatacja

- [Diagnostyka uwierzytelniania](debug-auth.md) — interpretacja błędów 401 i syntetycznych kodów `HTTP_*`.
- [Uruchom test dymny](run-smoke-test.md) — sprawdź, czy świeżo wdrożona instancja faktycznie rozmawia z Saldeo. Tylko odczyt — z założenia.

## Rozwój

- [Dodaj nowe narzędzie](add-a-tool.md) — opakuj endpoint SaldeoSMART w pięciu krokach.
- [Bumpnij wersję API SaldeoSMART](bump-saldeo-api-version.md) — gdy producent opublikuje 3.2, oto procedura.

## Wybór właściwego narzędzia odczytu

SaldeoSMART ma kilka ścieżek odczytu o nakładających się kształtach. Wybieraj
po pytaniu, na które odpowiadasz:

| Pytanie | Narzędzie |
|---|---|
| „Co dodano ostatnio?" | `list_documents` (policy: `LAST_10_DAYS` / `LAST_10_DAYS_OCRED` / `SALDEO`) |
| „Znajdź jeden dokument po ID/numerze/NIP/GUID." | `search_documents` |
| „Pobierz wszystko z folderu, stronicowo." | `get_document_id_list` → `get_documents_by_id` (3.0) |
| „Pokaż wystawione faktury sprzedaży." | `list_invoices` |
| „Pobierz faktury po liście ID." | `get_invoice_id_list` → `get_invoices_by_id` (3.0) |
| „Co OCR rozpoznał?" | `list_recognized_documents` |
| „Wymień kontrahentów / pracowników / wyciągi bankowe." | `list_contractors` / `list_employees` / `list_bank_statements` |
