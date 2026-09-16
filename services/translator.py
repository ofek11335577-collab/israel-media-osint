import concurrent.futures
import time
from functools import lru_cache

from deep_translator import GoogleTranslator

from database import get_db_connection, utc_now_iso


MAX_TRANSLATION_CHARS = 4500


def _chunks(text, max_chars=MAX_TRANSLATION_CHARS):
    text = (text or "").strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = []
    current_len = 0

    paragraphs = text.split("\n")
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Split extremely long paragraphs conservatively.
        parts = [paragraph[i:i + max_chars] for i in range(0, len(paragraph), max_chars)]

        for part in parts:
            extra = len(part) + (1 if current else 0)
            if current and current_len + extra > max_chars:
                chunks.append("\n".join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += extra

    if current:
        chunks.append("\n".join(current))

    return chunks


@lru_cache(maxsize=2048)
def translate_to_hebrew(text):
    """
    Best-effort English -> Hebrew translation.
    The result is cached in-process; article translations are also persisted in SQLite.
    """
    text = (text or "").strip()
    if not text:
        return ""

    translated_parts = []

    for chunk in _chunks(text):
        last_error = None
        for attempt in range(2):
            try:
                translated = GoogleTranslator(
                    source="auto",
                    target="he",
                ).translate(chunk)

                translated_parts.append(translated or chunk)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.35)

        if last_error is not None:
            translated_parts.append(chunk)

    return "\n".join(translated_parts).strip()


def _translate_card_row(row):
    article_id = int(row["id"])
    title = row["title"] or ""
    summary = row["summary"] or ""

    title_he = translate_to_hebrew(title)
    summary_he = translate_to_hebrew(summary)

    return article_id, title_he, summary_he


def ensure_hebrew_card_translations(article_ids, max_workers=4):
    """
    Translate titles and summaries for the requested IDs only.
    This is used lazily when the user switches the UI to Hebrew.
    """
    article_ids = [int(x) for x in article_ids if x is not None]
    if not article_ids:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in article_ids)
    cursor.execute(
        f"""
        SELECT id, title, summary, title_he, summary_he
        FROM articles
        WHERE id IN ({placeholders})
          AND (
              title_he IS NULL OR title_he = ''
              OR summary_he IS NULL OR summary_he = ''
          )
        """,
        article_ids,
    )

    rows = [dict(row) for row in cursor.fetchall()]
    if not rows:
        return 0

    results = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(max_workers, len(rows))
    ) as executor:
        futures = [executor.submit(_translate_card_row, row) for row in rows]
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                pass

    if not results:
        return 0

    now = utc_now_iso()
    cursor.executemany(
        """
        UPDATE articles
        SET title_he = ?,
            summary_he = ?,
            translation_status = 'card_done',
            updated_at = ?
        WHERE id = ?
        """,
        [
            (title_he, summary_he, now, article_id)
            for article_id, title_he, summary_he in results
        ],
    )
    conn.commit()
    return len(results)


def ensure_hebrew_full_translation(article_id):
    """
    Translate the selected article's full content on demand.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, summary, full_content,
               title_he, summary_he, full_content_he
        FROM articles
        WHERE id = ?
        """,
        (int(article_id),),
    )

    row = cursor.fetchone()
    if row is None:
        return False

    title_he = row["title_he"] or translate_to_hebrew(row["title"] or "")
    summary_he = row["summary_he"] or translate_to_hebrew(row["summary"] or "")

    if row["full_content_he"]:
        full_he = row["full_content_he"]
    else:
        full_text = row["full_content"] or row["summary"] or row["title"] or ""
        full_he = translate_to_hebrew(full_text)

    cursor.execute(
        """
        UPDATE articles
        SET title_he = ?,
            summary_he = ?,
            full_content_he = ?,
            translation_status = 'full_done',
            updated_at = ?
        WHERE id = ?
        """,
        (
            title_he,
            summary_he,
            full_he,
            utc_now_iso(),
            int(article_id),
        ),
    )
    conn.commit()
    return True
