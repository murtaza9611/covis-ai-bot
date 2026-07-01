from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.models import Base
from src.chat import models as _chat_models  # noqa: F401  — register ChatHistory, ChatSessionState
from contextlib import asynccontextmanager

from src.settings import settings

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)

# @asynccontextmanager
async def get_async_session():
    """Yield an async session.
    
    All conversations with the database are established via the session
    objects.
    """
    async_session = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession, 
        autoflush=False,
        expire_on_commit=False,
    )
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            print("Unable to yield session in database dependency")
            print(e)
        finally:
            await session.close() 



async def initialize_database() -> None:
    """Create tables if they don't exist yet
    
    This uses a sync connection because the 'create_all' doesn't
    feature async yet.
    """
    async_engine_local = async_engine
    async with async_engine_local.begin() as async_conn:
        
        await async_conn.run_sync(Base.metadata.create_all)
        print('success')
