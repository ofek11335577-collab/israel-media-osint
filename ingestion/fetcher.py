# ingestion/fetcher.py

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
import email.utils

from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from database import (
    get_db_connection,
    utc_now_iso,
)


# =========================================================
# LIVE RSS SOURCES
# =========================================================

DIRECT_RSS_CHANNELS = [
    {
        "name": "Reuters World",
        "url": "https://www.reuters.com/arc/outboundfeeds/v1/output/rss/?outputType=xml",
        "default_country": "US & Global",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "default_country": "US & Global",
    },
    {
        "name": "BBC Middle East",
        "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "default_country": "US & Global",
    },
]


DEFAULT_IMAGE = (
    "https://images.unsplash.com/"
    "photo-1504711434969-e33886168f5c?w=1200"
)


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_html(raw_html):
    """
    Remove HTML tags and decode HTML entities.
    """

    if not raw_html:
        return ""

    # Remove tags
    clean_text = re.sub(
        r"<[^>]+>",
        " ",
        raw_html
    )

    # Convert things such as &amp; -> &
    clean_text = html.unescape(clean_text)

    # Normalize whitespace
    clean_text = re.sub(
        r"\s+",
        " ",
        clean_text
    )

    return clean_text.strip()


# =========================================================
# URL NORMALIZATION
# =========================================================

def normalize_url(url):
    """
    Removes fragments and common tracking parameters
    so the same article is less likely to be inserted twice.
    """

    if not url:
        return ""

    url = url.strip()

    try:
        parts = urlsplit(url)

        # Fragment (#something) is irrelevant
        normalized = urlunsplit(
            (
                parts.scheme,
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                parts.query,
                "",
            )
        )

        return normalized

    except Exception:
        return url


# =========================================================
# TITLE NORMALIZATION FOR DEDUPLICATION
# =========================================================

def normalize_title(title):
    """
    Produces a simplified version of the title
    for duplicate detection.
    """

    if not title:
        return ""

    normalized = title.lower()

    normalized = re.sub(
        r"[^\w\s]",
        "",
        normalized
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    )

    return normalized.strip()


# =========================================================
# DATE PARSING
# =========================================================

def parse_rss_date(pub_date_elem):
    """
    Convert RSS pubDate into UTC ISO-8601.

    Example:
    2026-09-15T10:34:00+00:00
    """

    if (
        pub_date_elem is not None
        and pub_date_elem.text
    ):

        try:

            parsed = email.utils.parsedate_to_datetime(
                pub_date_elem.text
            )

            if parsed is not None:

                if parsed.tzinfo is None:
                    parsed = parsed.replace(
                        tzinfo=timezone.utc
                    )

                parsed = parsed.astimezone(
                    timezone.utc
                )

                return parsed.replace(
                    microsecond=0
                ).isoformat()

        except Exception:
            pass

    # Fallback if feed contains no usable date
    return utc_now_iso()


# =========================================================
# IMAGE EXTRACTION
# =========================================================

def extract_real_image(item, raw_description):
    """
    Tries multiple common RSS image standards.
    """

    possible_tags = [

        "{http://search.yahoo.com/mrss/}content",

        "{http://search.yahoo.com/mrss/}thumbnail",

        "enclosure",
    ]

    for tag in possible_tags:

        media = item.find(tag)

        if media is not None:

            image_url = media.get("url")

            if image_url:
                return image_url


    # Some feeds embed the image inside description HTML

    if raw_description:

        patterns = [

            r'<img[^>]+src=["\']([^"\']+)["\']',

            r'<img[^>]+data-src=["\']([^"\']+)["\']',

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                raw_description,
                flags=re.IGNORECASE
            )

            if match:
                return html.unescape(
                    match.group(1)
                )


    # Generic fallback — clearly only a placeholder
    return DEFAULT_IMAGE


# =========================================================
# GEOGRAPHIC CLASSIFICATION
# =========================================================

def classify_country(title, summary=""):
    """
    Rule-based geographic classification.
    Searches both headline and summary.
    """

    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()


    country_keywords = [

        (
            "Iran",
            [
                "iran",
                "iranian",
                "tehran",
                "khamenei",
            ],
        ),

        (
            "Saudi Arabia",
            [
                "saudi",
                "riyadh",
                "jeddah",
            ],
        ),

        (
            "UAE",
            [
                "uae",
                "emirates",
                "dubai",
                "abu dhabi",
            ],
        ),

        (
            "Yemen",
            [
                "yemen",
                "yemeni",
                "houthi",
                "houthis",
                "sanaa",
            ],
        ),

        (
            "Syria",
            [
                "syria",
                "syrian",
                "damascus",
            ],
        ),

        (
            "Iraq",
            [
                "iraq",
                "iraqi",
                "baghdad",
            ],
        ),

        (
            "Gaza & WB",
            [
                "gaza",
                "palestin",
                "west bank",
                "ramallah",
                "jenin",
                "nablus",
            ],
        ),

    ]


    for country, keywords in country_keywords:

        if any(
            keyword in text
            for keyword in keywords
        ):
            return country


    return "US & Global"


# =========================================================
# BASIC TOPIC CLASSIFICATION
# =========================================================

def classify_topic(title, summary=""):

    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()


    if any(
        word in text
        for word in [
            "missile",
            "military",
            "army",
            "strike",
            "attack",
            "defense",
            "security",
            "war",
        ]
    ):
        return "Security"


    if any(
        word in text
        for word in [
            "oil",
            "market",
            "economy",
            "economic",
            "trade",
            "bank",
        ]
    ):
        return "Economy"


    if any(
        word in text
        for word in [
            "talks",
            "diplomatic",
            "minister",
            "agreement",
            "negotiation",
        ]
    ):
        return "Diplomacy"


    if any(
        word in text
        for word in [
            "aid",
            "humanitarian",
            "hospital",
            "food",
            "water",
        ]
    ):
        return "Humanitarian"


    return "General"


# =========================================================
# DUPLICATE CHECK
# =========================================================

def article_already_exists(
    cursor,
    url,
    title
):
    """
    Deduplication:
    1. exact normalized URL
    2. normalized title match
    """

    cursor.execute(
        """
        SELECT id, title
        FROM articles
        WHERE url = ?
        LIMIT 1
        """,
        (url,)
    )

    if cursor.fetchone():
        return True


    normalized_new_title = normalize_title(
        title
    )

    if not normalized_new_title:
        return False


    # Compare only against recent-ish database titles.
    # With a small project this is sufficient.
    cursor.execute(
        """
        SELECT title
        FROM articles
        ORDER BY id DESC
        LIMIT 500
        """
    )

    for row in cursor.fetchall():

        existing_title = normalize_title(
            row["title"]
        )

        if (
            existing_title
            and existing_title
            == normalized_new_title
        ):
            return True


    return False


# =========================================================
# LIVE INGESTION PIPELINE
# =========================================================

def fetch_live_web_articles():

    conn = get_db_connection()
    cursor = conn.cursor()

    total_added = 0


    for source in DIRECT_RSS_CHANNELS:

        try:

            request = urllib.request.Request(
                source["url"],
                headers={
                    "User-Agent":
                        "Mozilla/5.0 "
                        "(compatible; OSINTGlobalDesk/1.0)"
                }
            )


            with urllib.request.urlopen(
                request,
                timeout=10
            ) as response:

                xml_data = response.read()


            root = ET.fromstring(
                xml_data
            )


            # Up to 25 recent items per source
            for item in root.findall(
                ".//item"
            )[:25]:


                # -----------------------------------------
                # RSS FIELDS
                # -----------------------------------------

                title_elem = item.find(
                    "title"
                )

                link_elem = item.find(
                    "link"
                )

                pub_date_elem = item.find(
                    "pubDate"
                )

                description_elem = item.find(
                    "description"
                )


                title = (
                    title_elem.text.strip()
                    if (
                        title_elem is not None
                        and title_elem.text
                    )
                    else "Untitled Report"
                )


                raw_url = (
                    link_elem.text.strip()
                    if (
                        link_elem is not None
                        and link_elem.text
                    )
                    else ""
                )


                # No real URL = don't ingest
                if not raw_url:
                    continue


                url = normalize_url(
                    raw_url
                )


                raw_description = (
                    description_elem.text
                    if (
                        description_elem
                        is not None
                        and description_elem.text
                    )
                    else ""
                )


                clean_description = clean_html(
                    raw_description
                )


                # -----------------------------------------
                # DEDUPLICATION
                # -----------------------------------------

                if article_already_exists(
                    cursor,
                    url,
                    title
                ):
                    continue


                # -----------------------------------------
                # DATE
                # -----------------------------------------

                published_at = parse_rss_date(
                    pub_date_elem
                )


                created_at = utc_now_iso()


                # -----------------------------------------
                # SUMMARY
                # -----------------------------------------

                if clean_description:

                    summary = (
                        clean_description[:400]
                    )

                else:

                    summary = title


                # -----------------------------------------
                # RSS CONTENT
                # -----------------------------------------

                # Important:
                # this is RSS-provided content,
                # NOT necessarily the full article body.

                full_content = (
                    clean_description
                    if clean_description
                    else summary
                )


                # -----------------------------------------
                # IMAGE
                # -----------------------------------------

                image_url = extract_real_image(
                    item,
                    raw_description
                )


                # -----------------------------------------
                # CLASSIFICATION
                # -----------------------------------------

                country = classify_country(
                    title,
                    summary
                )


                topic = classify_topic(
                    title,
                    summary
                )


                # -----------------------------------------
                # DATABASE INSERT
                # -----------------------------------------

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO articles
                    (
                        url,
                        source_name,
                        country,
                        title,
                        summary,
                        full_content,
                        analyst_name,
                        published_at,
                        image_url,
                        sentiment,
                        priority,
                        created_at
                    )

                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        source["name"],
                        country,
                        title,
                        summary,
                        full_content,
                        "Live RSS Ingestor",
                        published_at,
                        image_url,
                        topic,
                        10,
                        created_at,
                    )
                )


                if cursor.rowcount > 0:
                    total_added += 1


            conn.commit()


        except Exception as error:

            # One broken source should not kill
            # the rest of the ingestion pipeline.

            print(
                f"Feed error "
                f"({source['name']}): "
                f"{error}"
            )


    return total_added