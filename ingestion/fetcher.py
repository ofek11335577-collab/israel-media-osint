# ingestion/fetcher.py

import concurrent.futures
import email.utils
import html
import re
import urllib.request
import xml.etree.ElementTree as ET

from datetime import timezone
from urllib.parse import urlsplit, urlunsplit

from database import get_db_connection, utc_now_iso


# =========================================================
# SOURCES
# =========================================================
#
# domestic_country:
# אם זה מקור מקומי, זו המדינה שהוא מכסה כברירת מחדל.
#
# source_type:
# international / domestic
#
# =========================================================

RSS_CHANNELS = [
    {
        "name": "Reuters World",
        "url": "https://www.reuters.com/arc/outboundfeeds/v1/output/rss/?outputType=xml",
        "source_type": "international",
        "domestic_country": None,
    },
    {
        "name": "Al Jazeera English",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "source_type": "international",
        "domestic_country": None,
    },
    {
        "name": "BBC Middle East",
        "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "source_type": "international",
        "domestic_country": None,
    },
    {
        "name": "The Guardian Middle East",
        "url": "https://www.theguardian.com/world/middleeast/rss",
        "source_type": "international",
        "domestic_country": None,
    },

    # -------------------------
    # IRAN - DOMESTIC
    # -------------------------

    {
        "name": "IRNA English",
        "url": "https://en.irna.ir/rss",
        "source_type": "domestic",
        "domestic_country": "Iran",
    },

    # -------------------------
    # SAUDI ARABIA - DOMESTIC
    # -------------------------

    {
        "name": "Saudi Press Agency",
        "url": "http://www.spa.gov.sa/rss.xml",
        "source_type": "domestic",
        "domestic_country": "Saudi Arabia",
    },

    # -------------------------
    # SYRIA - DOMESTIC
    # -------------------------

    {
        "name": "SANA English",
        "url": "https://www.sana.sy/en/syria/feed/",
        "source_type": "domestic",
        "domestic_country": "Syria",
    },
]


# =========================================================
# NETWORK SETTINGS
# =========================================================

FETCH_TIMEOUT_SECONDS = 6
MAX_ITEMS_PER_SOURCE = 30

# רק RSS.
# לא פותחים דפי כתבות, לא HEAD לתמונות.
# זה קריטי כדי שהאתר לא ייתקע.


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_html(raw_html):
    if not raw_html:
        return ""

    text = raw_html

    # לפעמים entity מגיע מקודד יותר מפעם אחת
    for _ in range(2):
        text = html.unescape(text)

    # הסרת HTML
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # שוב unescape אחרי הסרת התגים
    text = html.unescape(text)

    # whitespace normalization
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# =========================================================
# URL NORMALIZATION
# =========================================================

def normalize_url(url):
    if not url:
        return ""

    url = url.strip()

    try:
        parts = urlsplit(url)

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                parts.query,
                "",
            )
        )

    except Exception:
        return url


# =========================================================
# TITLE NORMALIZATION
# =========================================================

def normalize_title(title):
    if not title:
        return ""

    title = html.unescape(title).lower()

    title = re.sub(
        r"[^\w\s]",
        " ",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    )

    return title.strip()


# =========================================================
# RSS DATE
# =========================================================

def parse_rss_date(pub_date_elem):
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

    return utc_now_iso()


# =========================================================
# FAST RSS IMAGE EXTRACTION
# =========================================================
#
# חשוב:
# לא פותחים את דף הכתבה.
# אם הפיד לא נותן תמונה - מחזירים None.
#
# =========================================================

def extract_feed_image(item, raw_description):
    candidates = []

    media_content = item.find(
        "{http://search.yahoo.com/mrss/}content"
    )

    if media_content is not None:
        candidate = media_content.get("url")

        if candidate:
            candidates.append(candidate)


    media_thumbnail = item.find(
        "{http://search.yahoo.com/mrss/}thumbnail"
    )

    if media_thumbnail is not None:
        candidate = media_thumbnail.get("url")

        if candidate:
            candidates.append(candidate)


    enclosure = item.find("enclosure")

    if enclosure is not None:
        candidate = enclosure.get("url")

        if candidate:
            candidates.append(candidate)


    if raw_description:
        patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+data-src=["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                raw_description,
                flags=re.IGNORECASE,
            )

            if match:
                candidates.append(
                    match.group(1)
                )


    for candidate in candidates:
        candidate = html.unescape(
            candidate.strip()
        )

        if candidate.startswith(
            ("http://", "https://")
        ):
            return candidate


    return None


# =========================================================
# ARTICLE COUNTRY CLASSIFICATION
# =========================================================

COUNTRY_KEYWORDS = {
    "Iran": [
        "iran",
        "iranian",
        "tehran",
        "khamenei",
        "pezeshkian",
        "irgc",
        "revolutionary guard",
    ],

    "Saudi Arabia": [
        "saudi",
        "riyadh",
        "jeddah",
        "kingdom",
        "bin salman",
        "mbs",
    ],

    "UAE": [
        "uae",
        "united arab emirates",
        "emirati",
        "dubai",
        "abu dhabi",
    ],

    "Yemen": [
        "yemen",
        "yemeni",
        "houthi",
        "houthis",
        "sanaa",
        "sana'a",
    ],

    "Syria": [
        "syria",
        "syrian",
        "damascus",
    ],

    "Iraq": [
        "iraq",
        "iraqi",
        "baghdad",
        "basra",
        "kurdistan",
    ],

    "Gaza & WB": [
        "gaza",
        "palestin",
        "west bank",
        "ramallah",
        "jenin",
        "nablus",
    ],

    "Israel": [
        "israel",
        "israeli",
        "jerusalem",
        "tel aviv",
        "idf",
    ],
}


def classify_country(
    title,
    summary,
    domestic_country=None,
):
    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()


    # מקור מקומי:
    # ברירת המחדל היא המדינה שלו,
    # אלא אם יש אינדיקציה חזקה למדינה אחרת.

    best_country = None
    best_score = 0

    for country, keywords in COUNTRY_KEYWORDS.items():
        score = sum(
            1
            for keyword in keywords
            if keyword in text
        )

        if score > best_score:
            best_country = country
            best_score = score


    if best_country:
        return best_country


    if domestic_country:
        return domestic_country


    return "US & Global"


# =========================================================
# TOPIC CLASSIFICATION
# =========================================================

TOPIC_KEYWORDS = {
    "Security / Military": [
        "military",
        "army",
        "missile",
        "ballistic",
        "air defense",
        "defence",
        "defense",
        "strike",
        "attack",
        "drone",
        "armed forces",
        "navy",
        "naval",
        "air force",
        "weapon",
        "weapons",
        "security forces",
        "irgc",
        "revolutionary guard",
        "mobilization",
        "militia",
        "border security",
    ],

    "Politics / Regime": [
        "president",
        "prime minister",
        "government",
        "cabinet",
        "parliament",
        "minister",
        "election",
        "elections",
        "political",
        "leadership",
        "supreme leader",
        "resigns",
        "resignation",
        "appointed",
        "appointment",
        "dismissed",
        "government formation",
        "opposition",
        "constitution",
    ],

    "Strategic Economy": [
        "oil",
        "gas",
        "currency",
        "rial",
        "inflation",
        "sanction",
        "sanctions",
        "bank",
        "central bank",
        "trade",
        "export",
        "exports",
        "import",
        "imports",
        "energy",
        "economic crisis",
        "economy",
        "budget",
        "debt",
        "market",
        "opec",
        "refinery",
        "production",
    ],

    "Internal Stability": [
        "protest",
        "protests",
        "demonstration",
        "demonstrations",
        "riot",
        "riots",
        "strike",
        "strikes",
        "unrest",
        "clashes",
        "arrest",
        "arrests",
        "detained",
        "detainees",
        "ethnic",
        "minority",
        "separatist",
        "internal security",
        "state of emergency",
    ],

    "Nuclear / Cyber / Technology": [
        "nuclear",
        "uranium",
        "enrichment",
        "centrifuge",
        "iaea",
        "cyber",
        "cyberattack",
        "cyber attack",
        "hack",
        "hacking",
        "artificial intelligence",
        "military technology",
        "satellite",
        "space program",
    ],

    "Diplomacy": [
        "diplomatic",
        "diplomacy",
        "foreign minister",
        "foreign ministry",
        "talks",
        "negotiation",
        "negotiations",
        "agreement",
        "deal",
        "summit",
        "delegation",
        "ambassador",
        "relations",
        "ceasefire",
        "truce",
    ],
}


def classify_topic(
    title,
    summary,
):
    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()

    best_topic = "General"
    best_score = 0

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(
            1
            for keyword in keywords
            if keyword in text
        )

        if score > best_score:
            best_topic = topic
            best_score = score

    return best_topic


# =========================================================
# RELEVANCE SCORING
# =========================================================
#
# 0-100
#
# הרעיון:
# לא רק "קשור לישראל".
# גם התפתחויות פנימיות משמעותיות במדינות היעד.
#
# =========================================================

NOISE_KEYWORDS = [
    "football",
    "soccer",
    "basketball",
    "tennis",
    "celebrity",
    "fashion",
    "recipe",
    "restaurant",
    "movie review",
    "film review",
    "music",
    "singer",
    "actor",
    "actress",
    "horoscope",
    "lottery",
    "travel tips",
]


HIGH_IMPACT_KEYWORDS = [
    "war",
    "attack",
    "missile",
    "strike",
    "nuclear",
    "sanctions",
    "government crisis",
    "resignation",
    "protest",
    "unrest",
    "coup",
    "election",
    "ceasefire",
    "currency collapse",
    "oil production",
    "central bank",
    "irgc",
]


def calculate_relevance_score(
    title,
    summary,
    country,
    topic,
    source_type,
):
    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()

    score = 0


    # מדינות יעד מקבלות בסיס
    if country != "US & Global":
        score += 20


    # מקור מקומי - נותן ערך להתפתחויות פנים
    if source_type == "domestic":
        score += 10


    # נושאים מבצעיים / אסטרטגיים
    topic_scores = {
        "Security / Military": 35,
        "Politics / Regime": 30,
        "Strategic Economy": 25,
        "Internal Stability": 30,
        "Nuclear / Cyber / Technology": 35,
        "Diplomacy": 20,
        "General": 0,
    }

    score += topic_scores.get(
        topic,
        0,
    )


    # מילות השפעה גבוהה
    impact_hits = sum(
        1
        for keyword in HIGH_IMPACT_KEYWORDS
        if keyword in text
    )

    score += min(
        impact_hits * 7,
        21,
    )


    # רעש
    if any(
        keyword in text
        for keyword in NOISE_KEYWORDS
    ):
        score -= 40


    # כתבה כללית בינלאומית בלי זירת יעד
    if (
        country == "US & Global"
        and topic == "General"
    ):
        score -= 20


    return max(
        0,
        min(score, 100),
    )


# =========================================================
# SHOULD INGEST?
# =========================================================

MIN_RELEVANCE_SCORE = 25


def should_ingest_article(
    relevance_score,
):
    return (
        relevance_score
        >= MIN_RELEVANCE_SCORE
    )


# =========================================================
# DEDUPLICATION
# =========================================================

def article_exists(
    cursor,
    url,
    title,
):
    cursor.execute(
        """
        SELECT id
        FROM articles
        WHERE url = ?
        LIMIT 1
        """,
        (url,),
    )

    if cursor.fetchone():
        return True


    normalized = normalize_title(
        title
    )

    if not normalized:
        return False


    cursor.execute(
        """
        SELECT title
        FROM articles
        ORDER BY id DESC
        LIMIT 500
        """
    )

    rows = cursor.fetchall()

    for row in rows:
        existing_title = normalize_title(
            row["title"]
        )

        if (
            existing_title
            and existing_title == normalized
        ):
            return True


    return False


# =========================================================
# FAST FEED DOWNLOAD
# =========================================================

def fetch_feed_xml(source):
    try:
        request = urllib.request.Request(
            source["url"],
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; OSINTGlobalDesk/2.0)"
                )
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=FETCH_TIMEOUT_SECONDS,
        ) as response:
            return (
                source,
                response.read(),
                None,
            )

    except Exception as error:
        return (
            source,
            None,
            error,
        )


# =========================================================
# LIVE INGESTION
# =========================================================

def fetch_live_web_articles():
    """
    FAST INGESTION ONLY.

    לא נכנסים לעמודי כתבות.
    לא עושים HEAD לתמונות.
    לא עושים enrichment כבד.

    המטרה:
    האפליקציה לא נתקעת.
    """

    conn = get_db_connection()
    cursor = conn.cursor()

    total_added = 0
    total_skipped_low_relevance = 0
    total_duplicate = 0


    # -----------------------------------------
    # Fetch all RSS sources concurrently
    # -----------------------------------------

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(
            len(RSS_CHANNELS),
            8,
        )
    ) as executor:

        futures = [
            executor.submit(
                fetch_feed_xml,
                source,
            )
            for source in RSS_CHANNELS
        ]

        results = [
            future.result()
            for future in futures
        ]


    # -----------------------------------------
    # Parse + insert sequentially
    # SQLite writes stay in one thread
    # -----------------------------------------

    for source, xml_data, error in results:

        if error is not None:
            print(
                f"Feed error "
                f"({source['name']}): "
                f"{error}"
            )
            continue


        try:
            root = ET.fromstring(
                xml_data
            )

        except Exception as error:
            print(
                f"XML parse error "
                f"({source['name']}): "
                f"{error}"
            )
            continue


        items = root.findall(
            ".//item"
        )

        for item in items[
            :MAX_ITEMS_PER_SOURCE
        ]:

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


            # ---------------------------------
            # TITLE
            # ---------------------------------

            title = (
                clean_html(
                    title_elem.text
                )
                if (
                    title_elem is not None
                    and title_elem.text
                )
                else "Untitled Report"
            )


            # ---------------------------------
            # URL
            # ---------------------------------

            raw_url = (
                link_elem.text.strip()
                if (
                    link_elem is not None
                    and link_elem.text
                )
                else ""
            )

            if not raw_url:
                continue


            url = normalize_url(
                raw_url
            )


            # ---------------------------------
            # DESCRIPTION
            # ---------------------------------

            raw_description = (
                description_elem.text
                if (
                    description_elem
                    is not None
                    and description_elem.text
                )
                else ""
            )


            summary = clean_html(
                raw_description
            )


            if not summary:
                summary = title


            summary = summary[:500]


            # ---------------------------------
            # DUPLICATES
            # ---------------------------------

            if article_exists(
                cursor,
                url,
                title,
            ):
                total_duplicate += 1
                continue


            # ---------------------------------
            # COUNTRY
            # ---------------------------------

            country = classify_country(
                title,
                summary,
                source.get(
                    "domestic_country"
                ),
            )


            # ---------------------------------
            # TOPIC
            # ---------------------------------

            topic = classify_topic(
                title,
                summary,
            )


            # ---------------------------------
            # RELEVANCE
            # ---------------------------------

            relevance_score = (
                calculate_relevance_score(
                    title=title,
                    summary=summary,
                    country=country,
                    topic=topic,
                    source_type=source[
                        "source_type"
                    ],
                )
            )


            if not should_ingest_article(
                relevance_score
            ):
                total_skipped_low_relevance += 1
                continue


            # ---------------------------------
            # IMAGE
            # ---------------------------------
            #
            # רק מה-RSS.
            # בלי פתיחת article page.
            #
            # ---------------------------------

            image_url = extract_feed_image(
                item,
                raw_description,
            )


            # ---------------------------------
            # DATES
            # ---------------------------------

            published_at = parse_rss_date(
                pub_date_elem
            )

            created_at = utc_now_iso()


            # ---------------------------------
            # CONTENT
            # ---------------------------------

            full_content = summary


            # ---------------------------------
            # INSERT
            # ---------------------------------

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
                    (
                        "Domestic RSS"
                        if source[
                            "source_type"
                        ] == "domestic"
                        else "International RSS"
                    ),
                    published_at,
                    image_url,
                    topic,
                    relevance_score,
                    created_at,
                ),
            )


            if cursor.rowcount > 0:
                total_added += 1


        conn.commit()


    print(
        "RSS sync finished | "
        f"new={total_added} | "
        f"duplicates={total_duplicate} | "
        f"low_relevance="
        f"{total_skipped_low_relevance}"
    )

    return total_added