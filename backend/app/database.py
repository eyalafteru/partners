"""
PartnerCalc OS - Database Connection
חיבור למסד הנתונים - תומך SQLite, MySQL/MariaDB, PostgreSQL
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, StaticPool, QueuePool
from loguru import logger

from app.config import settings

# Base class לכל המודלים
Base = declarative_base()

# Determine database type
db_type = settings.effective_db_type
logger.info(f"🗄️ Database type: {db_type}")
logger.debug(f"📍 Connection URL: {settings.get_database_url[:50]}...")


def create_engines():
    """Create sync and async engines based on database type"""
    
    if db_type == "sqlite":
        # ========== SQLite Configuration ==========
        logger.info("📦 Using SQLite database")
        
        sync_eng = create_engine(
            settings.get_database_url,
            echo=settings.debug,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
            },
            poolclass=StaticPool,
        )
        
        async_eng = create_async_engine(
            settings.async_database_url,
            echo=settings.debug,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
            },
        )
        
        # Enable WAL mode for better concurrent access
        @event.listens_for(sync_eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
        
        return sync_eng, async_eng
    
    elif db_type == "mysql":
        # ========== MySQL/MariaDB Configuration ==========
        logger.info("🐬 Using MySQL/MariaDB database")
        
        sync_eng = create_engine(
            settings.get_database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,  # Recycle connections after 1 hour
            poolclass=QueuePool,
        )
        
        async_eng = create_async_engine(
            settings.async_database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )
        
        return sync_eng, async_eng
    
    elif db_type == "postgresql":
        # ========== PostgreSQL Configuration ==========
        logger.info("🐘 Using PostgreSQL database")
        
        sync_eng = create_engine(
            settings.get_database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            poolclass=QueuePool,
        )
        
        async_eng = create_async_engine(
            settings.async_database_url,
            echo=settings.debug,
            poolclass=NullPool,  # NullPool for async PostgreSQL
        )
        
        return sync_eng, async_eng
    
    else:
        raise ValueError(f"Unknown database type: {db_type}")


# Create engines
sync_engine, async_engine = create_engines()

# Sync Session
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# Async Session
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncSession:
    """
    Dependency injection עבור async session
    שימוש: session: AsyncSession = Depends(get_async_session)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_session_context():
    """
    Context manager עבור async session
    שימוש: async with get_async_session_context() as session: ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session():
    """
    Dependency injection עבור sync session
    שימוש: session = Depends(get_sync_session)
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_db():
    """יצירת טבלאות (לפיתוח בלבד - בפרודקשן להשתמש ב-Alembic)"""
    logger.info(f"🔨 Creating tables for {db_type}...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables created successfully")


async def close_db():
    """סגירת חיבורים"""
    logger.info("🔒 Closing database connections...")
    await async_engine.dispose()


async def check_connection() -> bool:
    """בדיקת חיבור לדאטאבייס"""
    try:
        async with async_engine.connect() as conn:
            if db_type == "sqlite":
                await conn.execute("SELECT 1")
            else:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


# Aliases for convenience
SessionLocal = SyncSessionLocal
get_db = get_sync_session
