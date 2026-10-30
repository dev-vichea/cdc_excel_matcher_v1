"""Store reviewer-verified shipping translations in a local SQLite database."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path


SCHEMA = """CREATE TABLE IF NOT EXISTS verified_translations (
    chinese TEXT PRIMARY KEY,
    english TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""


def _connect(path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    connection=sqlite3.connect(path,timeout=5)
    connection.execute(SCHEMA)
    return connection


def load_verified_translations(path):
    with closing(_connect(path)) as connection:
        return dict(connection.execute('SELECT chinese, english FROM verified_translations'))


def save_verified_translation(path, chinese, english):
    chinese=str(chinese or '').strip()
    english=str(english or '').strip()
    if not chinese or not english:
        raise ValueError('Both Chinese and English terms are required')
    with closing(_connect(path)) as connection:
        with connection:
            connection.execute(
                """INSERT INTO verified_translations (chinese, english)
                   VALUES (?, ?)
                   ON CONFLICT(chinese) DO UPDATE SET
                       english=excluded.english,
                       updated_at=CURRENT_TIMESTAMP""",
                (chinese,english),
            )


def migrate_json_translations(json_path, database_path):
    """Copy legacy JSON terms once, without overwriting newer SQLite corrections."""
    try:
        with open(json_path,encoding='utf-8') as source:
            entries=json.load(source)
    except (OSError,ValueError):
        return 0
    if not isinstance(entries,dict):
        return 0
    valid=[(chinese.strip(),english.strip()) for chinese,english in entries.items()
           if isinstance(chinese,str) and isinstance(english,str)
           and chinese.strip() and english.strip()]
    with closing(_connect(database_path)) as connection:
        with connection:
            connection.executemany(
                'INSERT OR IGNORE INTO verified_translations (chinese, english) VALUES (?, ?)',valid)
        return connection.total_changes
