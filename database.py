# database.py
import sqlite3
import streamlit as st

DB_PATH = "osint_desk.db"

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # יצירת טבלה ראשונית אם אינה קיימת
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            source_name TEXT,
            country TEXT,
            title_hebrew TEXT,
            title_english TEXT,
            summary_hebrew TEXT,
            summary_english TEXT,
            full_content_hebrew TEXT,
            full_content_english TEXT,
            analyst_name TEXT,
            published_at TEXT,
            image_url TEXT,
            sentiment TEXT,
            priority INTEGER
        )
    ''')
    conn.commit()
    
    # בדיקה אוטומטית של מבנה העמודות והוספת עמודות חסרות (מניעת שגיאות SQL)
    cursor.execute("PRAGMA table_info(articles)")
    existing_columns = [col['name'] for col in cursor.fetchall()]
    
    required_columns = {
        "url": "TEXT UNIQUE",
        "source_name": "TEXT",
        "country": "TEXT",
        "title_hebrew": "TEXT",
        "title_english": "TEXT",
        "summary_hebrew": "TEXT",
        "summary_english": "TEXT",
        "full_content_hebrew": "TEXT",
        "full_content_english": "TEXT",
        "analyst_name": "TEXT",
        "published_at": "TEXT",
        "image_url": "TEXT",
        "sentiment": "TEXT",
        "priority": "INTEGER"
    }
    
    for col_name, col_type in required_columns.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
                conn.commit()
            except Exception as e:
                print(f"Auto-migration note for {col_name}: {e}")