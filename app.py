import streamlit as st
import pandas as pd
import threading
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

    .news-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 18px;
        display: flex;
        flex-direction: column;
        height: 100%;
        transition: all 0.2s ease;
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

    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 6px;
    }
    .badge-urgent { background-color: rgba(239, 68, 68, 0.25); color: #f87171; border: 1px solid #ef4444; }
    .badge-cat { background-color: rgba(14, 165, 233, 0.2); color: #38bdf8; border: 1px solid #0ea5e9; }
    .badge-src { background-color: #1e293b; color: #94a3b8; }

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

# --- מנגנון איסוף שקט ברקע (רץ כל 10 דקות בסרבר) ---
def background_scanner():
    while True:
        try:
            arts = fetch_relevant_articles()
            for a in arts:
                if not is_article_exists(a['url']):
                    res = analyze_article(a['title_original'], a['content_original'])
                    a.update({
                        'title_hebrew': res.get('title_hebrew'),
                        'summary_hebrew': res.get('summary_hebrew'),
                        'sentiment': res.get('category'),  # שימוש בעמודה לסיווג הקטגוריה
                        'sentiment_score': 1.0 if res.get('urgency') == 'מתפרצת' else 0.0
                    })
                    save_article(a)
                    time.sleep(6)
        except Exception as err:
            print(f"Background scanner error: {err}")
        time.sleep(600)  # המתנה של 10 דקות עד הסריקה הבאה

@st.cache_resource
def start_background_thread():
    t = threading.Thread(target=background_scanner, daemon=True)
    t.start()
    return True

start_background_thread()

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM articles ORDER BY id DESC", conn)
    conn.close()
    return df

df = load_data()

top_c1, top_c2, top_c3 = st.columns([6, 3, 3])
with top_c1:
    st.markdown("<h1 style='margin-bottom:2px; font-weight:900;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
    st.caption("איסוף שוטף 24/7 ממאגרי תקשורת בינלאומיים | עדכון שקט כל 10 דקות")
with top_c2:
    st.metric("סה\"כ ידיעות במאגר", len(df) if not df.empty else 0)
with top_c3:
    military_cnt = len(df[df['sentiment'].str.contains('צבאי', na=False)]) if not df.empty else 0
    st.metric("דיווחים ביטחוניים", military_cnt)

st.markdown("<hr style='border-color: #1e293b; margin: 15px 0 25px 0;'>", unsafe_allow_html=True)

if not df.empty:
    st.markdown("### 🔥 דיווחים במוקד")
    hero_df = df.head(2)
    h_col1, h_col2 = st.columns(2)

    for col, (_, row) in zip([h_col1, h_col2], hero_df.iterrows()):
        with col:
            cat = str(row.get('sentiment', 'כללי'))
            is_urgent = row.get('sentiment_score', 0.0) == 1.0
            urgency_badge = '<span class="badge badge-urgent">מתפרצת</span>' if is_urgent else ''
            img_url = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000"
            
            st.markdown(f"""
            <div class="hero-card" style="background-image: url('{img_url}');">
                <div class="hero-overlay"></div>
                <div class="hero-content">
                    <div style="margin-bottom: 8px;">
                        <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                        <span class="badge badge-src">🌍 {row.get('country', '')}</span>
                        <span class="badge badge-cat">{cat}</span>
                        {urgency_badge}
                    </div>
                    <h3 style="color:#ffffff; margin:0 0 8px 0; font-size:1.35rem; font-weight:800; line-height:1.3;">
                        {row.get('title_hebrew') or row.get('title_original')}
                    </h3>
                    <p style="color:#cbd5e1; font-size:0.9rem; line-height:1.5; margin-bottom:12px;">
                        {str(row.get('summary_hebrew', ''))[:160]}...
                    </p>
                    <a class="read-more" href="{row.get('url', '#')}" target="_blank">לקריאת המקור בערוץ ←</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

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
                    cat = str(row.get('sentiment', 'כללי'))
                    img_src = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"

                    st.markdown(f"""
                    <div class="news-card">
                        <img class="news-card-img" src="{img_src}" />
                        <div class="news-card-body">
                            <div style="margin-bottom: 8px;">
                                <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                                <span class="badge badge-cat">{cat}</span>
                            </div>
                            <div style="font-weight:700; color:#fff; font-size:1.02rem; margin-bottom:6px; line-height:1.4;">
                                {row.get('title_hebrew') or row.get('title_original')}
                            </div>
                            <div style="font-size:0.85rem; color:#94a3b8; line-height:1.5; margin-bottom:12px;">
                                {str(row.get('summary_hebrew', ''))[:120]}...
                            </div>
                            <a class="read-more" href="{row.get('url', '#')}" target="_blank">לכתבה המקורית ←</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)