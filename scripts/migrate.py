import sqlite3
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "../app.db"

def get_db_connection():
    """Возвращает подключение к базе данных SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_schema():
    """
    Выполняет миграцию схемы базы данных:
    1. Добавляет таблицы 'categories' и 'file_types'.
    2. Добавляет столбцы 'category_id' и 'file_type_id' в таблицу 'documents'.
    3. Переносит существующие данные из столбца 'category' в новую таблицу 'categories'.
    4. Обновляет 'category_id' в таблице 'documents'.
    5. (Комментарий) Удаляет старый столбец 'category' (требует более сложной логики в SQLite).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("Начало миграции базы данных...")

        # ============================================================================
        # 1. Проверка и создание новых таблиц
        # ============================================================================
        
        # Проверка существования таблицы 'categories'
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories';")
        if not cursor.fetchone():
            logger.info("Создание таблицы 'categories'...")
            cursor.execute("""
                CREATE TABLE categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL
                );
            """)
            cursor.execute("CREATE UNIQUE INDEX ix_categories_name ON categories (name);")
            cursor.execute("CREATE INDEX ix_categories_id ON categories (id);")
        else:
            logger.info("Таблица 'categories' уже существует.")

        # Проверка существования таблицы 'file_types'
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_types';")
        if not cursor.fetchone():
            logger.info("Создание таблицы 'file_types'...")
            cursor.execute("""
                CREATE TABLE file_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL
                );
            """)
            cursor.execute("CREATE UNIQUE INDEX ix_file_types_name ON file_types (name);")
            cursor.execute("CREATE INDEX ix_file_types_id ON file_types (id);")
        else:
            logger.info("Таблица 'file_types' уже существует.")

        # Проверка существования таблицы 'file_history'
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_history';")
        if not cursor.fetchone():
            logger.info("Создание таблицы 'file_history'...")
            cursor.execute("""
                CREATE TABLE file_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL REFERENCES documents(id),
                    changed_by_id INTEGER NOT NULL REFERENCES users(id),
                    change_type VARCHAR NOT NULL,
                    field_changed VARCHAR,
                    old_value TEXT,
                    new_value TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX ix_file_history_id ON file_history (id);")
            cursor.execute("CREATE INDEX ix_file_history_document_id ON file_history (document_id);")
        else:
            logger.info("Таблица 'file_history' уже существует.")
            
        # ============================================================================
        # 2. Модификация таблицы 'documents'
        # ============================================================================
        
        # Получаем информацию о столбцах таблицы 'documents'
        cursor.execute("PRAGMA table_info(documents);")
        columns = [row['name'] for row in cursor.fetchall()]

        if 'category_id' not in columns:
            logger.info("Добавление столбца 'category_id' в таблицу 'documents'...")
            cursor.execute("ALTER TABLE documents ADD COLUMN category_id INTEGER REFERENCES categories(id);")
        else:
            logger.info("Столбец 'category_id' уже существует.")

        if 'file_type_id' not in columns:
            logger.info("Добавление столбца 'file_type_id' в таблицу 'documents'...")
            cursor.execute("ALTER TABLE documents ADD COLUMN file_type_id INTEGER REFERENCES file_types(id);")
        else:
            logger.info("Столбец 'file_type_id' уже существует.")

        if 'is_public_edit' not in columns:
            logger.info("Добавление столбца 'is_public_edit' в таблицу 'documents'...")
            cursor.execute("ALTER TABLE documents ADD COLUMN is_public_edit BOOLEAN DEFAULT 0;")
        else:
            logger.info("Столбец 'is_public_edit' уже существует.")

        if 'notes' not in columns:
            logger.info("Добавление столбца 'notes' в таблицу 'documents'...")
            cursor.execute("ALTER TABLE documents ADD COLUMN notes TEXT;")
        else:
            logger.info("Столбец 'notes' уже существует.")

            
        # ============================================================================
        # 3. Перенос данных
        # ============================================================================

        # Проверяем, существует ли старый столбец 'category'
        if 'category' in columns:
            logger.info("Начало переноса данных из столбца 'category'...")

            # Получаем все уникальные категории из старого столбца
            cursor.execute("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL AND category != '';")
            old_categories = [row['category'] for row in cursor.fetchall()]
            
            if not old_categories:
                logger.info("Не найдено категорий для переноса.")
            else:
                logger.info(f"Найдены следующие категории для переноса: {old_categories}")

                # Переносим уникальные категории в новую таблицу
                for cat_name in old_categories:
                    # Проверяем, существует ли категория, чтобы избежать дубликатов
                    cursor.execute("SELECT id FROM categories WHERE name = ?;", (cat_name,))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO categories (name) VALUES (?);", (cat_name,))
                        logger.info(f"Категория '{cat_name}' добавлена в таблицу 'categories'.")
                
                # Обновляем `category_id` в таблице `documents`
                logger.info("Обновление `category_id` в таблице 'documents'...")
                cursor.execute("""
                    UPDATE documents
                    SET category_id = (SELECT id FROM categories WHERE name = documents.category)
                    WHERE documents.category IS NOT NULL;
                """)
                logger.info("`category_id` успешно обновлены.")

            # ============================================================================
            # 4. Удаление старого столбца (Опционально и сложно в SQLite)
            # ============================================================================
            
            # SQLite не поддерживает простое `ALTER TABLE DROP COLUMN`.
            # Стандартный способ - создать новую таблицу, скопировать данные и переименовать.
            # Для простоты, мы можем просто переименовать старый столбец, чтобы он не мешал.
            
            logger.info("Переименование старого столбца 'category' в 'category_old'...")
            cursor.execute("PRAGMA foreign_keys=off;") # Отключаем проверку внешних ключей
            cursor.execute("""
                ALTER TABLE documents RENAME COLUMN category TO category_old;
            """)
            cursor.execute("PRAGMA foreign_keys=on;") # Включаем проверку обратно
            logger.info("Столбец 'category' успешно переименован.")
            
        else:
            logger.info("Старый столбец 'category' не найден, перенос данных не требуется.")
            
        # Фиксируем изменения
        conn.commit()
        logger.info("Миграция успешно завершена!")

    except Exception as e:
        logger.error(f"Произошла ошибка во время миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # Перед запуском миграции убедитесь, что основной сервер FastAPI не запущен,
    # чтобы избежать блокировки файла базы данных.
    migrate_schema()
