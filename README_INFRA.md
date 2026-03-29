# Инструкция по запуску инфраструктуры (Podman / Docker)

## 1. Рекомендованный запуск: Podman
Podman является более безопасной альтернативой Docker для SaaS и LAN сред.

### Установка (Windows):
- Скачайте Podman Desktop: [https://podman-desktop.io/](https://podman-desktop.io/)
- Установите расширение `Compose` внутри Podman Desktop.

### Запуск проекта:
```powershell
# Запуск всех сервисов в фоновом режиме
podman-compose up -d --build
```

### Преимущества Podman для этого проекта:
- **Rootless:** Контейнеры запускаются от имени текущего пользователя, а не root (безопаснее).
- **No Daemon:** Нет центрального процесса Docker, который может упасть.
- **Valkey Ready:** Контейнер Valkey (замена Redis) работает "из коробки" без дополнительных настроек сети.

---

## 2. Запуск через Docker
Если вы предпочитаете классический Docker Desktop:

```powershell
docker-compose up -d --build
```

---

## 3. Миграция данных из локальной SQLite в PostgreSQL (LAN/SaaS)
После первого запуска контейнеров (когда база Postgres будет создана), выполните миграцию:

```powershell
# Убедитесь, что зависимости установлены локально (psycopg2-binary)
python scripts/migrate_to_postgres.py postgresql://pdflib:password@localhost:5432/pdflib
```

---

## 4. Мониторинг задач (Dramatiq)
В режиме сервера вы можете запустить `dramatiq-admin` (или аналоги), чтобы видеть очередь OCR задач в реальном времени.
Логи обработки доступны через:
```powershell
podman logs -f pdfcat-new_worker_1
```
