from src.config import Settings

LINK_PREFIXES = ("http://", "https://")
ROLE_FROM = "from"


def _messages_with_link_condition() -> str:
    return " OR ".join(f"chat.text_msg LIKE '%{prefix}%'" for prefix in LINK_PREFIXES)


def _build_queries(marts: str, dv: str) -> list[str]:
    return [
        f"""
        TRUNCATE TABLE {marts}.dm_person_activity
        """,
        f"""
        INSERT INTO {marts}.dm_person_activity
        SELECT p.person_id,
               info.name,
               info.country,
               COALESCE(owned.groups_owned, 0),
               COALESCE(sent.messages_sent, 0),
               COALESCE(received.messages_received, 0)
        FROM {dv}.h_people p
        LEFT JOIN {dv}.s_person_info info ON info.hk_person_id = p.hk_person_id
        LEFT JOIN (
            SELECT hk_person_id, COUNT(DISTINCT hk_group_id) AS groups_owned
            FROM {dv}.l_chat_owners
            GROUP BY hk_person_id
        ) owned ON owned.hk_person_id = p.hk_person_id
        LEFT JOIN (
            SELECT hk_person_id, COUNT(*) AS messages_sent
            FROM {dv}.l_person_chat
            WHERE participant_role = '{ROLE_FROM}'
            GROUP BY hk_person_id
        ) sent ON sent.hk_person_id = p.hk_person_id
        LEFT JOIN (
            SELECT hk_person_id, COUNT(*) AS messages_received
            FROM {dv}.l_person_chat
            WHERE participant_role <> '{ROLE_FROM}'
            GROUP BY hk_person_id
        ) received ON received.hk_person_id = p.hk_person_id
        """,
        f"""
        TRUNCATE TABLE {marts}.dm_group_activity
        """,
        f"""
        INSERT INTO {marts}.dm_group_activity
        SELECT g.group_id,
               info.title,
               owners.person_id,
               COALESCE(messages.messages_count, 0),
               COALESCE(members.members_count, 0)
        FROM {dv}.h_groups g
        LEFT JOIN {dv}.s_group_info info ON info.hk_group_id = g.hk_group_id
        LEFT JOIN (
            SELECT hk_group_id, MAX(person_id) AS person_id
            FROM {dv}.l_chat_owners o
            JOIN {dv}.h_people p ON p.hk_person_id = o.hk_person_id
            GROUP BY hk_group_id
        ) owners ON owners.hk_group_id = g.hk_group_id
        LEFT JOIN (
            SELECT hk_group_id, COUNT(*) AS messages_count
            FROM {dv}.l_groups
            GROUP BY hk_group_id
        ) messages ON messages.hk_group_id = g.hk_group_id
        LEFT JOIN (
            SELECT lgr.hk_group_id, COUNT(DISTINCT lpc.hk_person_id) AS members_count
            FROM {dv}.l_groups lgr
            JOIN {dv}.l_person_chat lpc ON lpc.hk_msg_id = lgr.hk_msg_id
            GROUP BY lgr.hk_group_id
        ) members ON members.hk_group_id = g.hk_group_id
        """,
        f"""
        TRUNCATE TABLE {marts}.dm_message_stats
        """,
        f"""
        INSERT INTO {marts}.dm_message_stats
        SELECT CAST(chat.msg_time AS DATE),
               COUNT(*) AS messages_total,
               COUNT(CASE WHEN groups.hk_msg_id IS NOT NULL THEN 1 END) AS group_messages,
               COUNT(CASE WHEN groups.hk_msg_id IS NULL THEN 1 END) AS private_messages,
               COUNT(CASE WHEN {_messages_with_link_condition()} THEN 1 END) AS messages_with_link,
               AVG(LENGTH(chat.text_msg)) AS avg_text_length
        FROM {dv}.h_chats m
        JOIN {dv}.s_chat_info chat ON chat.hk_msg_id = m.hk_msg_id
        LEFT JOIN {dv}.l_groups groups ON groups.hk_msg_id = m.hk_msg_id
        GROUP BY CAST(chat.msg_time AS DATE)
        """,
    ]


def build_marts(connection, settings: Settings) -> None:
    queries = _build_queries(settings.dwh.marts_schema, settings.dwh.dv_schema)
    with connection.cursor() as cursor:
        for query in queries:
            cursor.execute(query)
    connection.commit()
