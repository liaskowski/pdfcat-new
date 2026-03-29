# План Развития Проекта: От Локального ПК к SaaS

## 0. Стратегия "Progressive Scaling"
**Приоритеты:**
1.  🥇 **Single PC:** Работает "из коробки" (один .exe/.app), без сложной настройки.
2.  🥈 **Local Network (LAN):** Один сервер (Docker), много клиентов.
3.  🥉 **SaaS:** Облачный кластер, мульти-тенантность.

**Архитектурное решение:** "Modular Monolith".
Код должен быть написан так, чтобы сервисы (OCR, Поиск) могли вызываться **напрямую** (как библиотека) в режиме Single PC, или через **сеть/очередь** в режиме Server/SaaS.

---

## 1. Рефакторинг Backend (Python)

### 1.1. Очереди Задач (Task Queue)
*Вместо тяжелого Celery.*

*   **Анализ:**
    *   *Celery:* Слишком сложен, плохая поддержка Windows (важно для Single PC).
    *   *Hatchet:* Мощно, но требует отдельного оркестратора. Overkill для локального запуска.
    *   **Рекомендация: Dramatiq.**
        *   Простой, надежный, поддерживает приоритеты.
        *   Отлично работает с RabbitMQ и Redis (Valkey).
        *   Для режима "Single PC" можно использовать **StubBroker** (выполнение в потоках без внешнего брокера).

### 1.2. Брокер Сообщений и Кэш
*Вместо Redis (из-за смены лицензии).*

*   **Анализ:**
    *   *Redis:* Лицензия изменилась (SSPL/RSAL), риски для SaaS.
    *   *DragonflyDB:* Очень быстрый, но может быть избыточен для простых задач.
    *   **Рекомендация: Valkey.**
        *   Форк Redis от Linux Foundation (Open Source, BSD).
        *   Полная совместимость (Drop-in replacement).
        *   Идеально для Docker-контейнера в LAN/SaaS.

### 1.3. Хранение Данных (Storage Abstraction)
*   [ ] **Интерфейс `IStorage`:**
    *   `LocalFileSystemStorage`: Для Single PC и LAN (простая папка).
    *   `S3Storage`: Для SaaS (MinIO/AWS).
*   *Логика:* Приложение при старте читает конфиг и выбирает драйвер.

### 1.4. Организация Файлов (File System Strategy)
*Проблема: "Single Point of Failure" при случайном удалении файла.*

*   **Решение для Single PC (Local):**
    *   **Sharding (Шардирование):** Не хранить всё в одной папке `uploads/`. Использовать структуру `uploads/ab/cd/abcdef...pdf` (по хэшу). Это решает проблему "1000 файлов в одной папке".
    *   **Fail-Safe Handling:** Приложение НЕ должно падать, если файл отсутствует. Оно должно помечать его в БД как `MISSING` и предлагать пользователю восстановить/удалить запись.
    *   **Backup:** Встроенная утилита для создания полного бэкапа (DB + Files) в один `.zip` архив.
*   **Решение для SaaS:**
    *   S3 (MinIO) гарантирует сохранность.

---

## 2. Frontend: Выбор Стэка под приоритеты

Для приоритета №1 (Single PC) веб-технологии в чистом виде (браузер) не подходят. Нужна "оболочка".

### Вариант A: Tauri (Rust) + React/Vue
*Лучший баланс между Localhost и SaaS.*
*   **Single PC:** `.exe` файл 5 МБ. Бэкенд (Python) запускается как sidecar-процесс. Tauri общается с ним.
*   **LAN/SaaS:** Тот же React-код, но Tauri настраивается на удаленный API URL.
*   **Плюсы:** Минимальное потребление ресурсов пользователя.
*   **Минусы:** Сложнее сборка (нужен Rust toolchain).

### Вариант B: Electron
*Проще разработка, больше размер.*
*   **Single PC:** Внутри Electron запускается Python-процесс.
*   **Плюсы:** Огромное сообщество.
*   **Минусы:** Тяжелый дистрибутив (~150 МБ).

---

## 3. Сводная Таблица Технологий

| Компонент | Single PC (Local) | LAN Server (Docker) | SaaS (Cloud) |
| :--- | :--- | :--- | :--- |
| **App Entry** | `Launcher.exe` | Docker Container | K8s / Cloud Run |
| **Frontend** | Tauri/Electron (Localhost) | Tauri/Electron (Remote IP) | Web Browser + Desktop App |
| **API** | Direct Call / Local Loopback | FastAPI (Gunicorn) | FastAPI (Auto-scale) |
| **Queue** | `Dramatiq[threads]` (In-mem) | `Dramatiq` + **Valkey** | `Dramatiq` + **Valkey Cluster** |
| **DB** | **SQLite** (Embedded) | **PostgreSQL** (Docker) | **PostgreSQL** (Managed) |
| **Storage** | Local FS (Sharded) | Volume (Sharded) | S3 (Object Storage) |

---

## 4. План Миграции (Roadmap)

### Этап 1: "Clean Core" (Чистое Ядро)
1.  Выделить бизнес-логику (OCR, Search, Files) из контроллеров FastAPI в чистые Python-сервисы.
2.  Внедрить **Dramatiq** для фоновых задач.
    *   Настроить 2 режима: `Broker` (для сервера) и `Stub` (для локального запуска без Redis).
3.  Реализовать **Sharded Storage Service** (распределение файлов по подпапкам) + Fail-Safe проверки.

### Этап 2: Docker & LAN
1.  Написать `docker-compose.yml`:
    *   Service: `app` (FastAPI + Dramatiq Worker).
    *   Service: `valkey` (Брокер + Кэш).
    *   Service: `postgres` (БД).
2.  Скрипт миграции данных из SQLite в Postgres.

### Этап 3: Новый Frontend
1.  Инициализировать проект **Tauri + React**.
2.  Реализовать базовые экраны (Login, File List) потребляющие API.

---

## 5. Альтернативы Инструментов (Reference)

### Брокеры / Кэш
*   **Valkey (Winner):** Лицензия BSD, полная совместимость с Redis, активное комьюнити.
*   **KeyDB:** Многопоточный, быстрый, но Valkey сейчас стандарт де-факто для замены Redis.
*   **Dragonfly:** Отличный вариант для High-Load SaaS (>100k ops/sec), но сложнее в эксплуатации на Windows.

### Task Queues
*   **Dramatiq (Winner):** Простой, стабильный, нативный для Python 3. Автоматический ретрай, приоритеты.
*   **Hatchet:** Требует запуска отдельного сервера (Go), что усложняет дистрибуцию для Single PC.
*   **Huey:** Очень легкий, идеально для Single PC, но слабее для Enterprise SaaS.
