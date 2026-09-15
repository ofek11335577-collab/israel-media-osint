# ingestion/fetcher.py
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import email.utils
from database import get_db_connection
import re

# פידים ישירים ופתוחים שאינם נחסמים בשרתי ענן
DIRECT_RSS_FEEDS = [
    {"name": "BBC Middle East", "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"},
    {"name": "Al Jazeera English", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "The Guardian Middle East", "url": "https://www.theguardian.com/world/middleeast/rss"}
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

    # לפעמים RSS מכיל encoding כפול:
    # &amp;#039; -> &#039; -> '
    for _ in range(2):
        text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()

def extract_real_image(item, raw_description, article_url=None):

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

        enclosure_url = enclosure.get("url", "")
        enclosure_type = enclosure.get("type", "")

        if (
            enclosure_url
            and (
                enclosure_type.startswith("image/")
                or any(
                    ext in enclosure_url.lower()
                    for ext in [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                    ]
                )
            )
        ):
            return html.unescape(enclosure_url)


    # 4. image embedded in RSS description
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


    # 5. Open the actual article and look for OG image
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

                page_html = response.read().decode(
                    "utf-8",
                    errors="ignore",
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
                        image_url = "https:" + image_url

                    return image_url


        except Exception as e:

            print(
                f"OG image error "
                f"({article_url}): {e}"
            )


    return DEFAULT_IMAGE
def parse_rss_date(pub_date_elem):
    if pub_date_elem is not None and pub_date_elem.text:
        try:
            parsed_tuple = email.utils.parsedate_tz(pub_date_elem.text)
            if parsed_tuple:
                dt = datetime.fromtimestamp(email.utils.mktime_tz(parsed_tuple))
                return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M")

def fetch_live_web_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
    """
    SELECT id, image_url
    FROM articles
    WHERE url = ?
    LIMIT 1
    """,
    (url,)
)

    existing_article = cursor.fetchone()
    if existing_article:

    current_image = (
        existing_article["image_url"] or ""
    )

    # לנסות לתקן רק כתבות שיש להן
    # fallback או שאין להן תמונה בכלל
    if (
        not current_image
        or current_image == DEFAULT_IMAGE
        or "photo-1504711434969-e33886168f5c" in current_image
    ):

        better_image = extract_real_image(
            item,
            raw_description,
            url,
        )

        if (
            better_image
            and better_image != DEFAULT_IMAGE
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

    # הכתבה עצמה כבר קיימת,
    # אז לא מוסיפים אותה שוב
    continue



image_url = extract_real_image(
    item,
    raw_description,
    url,
)
    
    total_added = 0
    for feed in DIRECT_RSS_FEEDS:
        try:
            req = urllib.request.Request(
                feed['url'], 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                items = root.findall('.//item')
                for idx, item in enumerate(items[:15]):
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    desc_elem = item.find('description')
                    
                    title = title_elem.text if title_elem is not None else "Breaking Intelligence Report"
                    url = link_elem.text if link_elem is not None else "https://www.bbc.com"
                    published_at = parse_rss_date(pub_date_elem)
                    
                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    summary = clean_html(raw_desc)[:250] if raw_desc else title
                    full_content = f"Live verified intelligence report from {feed['name']}:\n\n{clean_html(raw_desc)}\n\n[Source URL: {url}]"
                    
                    image_url = extract_real_image(item,raw_description,url)

                    # סיווג גיאוגרפי אוטומטי לפי מילות מפתח בכותרת
                    country = "US & Global"
                    t_low = title.lower()
                    if any(k in t_low for k in ['iran', 'tehran', 'persian']): country = "Iran"
                    elif any(k in t_low for k in ['saudi', 'riyadh', 'aramco']): country = "Saudi Arabia"
                    elif any(k in t_low for k in ['uae', 'dubai', 'abu dhabi', 'emirates']): country = "UAE"
                    elif any(k in t_low for k in ['yemen', 'houthi', 'sana\'a']): country = "Yemen"
                    elif any(k in t_low for k in ['syria', 'damascus', 'aleppo']): country = "Syria"
                    elif any(k in t_low for k in ['iraq', 'baghdad', 'kurdistan']): country = "Iraq"
                    elif any(k in t_low for k in ['gaza', 'palestin', 'west bank', 'ramallah', 'hamas']): country = "Gaza & WB"

                    cursor.execute('''
                        INSERT OR IGNORE INTO articles 
                        (url, source_name, country, title, summary, full_content, analyst_name, published_at, image_url, sentiment, priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        url,
                        f"{feed['name']} [LIVE]",
                        country,
                        title,
                        summary,
                        full_content,
                        "Live RSS Ingestor",
                        published_at,
                        image_url,
                        "Active Feed",
                        10
                    ))
                    if cursor.rowcount > 0:
                        total_added += 1
            conn.commit()
        except Exception as e:
            print(f"Error fetching RSS feed {feed['name']}: {e}")
            
    return total_added