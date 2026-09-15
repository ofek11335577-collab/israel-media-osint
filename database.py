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
    
    # בדיקה האם קיימת טבלה ישנה עם מבנה לא תואם ומחיקתה אוטומטית
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        cursor.execute("PRAGMA table_info(articles)")
        columns = [col[1] for col in cursor.fetchall()]
        # אם עמודת 'title' החדשה לא קיימת, זה אומר שזו טבלה ישנה ויש לאפס אותה
        if 'title' not in columns:
            cursor.execute("DROP TABLE articles")
            conn.commit()

    # יצירת הטבלה החדשה והנקייה באנגלית מלאה
    cursor.execute('''
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
            priority INTEGER
        )
    ''')
    conn.commit()