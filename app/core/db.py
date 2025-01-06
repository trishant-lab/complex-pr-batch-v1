"""
This module sets up Jinja2 SQL library and provides helper functions to execute
the SQL template and returns the data
"""

from os import path

import asyncpg
import jinja2
from asyncpg import Record
from loguru import logger
from pydantic import PostgresDsn

from .jinjasql import JinjaSql
from .settings import PostgresSettings, get_settings

SQL_DIR: str = path.abspath(path.join(path.dirname(__file__), "../sql"))
CANNOT_FIND_TEMPLATE_ERROR_MSG = "Can not find the sql template"

config: PostgresSettings = get_settings().postgres


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

    def __init__(self: "DBManager", pool: asyncpg.pool.Pool, sqldir: str = SQL_DIR) -> None:
        """
        constructor sets up the jinjasql context with jinja2 environment
        """
        self.pool: asyncpg.pool.Pool = pool
        logger.info("Loading sql templates from: {}", sqldir)
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
        db_schema_name: str = config.schema_name,
        trigger_parameters: dict | None = None,
    ) -> None:
        """
        Executes raw SQL queries.
        :param query:
        :param db_schema_name:
        :param trigger_parameters:
        :return:
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{db_schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                await conn.execute(query)

    async def fetch_all(
        self: "DBManager",
        sqlfile: str,
        db_schema_name: str = config.schema_name,
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
        logger.info(f"Executing Query: {sqlfile}")
        template = self.jsql.env.get_template(sqlfile)
        assert template, CANNOT_FIND_TEMPLATE_ERROR_MSG
        query, values = self.jsql._prepare_query(template, data=kwargs)
        mapping = {key: f"${i!s}" for i, key in enumerate(values.keys(), start=1)}
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{db_schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                return await conn.fetch(query % mapping, *values.values())

    async def fetch_one(
        self: "DBManager",
        sqlfile: str,
        db_schema_name: str = config.schema_name,
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
        logger.info(f"Executing Query: {sqlfile}")
        template = self.jsql.env.get_template(sqlfile)
        assert template, CANNOT_FIND_TEMPLATE_ERROR_MSG
        query, values = self.jsql._prepare_query(template, data=kwargs)
        mapping = {key: f"${i!s}" for i, key in enumerate(values.keys(), start=1)}
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{db_schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                return await conn.fetchrow(query % mapping, *values.values())

    async def execute(
        self: "DBManager",
        sqlfile: str,
        db_schema_name: str = config.schema_name,
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
        logger.info(f"Executing Query: {sqlfile}")
        template = self.jsql.env.get_template(sqlfile)
        assert template, CANNOT_FIND_TEMPLATE_ERROR_MSG
        query, values = self.jsql._prepare_query(template, data=kwargs)
        mapping = {key: f"${i!s}" for i, key in enumerate(values.keys(), start=1)}
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f'SET SEARCH_PATH TO "{db_schema_name}", public;')
                await set_trigger_parameters(conn=conn, trigger_parameters=trigger_parameters)
                await conn.execute(query % mapping, *values.values())

    async def create_database(self: "DBManager", db_name: str) -> None:
        """
        Creates a new database. This method should be called outside of any transaction.
        """
        async with self.pool.acquire() as conn:
            # Disable autocommit to run CREATE DATABASE
            # await conn.execute('SET autocommit = on;')
            await conn.execute(f'CREATE DATABASE "{db_name}";')
            # await conn.execute('SET autocommit = off;')


async def get_db_manager(dsn: PostgresDsn) -> DBManager:
    """
    creates database manager object which will act as a singleton
    """
    pool: asyncpg.pool.Pool = await get_db(dsn)
    return DBManager(pool)


async def get_db(pg_dsn: str) -> asyncpg.pool.Pool:
    """
    creates database instance from PostgreSQL DSN
    """
    # config: AppSettings = get_settings()
    return await asyncpg.create_pool(str(pg_dsn), min_size=1, max_size=5)
