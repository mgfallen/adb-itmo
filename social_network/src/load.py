import csv
from datetime import datetime
from io import StringIO

from src.clean import read_and_clean
from src.config import Settings

SOURCE_TABLES = {
    "people": ("st_people", ("id", "name", "registration_date", "country", "date_of_birthday", "phone", "e_mail")),
    "groups": ("st_groups", ("id", "owner_id", "group_name", "created_date")),
    "chats": ("st_chats", ("msg_id", "msg_time", "msg_from", "msg_to", "text_msg", "msg_group_id")),
}

NULL_VALUE = "\\N"
KEY_SEPARATOR = "|"
ROLE_FROM = "from"
ROLE_TO = "to"
SOURCE_PEOPLE = "people"
SOURCE_GROUPS = "groups"
SOURCE_CHATS = "chats"


def to_csv_data(rows: list[dict], fields: tuple[str, ...]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=",", lineterminator="\n")
    for row in rows:
        writer.writerow([NULL_VALUE if row[field] is None else row[field] for field in fields])
    return buffer.getvalue()


def load_staging(connection, settings: Settings, records: dict[str, list[dict]] | None = None) -> dict[str, int]:
    if records is None:
        records = read_and_clean(settings)
    staging = settings.dwh.staging_schema
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        for name, (table, fields) in SOURCE_TABLES.items():
            reject_table = f"{table}{settings.dwh.reject_suffix}"
            copy_sql = (
                f"COPY {staging}.{table} ({', '.join(fields)}) "
                f"FROM STDIN DELIMITER ',' NULL '{NULL_VALUE}' "
                f"REJECTED DATA AS TABLE {staging}.{reject_table} "
                f"REJECTMAX {settings.source.reject_max}"
            )
            cursor.copy(copy_sql, to_csv_data(records[name], fields))
            cursor.execute("SELECT GET_NUM_ACCEPTED_ROWS()")
            counts[name] = cursor.fetchone()[0]
    connection.commit()
    return counts


def load_hubs(connection, settings: Settings, load_date: datetime) -> None:
    staging = settings.dwh.staging_schema
    dv = settings.dwh.dv_schema
    queries = [
        f"""
        INSERT INTO {dv}.h_people (hk_person_id, person_id, registration_date, source, load_date)
        SELECT MD5(CAST(person_id AS VARCHAR)), person_id, MAX(registration_date), MIN(source),
        CAST(:load_date AS TIMESTAMP)
        FROM (
            SELECT p.id AS person_id, p.registration_date, NULL, '{SOURCE_PEOPLE}' AS source FROM {staging}.st_people p
            UNION ALL
            SELECT g.owner_id, NULL, NULL, '{SOURCE_GROUPS}' FROM {staging}.st_groups g
            UNION ALL
            SELECT c.msg_from, NULL, NULL, '{SOURCE_CHATS}' FROM {staging}.st_chats c
            UNION ALL
            SELECT c.msg_to, NULL, NULL, '{SOURCE_CHATS}' FROM {staging}.st_chats c
        ) s
        WHERE person_id IS NOT NULL
          AND person_id NOT IN (SELECT person_id FROM {dv}.h_people)
        GROUP BY person_id
        """,
        f"""
        INSERT INTO {dv}.h_groups (hk_group_id, group_id, created_date, source, load_date)
        SELECT MD5(CAST(group_id AS VARCHAR)), group_id, MAX(created_date), MIN(source),
        CAST(:load_date AS TIMESTAMP)
        FROM (
            SELECT g.id AS group_id, g.created_date, '{SOURCE_GROUPS}' AS source FROM {staging}.st_groups g
            UNION ALL
            SELECT c.msg_group_id, NULL, '{SOURCE_CHATS}' FROM {staging}.st_chats c
        ) s
        WHERE group_id IS NOT NULL
          AND group_id NOT IN (SELECT group_id FROM {dv}.h_groups)
        GROUP BY group_id
        """,
        f"""
        INSERT INTO {dv}.h_chats (hk_msg_id, msg_id, msg_time, source, load_date)
        SELECT MD5(CAST(msg_id AS VARCHAR)), msg_id, MAX(msg_time), MIN(source),
        CAST(:load_date AS TIMESTAMP)
        FROM (
            SELECT c.msg_id, c.msg_time, '{SOURCE_CHATS}' AS source FROM {staging}.st_chats c
        ) s
        WHERE msg_id IS NOT NULL
          AND msg_id NOT IN (SELECT msg_id FROM {dv}.h_chats)
        GROUP BY msg_id
        """,
    ]
    with connection.cursor() as cursor:
        for query in queries:
            cursor.execute(query, {"load_date": load_date})
    connection.commit()


def load_links(connection, settings: Settings, load_date: datetime) -> None:
    staging = settings.dwh.staging_schema
    dv = settings.dwh.dv_schema
    queries = [
        f"""
        INSERT INTO {dv}.l_chat_owners (hk_l_chat_owner_id, hk_person_id, hk_group_id, source, load_date)
        SELECT MD5(CAST(g.owner_id AS VARCHAR) || '{KEY_SEPARATOR}' || CAST(g.id AS VARCHAR)),
               p.hk_person_id, h.hk_group_id, '{SOURCE_GROUPS}', CAST(:load_date AS TIMESTAMP)
        FROM {staging}.st_groups g
        JOIN {dv}.h_people p ON p.person_id = g.owner_id
        JOIN {dv}.h_groups h ON h.group_id = g.id
        WHERE MD5(CAST(g.owner_id AS VARCHAR) || '{KEY_SEPARATOR}' || CAST(g.id AS VARCHAR))
              NOT IN (SELECT hk_l_chat_owner_id FROM {dv}.l_chat_owners)
        """,
        f"""
        INSERT INTO {dv}.l_person_chat
            (hk_l_person_chat_id, hk_person_id, hk_msg_id, participant_role, source, load_date)
        SELECT MD5(CAST(c.msg_id AS VARCHAR) || '{KEY_SEPARATOR}'
                   || CAST(p.person_id AS VARCHAR) || '{KEY_SEPARATOR}' || '{ROLE_FROM}'),
               p.hk_person_id, m.hk_msg_id, '{ROLE_FROM}', '{SOURCE_CHATS}', CAST(:load_date AS TIMESTAMP)
        FROM {staging}.st_chats c
        JOIN {dv}.h_people p ON p.person_id = c.msg_from
        JOIN {dv}.h_chats m ON m.msg_id = c.msg_id
        WHERE MD5(CAST(c.msg_id AS VARCHAR) || '{KEY_SEPARATOR}'
                  || CAST(p.person_id AS VARCHAR) || '{KEY_SEPARATOR}' || '{ROLE_FROM}')
              NOT IN (SELECT hk_l_person_chat_id FROM {dv}.l_person_chat)
        UNION ALL
        SELECT MD5(CAST(c.msg_id AS VARCHAR) || '{KEY_SEPARATOR}'
                   || CAST(p.person_id AS VARCHAR) || '{KEY_SEPARATOR}' || '{ROLE_TO}'),
               p.hk_person_id, m.hk_msg_id, '{ROLE_TO}', '{SOURCE_CHATS}', CAST(:load_date AS TIMESTAMP)
        FROM {staging}.st_chats c
        JOIN {dv}.h_people p ON p.person_id = c.msg_to
        JOIN {dv}.h_chats m ON m.msg_id = c.msg_id
        WHERE MD5(CAST(c.msg_id AS VARCHAR) || '{KEY_SEPARATOR}'
                  || CAST(p.person_id AS VARCHAR) || '{KEY_SEPARATOR}' || '{ROLE_TO}')
              NOT IN (SELECT hk_l_person_chat_id FROM {dv}.l_person_chat)
        """,
        f"""
        INSERT INTO {dv}.l_groups (hk_l_group_id, hk_msg_id, hk_group_id, source, load_date)
        SELECT MD5(CAST(c.msg_id AS VARCHAR) || '{KEY_SEPARATOR}' || CAST(h.group_id AS VARCHAR)),
               m.hk_msg_id, h.hk_group_id, '{SOURCE_CHATS}', CAST(:load_date AS TIMESTAMP)
        FROM {staging}.st_chats c
        JOIN {dv}.h_chats m ON m.msg_id = c.msg_id
        JOIN {dv}.h_groups h ON h.group_id = c.msg_group_id
        WHERE MD5(CAST(c.msg_id AS VARCHAR) || '{KEY_SEPARATOR}' || CAST(h.group_id AS VARCHAR))
              NOT IN (SELECT hk_l_group_id FROM {dv}.l_groups)
        """,
    ]
    with connection.cursor() as cursor:
        for query in queries:
            cursor.execute(query, {"load_date": load_date})
    connection.commit()


def load_satellites(connection, settings: Settings, load_date: datetime) -> None:
    staging = settings.dwh.staging_schema
    dv = settings.dwh.dv_schema
    group_status = settings.source.group_status
    chat_status = settings.source.chat_status
    queries = [
        f"""
        INSERT INTO {dv}.s_person_info
            (hk_person_id, name, date_of_birthday, country, phone, e_mail, hash_diff, source, load_date)
        WITH attrs AS (
            SELECT p.hk_person_id, s.name, s.date_of_birthday, s.country, s.phone, s.e_mail,
                   MD5(COALESCE(s.name, '') || '{KEY_SEPARATOR}' || COALESCE(CAST(s.date_of_birthday AS VARCHAR), '')
                       || '{KEY_SEPARATOR}' || COALESCE(s.country, '') || '{KEY_SEPARATOR}' || COALESCE(s.phone, '')
                       || '{KEY_SEPARATOR}' || COALESCE(s.e_mail, '')) AS hash_diff
            FROM {staging}.st_people s
            JOIN {dv}.h_people p ON p.person_id = s.id
        )
        SELECT hk_person_id, name, date_of_birthday, country, phone, e_mail, hash_diff,
               '{SOURCE_PEOPLE}', CAST(:load_date AS TIMESTAMP)
        FROM attrs a
        WHERE hash_diff NOT IN (
            SELECT hash_diff FROM {dv}.s_person_info x WHERE x.hk_person_id = a.hk_person_id
        )
        """,
        f"""
        INSERT INTO {dv}.s_group_info (hk_group_id, title, status, hash_diff, source, load_date)
        WITH attrs AS (
            SELECT p.hk_group_id, g.group_name AS title, :group_status AS status,
                   MD5(COALESCE(g.group_name, '') || '{KEY_SEPARATOR}' || :group_status) AS hash_diff
            FROM {staging}.st_groups g
            JOIN {dv}.h_groups p ON p.group_id = g.id
        )
        SELECT hk_group_id, title, status, hash_diff, '{SOURCE_GROUPS}', CAST(:load_date AS TIMESTAMP)
        FROM attrs a
        WHERE hash_diff NOT IN (
            SELECT hash_diff FROM {dv}.s_group_info x WHERE x.hk_group_id = a.hk_group_id
        )
        """,
        f"""
        INSERT INTO {dv}.s_chat_info (hk_msg_id, text_msg, status, hash_diff, source, load_date)
        WITH attrs AS (
            SELECT p.hk_msg_id, c.text_msg, :chat_status AS status,
                   MD5(COALESCE(c.text_msg, '') || '{KEY_SEPARATOR}' || :chat_status) AS hash_diff
            FROM {staging}.st_chats c
            JOIN {dv}.h_chats p ON p.msg_id = c.msg_id
        )
        SELECT hk_msg_id, text_msg, status, hash_diff, '{SOURCE_CHATS}', CAST(:load_date AS TIMESTAMP)
        FROM attrs a
        WHERE hash_diff NOT IN (
            SELECT hash_diff FROM {dv}.s_chat_info x WHERE x.hk_msg_id = a.hk_msg_id
        )
        """,
    ]
    with connection.cursor() as cursor:
        for query in queries:
            cursor.execute(
                query,
                {
                    "load_date": load_date,
                    "group_status": group_status,
                    "chat_status": chat_status,
                },
            )
    connection.commit()
