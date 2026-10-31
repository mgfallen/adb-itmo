from datetime import date, datetime

from src.config import load_settings
from src.load import load_hubs, load_links, load_satellites, load_staging, to_csv_data
from tests.fakes import FakeConnection

LOAD_DATE = datetime(2024, 1, 1)


def test_to_csv_data():
    rows = [
        {"id": 1, "name": "Мария", "city": None},
        {"id": 2, "name": "Олег", "city": "Казань"},
    ]

    data = to_csv_data(rows, ("id", "name", "city"))

    assert data == "1,Мария,\\N\n2,Олег,Казань\n"


def test_load_staging_copies_csv_and_counts():
    connection = FakeConnection(accepted_rows=4)
    settings = load_settings()
    records = {
        "people": [{
            "id": 0,
            "name": "Мария Су",
            "registration_date": datetime(2020, 10, 16, 19, 18, 46),
            "country": "КНР",
            "date_of_birthday": date(2010, 3, 17),
            "phone": "79115700994",
            "e_mail": "maria@ya.ru",
        }],
        "groups": [],
        "chats": [],
    }

    counts = load_staging(connection, settings, records=records)

    assert counts == {"people": 4, "groups": 4, "chats": 4}
    truncates = [sql for sql, _ in connection._cursor.executed if "TRUNCATE TABLE staging" in sql]
    assert len(truncates) == 3
    assert connection.commits == 1
    assert len(connection._cursor.copied) == 3
    people_sql, people_data = connection._cursor.copied[0]
    assert (
        "COPY staging.st_people "
        "(id, name, registration_date, country, date_of_birthday, phone, e_mail)"
    ) in people_sql
    assert "REJECTED DATA AS TABLE staging.st_people_rej" in people_sql
    assert f"REJECTMAX {settings.source.reject_max}" in people_sql
    assert people_data == "0,Мария Су,2020-10-16 19:18:46,КНР,2010-03-17,79115700994,maria@ya.ru\n"


def test_load_hubs_merges_all_sources():
    connection = FakeConnection()

    load_hubs(connection, load_settings(), LOAD_DATE)

    executed_sql, params = connection._cursor.executed[0]
    assert connection.commits == 1
    assert "INSERT INTO dvs.h_people" in executed_sql
    assert "FROM staging.st_people p" in executed_sql
    assert "SELECT g.owner_id" in executed_sql
    assert "SELECT c.msg_from" in executed_sql
    assert "SELECT c.msg_to" in executed_sql
    assert "MD5(CAST(person_id AS VARCHAR))" in executed_sql
    assert params == {"load_date": LOAD_DATE}
    assert len(connection._cursor.executed) == 3


def test_load_links_creates_two_person_chat_rows():
    connection = FakeConnection()

    load_links(connection, load_settings(), LOAD_DATE)

    executed_sql, _ = connection._cursor.executed[1]
    assert "INSERT INTO dvs.l_person_chat" in executed_sql
    assert executed_sql.count("from") >= 2
    assert executed_sql.count("'to'") >= 2
    assert "UNION ALL" in executed_sql
    assert "INSERT INTO dvs.l_chat_owners" in connection._cursor.executed[0][0]
    assert "INSERT INTO dvs.l_groups" in connection._cursor.executed[2][0]


def test_load_satellites_uses_defaults_and_hash_diff():
    settings = load_settings()
    connection = FakeConnection()

    load_satellites(connection, settings, LOAD_DATE)

    person_sql, person_params = connection._cursor.executed[0]
    group_sql, group_params = connection._cursor.executed[1]
    chat_sql, chat_params = connection._cursor.executed[2]
    assert "INSERT INTO dvs.s_person_info" in person_sql
    assert "NOT EXISTS" in person_sql
    assert "INSERT INTO dvs.s_group_info" in group_sql
    assert "INSERT INTO dvs.s_chat_info" in chat_sql
    assert person_params["load_date"] == LOAD_DATE
    assert group_params["group_status"] == settings.source.group_status
    assert chat_params["chat_status"] == settings.source.chat_status
