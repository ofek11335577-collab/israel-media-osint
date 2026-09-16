import concurrent.futures
import re
import time
from functools import lru_cache

from deep_translator import GoogleTranslator

from database import get_db_connection, utc_now_iso


MAX_TRANSLATION_CHARS = 4200
HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


# Small post-translation glossary for recurring intelligence/news terminology.
# It only replaces English leftovers; it does not overwrite Hebrew produced by
# the translator.
HEBREW_GLOSSARY = {
    "IDF": 'צה״ל',
    "Israel Defense Forces": 'צה״ל',
    "Israel Defence Forces": 'צה״ל',
    "IRGC": 'משמרות המהפכה',
    "West Bank": 'הגדה המערבית',
    "Gaza Strip": 'רצועת עזה',
    "Hezbollah": 'חיזבאללה',
    "Hamas": 'חמאס',
    "Tehran": 'טהרן',
    "Jerusalem": 'ירושלים',
    "Tel Aviv": 'תל אביב',
}


def has_hebrew_text(text):
    return bool(HEBREW_RE.search((text or "").strip()))


def _valid_hebrew_translation(source, translated):
    source = (source or "").strip()
    translated = (translated or "").strip()

    if not source:
        return True
    if not translated:
        return False

    # If the original is already Hebrew, it is valid as-is.
    if has_hebrew_text(source):
        return True

    # Do not persist the original English text as a "translation" when the
    # translation service fails.
    if translated.casefold() == source.casefold():
        return False

    return has_hebrew_text(translated)


def _cleanup_translation(text):
    text = (text or "").strip()
    for english, hebrew in HEBREW_GLOSSARY.items():
        text = text.replace(english, hebrew)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


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

        # Keep sentence/paragraph structure when possible.
        parts = [
            paragraph[i:i + max_chars]
            for i in range(0, len(paragraph), max_chars)
        ]

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


@lru_cache(maxsize=4096)
def translate_to_hebrew(text):
    """
    Best-effort translation to Hebrew.

    deep-translator 1.11.x expects Google's Hebrew code "iw" (or the language
    name "hebrew"), not "he". We try both accepted forms and validate the
    output before it is allowed into the database.
    """
    text = (text or "").strip()
    if not text:
        return ""

    if has_hebrew_text(text):
        return text

    translated_parts = []

    for chunk in _chunks(text):
        translated_chunk = ""

        # "iw" is the code used by Google/deep-translator for Hebrew in the
        # currently pinned deep-translator release. "hebrew" is a second
        # accepted form and serves as a fallback.
        for target in ("iw", "hebrew"):
            for attempt in range(2):
                try:
                    candidate = GoogleTranslator(
                        source="auto",
                        target=target,
                    ).translate(chunk)
                    candidate = _cleanup_translation(candidate)

                    if _valid_hebrew_translation(chunk, candidate):
                        translated_chunk = candidate
                        break
                except Exception:
                    pass

                if attempt == 0:
                    time.sleep(0.45)

            if translated_chunk:
                break

        if not translated_chunk:
            # Empty means "retry later". Crucially, we do not save the English
            # source into *_he columns anymore.
            return ""

        translated_parts.append(translated_chunk)

    translated = "\n".join(translated_parts).strip()
    return translated if _valid_hebrew_translation(text, translated) else ""


def _translation_needed(source, stored):
    source = (source or "").strip()
    stored = (stored or "").strip()
    if not source:
        return False
    return not _valid_hebrew_translation(source, stored)


def _translate_card_row(row):
    article_id = int(row["id"])
    title = row.get("title") or ""
    summary = row.get("summary") or ""

    title_he = row.get("title_he") or ""
    summary_he = row.get("summary_he") or ""

    if _translation_needed(title, title_he):
        title_he = translate_to_hebrew(title)

    if _translation_needed(summary, summary_he):
        summary_he = translate_to_hebrew(summary)

    title_ok = (not title) or _valid_hebrew_translation(title, title_he)
    summary_ok = (not summary) or _valid_hebrew_translation(summary, summary_he)

    return article_id, title_he if title_ok else "", summary_he if summary_ok else "", title_ok and summary_ok


def ensure_hebrew_card_translations(article_ids, max_workers=2):
    """
    Translate only the requested cards. Existing *_he values that contain the
    original English text are treated as invalid and are repaired automatically.
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
        """,
        article_ids,
    )

    rows = [dict(row) for row in cursor.fetchall()]
    rows = [
        row for row in rows
        if _translation_needed(row.get("title"), row.get("title_he"))
        or _translation_needed(row.get("summary"), row.get("summary_he"))
    ]

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

    now = utc_now_iso()
    updated = 0

    for article_id, title_he, summary_he, complete in results:
        if not title_he and not summary_he:
            cursor.execute(
                """
                UPDATE articles
                SET translation_status = 'retry', updated_at = ?
                WHERE id = ?
                """,
                (now, article_id),
            )
            continue

        cursor.execute(
            """
            UPDATE articles
            SET title_he = CASE WHEN ? != '' THEN ? ELSE title_he END,
                summary_he = CASE WHEN ? != '' THEN ? ELSE summary_he END,
                translation_status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                title_he, title_he,
                summary_he, summary_he,
                "card_done" if complete else "retry",
                now,
                article_id,
            ),
        )
        updated += 1

    conn.commit()
    return updated


def ensure_hebrew_full_translation(article_id):
    """Translate the selected article's title, summary and body on demand."""
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

    row = dict(row)
    title = row.get("title") or ""
    summary = row.get("summary") or ""
    full_text = row.get("full_content") or summary or title

    title_he = row.get("title_he") or ""
    summary_he = row.get("summary_he") or ""
    full_he = row.get("full_content_he") or ""

    if _translation_needed(title, title_he):
        title_he = translate_to_hebrew(title)
    if _translation_needed(summary, summary_he):
        summary_he = translate_to_hebrew(summary)
    if _translation_needed(full_text, full_he):
        full_he = translate_to_hebrew(full_text)

    title_ok = (not title) or _valid_hebrew_translation(title, title_he)
    summary_ok = (not summary) or _valid_hebrew_translation(summary, summary_he)
    full_ok = (not full_text) or _valid_hebrew_translation(full_text, full_he)

    cursor.execute(
        """
        UPDATE articles
        SET title_he = CASE WHEN ? != '' THEN ? ELSE title_he END,
            summary_he = CASE WHEN ? != '' THEN ? ELSE summary_he END,
            full_content_he = CASE WHEN ? != '' THEN ? ELSE full_content_he END,
            translation_status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            title_he, title_he,
            summary_he, summary_he,
            full_he, full_he,
            "full_done" if (title_ok and summary_ok and full_ok) else "retry",
            utc_now_iso(),
            int(article_id),
        ),
    )
    conn.commit()
    return title_ok and summary_ok and full_ok
