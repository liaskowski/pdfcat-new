from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging
import threading
from .config import settings

logger = logging.getLogger(__name__)

# Thread-safe lock for SQLite operations
sqlite_lock = threading.Lock()

# Use database URL from settings
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Common arguments for all databases
engine_args = {
    "echo": False,
    "pool_pre_ping": True,
}

# SQLite specific arguments
if is_sqlite:
    engine_args.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    })
else:
    # Standard connection pooling for PostgreSQL/others
    engine_args.update({
        "pool_size": 10,
        "max_overflow": 20,
    })

logger.info(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
engine = create_engine(settings.DATABASE_URL, **engine_args)

# Enable WAL mode for better concurrent access in SQLite
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    with sqlite_lock:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

def get_db_session():
    return SessionLocal()
