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

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def extract_real_image(item, raw_description, article_url=None):
    """
    Try to find the real article image from:
    1. RSS media tags
    2. enclosure
    3. image inside RSS description
    4. article page og:image
    5. fallback image
    """

    # 1. RSS media tags
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


    # 2. Image inside description
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


    # 3. Try article OG image
    if article_url:
        try:
            req = urllib.request.Request(
                article_url,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            with urllib.request.urlopen(
                req,
                timeout=5
            ) as response:
                page_html = response.read().decode(
                    "utf-8",
                    errors="ignore"
                )

            og_patterns = [
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            ]

            for pattern in og_patterns:
                match = re.search(
                    pattern,
                    page_html,
                    flags=re.IGNORECASE
                )

                if match:
                    return html.unescape(
                        match.group(1)
                    )

        except Exception as e:
            print(
                f"Image extraction failed "
                f"for {article_url}: {e}"
            )


    # 4. Final fallback
    return (
        "https://images.unsplash.com/"
        "photo-1504711434969-e33886168f5c?w=1200"
    )

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