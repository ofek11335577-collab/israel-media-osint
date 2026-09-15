# database.py
import sqlite3
import streamlit as st
from datetime import datetime, timezone

DB_PATH = "osint_desk.db"


@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    # SQLite settings
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            source_name TEXT NOT NULL,
            country TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            full_content TEXT,
            analyst_name TEXT,
            published_at TEXT NOT NULL,
            image_url TEXT,
            sentiment TEXT,
            priority INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # אינדקסים לשיפור ביצועי חיפוש ומיון
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_published_at
        ON articles(published_at DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_country
        ON articles(country)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_source
        ON articles(source_name)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_priority
        ON articles(priority DESC)
    """)

    conn.commit()


def utc_now_iso():
    """
    מחזיר זמן UTC בפורמט ISO אחיד.
    דוגמה:
    2026-09-15T10:35:00+00:00
    """
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def normalize_datetime(dt):
    """
    מקבל datetime ומחזיר ISO 8601 אחיד ב-UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt = dt.astimezone(timezone.utc)

    return dt.replace(
        microsecond=0
    ).isoformat()