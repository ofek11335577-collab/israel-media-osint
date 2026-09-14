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

# עיצוב כללי - רקע כהה ופונט עברית נקי
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

    /* הסתרת סיידבר לחלוטין למניעת עיוותים */
    [data-testid="stSidebarCollapseButton"], section[data-testid="stSidebar"] {
        display: none !important;
    }

    /* עיצוב כרטיסי container */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #0f172a !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px !important;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #0ea5e9 !important;
        transform: translateY(-2px);
    }

    /* תגים מעוצבים */
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

    a.read-link {
        color: #38bdf8 !important;
        font-weight: 700;
        font-size: 0.85rem;
        text-decoration: none;
    }
    a.read-link:hover {
        text-decoration: underline;
    }
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

# כותרת עליונה
top_c1, top_c2, top_c3 = st.columns([6, 3, 3])
with top_c1:
    st.markdown("<h1 style='margin-bottom:2px; font-weight:900;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
    st.caption("איסוף שוטף 24/7 ממאגרי תקשורת בינלאומיים | עדכון שקט כל 10 דקות")
with top_c2:
    st.metric("סה\"כ דיווחים במאגר", len(df))
with top_c3:
    military_cnt = len(df[df['sentiment'].astype(str).str.contains('צבאי', na=False)])
    st.metric("דיווחים ביטחוניים", military_cnt)

st.markdown("<hr style='border-color: #1e293b; margin: 15px 0 25px 0;'>", unsafe_allow_html=True)

# אזור דיווחי מוקד (Hero) - בנוי עם st.container כדי למנוע באגי רינדור
st.markdown("### 🔥 דיווחים במוקד")
hero_df = df.head(2)
h_col1, h_col2 = st.columns(2)

for col, (_, row) in zip([h_col1, h_col2], hero_df.iterrows()):
    with col:
        with st.container(border=True):
            img_url = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000"
            st.image(img_url, use_container_width=True)
            
            cat = str(row.get('sentiment', 'כללי'))
            is_urgent = row.get('sentiment_score', 0.0) == 1.0
            urgency_html = '<span class="badge badge-urgent">מתפרצת</span>' if is_urgent else ''
            
            st.markdown(f"""
            <div style="margin: 8px 0;">
                <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                <span class="badge badge-cat">{cat}</span>
                {urgency_html}
            </div>
            """, unsafe_allow_html=True)
            
            title = row.get('title_hebrew') or row.get('title_original')
            st.markdown(f"<h3 style='color: #ffffff; margin: 4px 0 8px 0; font-size: 1.25rem; font-weight: 800; line-height: 1.4;'>{title}</h3>", unsafe_allow_html=True)
            
            summary = str(row.get('summary_hebrew', ''))[:160]
            st.markdown(f"<p style='color: #94a3b8; font-size: 0.92rem; line-height: 1.6; margin-bottom: 12px;'>{summary}...</p>", unsafe_allow_html=True)
            
            url = row.get('url', '#')
            st.markdown(f"<a class='read-link' href='{url}' target='_blank'>לקריאת המקור בערוץ ←</a>", unsafe_allow_html=True)

# גזרות
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
                with st.container(border=True):
                    img_src = row.get('image_url') if ('image_url' in row and pd.notna(row['image_url']) and row['image_url']) else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
                    st.image(img_src, use_container_width=True)

                    cat = str(row.get('sentiment', 'כללי'))
                    st.markdown(f"""
                    <div style="margin: 6px 0;">
                        <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                        <span class="badge badge-cat">{cat}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    c_title = row.get('title_hebrew') or row.get('title_original')
                    st.markdown(f"<div style='font-weight: 700; color: #fff; font-size: 1.02rem; margin-bottom: 6px; line-height: 1.4;'>{c_title}</div>", unsafe_allow_html=True)

                    c_summary = str(row.get('summary_hebrew', ''))[:120]
                    st.markdown(f"<div style='font-size: 0.85rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;'>{c_summary}...</div>", unsafe_allow_html=True)

                    c_url = row.get('url', '#')
                    st.markdown(f"<a class='read-link' href='{c_url}' target='_blank'>לכתבה המקורית ←</a>", unsafe_allow_html=True)