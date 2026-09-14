import sqlite3
import os

DB_PATH = "osint.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

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
            published_at TEXT,
            image_url TEXT,
            title_hebrew TEXT,
            summary_hebrew TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            mentioned_countries TEXT
        )
    ''')
    conn.commit()
    conn.close()

def is_article_exists(url: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False

def save_article(article: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            OR IGNORE INTO articles 
            (url, source_name, country, title_original, content_original, published_at, image_url, title_hebrew, summary_hebrew, sentiment, sentiment_score, mentioned_countries)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article.get('url'),
            article.get('source_name'),
            article.get('country'),
            article.get('title_original'),
            article.get('content_original'),
            article.get('published_at'),
            article.get('image_url'),
            article.get('title_hebrew'),
            article.get('summary_hebrew'),
            article.get('sentiment'),
            article.get('sentiment_score', 0.0),
            article.get('mentioned_countries')
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database save error: {e}")