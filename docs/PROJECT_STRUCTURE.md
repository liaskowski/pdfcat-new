# Project Structure

## Client Architecture

### UI Components (`client/ui/`)
All visual components reside here.
- **Main Window**: `client/main_window.py` (Entry point for UI)
- **Dialogs**: `client/ui/` (e.g., `auth_dialog.py`, `upload_dialog.py`, `manage_dialog.py`)
- **Panels**: `client/ui/` (e.g., `preview_panel.py`, `file_grid.py`)
- **Layouts**: `client/ui/layouts/` (Main window layout logic)

### Controllers (`client/ui/controllers/`)
Business logic separated from UI.
- `main_controller.py`: Central hub, connects API, UI, and Signals.
- `file_operations.py`: Handles Download, Edit, Delete, Open.
- `search_handler.py`: Search and Filtering logic.

### API Layer (`client/api_manager.py`)
Handles all HTTP communication with the backend.

### Utilities (`client/utils/`)
- `cache_manager.py`: Thumbnails and Preview caching.
- `config_manager.py`: Local settings (theme, language).
- `translator.py`: I18n support.

## Data Flow
1. **User Action** (Click) -> **UI Component** (FileGrid) -> **Signal** (file_selected)
2. **Controller** (MainController) receives Signal -> Calls **API** (get_document)
3. **API** returns Data -> **Controller** updates **UI** (PreviewPanel)

## Key Directories
- `client/assets/`: Icons, Styles (QSS), Language files (JSON).
- `client/widgets/`: Reusable custom widgets (PDFViewer).
