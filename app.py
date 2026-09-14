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

    .stApp {
        background-color: #080b11;
        color: #e2e8f0;
        font-family: 'Heebo', sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    [data-testid="stSidebarCollapseButton"], section[data-testid="stSidebar"] {
        display: none !important;
    }

    /* כרטיס Hero מתוקן ונקי */
    .hero-box {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 14px;
        overflow: hidden;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .hero-box:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }
    .hero-img {
        width: 100%;
        height: 220px;
        object-fit: cover;
    }
    .hero-body {
        padding: 20px;
    }
    .hero-title {
        color: #ffffff;
        margin: 10px 0;
        font-size: 1.3rem;
        font-weight: 800;
        line-height: 1.4;
    }
    .hero-desc {
        color: #94a3b8;
        font-size: 0.92rem;
        line-height: 1.6;
        margin-bottom: 14px;
    }

    /* כרטיס גזרה */
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
        padding: 16px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    .sector-header {
        display: flex;
        align-items: center;
        gap: 10px;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 8px;
        margin-top: 36px;
        margin-bottom: 20px;
    }
    .sector-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #f1f5f9;
    }

    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 6px;
    }
    .badge-urgent { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }
    .badge-cat { background-color: rgba(14, 165, 233, 0.2); color: #38bdf8; border: 1px solid #0ea5e9; }
    .badge-src { background-color: #1e293b; color: #cbd5e1; }

    .read-more {
        color: #38bdf8;
        font-weight: 700;
        font-size: 0.82rem;
        text-decoration: none;
        margin-top: auto;
        padding-top: 8px;
        display: inline-block;
    }
    .read-more:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

init_db()

SEED_ARTICLES = [
    {
        "url": "https://www.telegraph.co.uk/world-news/2026/lebanon-pagers-special-report",
        "source_name": "The Telegraph",
        "country": "לבנון",
        "title_original": "Pager blasts strike thousands of Hezbollah targets across Lebanon",
        "content_original": "A coordinated detonation of secure communication devices used by Hezbollah fighters in Beirut and Southern Lebanon.",
        "published_at": "Recent",
        "image_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000",
        "title_hebrew": "פיצוצי ביפרים מתואמים פגעו באלפי יעדי חיזבאללה ברחבי לבנון",
        "summary_hebrew": "גל פיצוצים מתואם של מכשירי קשר מוצפנים אשר שימשו את פעילי חיזבאללה הוביל לפגיעה נרחבת ברשת הפיקוד בביירות ודרום לבנון.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0
    },
    {
        "url": "https://www.aljazeera.com/news/2026/iran-nuclear-developments",
        "source_name": "Al Jazeera",
        "country": "איראן",
        "title_original": "Tehran announces advancement in regional ballistic deterrence",
        "content_original": "Iranian military officials claim deployment of new surface-to-surface capabilities amid escalating regional tensions.",
        "published_at": "Recent",
        "image_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1000",
        "title_hebrew": "טהראן מכריזה על שדרוג מערכי הטילים וההרתעה האזורית",
        "summary_hebrew": "בכירים במשמרות המהפכה מדווחים על פריסת יכולות בליסטיות חדשות ומאיימים במענה תקיף מול כל פעילות של כוחות הקואליציה.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0
    },
    {
        "url": "https://www.reuters.com/world/middle-east/gaza-humanitarian-diplomacy-2026",
        "source_name": "Reuters",
        "country": "עזה",
        "title_original": "Diplomatic summits intensify discussions on regional stability in Gaza",
        "content_original": "International mediators hold rounds of discussions regarding humanitarian corridors and long-term security mechanisms.",
        "published_at": "Recent",
        "image_url": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1000",
        "title_hebrew": "פסגה בינלאומית מאיצה מגעים להסדרי ביטחון ומסדרונות סיוע בעזה",
        "summary_hebrew": "מתווכים בינלאומיים מקיימים סבב דיונים בקהיר במטרה להגיע למנגנון הסדרה וערבויות בינלאומיות למניעת הסלמה.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 0.0
    },
    {
        "url": "https://wafa.ps/ar/news/westbank-economic-developments",
        "source_name": "Wafa",
        "country": "יהודה ושומרון",
        "title_original": "West Bank security operations and commercial impacts",
        "content_original": "Reports on security closures impacting local transport and market supply chains across Nablus and Jenin.",
        "published_at": "Recent",
        "image_url": "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=1000",
        "title_hebrew": "פעילות ביטחונית נרחבת ביהודה ושומרון: השפעה על צירי הסחר והתנועה",
        "summary_hebrew": "מבצעי סיכול מתמשכים בגזרת שכם וג'נין הובילו לסגירת צירים מרכזיים ולהגבלות תנועה במוקדי חיכוך.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 0.0
    },
    {
        "url": "https://www.france24.com/en/diplomatic-sanctions-iran",
        "source_name": "France 24",
        "country": "אירופה",
        "title_original": "European Union drafts new sanctions targeting Iranian supply chains",
        "content_original": "EU envoys agree on comprehensive sanctions packet targeting manufacturers of drones and precision components.",
        "published_at": "Recent",
        "image_url": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1000",
        "title_hebrew": "האיחוד האירופי מגבש חבילת סנקציות מקיפה נגד רשתות אספקה איראניות",
        "summary_hebrew": "שרי החוץ של אירופה אישרו צעדים כלכליים ממוקדים נגד חברות ומפקדים המעורבים בייצור והפצת כטב\"מים במזרח התיכון.",
        "sentiment": "כלכלה וסנקציות",
        "sentiment_score": 0.0
    }
]

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM articles ORDER BY id DESC", conn)
    conn.close()
    return df

df = load_data()
if df.empty:
    for art in SEED_ARTICLES:
        save_article(art)
    df = load_data()

def background_worker():
    while True:
        try:
            time.sleep(600)
            arts = fetch_relevant_articles()
            for a in arts:
                if not is_article_exists(a['url']):
                    try:
                        res = analyze_article(a['title_original'], a['content_original'])
                        a.update({
                            'title_hebrew': res.get('title_hebrew'),
                            'summary_hebrew': res.get('summary_hebrew'),
                            'sentiment': res.get('category'),
                            'sentiment_score': 1.0 if res.get('urgency') == 'מתפרצת' else 0.0
                        })
                    except Exception:
                        a.update({
                            'title_hebrew': a['title_original'],
                            'summary_hebrew': a['content_original'][:160],
                            'sentiment': 'שוטף',
                            'sentiment_score': 0.0
                        })
                    save_article(a)
                    time.sleep(5)
        except Exception as e:
            print(f"Background worker error: {e}")

@st.cache_resource
def start_worker():
    t = threading.Thread(target=background_worker, daemon=True)
    t.start()
    return True

start_worker()

# כותרת ראשית
top_c1, top_c2, top_c3 = st.columns([6, 3, 3])
with top_c1:
    st.markdown("<h1 style='margin-bottom:2px; font-weight:900;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
    st.caption("איסוף שוטף 24/7 ממאגרי תקשורת בינלאומיים | סריקה שקטה כל 10 דקות")
with top_c2:
    st.metric("סה\"כ דיווחים במאגר", len(df))
with top_c3:
    military_cnt = len(df[df['sentiment'].astype(str).str.contains('צבאי', na=False)])
    st.metric("דיווחים ביטחוניים", military_cnt)

st.markdown("<hr style='border-color: #1e293b; margin: 15px 0 25px 0;'>", unsafe_allow_html=True)

# אזור דיווחי מוקד (Hero) ללא באגים ב-CSS
st.markdown("### 🔥 דיווחים במוקד")
hero_df = df.head(2)
h_col1, h_col2 = st.columns(2)

for col, (_, row) in zip([h_col1, h_col2], hero_df.iterrows()):
    with col:
        cat = str(row.get('sentiment', 'כללי'))
        is_urgent = row.get('sentiment_score', 0.0) == 1.0
        urgency_badge = '<span class="badge badge-urgent">מתפרצת</span>' if is_urgent else ''
        img_url = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000"
        title = row.get('title_hebrew') or row.get('title_original')
        summary = str(row.get('summary_hebrew', ''))[:160]
        url = row.get('url', '#')

        st.markdown(f"""
        <div class="hero-box">
            <img class="hero-img" src="{img_url}" alt="News image" />
            <div class="hero-body">
                <div>
                    <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                    <span class="badge badge-cat">{cat}</span>
                    {urgency_badge}
                </div>
                <div class="hero-title">{title}</div>
                <div class="hero-desc">{summary}...</div>
                <a class="read-more" href="{url}" target="_blank">לקריאת המקור בערוץ ←</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

# גזרות עם אייקונים אחידים ונקיים
SECTORS = [
    {"title": "איראן והציר האזורי", "icon": "🎯", "keys": ["iran", "tehran", "איראן", "טהראן", "Houthi", "תימן"]},
    {"title": "לבנון וחיזבאללה", "icon": "🇱🇧", "keys": ["lebanon", "hezbollah", "beirut", "לבנון", "חיזבאללה", "Telegraph"]},
    {"title": "רצועת עזה והעולם הערבי", "icon": "⚡", "keys": ["gaza", "hamas", "עזה", "חמאס", "Al Jazeera", "Reuters"]},
    {"title": "יהודה ושומרון", "icon": "🛡️", "keys": ["west bank", "settler", "jenin", "איו\"ש", "גדה", "Wafa", "שומרון"]},
    {"title": "אירופה וזירה בינלאומית", "icon": "🌍", "keys": ["United States", "United Kingdom", "France", "Spain", "אירופה"]}
]

for sec in SECTORS:
    pattern = "|".join(sec["keys"])
    sec_df = df[
        df['country'].astype(str).str.contains(pattern, case=False, na=False) |
        df['source_name'].astype(str).str.contains(pattern, case=False, na=False) |
        df['title_original'].astype(str).str.contains(pattern, case=False, na=False) |
        df['title_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
        df['summary_hebrew'].astype(str).str.contains(pattern, case=False, na=False)
    ].head(3)

    if not sec_df.empty:
        st.markdown(f"""
        <div class="sector-header">
            <span style="font-size: 1.4rem;">{sec['icon']}</span>
            <span class="sector-title">{sec['title']}</span>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(3)
        for c_idx, (_, row) in enumerate(sec_df.iterrows()):
            with cols[c_idx]:
                cat = str(row.get('sentiment', 'כללי'))
                img_src = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
                c_title = row.get('title_hebrew') or row.get('title_original')
                c_summary = str(row.get('summary_hebrew', ''))[:120]
                c_url = row.get('url', '#')

                st.markdown(f"""
                <div class="news-card">
                    <img class="news-card-img" src="{img_src}" alt="News image" />
                    <div class="news-card-body">
                        <div style="margin-bottom: 8px;">
                            <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                            <span class="badge badge-cat">{cat}</span>
                        </div>
                        <div style="font-weight:700; color:#fff; font-size:1.02rem; margin-bottom:6px; line-height:1.4;">
                            {c_title}
                        </div>
                        <div style="font-size:0.85rem; color:#94a3b8; line-height:1.5; margin-bottom:12px;">
                            {c_summary}...
                        </div>
                        <a class="read-more" href="{c_url}" target="_blank">לכתבה המקורית ←</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)