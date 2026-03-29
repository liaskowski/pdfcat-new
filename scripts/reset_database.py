import os
import shutil
import logging
from sqlalchemy import create_engine
from server.database import Base, SQLALCHEMY_DATABASE_URL
from server.config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """
    Полностью сбрасывает базу данных и файловое хранилище.
    """
    logger.info("Starting database and storage hard reset...")

    # 1. Удаление файла БД
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Removed database file: {db_path}")
        except OSError as e:
            logger.error(f"Error removing database file {db_path}: {e}")
            return

    # 2. Очистка папки uploads
    upload_path = settings.UPLOAD_DIR
    if os.path.exists(upload_path):
        try:
            # Удаляем все содержимое папки
            for filename in os.listdir(upload_path):
                file_path = os.path.join(upload_path, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            logger.info(f"Cleared uploads directory: {upload_path}")
        except OSError as e:
            logger.error(f"Error clearing uploads directory {upload_path}: {e}")
            return

    # 3. Инициализация новых таблиц
    try:
        logger.info("Initializing new database schema...")
        engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema created successfully.")
    except Exception as e:
        logger.error(f"Failed to create database schema: {e}")
        return

    logger.info("Hard reset completed successfully!")

if __name__ == "__main__":
    reset_database()