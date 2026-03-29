# Карта модулей (Modules Map)

## Корень проекта
- `main.py`: Точка входа для запуска сервера (враппер над `server/main.py`).
- `migrate.py` и др.: Скрипты миграции базы данных.
- `check_admin.py`: Скрипт проверки/создания администратора.
- `reset_database.py`: Скрипт для полной очистки и инициализации БД.
- `requirements.txt`: Список зависимостей Python.
- `GEMINI.md`: Инструкции и контекст для AI-ассистента.

## Сервер (`server/`)
- `server/main.py`: Инициализация FastAPI приложения.
- `server/config.py`: Конфигурация приложения.
- `server/database.py`: Подключение к SQLAlchemy.
- `server/models.py`: SQLAlchemy модели данных.
- `server/schemas.py`: Pydantic схемы (DTO).
- `server/security.py`: Логика аутентификации (JWT).
- `server/services/`: Бизнес-логика (PDF процессинг, Email).
- `server/routers/`: API Эндпоинты (Auth, Users, Documents).

## Клиент (`client/`)
- `client/main.py`: Запуск PyQt приложения.
- `client/main_window.py`: Главное окно, связывает Layout и Controller.
- `client/api_manager.py`: Фасад для API.
- `client/workers.py`: Фоновые потоки (UploadWorker).
- `client/themes.py`: Менеджер тем.

### Клиент UI (`client/ui/`)
**Диалоги:**
- `client/ui/auth_dialog.py`: Вход и регистрация.
- `client/ui/upload_dialog.py`: Загрузка и редактирование файлов.
- `client/ui/manage_dialog.py`: Управление категориями/тегами.
- `client/ui/profile_dialog.py`: Настройки профиля.
- `client/ui/settings_dialog.py`: Настройки приложения.
- `client/ui/forgot_password_dialog.py`: Восстановление пароля.
- `client/ui/admin_panel.py`: Администрирование пользователей.

**Компоненты (Панели):**
- `client/ui/preview_panel.py`: Панель справа (Инфо + Превью).
- `client/ui/file_grid.py`: Сетка файлов (Центральная область).
- `client/ui/navigation_tree.py`: Дерево слева.
- `client/ui/search_bar.py`: Строка поиска.
- `client/ui/custom_title_bar.py`: Кастомный заголовок окна.

**Контроллеры (`client/ui/controllers/`):**
- `main_controller.py`: Главный координатор.
- `file_operations.py`: Логика работы с файлами.
- `search_handler.py`: Логика поиска.

**Макеты (`client/ui/layouts/`):**
- `main_layout.py`: Компоновка главного окна.

### Клиент Widgets (`client/widgets/`)
- `client/widgets/modern_pdf_viewer.py`: Основной компонент просмотра PDF (Viewport/Tiling).
- `client/widgets/pdf_viewer.py`: Базовая реализация просмотра (Legacy/Simple).

### Клиент Utils (`client/utils/`)
- `client/utils/cache_manager.py`: Кеширование иконок и превью.
- `client/utils/config_manager.py`: Управление настройками.
- `client/utils/translator.py`: Локализация.
- `client/utils/thumbnail_manager.py`: (Legacy) Менеджер миниатюр.

### Клиент API (`client/api/`)
- `client/api/*.py`: Реализация методов API, сгруппированная по доменам.