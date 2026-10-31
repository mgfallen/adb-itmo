import csv
from datetime import date, datetime
from pathlib import Path

from src.config import Settings


def repair_quoted_line(line: str) -> str:
    if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
        return line[1:-1].replace('""', '"')
    return line


def read_source_rows(path: Path, encoding: str, delimiter: str) -> list[dict[str, str]]:
    text = path.read_text(encoding=encoding)
    lines = [repair_quoted_line(line) for line in text.splitlines() if line.strip()]
    rows = csv.DictReader(lines, delimiter=delimiter)
    return [{key.replace("-", "_"): value for key, value in row.items()} for row in rows]


def truncate_timestamp_fraction(value: str, max_fraction: int) -> str:
    if "." not in value:
        return value
    base, fraction = value.split(".", 1)
    return f"{base}.{fraction[:max_fraction]}"


def to_int(value: str | None) -> int | None:
    return int(value) if value else None


def to_datetime(value: str | None, max_fraction: int | None = None) -> datetime | None:
    if not value:
        return None
    if max_fraction is not None:
        value = truncate_timestamp_fraction(value, max_fraction)
    return datetime.fromisoformat(value)


def to_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def clean_people(rows: list[dict[str, str]]) -> list[dict]:
    return [
        {
            "id": to_int(row["id"]),
            "name": row["name"],
            "registration_date": to_datetime(row["registration_date"]),
            "country": row["country"],
            "date_of_birthday": to_date(row["date_of_birthday"]),
            "phone": row["phone"],
            "e_mail": row["e_mail"],
        }
        for row in rows
    ]


def clean_groups(rows: list[dict[str, str]]) -> list[dict]:
    return [
        {
            "id": to_int(row["id"]),
            "owner_id": to_int(row["owner_id"]),
            "group_name": row["group_name"],
            "created_date": to_datetime(row["created_date"]),
        }
        for row in rows
    ]


def clean_chats(rows: list[dict[str, str]], max_fraction: int) -> list[dict]:
    return [
        {
            "msg_id": to_int(row["msg_id"]),
            "msg_time": to_datetime(row["msg_time"], max_fraction),
            "msg_from": to_int(row["msg_from"]),
            "msg_to": to_int(row["msg_to"]),
            "text_msg": row["text_msg"],
            "msg_group_id": to_int(row["msg_group_id"]),
        }
        for row in rows
    ]


def read_and_clean(settings: Settings) -> dict[str, list[dict]]:
    source = settings.source

    def read_rows(path: Path) -> list[dict[str, str]]:
        return read_source_rows(path, source.encoding, source.delimiter)

    return {
        "people": clean_people(read_rows(source.people_file)),
        "groups": clean_groups(read_rows(source.groups_file)),
        "chats": clean_chats(read_rows(source.chats_file), source.timestamp_max_fraction),
    }
