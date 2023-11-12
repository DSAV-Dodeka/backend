from loguru import logger

from sqlalchemy import text
from sqlalchemy.engine import Engine


def drop_recreate_database(engine: Engine, db_name: str) -> None:
    with engine.connect() as connection:
        drop_db = text(f"DROP DATABASE IF EXISTS {db_name}")
        connection.execute(drop_db)
        create_db = text(f"CREATE DATABASE {db_name}")
        connection.execute(create_db)
        logger.warning("Dropped and recreated database.")
