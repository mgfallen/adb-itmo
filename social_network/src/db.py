from pathlib import Path

import vertica_python

from src.config import VerticaConnectionSettings, load_vertica_settings


def connect(settings: VerticaConnectionSettings | None = None):
    if settings is None:
        settings = load_vertica_settings()
    return vertica_python.connect(
        host=settings.host,
        port=settings.port,
        database=settings.database,
        user=settings.user,
        password=settings.password,
    )


def split_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def execute_script(connection, path: Path) -> None:
    with connection.cursor() as cursor:
        for statement in split_statements(path.read_text(encoding="utf-8")):
            cursor.execute(statement)
