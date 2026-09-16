import sqlite3
from datetime import datetime, timezone

import streamlit as st

DB_PATH = "osint_desk.db"


@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=30,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _existing_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_column(cursor, table_name, column_name, sql_type):
    columns = _existing_columns(cursor, table_name)
    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {sql_type}"
        )


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Keep legacy columns so existing data and older deployments remain compatible.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            source_name TEXT,
            country TEXT,
            title TEXT,
            summary TEXT,
            full_content TEXT,
            analyst_name TEXT,
            published_at TEXT,
            image_url TEXT,
            sentiment TEXT,
            priority INTEGER,
            created_at TEXT
        )
        """
    )

    # New explicit fields. No destructive migration is performed.
    new_columns = {
        "source_type": "TEXT",
        "source_country": "TEXT",
        "topic": "TEXT",
        "relevance_score": "INTEGER",
        "israel_related": "INTEGER DEFAULT 0",
        "israel_framing": "TEXT",
        "framing_evidence": "TEXT",
        "title_he": "TEXT",
        "summary_he": "TEXT",
        "full_content_he": "TEXT",
        "translation_status": "TEXT",
        "updated_at": "TEXT",
    }

    for column_name, sql_type in new_columns.items():
        _ensure_column(
            cursor,
            "articles",
            column_name,
            sql_type,
        )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articles_published_at
        ON articles(published_at)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articles_country
        ON articles(country)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articles_source
        ON articles(source_name)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articles_topic
        ON articles(topic)
        """
    )

    # Migrate useful legacy values into the new explicit fields once.
    cursor.execute(
        """
        UPDATE articles
        SET topic = COALESCE(NULLIF(topic, ''), sentiment)
        WHERE topic IS NULL OR topic = ''
        """
    )

    cursor.execute(
        """
        UPDATE articles
        SET relevance_score = COALESCE(relevance_score, priority)
        WHERE relevance_score IS NULL
        """
    )

    cursor.execute(
        """
        UPDATE articles
        SET israel_framing = analyst_name
        WHERE (israel_framing IS NULL OR israel_framing = '')
          AND LOWER(COALESCE(analyst_name, '')) IN (
              'hostile', 'positive', 'neutral',
              'critical', 'supportive'
          )
        """
    )

    cursor.execute(
        """
        UPDATE articles
        SET created_at = COALESCE(created_at, published_at, ?)
        WHERE created_at IS NULL OR created_at = ''
        """,
        (utc_now_iso(),),
    )

    conn.commit()
