"""
This module sets up Jinja2 SQL library and provides helper functions to execute
the SQL template and returns the data
"""

import uuid
from os import path

import asyncpg
import jinja2
from asyncpg import Connection, Record
from pydantic import PostgresDsn
from pydantic_core import MultiHostUrl

from .jinjasql import JinjaSql
from .settings import AppSettings, PostgresSettings, get_settings

SQL_DIR: str = path.abspath(path.join(path.dirname(__file__), "../sql"))
CANNOT_FIND_TEMPLATE_ERROR_MSG = "Can not find the sql template"


config: AppSettings = get_settings()


async def set_trigger_parameters(conn, trigger_parameters: None | dict = None) -> None:  # noqa: ANN001
    """
    Sets the parameters for the trigger
    """
    if not trigger_parameters:
        return
    for key, value in trigger_parameters.items():
        await conn.execute(f"SELECT set_config('myvars.{key}', '{value}', true);")


class DBManager:
    """
    This class uses jinjasql library to execute queries defined from sql folder
    """

    def __init__(
        self: "DBManager",
        pool: asyncpg.pool.Pool,
        schema_name: str,
        sqldir: str = SQL_DIR,
    ) -> None:
        """
        constructor sets up the jinjasql context with jinja2 environment
        """
        self.pool: asyncpg.pool.Pool = pool
        self.schema_name: str = schema_name
        env: jinja2.Environment = self.get_env(sqldir)
        self.jsql: JinjaSql = JinjaSql(env=env, param_style="pyformat")

    @classmethod
    def get_env(cls: "DBManager", directory: str) -> jinja2.Environment:
        """
        Sets up jinja2 environment using file loader
        """
        loader: jinja2.FileSystemLoader = jinja2.FileSystemLoader(directory)
        env: jinja2.Environment = jinja2.Environment(loader=loader, autoescape=True, trim_blocks=True)
        return env

    async def execute_raw_sql(
        self: "DBManager",
        query: str,
        db_schema_name: str | None = None,
        trigger_parameters: dict | None = None,
    ) -> None:
        """
        Executes raw SQL queries.
        :param query:
        :param db_schema_name:
        :param trigger_parameters:
        :return:
        """
        schema_name: str = db_schema_name or self.schema_name
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                await conn.execute(query)

    async def fetch_all(
        self: "DBManager",
        sqlfile: str,
        db_schema_name: str | None = None,
        trigger_parameters: dict | None = None,
        **kwargs: int | str | list | dict | None,
    ) -> list[Record]:
        """
        Executes query identified by the given sqlfile.
        The given sql file is loaded by jinjasql and then uses asyncpg to execute the query
        :param sqlfile:
        :param db_schema_name:
        # :param timezone:
        :param trigger_parameters:
        :param kwargs:
        :return:
        """
        schema_name: str = db_schema_name or self.schema_name
        template = self.jsql.env.get_template(sqlfile)
        assert template, CANNOT_FIND_TEMPLATE_ERROR_MSG
        query, values = self.jsql._prepare_query(template, data=kwargs)
        mapping = {key: f"${i!s}" for i, key in enumerate(values.keys(), start=1)}
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                return await conn.fetch(query % mapping, *values.values())

    async def fetch_one(
        self: "DBManager",
        sqlfile: str,
        db_schema_name: str | None = None,
        trigger_parameters: dict | None = None,
        **kwargs: int | str | list | dict | None,
    ) -> Record:
        """
        Executes query identified by the given sqlfile.
        The given sql file is loaded by jinjasql and then uses asyncpg to execute the query
        :param sqlfile:
        :param db_schema_name:
        :param trigger_parameters:
        :param kwargs:
        :return:
        """
        schema_name: str = db_schema_name or self.schema_name
        template = self.jsql.env.get_template(sqlfile)
        assert template, CANNOT_FIND_TEMPLATE_ERROR_MSG
        query, values = self.jsql._prepare_query(template, data=kwargs)
        mapping = {key: f"${i!s}" for i, key in enumerate(values.keys(), start=1)}
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                return await conn.fetchrow(query % mapping, *values.values())

    async def execute(
        self: "DBManager",
        sqlfile: str,
        db_schema_name: str | None = None,
        trigger_parameters: dict | None = None,
        **kwargs: int | str | list | dict | None,
    ) -> None:
        """
        Executes query identified by the given sqlfile.
        The given sql file is loaded by jinjasql and then uses asyncpg to execute the query
        :param sqlfile:
        :param db_schema_name:
        # :param timezone:
        :param trigger_parameters:
        :param kwargs:
        :return:
        """
        schema_name: str = db_schema_name or self.schema_name
        template = self.jsql.env.get_template(sqlfile)
        assert template, CANNOT_FIND_TEMPLATE_ERROR_MSG
        query, values = self.jsql._prepare_query(template, data=kwargs)
        mapping = {key: f"${i!s}" for i, key in enumerate(values.keys(), start=1)}
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                await conn.execute(query % mapping, *values.values())

    def _prepare_execute_many_queries(self: "DBManager", queries: list[tuple[str, dict]]) -> list:
        """
        function to preapare a list of queires
        """
        _queries = []
        for sqlfile, params in queries:
            template = self.jsql.env.get_template(sqlfile)
            assert template, CANNOT_FIND_TEMPLATE_ERROR_MSG
            query, values = self.jsql.prepare_query(template, data=params)
            mapping = {key: f"${i!s}" for i, key in enumerate(values.keys(), start=1)}
            _queries.append((sqlfile, query, mapping, values))
        return _queries

    async def execute_many(
        self: "DBManager",
        queries: list[tuple[str, dict]],
        db_schema_name: str | None = None,
        trigger_parameters: dict | None = None,
    ) -> None:
        """
        executes multiple queries in a transaction
        """
        schema_name: str = db_schema_name or self.schema_name
        _queries = self._prepare_execute_many_queries(queries)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                for sqlfile, query, mapping, values in _queries:
                    await conn.execute(query % mapping, *values.values())

    async def fetch_many(
        self: "DBManager",
        queries: list[tuple[str, dict]],
        db_schema_name: str | None = None,
        trigger_parameters: dict | None = None,
    ) -> list[Record | list[Record] | None]:
        """
        fetches results for multiple queries
        """
        schema_name: str = db_schema_name or self.schema_name
        _queries = self._prepare_execute_many_queries(queries)
        results = []
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                for sqlfile, query, mapping, values in _queries:
                    results.append(await conn.fetch(query % mapping, *values.values()))
        return results

    async def create_database(self: "DBManager", db_name: str) -> None:
        """
        Creates a new database. This method should be called outside of any transaction.
        """
        async with self.pool.acquire() as conn:
            # Disable autocommit to run CREATE DATABASE
            # await conn.execute('SET autocommit = on;')
            await conn.execute(f'CREATE DATABASE "{db_name}";')
            # await conn.execute('SET autocommit = off;')


class _Connection(Connection):
    def _get_unique_id(self: "_Connection", prefix: str) -> str:
        return f"__asyncpg_{prefix}_{uuid.uuid4().hex}__"


async def get_db(pg_dsn: PostgresDsn) -> asyncpg.pool.Pool:
    """
    creates database instance from PostgreSQL DSN
    """
    return await asyncpg.create_pool(
        pg_dsn, min_size=0, max_size=2, statement_cache_size=0, connection_class=_Connection
    )


async def get_db_manager(dsn: PostgresDsn | None = None) -> DBManager:
    """
    creates database manager object which will act as a singleton
    """
    postgres_config: PostgresSettings = config.postgres
    _dsn: PostgresDsn = dsn or postgres_config.dsn
    pool: asyncpg.pool.Pool = await get_db(_dsn)
    return DBManager(pool, postgres_config.schema_name)


async def get_super_admin_db_manager() -> DBManager:
    """
    creates database manager object for super admin
    """
    pg_super_admin_config: PostgresSettings = config.pg_super_admin
    pool: asyncpg.pool.Pool = await get_db(pg_super_admin_config.dsn)
    return DBManager(pool, pg_super_admin_config.schema_name)


async def get_super_admin_for_database(database_name: str) -> DBManager:
    """
    creates database manager object for super admin
    """
    pg_super_admin_config: PostgresSettings = config.pg_super_admin
    dsn = f"postgres://{pg_super_admin_config.user}:{pg_super_admin_config.password}@{pg_super_admin_config.host}:{pg_super_admin_config.port}/{database_name}"
    pool: asyncpg.pool.Pool = await get_db(MultiHostUrl(dsn))
    return DBManager(pool, pg_super_admin_config.schema_name)


async def database() -> DBManager:
    """
    Dependency to get Database manager
    """
    return await get_db_manager()
