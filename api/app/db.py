from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .settings import settings

# MariaDB async URL (using aiomysql)
DATABASE_URL = (
    f"mysql+aiomysql://{settings.db_user}:{settings.db_pass}@"
    f"{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,  # For serverless, adjust as needed
    echo=False,  # Set to True for debug
)

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
