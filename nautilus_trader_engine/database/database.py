from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
import os
from sqlalchemy.pool import StaticPool

from nautilus_trader_engine.config.database_config import DATABASE_URL

# Create the SQLAlchemy engine
# Be resilient in test/dev environments: if the configured driver/module is missing
# or invalid, fall back to an in-memory SQLite database so imports don't fail.
db_url = os.getenv("NAUTILUS_DATABASE_URL") or DATABASE_URL
try:
    engine = create_engine(db_url)
except Exception:
    # Safe fallback for testing to avoid external dependencies at import time
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for declarative models
Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()