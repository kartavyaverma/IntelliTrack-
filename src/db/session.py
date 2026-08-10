"""
SQLite engine + session setup. One DB file: data/intellitrack.db.
Kept deliberately simple (no Alembic migrations) — matches the "SQLite for
viva demo" scope decision; call init_db() once at the start of any script
that touches the DB, it's a no-op if tables already exist.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base

DB_PATH = "data/intellitrack.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()