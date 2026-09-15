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
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


def utc_now_iso():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ------------------------------------------
    # Main articles table
    # ------------------------------------------

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
            published_at TEXT,
            image_url TEXT,
            sentiment TEXT,
            priority INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # ------------------------------------------
    # Migration for older databases
    # IMPORTANT: never DROP the table
    # ------------------------------------------

    cursor.execute(
        "PRAGMA table_info(articles)"
    )

    columns = {
        row[1]
        for row in cursor.fetchall()
    }

    if "created_at" not in columns:
        cursor.execute("""
            ALTER TABLE articles
            ADD COLUMN created_at TEXT
        """)

    # ------------------------------------------
    # Indexes
    # ------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_articles_published_at
        ON articles(published_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_articles_country
        ON articles(country)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_articles_source
        ON articles(source_name)
    """)

    # ------------------------------------------
    # Fetch-state table
    # lets us know when last RSS sync happened
    # ------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()