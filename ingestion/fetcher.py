# ingestion/fetcher.py

import email.utils
import html
import re
import urllib.request
import xml.etree.ElementTree as ET

from datetime import timezone
from urllib.parse import urlsplit, urlunsplit

from database import get_db_connection, utc_now_iso


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


def clean_html(raw_html):
    if not raw_html:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        raw_html,
    )

    # לפעמים RSS מגיע עם encoding כפול
    for _ in range(2):
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


def normalize_title(title):
    if not title:
        return ""

    normalized = title.lower()

    normalized = re.sub(
        r"[^\w\s]",
        "",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


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


def extract_real_image(
    item,
    raw_description,
    article_url=None,
):
    # 1. media:content
    media_content = item.find(
        "{http://search.yahoo.com/mrss/}content"
    )

    if media_content is not None:
        image_url = media_content.get("url")

        if image_url:
            return html.unescape(image_url)


    # 2. media:thumbnail
    media_thumbnail = item.find(
        "{http://search.yahoo.com/mrss/}thumbnail"
    )

    if media_thumbnail is not None:
        image_url = media_thumbnail.get("url")

        if image_url:
            return html.unescape(image_url)


    # 3. enclosure
    enclosure = item.find("enclosure")

    if enclosure is not None:
        enclosure_url = enclosure.get(
            "url",
            "",
        )

        enclosure_type = enclosure.get(
            "type",
            "",
        )

        if (
            enclosure_url
            and (
                enclosure_type.startswith("image/")
                or any(
                    extension in enclosure_url.lower()
                    for extension in [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                    ]
                )
            )
        ):
            return html.unescape(
                enclosure_url
            )


    # 4. image בתוך description
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
                return html.unescape(
                    match.group(1)
                )


    # 5. ניסיון לשלוף og:image מדף הכתבה
    if article_url:
        try:
            req = urllib.request.Request(
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
                req,
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
                    image_url = html.unescape(
                        match.group(1)
                    )

                    if image_url.startswith("//"):
                        image_url = (
                            "https:" + image_url
                        )

                    return image_url

        except Exception as e:
            print(
                f"OG image error "
                f"({article_url}): {e}"
            )

    return DEFAULT_IMAGE


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


                # =========================================
                # בדיקה אם הכתבה כבר קיימת
                # =========================================

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


                # =========================================
                # אם קיימת:
                # לא מוסיפים שוב,
                # אבל כן מנסים לשפר תמונת fallback
                # =========================================

                if existing_article:
                    current_image = (
                        existing_article["image_url"]
                        or ""
                    )

                    if (
                        not current_image
                        or current_image == DEFAULT_IMAGE
                        or (
                            "photo-1504711434969"
                            in current_image
                        )
                    ):

                        better_image = (
                            extract_real_image(
                                item,
                                raw_description,
                                url,
                            )
                        )

                        if (
                            better_image
                            and better_image
                            != DEFAULT_IMAGE
                        ):
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


                # =========================================
                # כתבה חדשה
                # =========================================

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