# ingestion/fetcher.py
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from database import get_db_connection
import re

# מנועי חיפוש ופידים חיים לכל זירה ברשת
LIVE_RSS_CHANNELS = [
    {"country": "Iran", "query": "Iran military politics news"},
    {"country": "Saudi Arabia", "query": "Saudi Arabia economy defense news"},
    {"country": "UAE", "query": "UAE Dubai business tech news"},
    {"country": "Yemen", "query": "Yemen conflict humanitarian news"},
    {"country": "Syria", "query": "Syria updates Damascus news"},
    {"country": "Iraq", "query": "Iraq security energy news"},
    {"country": "Gaza & WB", "query": "Gaza Palestine humanitarian news"},
    {"country": "US & Global", "query": "Middle East US foreign policy Reuters"}
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

def fetch_live_web_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_added = 0
    for channel in LIVE_RSS_CHANNELS:
        try:
            encoded_query = urllib.parse.quote(channel['query'])
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                items = root.findall('.//item')
                for idx, item in enumerate(items[:10]): # שולב 10 כתבות חיות לכל זירה בכל סנכרון
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    source_elem = item.find('source')
                    desc_elem = item.find('description')
                    
                    title = title_elem.text if title_elem is not None else "Breaking Intelligence Report"
                    url = link_elem.text if link_elem is not None else "https://news.google.com"
                    published_at = pub_date_elem.text[:16] if pub_date_elem is not None else datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                    source_name = source_elem.text if source_elem is not None else "Live Web Wire"
                    
                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    summary = clean_html(raw_desc)[:250] if raw_desc else title
                    full_content = f"Live intelligence wire report extracted from {source_name}:\n\n{clean_html(raw_desc)}\n\n[Original Source Link: {url}]"
                    
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
                        "Global Web Crawler",
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
            
    print(f"Successfully ingested {total_added} new live articles from the internet.")