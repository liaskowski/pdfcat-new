# Gemini Project Guidelines: PDFLibrary Client

## 1. Project Overview
A modular, high-performance Document Management System (DMS) client built with Python.
* **Core Framework:** PyQt6 (UI), PyMuPDF/Fitz (Rendering), Requests (API).
* **Architecture:** Modular MVC (Model-View-Controller). Logic and UI must be separated.

## 2. Critical Rules (DO NOT BREAK)
1.  **Strict Typing:** All new methods must have type hints (`def func(a: int) -> str:`).
2.  **No Monoliths:** Do not create files larger than 400 lines. If a class grows too big, extract logic into a Mixin, a Helper, or a separate Controller.
3.  **Threading:** heavy operations (PDF rendering, Network calls, File IO) **MUST** run in `QThread` or `QRunnable`. Never block the Main Loop.
4.  **Error Handling:** Use `try-except` blocks around external calls (API, File System). Log errors via the centralized `Logger`, do not just `print()`.

## 3. UI & Styling Guidelines
* **Theming:** NEVER hardcode colors (e.g., `#000000`). Use the `ThemeManager` or CSS variables defined in `assets/themes`.
* **Layouts:** Always use `QVBoxLayout`, `QHBoxLayout`, or `QGridLayout`. Do not use absolute positioning (`setGeometry`).
* **Icons:** Use `qtawesome` with FontAwesome 5 Solid (`fa5s`).

## 4. Internationalization (i18n)
* **Strict Rule:** No hardcoded strings in UI.
* **Mechanism:** Use the `Translator` class.
* **Format:** `self.tr("category.key")`.
* **Maintenance:** When adding a new key to `en.json`, IMMEDIATELY add it to `ru.json` and `pl.json` (even if untranslated).

## 5. Module Specifics
* **ModernPDFViewer:** Uses a Viewport-based rendering approach (Dynamic Tiling).
    * *Do not* revert to full-page rendering for large files.
    * *Do not* remove `update_theme` or `setMinimalMode` methods; they are part of the Public API.
* **API Layer:** All network calls go through `client/api/`. Widgets should never import `requests` directly.

## 6. Architecture & Patterns
* **Controller Pattern:** The `client/ui/controllers/` directory contains business logic.
    * **UI Components** (Views) should only handle display and user input.
    * **Controllers** handle the logic (e.g., `file_operations.py`, `search_handler.py`) and bridge the UI with the API/Models.
    * **MainController** (`main_controller.py`) acts as the central hub, connecting signals between components.

## 7. Refactoring Protocol
Before deleting a method, check if it is called dynamically or by a Controller. If rewriting a class:
1.  Map the existing Public API.
2.  Implement the internal logic.
3.  Ensure all old Public API methods exist (even if they just wrap the new logic).