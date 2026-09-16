OSINT Global Desk - integrated upgrade

Replace these files in your project:
1. app.py
2. database.py
3. ingestion/fetcher.py
4. requirements.txt

Add this new folder/file:
5. services/__init__.py
6. services/translator.py

The ingestion/__init__.py file is included as well.

What this version changes:
- English remains the default UI.
- Top button switches between English and Hebrew.
- Hebrew article titles/summaries are translated lazily and cached in SQLite.
- Article full text is translated when a Hebrew reader opens the report.
- The feed is sorted by publication time: newest first.
- The red ticker always uses the newest reports from the database.
- More RSS/news sources and fallbacks are configured.
- Startup uses RSS-only ingestion; expensive article-page enrichment is manual via Sync & Enrich Feeds.
- Manual enrichment improves original images, article body text, topics and Israel-framing analysis.
- Sports/lifestyle noise is filtered and old sports/noise rows are cleaned up.
- Near-duplicate headlines are filtered.
- Israel-framing labels are based on textual evidence and attribution/negation context; no publisher is hard-coded as supportive or critical.

After deploying:
- Let the app boot once so database.py can add the new columns.
- Click "Sync & Enrich Feeds" once. This backfills classification and enriches a bounded set of recent articles.
- Switch to Hebrew. Visible report titles/summaries will translate and be cached.
- For older articles, subsequent enrich syncs progressively improve full article content/images.
