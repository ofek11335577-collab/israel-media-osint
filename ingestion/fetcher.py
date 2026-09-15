# ingestion/fetcher.py
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import email.utils
from database import get_db_connection
import re

# שאילתות חיפוש חיות לכל זירה - יציבות לחלוטין ועוקפות חסימות ענן
ZONE_RSS_QUERIES = [
    {"country": "Iran", "query": "Iran military defense nuclear news"},
    {"country": "Saudi Arabia", "query": "Saudi Arabia economy oil defense news"},
    {"country": "UAE", "query": "UAE Dubai tech business news"},
    {"country": "Yemen", "query": "Yemen conflict humanitarian news"},
    {"country": "Syria", "query": "Syria updates Damascus military news"},
    {"country": "Iraq", "query": "Iraq security energy Baghdad news"},
    {"country": "Gaza & WB", "query": "Gaza Palestine humanitarian West Bank news"},
    {"country": "US & Global", "query": "Middle East US foreign policy diplomacy news"}
]

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_context_image(title, index):
    title_lower = title.lower()
    military_pool = [
        "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=1200",
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1200",
        "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1200"
    ]
    economy_pool = [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200"
    ]
    tech_pool = [
        "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1200",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200"
    ]
    diplomacy_pool = [
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200",
        "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=1200",
        "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=1200"
    ]
    humanitarian_pool = [
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1200",
        "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1200",
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200"
    ]
    
    if any(k in title_lower for k in ['military', 'defense', 'missile', 'security', 'naval', 'forces', 'army', 'strike']):
        pool = military_pool
    elif any(k in title_lower for k in ['economy', 'trade', 'market', 'oil', 'bank', 'financial', 'vision']):
        pool = economy_pool
    elif any(k in title_lower for k in ['ai', 'tech', 'digital', 'innovation', 'summit', 'cyber']):
        pool = tech_pool
    elif any(k in title_lower for k in ['un', 'diplomat', 'talks', 'minister', 'council', 'agreement']):
        pool = diplomacy_pool
    else:
        pool = humanitarian_pool
    return pool[index % len(pool)]

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
    for channel in ZONE_RSS_QUERIES:
        try:
            encoded_query = urllib.parse.quote(channel['query'])
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            req = urllib.request.Request(
                rss_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                items = root.findall('.//item')
                for idx, item in enumerate(items[:10]):
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    source_elem = item.find('source')
                    desc_elem = item.find('description')
                    
                    title = title_elem.text if title_elem is not None else "Breaking Intelligence Report"
                    url = link_elem.text if link_elem is not None else "https://news.google.com"
                    published_at = parse_rss_date(pub_date_elem)
                    source_name = source_elem.text if source_elem is not None else "Live News Wire"
                    
                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    summary = clean_html(raw_desc)[:250] if raw_desc else title
                    full_content = f"Live verified intelligence feed from {source_name}:\n\n{clean_html(raw_desc)}\n\n[Source URL: {url}]"
                    
                    image_url = get_context_image(title, idx)
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO articles 
                        (url, source_name, country, title, summary, full_content, analyst_name, published_at, image_url, sentiment, priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        url,
                        f"{source_name} [LIVE]",
                        channel['country'],
                        title,
                        summary,
                        full_content,
                        "Live Web Crawler",
                        published_at,
                        image_url,
                        "Active Feed",
                        10
                    ))
                    if cursor.rowcount > 0:
                        total_added += 1
            conn.commit()
        except Exception as e:
            print(f"Error fetching live feed for {channel['country']}: {e}")
            
    return total_added