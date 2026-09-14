import sqlite3
import os

DB_PATH = "data/osint.db"

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            source_name TEXT,
            country TEXT,
            title_original TEXT,
            content_original TEXT,
            title_hebrew TEXT,
            summary_hebrew TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            image_url TEXT,
            published_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_article_exists(url: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_article(art: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        OR IGNORE INTO articles (
            url, source_name, country, title_original, content_original,
            title_hebrew, summary_hebrew, sentiment, sentiment_score, image_url, published_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        art.get('url'),
        art.get('source_name'),
        art.get('country'),
        art.get('title_original'),
        art.get('content_original'),
        art.get('title_hebrew'),
        art.get('summary_hebrew'),
        art.get('sentiment'),
        art.get('sentiment_score'),
        art.get('image_url'),
        art.get('published_at')
    ))
    conn.commit()
    conn.close()