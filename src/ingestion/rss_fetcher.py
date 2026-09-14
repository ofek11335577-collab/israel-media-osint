import feedparser
from datetime import datetime
import email.utils
import pytz
import re

FEEDS = [
    {"url": "https://www.tehrantimes.com/rss", "source": "Tehran Times", "country": "איראן", "tz": "Asia/Tehran"},
    {"url": "https://en.irna.ir/rss", "source": "IRNA", "country": "איראן", "tz": "Asia/Tehran"},
    {"url": "https://www.tasnimnews.com/en/rss/feed/0/7/0/", "source": "Tasnim News", "country": "איראן", "tz": "Asia/Tehran"},
    {"url": "https://en.mehrnews.com/rss", "source": "Mehr News", "country": "איראן", "tz": "Asia/Tehran"},
    {"url": "https://en.almayadeen.net/rss", "source": "Al Mayadeen", "country": "לבנון", "tz": "Asia/Beirut"},
    {"url": "https://english.alarabiya.net/rss", "source": "Al Arabiya", "country": "סעודיה", "tz": "Asia/Riyadh"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "country": "קטר", "tz": "Asia/Qatar"},
    {"url": "https://wafa.ps/ar/Rss/GetRss", "source": "Wafa News", "country": "איו\"ש", "tz": "Asia/Hebron"},
    {"url": "https://safa.ps/rss", "source": "Safa Press", "country": "רצועת עזה", "tz": "Asia/Gaza"},
    {"url": "https://rss.cnn.com/rss/edition_mideast.rss", "source": "CNN", "country": "ארה\"ב", "tz": "America/New_York"},
    {"url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "source": "BBC News", "country": "בריטניה", "tz": "Europe/London"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=middle-east&post_type=best", "source": "Reuters", "country": "בריטניה", "tz": "Europe/London"}
]

def normalize_timezone(published_dt, source_tz_str):
    if not published_dt:
        return datetime.now()
    try:
        source_tz = pytz.timezone(source_tz_str)
        israel_tz = pytz.timezone("Asia/Jerusalem")
        if published_dt.tzinfo is None:
            localized_dt = source_tz.localize(published_dt)
        else:
            localized_dt = published_dt
        return localized_dt.astimezone(israel_tz).replace(tzinfo=None)
    except Exception:
        return datetime.now()

def parse_date(entry, tz_str):
    dt = None
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6])
    elif hasattr(entry, 'published') and entry.published:
        try:
            dt = email.utils.parsedate_to_datetime(entry.published)
        except Exception:
            pass
    if not dt:
        dt = datetime.now()
    return normalize_timezone(dt, tz_str).strftime("%Y-%m-%d %H:%M")

def extract_real_image(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        for m in entry.media_content:
            if 'url' in m and m.get('url', '').endswith(('jpg', 'jpeg', 'png', 'webp')):
                return m['url']
        return entry.media_content[0].get('url')
    summary = entry.get('summary', '') or entry.get('description', '')
    img_match = re.search(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']', summary, re.I)
    if img_match:
        return img_match.group(1)
    return None

def fetch_relevant_articles():
    articles = []
    seen_titles = set()
    keywords = [
        "israel", "netanyahu", "gaza", "lebanon", "hezbollah", "beirut", "iran", 
        "tehran", "hamas", "tel aviv", "idf", "houthi", "yemen", "west bank", 
        "jerusalem", "syria", "damascus", "palestin", "middle east", "ceasefire",
        "strike", "military", "missile", "war", "drone", "hostage", "saudi", "iraq", "irgc"
    ]
    
    for f in FEEDS:
        try:
            feed = feedparser.parse(f['url'])
            for entry in feed.entries[:15]:
                title = entry.get('title', '').strip()
                # נרמול הכותרת לבדיקת כפילויות (הסרת אותיות גדולות וסימני פיסוק)
                clean_title_key = re.sub(r'[^a-zA-Z0-9\u0590-\u05ea]', '', title.lower())
                if not clean_title_key or clean_title_key in seen_titles:
                    continue
                seen_titles.add(clean_title_key)
                
                link = entry.get('link', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                full_text = f"{title} {summary}".lower()
                
                if any(k in full_text for k in keywords) or "middle" in f['url'] or "mideast" in f['url'] or "iran" in f['url']:
                    if link:
                        articles.append({
                            "url": link,
                            "source_name": f['source'],
                            "country": f['country'],
                            "title_original": title,
                            "content_original": summary,
                            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "image_url": extract_real_image(entry)
                        })
        except Exception as e:
            print(f"Error {f['source']}: {e}")
    return articles