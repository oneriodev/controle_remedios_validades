"""Conexão assíncrona com o PostgreSQL e dependência de sessão."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# pool_pre_ping: testa a conexão antes de usar (evita erro se o banco reiniciou)
engine = create_async_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Entrega uma sessão por requisição e garante o fechamento ao final."""
    async with SessionLocal() as session:
        yield session