from src.config import load_settings, load_vertica_settings


def test_load_settings():
    settings = load_settings()

    assert settings.source.encoding == "cp1251"
    assert settings.source.delimiter == ","
    assert settings.source.timestamp_max_fraction == 6
    assert settings.source.people_file.name == "people.csv"
    assert settings.source.groups_file.name == "groups.csv"
    assert settings.source.chats_file.name == "chats.csv"
    assert settings.source.people_file.exists()
    assert settings.source.group_status == "active"
    assert settings.source.chat_status == "delivered"

    assert settings.dwh.staging_schema == "staging"
    assert settings.dwh.dv_schema == "dvs"
    assert settings.dwh.marts_schema == "marts"
    assert settings.dwh.sys_marts_schema == "sys_marts"


def test_load_vertica_settings(monkeypatch):
    monkeypatch.setenv("VERTICA_HOST", "localhost")
    monkeypatch.setenv("VERTICA_PORT", "5555")
    monkeypatch.setenv("VERTICA_DATABASE", "testdb")
    monkeypatch.setenv("VERTICA_USER", "testuser")
    monkeypatch.delenv("VERTICA_PASSWORD", raising=False)

    settings = load_vertica_settings()

    assert settings.host == "localhost"
    assert settings.port == 5555
    assert settings.database == "testdb"
    assert settings.user == "testuser"
    assert settings.password == ""
