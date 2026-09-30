import sqlite3

from alembic import command
from alembic.config import Config

from app.config import get_settings


def test_rich_text_migration_preserves_existing_key_and_description(tmp_path, monkeypatch):
    database = tmp_path / "legacy.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database.as_posix()}")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    try:
        command.upgrade(config, "0002")
        with sqlite3.connect(database) as connection:
            connection.execute(
                "INSERT INTO access_entries "
                "(display_name, description, is_active) VALUES (?, ?, ?)",
                ("Existing", "Старое описание", 1),
            )
            connection.execute(
                "INSERT INTO access_keys "
                "(access_entry_id, display_name, vpn_key, sort_order) VALUES (?, ?, ?, ?)",
                (1, "Mac", "vpn://existing-key", 0),
            )
        command.upgrade(config, "head")
        with sqlite3.connect(database) as connection:
            entry = connection.execute(
                "SELECT description, description_format FROM access_entries WHERE id = 1"
            ).fetchone()
            key = connection.execute(
                "SELECT vpn_key, comment_html FROM access_keys WHERE access_entry_id = 1"
            ).fetchone()
        assert entry == ("Старое описание", "plain")
        assert key == ("vpn://existing-key", None)
    finally:
        get_settings.cache_clear()
