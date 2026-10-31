import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yml"
ENV_LOCAL_PATH = PROJECT_ROOT / ".env.local"

VERTICA_HOST_ENV = "VERTICA_HOST"
VERTICA_PORT_ENV = "VERTICA_PORT"
VERTICA_DATABASE_ENV = "VERTICA_DATABASE"
VERTICA_USER_ENV = "VERTICA_USER"
VERTICA_PASSWORD_ENV = "VERTICA_PASSWORD"
VERTICA_DEFAULT_PORT = 5433


@dataclass(frozen=True)
class SourceConfig:
    encoding: str
    delimiter: str
    timestamp_max_fraction: int
    people_file: Path
    groups_file: Path
    chats_file: Path
    group_status: str
    chat_status: str


@dataclass(frozen=True)
class DwhConfig:
    staging_schema: str
    dv_schema: str
    marts_schema: str
    sys_marts_schema: str


@dataclass(frozen=True)
class Settings:
    source: SourceConfig
    dwh: DwhConfig


def load_env_local() -> None:
    if ENV_LOCAL_PATH.exists():
        load_dotenv(ENV_LOCAL_PATH)


def load_settings() -> Settings:
    load_env_local()
    raw = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8"))

    files = raw["source"]["files"]
    defaults = raw["source"]["defaults"]
    source = SourceConfig(
        encoding=raw["source"]["encoding"],
        delimiter=raw["source"]["delimiter"],
        timestamp_max_fraction=raw["source"]["timestamp_max_fraction"],
        people_file=PROJECT_ROOT / "data" / "csv" / files["people"],
        groups_file=PROJECT_ROOT / "data" / "csv" / files["groups"],
        chats_file=PROJECT_ROOT / "data" / "csv" / files["chats"],
        group_status=defaults["group_status"],
        chat_status=defaults["chat_status"],
    )
    dwh = DwhConfig(
        staging_schema=raw["dwh"]["staging_schema"],
        dv_schema=raw["dwh"]["dv_schema"],
        marts_schema=raw["dwh"]["marts_schema"],
        sys_marts_schema=raw["dwh"]["sys_marts_schema"],
    )
    return Settings(source=source, dwh=dwh)


@dataclass(frozen=True)
class VerticaConnectionSettings:
    host: str
    port: int
    database: str
    user: str
    password: str


def load_vertica_settings() -> VerticaConnectionSettings:
    load_env_local()
    return VerticaConnectionSettings(
        host=os.environ[VERTICA_HOST_ENV],
        port=int(os.environ.get(VERTICA_PORT_ENV, VERTICA_DEFAULT_PORT)),
        database=os.environ[VERTICA_DATABASE_ENV],
        user=os.environ[VERTICA_USER_ENV],
        password=os.environ.get(VERTICA_PASSWORD_ENV, ""),
    )
