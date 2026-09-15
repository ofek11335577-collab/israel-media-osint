# ingestion/fetcher.py
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from database import get_db_connection
import re

# פידים ישירים ויציבים מסוכנויות מובילות (ללא קישורים עקיפים שנופלים)
DIRECT_RSS_CHANNELS = [
    {"name": "Reuters World", "url": "https://www.reuters.com/arc/outboundfeeds/v1/output/rss/?outputType=xml", "country": "US & Global"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "country": "US & Global"},
    {"name": "BBC Middle East", "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "country": "US & Global"},
]

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_context_image(title, index):
    title_lower = title.lower()
    pools = [
        "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=1200",
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200",
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1200"
    ]
    return pools[index % len(pools)]

def fetch_live_web_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for source in DIRECT_RSS_CHANNELS:
        try:
            req = urllib.request.Request(source['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                for idx, item in enumerate(root.findall('.//item')[:15]):
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    desc_elem = item.find('description')
                    
                    title = title_elem.text if title_elem is not None else "Breaking Intelligence Report"
                    url = link_elem.text if link_elem is not None else "https://www.reuters.com"
                    published_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M") # תאריך אחיד ומדויק למיון מושלם
                    
                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    summary = clean_html(raw_desc)[:250] if raw_desc else title
                    full_content = f"Live verified report from {source['name']}:\n\n{clean_html(raw_desc)}\n\n[Direct Link: {url}]"
                    
                    image_url = get_context_image(title, idx)
                    
                    # זיהוי אוטומטי של אזור לפי מילות מפתח בכותרת
                    country = "US & Global"
                    t_low = title.lower()
                    if any(k in t_low for k in ['iran', 'tehran']): country = "Iran"
                    elif any(k in t_low for k in ['saudi', 'riyadh']): country = "Saudi Arabia"
                    elif any(k in t_low for k in ['uae', 'dubai', 'abu dhabi']): country = "UAE"
                    elif any(k in t_low for k in ['yemen', 'houthi']): country = "Yemen"
                    elif any(k in t_low for k in ['syria', 'damascus']): country = "Syria"
                    elif any(k in t_low for k in ['iraq', 'baghdad']): country = "Iraq"
                    elif any(k in t_low for k in ['gaza', 'palestin', 'west bank', 'ramallah']): country = "Gaza & WB"

                    cursor.execute('''
                        INSERT OR IGNORE INTO articles 
                        (url, source_name, country, title, summary, full_content, analyst_name, published_at, image_url, sentiment, priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        url,
                        f"{source['name']} [DIRECT]",
                        country,
                        title,
                        summary,
                        full_content,
                        "Live Direct Wire",
                        published_at,
                        image_url,
                        "Active Feed",
                        10
                    ))
            conn.commit()
        except Exception as e:
            print(f"Feed error ({source['name']}): {e}")