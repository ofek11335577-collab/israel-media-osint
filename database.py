# database.py
import sqlite3
import streamlit as st
from datetime import datetime, timedelta

DB_PATH = "osint_desk.db"

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    # 🧹 מדיניות ניקוי אוטומטית: מחיקת כל הכתבות הישנות שגילן עולה על 14 יום (שלא יהיו כתבות ישנות מעופשות בדסק)
    try:
        cutoff_date = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d %H:%M")
        cursor.execute("DELETE FROM articles WHERE published_at < ?", (cutoff_date,))
        conn.commit()
    except Exception as e:
        print(f"Auto-purge note: {e}")