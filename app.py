import streamlit as st
import pandas as pd
import time
from src.storage.database import get_connection, init_db, is_article_exists, save_article
from src.ingestion.rss_fetcher import fetch_relevant_articles
from src.nlp.llm_client import analyze_article

st.set_page_config(
    page_title="דסק מודיעין תקשורת | OSINT IL",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif !important;
        direction: rtl;
        text-align: right;
    }
    .stApp {
        background-color: #080b11;
        color: #e2e8f0;
    }

    /* כרטיס ראשי מוביל (Hero Banner) */
    .hero-card {
        position: relative;
        border-radius: 14px;
        overflow: hidden;
        height: 380px;
        border: 1px solid #1e293b;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        background-size: cover;
        background-position: center;
        margin-bottom: 24px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .hero-card:hover {
        transform: scale(1.01);
        border-color: #38bdf8;
    }
    .hero-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(to top, rgba(8, 11, 17, 0.95) 15%, rgba(8, 11, 17, 0.5) 60%, rgba(8, 11, 17, 0.2) 100%);
        z-index: 1;
    }
    .hero-content {
        position: relative;
        z-index: 2;
    }

    /* כרטיס כתבה סטנדרטי */
    .news-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 18px;
        transition: all 0.2s ease;
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    .news-card:hover {
        border-color: #0ea5e9;
        transform: translateY(-3px);
    }
    .news-card-img {
        width: 100%;
        height: 160px;
        object-fit: cover;
    }
    .news-card-body {
        padding: 14px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    /* כותרת קטגוריית גזרה */
    .sector-header {
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 10px;
        margin-top: 36px;
        margin-bottom: 20px;
    }
    .sector-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #ffffff;
    }

    /* תגיות */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 6px;
    }
    .badge-hostile { background-color: rgba(239, 68, 68, 0.25); color: #f87171; border: 1px solid #ef4444; }
    .badge-neutral { background-color: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid #64748b; }
    .badge-positive { background-color: rgba(34, 197, 94, 0.25); color: #4ade80; border: 1px solid #22c55e; }
    .badge-src { background-color: #1e293b; color: #38bdf8; }

    .read-more {
        color: #38bdf8;
        font-weight: 700;
        font-size: 0.8rem;
        text-decoration: none;
        margin-top: auto;
        padding-top: 10px;
    }
    .read-more:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

init_db()

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM articles ORDER BY id DESC", conn)
    conn.close()
    return df

with st.sidebar:
    st.markdown("### ⚙️ פעולות דסק")
    if st.button("🔄 סרוק מקורות גלובליים", use_container_width=True):
        with st.status("איסוף וניתוח בתהליך...") as s:
            arts = fetch_relevant_articles()
            new_c = 0
            for a in arts:
                if not is_article_exists(a['url']):
                    a.update(analyze_article(a['title_original'], a['content_original']))
                    save_article(a)
                    new_c += 1
                    time.sleep(12)
            s.update(label=f"התווספו {new_c} דיווחים", state="complete")
            st.rerun()

df = load_data()

# כותרת האתר ומדדים עליונים
top_c1, top_c2, top_c3 = st.columns([6, 3, 3])
with top_c1:
    st.markdown("<h1 style='margin-bottom:2px; font-weight:900;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
    st.caption("ניטור נרטיבים, סנטימנט והשפעה בזמן אמת ממאגרי תקשורת בינלאומיים")
with top_c2:
    st.metric("סה\"כ ידיעות במאגר", len(df) if not df.empty else 0)
with top_c3:
    avg_s = df['sentiment_score'].mean() if (not df.empty and 'sentiment_score' in df.columns) else 0.0
    st.metric("מדד סנטימנט משוקלל", f"{avg_s:.2f}")

st.markdown("<hr style='border-color: #1e293b; margin: 15px 0 25px 0;'>", unsafe_allow_html=True)

if df.empty:
    st.info("בסיס הנתונים ריק כרגע. לחץ על 'סרוק מקורות גלובליים' בסרגל הצד כדי להתחיל באיסוף.")
else:
    # --- אזור מבזקי על (HERO SECTION) ---
    st.markdown("### 🔥 דיווחי מוקד")
    
    # מיון לפי קיצוניות סנטימנט או תאריך אחרון
    hero_df = df.sort_values(by="sentiment_score", ascending=True).head(2)
    h_col1, h_col2 = st.columns(2)

    for idx, (col, (_, row)) in enumerate(zip([h_col1, h_col2], hero_df.iterrows())):
        with col:
            sent = str(row.get('sentiment', 'נייטרלי'))
            badge_class = "badge-hostile" if "עוין" in sent else ("badge-positive" if "חיובי" in sent else "badge-neutral")
            img_url = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000"
            
            st.markdown(f"""
            <div class="hero-card" style="background-image: url('{img_url}');">
                <div class="hero-overlay"></div>
                <div class="hero-content">
                    <div style="margin-bottom: 8px;">
                        <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                        <span class="badge badge-src">🌍 {row.get('country', '')}</span>
                        <span class="badge {badge_class}">{sent} ({row.get('sentiment_score', 0.0)})</span>
                    </div>
                    <h3 style="color:#ffffff; margin:0 0 8px 0; font-size:1.35rem; font-weight:800; line-height:1.3;">
                        {row.get('title_hebrew') or row.get('title_original')}
                    </h3>
                    <p style="color:#cbd5e1; font-size:0.9rem; line-height:1.5; margin-bottom:12px;">
                        {row.get('summary_hebrew', '')[:160]}...
                    </p>
                    <a class="read-more" href="{row.get('url', '#')}" target="_blank">לקריאת המקור בערוץ ←</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- חלוקה לגזרות ומדינות לאורך כל הדף ---
    SECTORS = [
        {"title": "איראן והציר האזורי", "flag": "🇮🇷", "keys": ["iran", "tehran", "איראן", "טהראן", "Houthi", "תימן"]},
        {"title": "לבנון וחיזבאללה", "flag": "🇱🇧", "keys": ["lebanon", "hezbollah", "beirut", "לבנון", "חיזבאללה"]},
        {"title": "רצועת עזה והעולם הערבי", "flag": "🇵🇸", "keys": ["gaza", "hamas", "עזה", "חמאס", "Al Jazeera", "Maan"]},
        {"title": "יהודה ושומרון", "flag": "🛡️", "keys": ["west bank", "settler", "jenin", "איו\"ש", "גדה", "wafa"]},
        {"title": "ארה\"ב וזירה בינלאומית", "flag": "🌐", "keys": ["United States", "United Kingdom", "France", "Spain", "Turkey"]}
    ]

    for sec in SECTORS:
        pattern = "|".join(sec["keys"])
        sec_df = df[
            df['country'].astype(str).str.contains(pattern, case=False, na=False) |
            df['title_original'].astype(str).str.contains(pattern, case=False, na=False) |
            df['title_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
            df['summary_hebrew'].astype(str).str.contains(pattern, case=False, na=False)
        ].head(3)

        if not sec_df.empty:
            st.markdown(f"""
            <div class="sector-header">
                <span style="font-size: 1.8rem;">{sec['flag']}</span>
                <span class="sector-title">{sec['title']}</span>
            </div>
            """, unsafe_allow_html=True)

            cols = st.columns(3)
            for c_idx, (_, row) in enumerate(sec_df.iterrows()):
                with cols[c_idx]:
                    sent = str(row.get('sentiment', 'נייטרלי'))
                    badge_class = "badge-hostile" if "עוין" in sent else ("badge-positive" if "חיובי" in sent else "badge-neutral")
                    img_src = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"

                    st.markdown(f"""
                    <div class="news-card">
                        <img class="news-card-img" src="{img_src}" />
                        <div class="news-card-body">
                            <div style="margin-bottom: 8px;">
                                <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                                <span class="badge {badge_class}">{sent}</span>
                            </div>
                            <div style="font-weight:700; color:#fff; font-size:1.02rem; margin-bottom:6px; line-height:1.4;">
                                {row.get('title_hebrew') or row.get('title_original')}
                            </div>
                            <div style="font-size:0.85rem; color:#94a3b8; line-height:1.5; margin-bottom:12px;">
                                {row.get('summary_hebrew', '')[:120]}...
                            </div>
                            <a class="read-more" href="{row.get('url', '#')}" target="_blank">לכתבה המקורית ←</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)