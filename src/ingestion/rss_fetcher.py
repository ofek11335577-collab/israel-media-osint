import feedparser
from datetime import datetime, timedelta
import email.utils
import pytz

# מאגר פידים מורחב הכולל את כל סוכנויות הידיעות במזרח התיכון ובעולם
FEEDS = [
    # --- איראן ---
    {"url": "https://www.tehrantimes.com/rss", "source": "Tehran Times", "country": "איראן", "tz": "Asia/Tehran"},
    {"url": "https://en.irna.ir/rss", "source": "IRNA", "country": "איראן", "tz": "Asia/Tehran"},
    {"url": "https://www.tasnimnews.com/en/rss/feed/0/7/0/", "source": "Tasnim News", "country": "איראן", "tz": "Asia/Tehran"},

    # --- עיראק ---
    {"url": "https://www.ina.iq/en/rss.xml", "source": "INA Iraq", "country": "עיראק", "tz": "Asia/Baghdad"},
    {"url": "https://shafaq.com/en/rss", "source": "Shafaq News", "country": "עיראק", "tz": "Asia/Baghdad"},

    # --- ירדן ---
    {"url": "https://en.ammonnews.net/rss.php", "source": "Ammon News", "country": "ירדן", "tz": "Asia/Amman"},
    {"url": "https://almamlaka.tv/rss", "source": "Al Mamlaka TV", "country": "ירדן", "tz": "Asia/Amman"},

    # --- עזה ואיו"ש ---
    {"url": "https://wafa.ps/ar/Rss/GetRss", "source": "Wafa News", "country": "איו\"ש", "tz": "Asia/Hebron"},
    {"url": "https://safa.ps/rss", "source": "Safa Press", "country": "רצועת עזה", "tz": "Asia/Gaza"},

    # --- קטר ואיחוד האמירויות ---
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "country": "קטר", "tz": "Asia/Qatar"},
    {"url": "https://www.thenationalnews.com/arc/outbound/rss/?outputType=xml", "source": "The National (UAE)", "country": "איחוד האמירויות", "tz": "Asia/Dubai"},
    {"url": "https://www.albayan.ae/polopoly_fs/1.3789530!/menu/standard/file/ae.xml", "source": "Al Bayan", "country": "איחוד האמירויות", "tz": "Asia/Dubai"},

    # --- תימן ---
    {"url": "https://www.sabanews.net/en/rss.php", "source": "Saba Yemen", "country": "תימן", "tz": "Asia/Aden"},

    # --- סעודיה ומפרץ ---
    {"url": "https://english.alarabiya.net/rss", "source": "Al Arabiya", "country": "סעודיה", "tz": "Asia/Riyadh"},
    {"url": "https://www.spa.gov.sa/rss/rss_all.xml", "source": "SPA Saudi", "country": "סעודיה", "tz": "Asia/Riyadh"},

    # --- מערב ועולם ---
    {"url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "source": "BBC News", "country": "בריטניה", "tz": "Europe/London"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml", "source": "NY Times", "country": "ארה\"ב", "tz": "America/New_York"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=middle-east&post_type=best", "source": "Reuters", "country": "בריטניה", "tz": "Europe/London"},
    {"url": "https://www.france24.com/en/middle-east/rss", "source": "France 24", "country": "צרפת", "tz": "Europe/Paris"}
]

def normalize_timezone(published_dt, source_tz_str):
    """ממיר את זמן הפרסום המקורי של העיתון לשעון ישראל המקומי במדויק"""
    if not published_dt:
        return datetime.now()
    try:
        source_tz = pytz.timezone(source_tz_str)
        israel_tz = pytz.timezone("Asia/Jerusalem")
        
        # אם התאריך הוא "Naive" (ללא אזור זמן), נניח שהוא בשעון המקומי של המדינה
        if published_dt.tzinfo is None:
            localized_dt = source_tz.localize(published_dt)
        else:
            localized_dt = published_dt
            
        # המרה לשעון ישראל
        israel_dt = localized_dt.astimezone(israel_tz)
        return israel_dt.replace(tzinfo=None)
    except Exception:
        return published_dt.replace(tzinfo=None) if published_dt.tzinfo else published_dt

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
        
    normalized_dt = normalize_timezone(dt, tz_str)
    return normalized_dt.strftime("%Y-%m-%d %H:%M")

def extract_image(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        return entry.media_content[0].get('url')
    if hasattr(entry, 'links'):
        for l in entry.links:
            if 'image' in l.get('type', ''):
                return l.get('href')
    return None

def fetch_relevant_articles():
    articles = []
    keywords = [
        "israel", "netanyahu", "gaza", "lebanon", "hezbollah", "beirut", "iran", 
        "tehran", "hamas", "tel aviv", "idf", "houthi", "yemen", "west bank", 
        "jerusalem", "syria", "damascus", "palestin", "middle east", "ceasefire",
        "strike", "military", "missile", "war", "drone", "hostage", "saudi", "iraq"
    ]
    
    for f in FEEDS:
        try:
            feed = feedparser.parse(f['url'])
            for entry in feed.entries[:15]:
                title = entry.get('title', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                full_text = f"{title} {summary}".lower()
                
                if any(k in full_text for k in keywords) or len(keywords) == 0:
                    articles.append({
                        "url": entry.get('link', ''),
                        "source_name": f['source'],
                        "country": f['country'],
                        "title_original": title,
                        "content_original": summary,
                        "published_at": parse_date(entry, f['tz']),
                        "image_url": extract_image(entry)
                    })
        except Exception as e:
            print(f"Fetch error {f['source']}: {e}")
            
    return articles