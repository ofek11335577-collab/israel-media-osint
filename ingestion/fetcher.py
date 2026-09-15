# ingestion/fetcher.py
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from database import get_db_connection
from services.translator import translate_to_hebrew
import re

# שאילתות חיפוש חיות ב-Google News לכל זירה ומדינה (מושך כתבות אמת בזמן אמת)
RSS_SOURCES = [
    {"name": "Google News (Iran)", "query": "Iran military politics", "country": "איראן"},
    {"name": "Google News (Saudi Arabia)", "query": "Saudi Arabia news", "country": "סעודיה"},
    {"name": "Google News (UAE)", "query": "UAE Dubai business news", "country": "איחוד האמירויות"},
    {"name": "Google News (Yemen)", "query": "Yemen conflict news", "country": "תימן"},
    {"name": "Google News (Syria)", "query": "Syria updates", "country": "סוריה"},
    {"name": "Google News (Iraq)", "query": "Iraq security news", "country": "עיראק"},
    {"name": "Google News (Gaza/Palestine)", "query": "Gaza Palestine news", "country": "רצועת עזה"},
    {"name": "Google News (Middle East)", "query": "Middle East politics US", "country": "ארה\"ב"}
]

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def extract_image_from_item(item, description_text):
    for tag in ['{http://search.yahoo.com/mrss/}content', '{http://search.yahoo.com/mrss/}thumbnail', 'enclosure']:
        media = item.find(tag)
        if media is not None and media.get('url'):
            return media.get('url')
    if description_text:
        img_match = re.search(r'<img[^>]+src="([^">]+)"', description_text)
        if img_match:
            return img_match.group(1)
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200"

def ingest_live_feeds():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for source in RSS_SOURCES:
        try:
            encoded_query = urllib.parse.quote(source['query'])
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                for item in root.findall('.//item')[:4]: # 4 כתבות חיות לכל קטגוריה
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    source_elem = item.find('source')
                    desc_elem = item.find('description')
                    
                    title_en = title_elem.text if title_elem is not None else "Breaking Intelligence Report"
                    link = link_elem.text if link_elem is not None else "https://news.google.com"
                    pub_at = pub_date_elem.text if pub_date_elem is not None else datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    # זיהוי שם המקור המקורי (למשל Reuters, Al Jazeera וכו')
                    real_source_name = source_elem.text if source_elem is not None else "Global Media"
                    
                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    desc_clean = clean_html(raw_desc)
                    
                    image_url = extract_image_from_item(item, raw_desc)
                    
                    # תרגום אוטומטי חם לעברית
                    title_he = translate_to_hebrew(title_en)
                    desc_he = translate_to_hebrew(desc_clean[:300] if desc_clean else title_en)
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO articles 
                        (url, source_name, country, title_hebrew, title_english, summary_hebrew, summary_english, full_content_hebrew, full_content_english, analyst_name, published_at, image_url, sentiment, priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        link,
                        f"{real_source_name} [LIVE]",
                        source['country'],
                        title_he,
                        title_en,
                        desc_he,
                        desc_clean,
                        f"דיווח חי אמיתי מתוך {real_source_name}:\n\n{desc_clean}\n\n[קישור מקור חיצוני: {link}]",
                        f"Live intelligence report from {real_source_name}:\n\n{desc_clean}",
                        "מערכת אינגסטשן חיה",
                        pub_at,
                        image_url,
                        "מבצעי חי",
                        10
                    ))
            conn.commit()
        except Exception as e:
            print(f"Fetch Error ({source['name']}): {e}")