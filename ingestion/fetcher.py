# ingestion/fetcher.py

import email.utils
import html
import re
import urllib.request
import xml.etree.ElementTree as ET

from datetime import timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

from database import get_db_connection, utc_now_iso


# =========================================================
# RSS SOURCES
# =========================================================

DIRECT_RSS_CHANNELS = [
    {
        "name": "Reuters World",
        "url": "https://www.reuters.com/arc/outboundfeeds/v1/output/rss/?outputType=xml",
        "country": "US & Global",
    },
    {
        "name": "Al Jazeera English",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "country": "US & Global",
    },
    {
        "name": "BBC Middle East",
        "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "country": "US & Global",
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
    if not raw_html:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        raw_html,
    )

    # RSS sometimes contains double-encoded entities
    for _ in range(2):
        text = html.unescape(text)

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
# DATE PARSING
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
# IMAGE VALIDATION
# =========================================================

def is_valid_image_url(image_url):
    if not image_url:
        return False

    try:
        request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                )
            },
            method="HEAD",
        )

        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:

            content_type = response.headers.get(
                "Content-Type",
                ""
            ).lower()

            return content_type.startswith(
                "image/"
            )

    except Exception:
        return False


def prepare_image_url(
    image_url,
    article_url,
):
    if not image_url:
        return None

    image_url = html.unescape(
        image_url.strip()
    )

    if image_url.startswith("//"):
        image_url = "https:" + image_url

    elif image_url.startswith("/"):
        image_url = urljoin(
            article_url,
            image_url,
        )

    elif not image_url.startswith(
        ("http://", "https://")
    ):
        image_url = urljoin(
            article_url,
            image_url,
        )

    if is_valid_image_url(
        image_url
    ):
        return image_url

    return None


# =========================================================
# IMAGE EXTRACTION
# =========================================================

def extract_real_image(
    item,
    raw_description,
    article_url=None,
):
    candidates = []


    # 1. media:content
    media_content = item.find(
        "{http://search.yahoo.com/mrss/}content"
    )

    if media_content is not None:
        candidate = media_content.get(
            "url"
        )

        if candidate:
            candidates.append(
                candidate
            )


    # 2. media:thumbnail
    media_thumbnail = item.find(
        "{http://search.yahoo.com/mrss/}thumbnail"
    )

    if media_thumbnail is not None:
        candidate = media_thumbnail.get(
            "url"
        )

        if candidate:
            candidates.append(
                candidate
            )


    # 3. enclosure
    enclosure = item.find(
        "enclosure"
    )

    if enclosure is not None:
        candidate = enclosure.get(
            "url"
        )

        if candidate:
            candidates.append(
                candidate
            )


    # 4. image inside RSS description
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


    # 5. og:image / twitter:image from article page
    if article_url:
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
                    )
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=6,
            ) as response:

                page_html = (
                    response
                    .read()
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

                if match:
                    candidates.append(
                        match.group(1)
                    )

        except Exception as e:
            print(
                f"Article image scan failed "
                f"({article_url}): {e}"
            )


    # Validate all candidates
    for candidate in candidates:
        valid_image = prepare_image_url(
            candidate,
            article_url or "",
        )

        if valid_image:
            return valid_image


    return DEFAULT_IMAGE


# =========================================================
# CLASSIFICATION
# =========================================================

def classify_country(
    title,
    summary="",
):
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


def classify_topic(
    title,
    summary="",
):
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
            "bond",
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
# FETCH PIPELINE
# =========================================================

def fetch_live_web_articles():
    conn = get_db_connection()
    cursor = conn.cursor()

    total_added = 0
    total_images_updated = 0

    for source in DIRECT_RSS_CHANNELS:
        try:
            request = urllib.request.Request(
                source["url"],
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; OSINTGlobalDesk/1.0)"
                    )
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=10,
            ) as response:
                xml_data = response.read()

            root = ET.fromstring(
                xml_data
            )

            for item in root.findall(
                ".//item"
            )[:25]:

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

                if not raw_url:
                    continue


                url = normalize_url(
                    raw_url
                )


                raw_description = (
                    description_elem.text
                    if (
                        description_elem is not None
                        and description_elem.text
                    )
                    else ""
                )


                clean_description = clean_html(
                    raw_description
                )


                # -----------------------------------------
                # Existing article check
                # -----------------------------------------

                cursor.execute(
                    """
                    SELECT id, image_url
                    FROM articles
                    WHERE url = ?
                    LIMIT 1
                    """,
                    (url,),
                )

                existing_article = (
                    cursor.fetchone()
                )


                # -----------------------------------------
                # Existing article:
                # repair image if needed
                # -----------------------------------------

                if existing_article:
                    current_image = (
                        existing_article["image_url"]
                        or ""
                    )

                    image_needs_repair = (
                        not current_image
                        or current_image == DEFAULT_IMAGE
                        or not is_valid_image_url(
                            current_image
                        )
                    )

                    if image_needs_repair:
                        better_image = (
                            extract_real_image(
                                item,
                                raw_description,
                                url,
                            )
                        )

                        cursor.execute(
                            """
                            UPDATE articles
                            SET image_url = ?
                            WHERE id = ?
                            """,
                            (
                                better_image,
                                existing_article["id"],
                            ),
                        )

                        total_images_updated += 1

                    continue


                # -----------------------------------------
                # New article
                # -----------------------------------------

                published_at = parse_rss_date(
                    pub_date_elem
                )

                created_at = utc_now_iso()


                summary = (
                    clean_description[:400]
                    if clean_description
                    else title
                )


                full_content = (
                    clean_description
                    if clean_description
                    else summary
                )


                image_url = extract_real_image(
                    item,
                    raw_description,
                    url,
                )


                country = classify_country(
                    title,
                    summary,
                )


                topic = classify_topic(
                    title,
                    summary,
                )


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
                    ),
                )


                if cursor.rowcount > 0:
                    total_added += 1


            conn.commit()


        except Exception as e:
            print(
                f"Feed error "
                f"({source['name']}): "
                f"{e}"
            )


    print(
        f"RSS sync finished: "
        f"{total_added} new articles, "
        f"{total_images_updated} images updated."
    )

    return total_added