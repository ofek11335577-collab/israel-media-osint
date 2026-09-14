import feedparser
from datetime import datetime
import re

FEEDS = [
    {"url": "https://www.tehrantimes.com/rss", "source": "Tehran Times", "country": "איראן"},
    {"url": "https://en.irna.ir/rss", "source": "IRNA", "country": "איראן"},
    {"url": "https://www.tasnimnews.com/en/rss/feed/0/7/0/", "source": "Tasnim News", "country": "איראן"},
    {"url": "https://en.almayadeen.net/rss", "source": "Al Mayadeen", "country": "לבנון"},
    {"url": "https://english.alarabiya.net/rss", "source": "Al Arabiya", "country": "סעודיה"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "country": "קטר"},
    {"url": "https://wafa.ps/ar/Rss/GetRss", "source": "Wafa News", "country": "איו\"ש"},
    {"url": "https://safa.ps/rss", "source": "Safa Press", "country": "רצועת עזה"},
    {"url": "https://rss.cnn.com/rss/edition_mideast.rss", "source": "CNN", "country": "ארה\"ב"},
    {"url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "source": "BBC News", "country": "בריטניה"},
    {"url": "https://www.reutersagency.com/feed/?best-topics=middle-east&post_type=best", "source": "Reuters", "country": "בריטניה"}
]

def fetch_relevant_articles():
    articles = []
    for f in FEEDS:
        try:
            feed = feedparser.parse(f['url'])
            for entry in feed.entries[:10]:
                title = entry.get('title', '').strip()
                link = entry.get('link', '')
                summary = entry.get('summary', '') or entry.get('description', '')
                if title and link:
                    articles.append({
                        "url": link,
                        "source_name": f['source'],
                        "country": f['country'],
                        "title_original": title,
                        "content_original": summary,
                        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "image_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=1000"
                    })
        except Exception as e:
            print(f"Error {f['source']}: {e}")
    return articles