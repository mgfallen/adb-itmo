from src.config import load_settings
from src.marts import build_marts
from tests.fakes import FakeConnection


def test_build_marts_rebuilds_three_marts():
    connection = FakeConnection()

    build_marts(connection, load_settings())

    executed_sql = [sql.strip() for sql, _ in connection._cursor.executed]
    assert connection.commits == 1
    assert len(executed_sql) == 6
    assert executed_sql.count("TRUNCATE TABLE marts.dm_person_activity") == 1
    assert executed_sql.count("TRUNCATE TABLE marts.dm_group_activity") == 1
    assert executed_sql.count("TRUNCATE TABLE marts.dm_message_stats") == 1
    insert_person = executed_sql[1]
    assert "INSERT INTO marts.dm_person_activity" in insert_person
    assert "FROM dvs.h_people" in insert_person
    assert "participant_role = 'from'" in insert_person
    insert_group = executed_sql[3]
    assert "INSERT INTO marts.dm_group_activity" in insert_group
    assert "FROM dvs.h_groups" in insert_group
    insert_stats = executed_sql[5]
    assert "INSERT INTO marts.dm_message_stats" in insert_stats
    assert "AVG(LENGTH(chat.text_msg))" in insert_stats


def test_build_marts_link_condition_covers_prefixes():
    from src.marts import _messages_with_link_condition

    condition = _messages_with_link_condition()
    assert "chat.text_msg LIKE '%http://%'" in condition
    assert "chat.text_msg LIKE '%https://%'" in condition
