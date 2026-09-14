import json
import feedparser
from datetime import datetime
import time

def load_sources():
    try:
        with open("config/sources.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading sources.json: {e}")
        return {}

def extract_image(entry) -> str:
    # חיפוש תמונה במבני RSS נפוצים (media:content, enclosures, וכו')
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            if 'url' in media and ('image' in media.get('type', '') or 'jpg' in media.get('url', '') or 'png' in media.get('url', '')):
                return media['url']
                
    if hasattr(entry, 'enclosures'):
        for enc in entry.enclosures:
            if 'type' in enc and 'image' in enc['type']:
                return enc['href']
                
    # חיפוש תמונה מתוך תוכן HTML אם קיים
    content_html = ""
    if hasattr(entry, 'summary'):
        content_html += entry.summary
    if hasattr(entry, 'content'):
        for c in entry.content:
            content_html += c.value
            
    if '<img' in content_html:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content_html, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']
        except:
            pass
            
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"  # תמונת ברירת מחדל מודיעינית

def fetch_relevant_articles():
    sources_map = load_sources()
    all_articles = []

    for country, sources in sources_map.items():
        for source in sources:
            try:
                feed = feedparser.parse(source['url'])
                for entry in feed.entries[:5]:  # לוקח את ה-5 החדשים מכל מקור
                    title = entry.get('title', '')
                    summary = entry.get('summary', entry.get('description', ''))
                    url = entry.get('link', '')
                    
                    # חילוץ תאריך פרסום או מתן תאריך נוכחי
                    pub_date = entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    
                    image_url = extract_image(entry)

                    if title and url:
                        all_articles.append({
                            "source_name": source['name'],
                            "country": country,
                            "title_original": title,
                            "content_original": summary,
                            "url": url,
                            "image_url": image_url,
                            "published_at": pub_date
                        })
            except Exception as e:
                print(f"Failed to fetch {source['name']}: {e}")

    return all_articles