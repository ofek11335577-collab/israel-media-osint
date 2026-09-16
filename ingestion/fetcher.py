# ingestion/fetcher.py

import concurrent.futures
import email.utils
import html
import re
import urllib.request
import xml.etree.ElementTree as ET

from datetime import timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

from database import get_db_connection, utc_now_iso


# =========================================================
# CONFIG
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
    {
        "name": "IRNA English",
        "url": "https://en.irna.ir/rss",
        "source_type": "domestic",
        "domestic_country": "Iran",
    },
    {
        "name": "Saudi Press Agency",
        "url": "https://www.spa.gov.sa/rss.xml",
        "source_type": "domestic",
        "domestic_country": "Saudi Arabia",
    },
    {
        "name": "SANA English",
        "url": "https://www.sana.sy/en/syria/feed/",
        "source_type": "domestic",
        "domestic_country": "Syria",
    },
]


RSS_TIMEOUT = 6
ARTICLE_TIMEOUT = 4
MAX_ITEMS_PER_SOURCE = 30

# כדי שתמונות לא יתקעו את האתר:
MAX_IMAGE_ENRICHMENTS_PER_SYNC = 12
IMAGE_WORKERS = 6

MIN_RELEVANCE_SCORE = 30


# =========================================================
# CLEANING
# =========================================================

def clean_html(raw_html):
    if not raw_html:
        return ""

    text = raw_html

    for _ in range(2):
        text = html.unescape(text)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def normalize_url(url):
    if not url:
        return ""

    try:
        parts = urlsplit(url.strip())

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
        return url.strip()


def normalize_title(title):
    if not title:
        return ""

    text = html.unescape(title).lower()

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# =========================================================
# DATES
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
# NOISE / SPORTS FILTER
# =========================================================

SPORTS_KEYWORDS = [
    "football",
    "soccer",
    "premier league",
    "champions league",
    "europa league",
    "world cup",
    "stadium",
    "var ",
    " var",
    "match",
    "fixture",
    "goalkeeper",
    "striker",
    "midfielder",
    "coach",
    "manager",
    "fans",
    "penalty",
    "red card",
    "yellow card",

    # common clubs / competitions
    "manchester united",
    "manchester city",
    "chelsea",
    "arsenal",
    "liverpool",
    "tottenham",
    "real madrid",
    "barcelona",
    "psg",
    "bayern",
    "serie a",
    "la liga",
    "bundesliga",
]


OTHER_NOISE_KEYWORDS = [
    "celebrity",
    "fashion",
    "recipe",
    "restaurant review",
    "movie review",
    "film review",
    "album review",
    "music festival",
    "horoscope",
    "lottery",
    "travel tips",
]


def is_noise_article(title, summary):
    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()

    if any(
        keyword in text
        for keyword in SPORTS_KEYWORDS
    ):
        return True

    if any(
        keyword in text
        for keyword in OTHER_NOISE_KEYWORDS
    ):
        return True

    return False


# =========================================================
# COUNTRY CLASSIFICATION
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
        "bin salman",
        "mohammed bin salman",
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

    best_country = None
    best_score = 0

    for country, keywords in COUNTRY_KEYWORDS.items():

        score = sum(
            1
            for keyword in keywords
            if keyword in text
        )

        if score > best_score:
            best_score = score
            best_country = country

    if best_country:
        return best_country

    if domestic_country:
        return domestic_country

    return "US & Global"


# =========================================================
# TOPICS
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
        "airstrike",
        "air strike",
        "drone",
        "armed forces",
        "navy",
        "naval",
        "weapon",
        "weapons",
        "security forces",
        "irgc",
        "revolutionary guard",
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
        "resignation",
        "resigns",
        "appointed",
        "appointment",
        "dismissed",
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
        "central bank",
        "trade",
        "exports",
        "imports",
        "energy",
        "economic crisis",
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
        "unrest",
        "clashes",
        "arrest",
        "arrests",
        "detained",
        "ethnic",
        "minority",
        "separatist",
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
        "hacking",
        "military technology",
        "satellite",
        "space program",
    ],

    "Diplomacy": [
        "diplomatic",
        "diplomacy",
        "foreign minister",
        "foreign ministry",
        "negotiation",
        "negotiations",
        "agreement",
        "summit",
        "delegation",
        "ambassador",
        "relations",
        "ceasefire",
        "truce",
    ],
}


def classify_topic(title, summary):
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
            best_score = score
            best_topic = topic

    return best_topic


# =========================================================
# RELEVANCE
# =========================================================

HIGH_IMPACT_KEYWORDS = [
    "war",
    "attack",
    "missile",
    "airstrike",
    "nuclear",
    "sanctions",
    "government crisis",
    "resignation",
    "protest",
    "unrest",
    "coup",
    "election",
    "ceasefire",
    "currency crisis",
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

    if country != "US & Global":
        score += 20

    if source_type == "domestic":
        score += 10

    topic_scores = {
        "Security / Military": 40,
        "Politics / Regime": 32,
        "Strategic Economy": 27,
        "Internal Stability": 35,
        "Nuclear / Cyber / Technology": 38,
        "Diplomacy": 25,
        "General": 0,
    }

    score += topic_scores.get(
        topic,
        0,
    )

    impact_hits = sum(
        1
        for keyword in HIGH_IMPACT_KEYWORDS
        if keyword in text
    )

    score += min(
        impact_hits * 6,
        18,
    )

    if (
        country == "US & Global"
        and topic == "General"
    ):
        score -= 30

    return max(
        0,
        min(score, 100),
    )


# =========================================================
# RSS IMAGE
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
# ORIGINAL ARTICLE IMAGE
# =========================================================
#
# מופעל רק על מספר קטן של כתבות בכל Sync.
# לכן לא אמור לתקוע שוב את האתר.
#
# =========================================================

def extract_original_article_image(article_url):
    if not article_url:
        return None

    try:
        request = urllib.request.Request(
            article_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
                # לרוב המטא-תגים נמצאים בתחילת העמוד
                "Range": "bytes=0-350000",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=ARTICLE_TIMEOUT,
        ) as response:

            page_html = (
                response.read()
                .decode(
                    "utf-8",
                    errors="ignore",
                )
            )


        patterns = [
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',

            r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
        ]


        for pattern in patterns:

            match = re.search(
                pattern,
                page_html,
                flags=re.IGNORECASE,
            )

            if not match:
                continue


            image_url = html.unescape(
                match.group(1).strip()
            )


            if image_url.startswith("//"):
                image_url = (
                    "https:" + image_url
                )

            elif image_url.startswith("/"):
                image_url = urljoin(
                    article_url,
                    image_url,
                )


            if image_url.startswith(
                ("http://", "https://")
            ):
                return image_url


    except Exception as error:
        print(
            f"Image enrichment error "
            f"({article_url}): {error}"
        )


    return None


# =========================================================
# DEDUP
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


    normalized_title = normalize_title(
        title
    )

    if not normalized_title:
        return False


    cursor.execute(
        """
        SELECT title
        FROM articles
        ORDER BY id DESC
        LIMIT 500
        """
    )


    for row in cursor.fetchall():

        existing = normalize_title(
            row["title"]
        )

        if (
            existing
            and existing == normalized_title
        ):
            return True


    return False


# =========================================================
# RSS DOWNLOAD
# =========================================================

def fetch_feed_xml(source):
    try:
        request = urllib.request.Request(
            source["url"],
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; OSINTGlobalDesk/3.0)"
                )
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=RSS_TIMEOUT,
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
# IMAGE ENRICHMENT
# =========================================================

def enrich_missing_images(
    conn,
    articles_to_enrich,
):
    if not articles_to_enrich:
        return 0


    articles_to_enrich = (
        articles_to_enrich[
            :MAX_IMAGE_ENRICHMENTS_PER_SYNC
        ]
    )


    updates = []


    with concurrent.futures.ThreadPoolExecutor(
        max_workers=IMAGE_WORKERS
    ) as executor:

        future_map = {
            executor.submit(
                extract_original_article_image,
                article["url"],
            ): article

            for article
            in articles_to_enrich
        }


        for future in concurrent.futures.as_completed(
            future_map
        ):

            article = future_map[future]

            try:
                image_url = future.result()

                if image_url:

                    updates.append(
                        (
                            image_url,
                            article["id"],
                        )
                    )

            except Exception:
                pass


    if not updates:
        return 0


    cursor = conn.cursor()

    cursor.executemany(
        """
        UPDATE articles
        SET image_url = ?
        WHERE id = ?
        """,
        updates,
    )

    conn.commit()

    return len(updates)


# =========================================================
# MAIN INGESTION
# =========================================================

def fetch_live_web_articles():
    conn = get_db_connection()
    cursor = conn.cursor()

    total_added = 0
    total_duplicates = 0
    total_noise = 0
    total_low_relevance = 0

    needs_image_enrichment = []


    # -----------------------------------------
    # Fetch all RSS concurrently
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

        feed_results = [
            future.result()
            for future in futures
        ]


    # -----------------------------------------
    # Parse feeds
    # -----------------------------------------

    for (
        source,
        xml_data,
        feed_error,
    ) in feed_results:

        if feed_error is not None:

            print(
                f"Feed error "
                f"({source['name']}): "
                f"{feed_error}"
            )

            continue


        try:
            root = ET.fromstring(
                xml_data
            )

        except Exception as error:

            print(
                f"XML error "
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
                else ""
            )

            if not title:
                continue


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
                    description_elem is not None
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
            # SPORT / NOISE FILTER
            # ---------------------------------

            if is_noise_article(
                title,
                summary,
            ):
                total_noise += 1
                continue


            # ---------------------------------
            # DUPLICATES
            # ---------------------------------

            if article_exists(
                cursor,
                url,
                title,
            ):
                total_duplicates += 1
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
            # RELEVANCE SCORE
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


            if (
                relevance_score
                < MIN_RELEVANCE_SCORE
            ):
                total_low_relevance += 1
                continue


            # ---------------------------------
            # RSS IMAGE
            # ---------------------------------

            image_url = extract_feed_image(
                item,
                raw_description,
            )


            # ---------------------------------
            # TIME
            # ---------------------------------

            published_at = parse_rss_date(
                pub_date_elem
            )

            created_at = utc_now_iso()


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
                    summary,

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

                article_id = (
                    cursor.lastrowid
                )

                total_added += 1


                # רק כתבות בלי RSS image
                # מועברות ל-enrichment

                if not image_url:

                    needs_image_enrichment.append(
                        {
                            "id": article_id,
                            "url": url,
                        }
                    )


        conn.commit()


    # =====================================================
    # BACKFILL OLD ARTICLES WITHOUT IMAGES
    # =====================================================
    #
    # כך גם הכתבות שכבר במסד יקבלו
    # בהדרגה תמונה מהמקור.
    #
    # =====================================================

    remaining_slots = (
        MAX_IMAGE_ENRICHMENTS_PER_SYNC
        - len(needs_image_enrichment)
    )


    if remaining_slots > 0:

        cursor.execute(
            """
            SELECT id, url
            FROM articles
            WHERE
                image_url IS NULL
                OR image_url = ''
            ORDER BY id DESC
            LIMIT ?
            """,
            (remaining_slots,),
        )


        existing_missing = (
            cursor.fetchall()
        )


        already_queued = {
            item["id"]
            for item
            in needs_image_enrichment
        }


        for row in existing_missing:

            if row["id"] in already_queued:
                continue

            needs_image_enrichment.append(
                {
                    "id": row["id"],
                    "url": row["url"],
                }
            )


    images_updated = enrich_missing_images(
        conn,
        needs_image_enrichment,
    )


    print(
        "RSS sync complete | "
        f"new={total_added} | "
        f"duplicates={total_duplicates} | "
        f"sports/noise={total_noise} | "
        f"low_relevance={total_low_relevance} | "
        f"images_updated={images_updated}"
    )


    return total_added