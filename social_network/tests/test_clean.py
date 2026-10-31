from datetime import date, datetime

from src.clean import (
    clean_chats,
    clean_groups,
    clean_people,
    read_and_clean,
    read_source_rows,
    repair_quoted_line,
    truncate_timestamp_fraction,
)
from src.config import load_settings


def test_repair_quoted_line():
    broken = '"0,2023-06-18 09:39:05.363384736,41492,171717,""Hello "",7777"'
    expected = '0,2023-06-18 09:39:05.363384736,41492,171717,"Hello ",7777'
    assert repair_quoted_line(broken) == expected
    plain = "1,2023-06-22 04:47:59,41492,171717,hi,7777"
    assert repair_quoted_line(plain) == plain


def test_truncate_timestamp_fraction():
    assert truncate_timestamp_fraction("2023-06-18 09:39:05.363384736", 6) == "2023-06-18 09:39:05.363384"
    assert truncate_timestamp_fraction("2023-06-18 09:39:05", 6) == "2023-06-18 09:39:05"


def test_read_source_rows_decodes_cp1251(tmp_path):
    source = tmp_path / "people.csv"
    source.write_text("id,name\n0,Мария Су\n", encoding="cp1251")

    rows = read_source_rows(source, "cp1251", ",")

    assert rows == [{"id": "0", "name": "Мария Су"}]


def test_read_source_rows_renames_hyphen_fields():
    settings = load_settings()
    rows = read_source_rows(settings.source.people_file, settings.source.encoding, settings.source.delimiter)

    assert len(rows) == 4
    assert rows[0]["e_mail"] == "maria@ya.ru"


def test_clean_people():
    settings = load_settings()
    rows = read_source_rows(settings.source.people_file, settings.source.encoding, settings.source.delimiter)

    people = clean_people(rows)

    assert len(people) == 4
    assert people[0] == {
        "id": 0,
        "name": "Мария Су",
        "registration_date": datetime(2020, 10, 16, 19, 18, 46),
        "country": "КНР",
        "date_of_birthday": date(2010, 3, 17),
        "phone": "79115700994",
        "e_mail": "maria@ya.ru",
    }


def test_clean_groups():
    settings = load_settings()
    rows = read_source_rows(settings.source.groups_file, settings.source.encoding, settings.source.delimiter)

    groups = clean_groups(rows)

    assert len(groups) == 9
    assert groups[0]["owner_id"] == 14584
    assert groups[0]["group_name"] == "Группа1"
    assert groups[0]["created_date"] == datetime(2019, 2, 10, 5, 31, 20, 990338)


def test_clean_chats_truncates_nanoseconds():
    settings = load_settings()
    rows = read_source_rows(settings.source.chats_file, settings.source.encoding, settings.source.delimiter)

    chats = clean_chats(rows, settings.source.timestamp_max_fraction)

    assert len(chats) == 10
    first = chats[0]
    assert first["msg_id"] == 0
    assert first["msg_time"] == datetime(2023, 6, 18, 9, 39, 5, 363384)
    assert first["text_msg"] == "Hello "
    assert first["msg_group_id"] == 7777
    assert "http://www.link/" in chats[8]["text_msg"]


def test_read_and_clean_counts():
    settings = load_settings()
    records = read_and_clean(settings)

    assert len(records["people"]) == 4
    assert len(records["groups"]) == 9
    assert len(records["chats"]) == 10
