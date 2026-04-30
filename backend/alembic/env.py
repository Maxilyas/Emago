"""
Alembic env.py — Configuration async pour Emago
Compatible SQLAlchemy 2.0 + asyncpg
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import des modèles pour l'autogenerate
from app.models.models import Base
from app.core.config import settings

# ---------------------------------------------------------------------------
# Config Alembic
# ---------------------------------------------------------------------------
config = context.config

# Injecte l'URL de BDD depuis les settings (jamais en dur ici)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Mode offline (génération SQL sans connexion — pour review de migrations)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Génère le SQL de migration sans connexion à la BDD.
    Utile pour review en CI ou déploiement manuel.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Inclut les types PostgreSQL custom (enums) dans les migrations
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Mode online (async — connexion réelle à PostgreSQL via asyncpg)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        # Compare les types de colonnes pour détecter les changements
        compare_type=True,
        # Compare les server_default pour détecter les changements
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Exécute les migrations en mode async."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Pas de pool pour les migrations
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
