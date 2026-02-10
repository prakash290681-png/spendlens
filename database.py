import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "spendlens.db")

DATABASE_URL = f"sqlite:///{DB_PATH}"

print("🔥 USING DB FILE:", DB_PATH)

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

def enable_sqlite_wal():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            print("🔥 WAL mode enabled")
    except Exception as e:
        print("⚠️ WAL enable failed:", e)
