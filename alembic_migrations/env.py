import sys
from logging.config import fileConfig

import sqlalchemy
from alembic import context
from alembic.operations import Operations
from sqlalchemy import engine_from_config, text
from sqlalchemy import pool


sys.path = ["", ".."] + sys.path[1:]

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _get_database_info() -> dict:
    from app.core.settings import get_settings

    settings = get_settings()
    return dict(settings.postgres)


def _get_alembic_config(**kwargs: str | int) -> dict:
    alembic_config = config.get_section(config.config_ini_section)
    postgres_dsn = "postgresql://__username__:__password__@__host__:__port__/__database__"
    alembic_config["sqlalchemy.url"] = (
        postgres_dsn.replace("__username__", kwargs.get("user"))
        .replace("__password__", kwargs.get("password"))
        .replace("__database__", kwargs.get("db"))
        .replace("__port__", str(kwargs.get("port")))
        .replace("__host__", kwargs.get("host"))
    )
    return alembic_config


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    kwargs = _get_database_info()
    context.configure(
        url=_get_alembic_config(**kwargs)["sqlalchemy.url"],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    def get_sa_meta_data(op: Operations, sa: sqlalchemy, tables: list[str]) -> sqlalchemy.MetaData | None:
        for schema in [kwargs.get("schema_name")]:
            try:
                meta = sa.MetaData(schema=schema)
                meta.reflect(only=tables, bind=op.get_bind())
                return meta
            except sa.exc.InvalidRequestError:
                continue
        return None

    kwargs["get_sa_meta_data"] = get_sa_meta_data

    with context.begin_transaction():
        context.run_migrations(**kwargs)
        if "dry-run" in context.get_x_argument():
            print("Dry-run succeeded; now rolling back transaction...")
            context.execute(text("ABORT;"))
            return


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    kwargs = _get_database_info()
    connectable = engine_from_config(
        _get_alembic_config(**kwargs),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    def get_sa_meta_data(op: Operations, sa: sqlalchemy, tables: list[str]) -> sqlalchemy.MetaData | None:
        for schema in [kwargs.get("schema_name")]:
            try:
                meta = sa.MetaData(schema=schema)
                meta.reflect(only=tables, bind=op.get_bind())
                return meta
            except sa.exc.InvalidRequestError:
                continue
        return None

    kwargs["get_sa_meta_data"] = get_sa_meta_data

    with connectable.begin() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        context.execute(text(f"CREATE SCHEMA IF NOT EXISTS {kwargs.get('schema_name')};"))
        context.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp" schema public;'))
        with context.begin_transaction():
            context.execute(text(f"SET search_path = {kwargs.get('schema_name')}, public;"))
            context.run_migrations(**kwargs)
            if "dry-run" in context.get_x_argument():
                print("Dry-run succeeded; now rolling back transaction...")
                context.execute(text("ABORT;"))
                return


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
