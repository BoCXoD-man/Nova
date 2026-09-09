from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from memory.models import Base


BASE_DIR = Path(__file__).resolve().parent.parent

MEMORY_DIR = BASE_DIR / "memory_data"
MEMORY_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_PATH = MEMORY_DIR / "assistant.db"

DATABASE_URL = (
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)


engine = create_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def init_database():
    Base.metadata.create_all(
        bind=engine,
    )


def get_session() -> Session:
    return SessionLocal()