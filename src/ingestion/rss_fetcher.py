import feedparser
from datetime import datetime
import email.utils

FEEDS = [
    # סוכנויות עולמיות
    {"url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "source": "BBC News", "country": "בריטניה"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml", "source": "NY Times", "country": "ארה\"ב"},
    {"url": "https://www.france24.com/en/middle-east/rss", "source": "France 24", "country": "צרפת"},
    {"url": "https://rss.dw.com/rdf/rss-en-world", "source": "Deutsche Welle", "country": "גרמניה"},
    {"url": "https://www.theguardian.com/world/middleeast/rss", "source": "The Guardian", "country": "בריטניה"},
    {"url": "https://feeds.washingtonpost.com/rss/world", "source": "Washington Post", "country": "ארה\"ב"},

    # תקשורת אזורית
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "country": "קטר"},
    {"url": "https://english.alarabiya.net/rss", "source": "Al Arabiya", "country": "סעודיה"},
    {"url": "https://en.almayadeen.net/rss", "source": "Al Mayadeen", "country": "לבנון"},
    {"url": "https://today.lorientlejour.com/rss", "source": "L'Orient Today", "country": "לבנון"},

    # ציר איראן ואזור
    {"url": "https://www.tehrantimes.com/rss", "source": "Tehran Times", "country": "איראן"},
    {"url": "https://en.irna.ir/rss", "source": "IRNA", "country": "איראן"},
    {"url": "https://www.middleeasteye.net/rss", "source": "Middle East Eye", "country": "בריטניה"}
]

def parse_date(entry):
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")
    if hasattr(entry, 'published') and entry.published:
        try:
            parsed = email.utils.parsedate_to_datetime(entry.published)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M")

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
        "strike", "military", "missile", "war", "drone", "hostage"
    ]
    
    for f in FEEDS:
        try:
            feed = feedparser.parse(f['url'])
            for entry in feed.entries[:25]:
                title = entry.get('title', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                full_text = f"{title} {summary}".lower()
                
                # בדיקת רלוונטיות
                if any(k in full_text for k in keywords):
                    articles.append({
                        "url": entry.get('link', ''),
                        "source_name": f['source'],
                        "country": f['country'],
                        "title_original": title,
                        "content_original": summary,
                        "published_at": parse_date(entry),
                        "image_url": extract_image(entry)
                    })
        except Exception as e:
            print(f"Fetch error {f['source']}: {e}")
            
    return articles