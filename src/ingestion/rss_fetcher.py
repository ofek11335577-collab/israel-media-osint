import feedparser
from datetime import datetime
import email.utils

FEEDS = [
    # לבנון והציר
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "country": "קטר / אזורי"},
    {"url": "https://en.almayadeen.net/rss", "source": "Al Mayadeen", "country": "לבנון / ציר"},
    {"url": "https://english.alarabiya.net/rss", "source": "Al Arabiya", "country": "סעודיה / מפרץ"},
    
    # איראן
    {"url": "https://www.tehrantimes.com/rss", "source": "Tehran Times", "country": "איראן"},
    {"url": "https://en.irna.ir/rss", "source": "IRNA", "country": "איראן"},
    
    # זירה בינלאומית ומעצמות
    {"url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "source": "BBC News", "country": "בריטניה"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml", "source": "NY Times", "country": "ארה\"ב"},
    {"url": "https://www.france24.com/en/middle-east/rss", "source": "France 24", "country": "צרפת"}
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
    for f in FEEDS:
        try:
            feed = feedparser.parse(f['url'])
            for entry in feed.entries[:10]:  # שואב 10 מכל מקור
                title = entry.get('title', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                
                # סינון בסיסי לרלוונטיות אזורית
                text_to_check = (title + " " + summary).lower()
                keywords = ["israel", "gaza", "lebanon", "hezbollah", "iran", "hamas", "strike", "war", "middle east", "idf", "houthi", "west bank", "syria"]
                
                if any(kw in text_to_check for kw in keywords):
                    articles.append({
                        "url": entry.get('link', ''),
                        "source_name": f['source'],
                        "country": f['country'],
                        "title_original": title,
                        "content_original": summary,
                        "published_at": parse_date(entry),
                        "image_url": extract_image(entry) or "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
                    })
        except Exception as e:
            print(f"Error fetching {f['source']}: {e}")
            
    return articles