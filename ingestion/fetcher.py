# ingestion/fetcher.py
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import email.utils
from database import get_db_connection
import re

DIRECT_RSS_CHANNELS = [
    {"name": "Reuters World", "url": "https://www.reuters.com/arc/outboundfeeds/v1/output/rss/?outputType=xml", "country": "US & Global"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "country": "US & Global"},
    {"name": "BBC Middle East", "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "country": "US & Global"},
]

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def extract_real_image(item, raw_desc):
    for tag in ['{http://search.yahoo.com/mrss/}content', '{http://search.yahoo.com/mrss/}thumbnail', 'enclosure']:
        media = item.find(tag)
        if media is not None and media.get('url'):
            return media.get('url')
    if raw_desc:
        img_match = re.search(r'<img[^>]+src="([^">]+)"', raw_desc)
        if img_match:
            return img_match.group(1)
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200"

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
    for source in DIRECT_RSS_CHANNELS:
        try:
            req = urllib.request.Request(source['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                for item in root.findall('.//item')[:15]:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    desc_elem = item.find('description')
                    
                    title = title_elem.text if title_elem is not None else "Breaking Intelligence Report"
                    url = link_elem.text if link_elem is not None else "https://www.reuters.com"
                    
                    published_at = parse_rss_date(pub_date_elem)
                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    summary = clean_html(raw_desc)[:250] if raw_desc else title
                    full_content = f"Live verified report from {source['name']}:\n\n{clean_html(raw_desc)}\n\n[Direct Link: {url}]"
                    
                    image_url = extract_real_image(item, raw_desc)
                    
                    # סיווג גיאוגרפי (מתוקן וללא שגיאות תחביר)
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
                        f"{source['name']} [LIVE]",
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
            print(f"Feed error ({source['name']}): {e}")
            
    return total_added