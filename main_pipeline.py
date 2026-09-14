import time
from src.storage.database import init_db, is_article_exists, save_article
from src.ingestion.rss_fetcher import fetch_relevant_articles
from src.nlp.llm_client import analyze_article

def run_pipeline():
    init_db()
    print("[1/3] סורק פידים ומאתר כתבות רלוונטיות לישראל...")
    articles = fetch_relevant_articles()
    print(f"נמצאו {len(articles)} כתבות רלוונטיות.")

    new_count = 0
    for i, art in enumerate(articles, 1):
        if is_article_exists(art['url']):
            continue

        print(f"[{i}/{len(articles)}] מעבד כתבה חדשה מ-{art['source_name']}: {art['title_original'][:60]}...")
        
        # העשרה וניתוח באמצעות LLM
        nlp_result = analyze_article(art['title_original'], art['content_original'])
        
        # מיזוג ושמירה בבסיס הנתונים
        art.update(nlp_result)
        if save_article(art):
            new_count += 1

        # השהייה קלה למניעת חסימת קצב ב-Free Tier
        time.sleep(1)

    print(f"\nהסריקה הושלמה! {new_count} כתבות חדשות נשמרו בבסיס הנתונים.")

if __name__ == '__main__':
    run_pipeline()