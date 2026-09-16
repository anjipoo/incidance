from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Base

# File-based SQLite database, created in the project root on first run.
DATABASE_URL = "sqlite:///./incidents.db"

# check_same_thread=False is required because FastAPI can use the connection
# across different threads for a single request.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    # Creates tables if they don't already exist. Safe to call on every startup.
    Base.metadata.create_all(bind=engine)


def get_db():
    # FastAPI dependency: yields a session, guarantees it closes after the request.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()