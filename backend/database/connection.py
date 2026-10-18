"""SQLAlchemy engine and session management."""
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config import get_settings
from logger import get_logger

logger = get_logger(__name__)

_settings = get_settings()

# Read-write engine (for seeding / migrations)
rw_engine = create_engine(
    _settings.normalized_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 10},
)

# Read-only engine (for query execution)
ro_engine = create_engine(
    _settings.readonly_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 10},
)

RWSession = sessionmaker(bind=rw_engine, autoflush=False, autocommit=False)
ROSession = sessionmaker(bind=ro_engine, autoflush=False, autocommit=False)


@contextmanager
def get_rw_session() -> Session:
    session = RWSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_ro_session() -> Session:
    session = ROSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def check_connection() -> bool:
    """Verify database connectivity."""
    try:
        with rw_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False
