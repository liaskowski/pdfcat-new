from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.orm import sessionmaker
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.database import Base, engine as sqlite_engine
from server.models import User, Category, FileType, Folder, Document, FileHistory, DocumentIndex

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate(postgres_url):
    # 1. Connect to Postgres
    pg_engine = create_engine(postgres_url)
    
    # 2. Create tables in Postgres
    logger.info("Creating tables in PostgreSQL...")
    Base.metadata.create_all(pg_engine)

    # 3. Define tables to migrate in order
    models = [User, Category, FileType, Folder, Document, FileHistory, DocumentIndex]
    
    # SQLite Session
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    try:
        with pg_engine.connect() as pg_conn:
            for model in models:
                table_name = model.__tablename__
                logger.info(f"Migrating table: {table_name}...")
                
                # Fetch all from SQLite
                items = sqlite_session.query(model).all()
                if not items:
                    logger.info(f"Table {table_name} is empty, skipping.")
                    continue

                # Convert to dicts for bulk insert
                data = []
                for item in items:
                    d = {c.name: getattr(item, c.name) for c in model.__table__.columns}
                    data.append(d)

                # Insert into Postgres using connection
                pg_conn.execute(model.__table__.insert(), data)
                logger.info(f"Successfully migrated {len(data)} rows to {table_name}.")

            # Handle sequence reset for Postgres (serial columns)
            logger.info("Resetting sequences in PostgreSQL...")
            for model in models:
                table_name = model.__tablename__
                pg_conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1), false) FROM {table_name}"))
            
            pg_conn.commit()
            logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        sqlite_session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_to_postgres.py <postgres_url>")
        sys.exit(1)
    
    migrate(sys.argv[1])
