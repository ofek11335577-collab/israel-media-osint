import streamlit as st
import pandas as pd
import threading
import time
from datetime import datetime
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
    .badge-time { background-color: rgba(100, 116, 139, 0.2); color: #94a3b8; border: 1px solid #334155; }

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

# נתוני אתחול טריים מהיום כדי שהדף ייפתח תמיד מלא
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
SEED_DATA = [
    {
        "url": "https://www.aljazeera.com/news/liveblog/2026/mideast-tensions-live",
        "source_name": "Al Jazeera",
        "country": "קטר / אזורי",
        "title_original": "Regional diplomatic efforts intensify as security tensions rise",
        "content_original": "Mediators meet to discuss ceasefire frameworks and border security guarantees across regional fronts.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1000",
        "title_hebrew": "מגעים דיפלומטיים קדחתניים באזור סביב מנגנוני ביטחון והסדרה",
        "summary_hebrew": "משלחות תיווך בינלאומיות פועלות למנוע התרחבות של העימות ולגבש ערבויות ביטחוניות בגבולות.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 1.0
    },
    {
        "url": "https://english.alarabiya.net/news/middle-east/2026/gulf-security-talks",
        "source_name": "Al Arabiya",
        "country": "סעודיה / מפרץ",
        "title_original": "Gulf security coordination focuses on maritime trade protection",
        "content_original": "High-level meetings addressing navigational safety and deterrence against asymmetric threats in shipping corridors.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1000",
        "title_hebrew": "מדינות המפרץ מהדקות את התיאום להגנת נתיבי השיט הבינלאומיים",
        "summary_hebrew": "התייעצויות ביטחוניות נרחבות במפרץ במטרה לבלום איומי כטב\"מים וטילים לעבר ספינות סוחר.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0
    },
    {
        "url": "https://www.tehrantimes.com/news/2026/iran-defense-capabilities",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_original": "Tehran showcases modernized tactical aerospace systems",
        "content_original": "Defense units unveil integrated radar arrays and upgraded surface launch capabilities.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1000",
        "title_hebrew": "איראן חושפת מערכי מכ\"ם ויירוט טקטיים חדשים",
        "summary_hebrew": "משמרות המהפכה מציגים פריסה של מערכות גילוי מתקדמות לצד הצהרות הרתעה מול המערב.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 0.0
    },
    {
        "url": "https://en.almayadeen.net/news/politics/2026/beirut-border-updates",
        "source_name": "Al Mayadeen",
        "country": "לבנון",
        "title_original": "Border developments escalate discussions on UN resolution monitoring",
        "content_original": "Field reports from Southern Lebanon highlight ongoing surveillance and diplomatic backchannel communication.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000",
        "title_hebrew": "דרום לבנון: מתיחות מתמשכת על קו הגבול וחילופי אש ממוקדים",
        "summary_hebrew": "דיווחים על פעילות איסוף מוגברת לאורך הקו הכחול ומגעים של יוניפי\"ל למניעת הידרדרות.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0
    },
    {
        "url": "https://www.france24.com/en/middle-east/2026/economic-sanctions-review",
        "source_name": "France 24",
        "country": "אירופה",
        "title_original": "European allies review trade compliance and dual-use restrictions",
        "content_original": "European regulatory agencies intensify scrutiny over export permits to prevent regional diversion.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=1000",
        "title_hebrew": "האיחוד האירופי מחמיר את הפיקוח על ייצוא טכנולוגיה רגישה למזרח התיכון",
        "summary_hebrew": "החלטה חדשה בבריסל להגביר את הסנקציות על רשתות שמספקות רכיבים אלקטרוניים לפרויקטי נשק.",
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

# אתחול מהיר במידה והמאגר ריק
if df.empty:
    for art in SEED_DATA:
        save_article(art)
    df = load_data()

# תהליך רקע עצמאי שסורק כל 10 דקות
def background_worker():
    while True:
        try:
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
            print(f"Worker background error: {e}")
        time.sleep(600)

@st.cache_resource
def start_worker():
    t = threading.Thread(target=background_worker, daemon=True)
    t.start()
    return True

start_worker()

# כותרת ראשית ומדדים
top_c1, top_c2, top_c3 = st.columns([6, 3, 3])
with top_c1:
    st.markdown("<h1 style='margin-bottom:2px; font-weight:900;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
    st.caption("מבזקים מתפרצים בזמן אמת וסריקת עומק שקטה כל 10 דקות")
with top_c2:
    st.metric("סה\"כ דיווחים במערכת", len(df))
with top_c3:
    military_cnt = len(df[df['sentiment'].astype(str).str.contains('צבאי', na=False)])
    st.metric("דיווחים ביטחוניים", military_cnt)

st.markdown("<hr style='border-color: #1e293b; margin: 15px 0 25px 0;'>", unsafe_allow_html=True)

# 1. דיווחי מוקד חמים (הכתבות האחרונות שנכנסו)
st.markdown("### 🔥 דיווחי מוקד חמים")
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
            pub_time = str(row.get('published_at', 'עדכון שוטף'))[:16]
            
            st.markdown(f"""
            <div style="margin: 8px 0;">
                <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                <span class="badge badge-cat">{cat}</span>
                <span class="badge badge-time">🕒 {pub_time}</span>
                {urgency_html}
            </div>
            """, unsafe_allow_html=True)
            
            title = row.get('title_hebrew') or row.get('title_original')
            st.markdown(f"<h3 style='color: #ffffff; margin: 4px 0 8px 0; font-size: 1.25rem; font-weight: 800; line-height: 1.4;'>{title}</h3>", unsafe_allow_html=True)
            
            summary = str(row.get('summary_hebrew', ''))[:160]
            st.markdown(f"<p style='color: #94a3b8; font-size: 0.92rem; line-height: 1.6; margin-bottom: 12px;'>{summary}...</p>", unsafe_allow_html=True)
            
            url = row.get('url', '#')
            st.markdown(f"<a class='read-link' href='{url}' target='_blank'>לקריאת המקור בערוץ ←</a>", unsafe_allow_html=True)

# 2. חלוקה לגזרות פעילות
SECTORS = [
    {"title": "איראן והציר האזורי", "icon": "🎯", "keys": ["iran", "tehran", "איראן", "טהראן", "Houthi", "תימן", "Tehran Times", "IRNA"]},
    {"title": "לבנון וחיזבאללה", "icon": "🇱🇧", "keys": ["lebanon", "hezbollah", "beirut", "לבנון", "חיזבאללה", "Al Mayadeen"]},
    {"title": "רצועת עזה והעולם הערבי", "icon": "⚡", "keys": ["gaza", "hamas", "עזה", "חמאס", "Al Jazeera", "Al Arabiya"]},
    {"title": "יהודה ושומרון", "icon": "🛡️", "keys": ["west bank", "settler", "jenin", "איו\"ש", "גדה", "Wafa", "שומרון"]},
    {"title": "ארה\"ב וזירה בינלאומית", "icon": "🌍", "keys": ["United States", "BBC", "NY Times", "France 24", "אירופה", "צרפת", "בריטניה"]}
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
                    pub_time = str(row.get('published_at', 'עדכון שוטף'))[:16]
                    
                    st.markdown(f"""
                    <div style="margin: 6px 0;">
                        <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                        <span class="badge badge-cat">{cat}</span>
                        <span class="badge badge-time">🕒 {pub_time}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    c_title = row.get('title_hebrew') or row.get('title_original')
                    st.markdown(f"<div style='font-weight: 700; color: #fff; font-size: 1.02rem; margin-bottom: 6px; line-height: 1.4;'>{c_title}</div>", unsafe_allow_html=True)

                    c_summary = str(row.get('summary_hebrew', ''))[:120]
                    st.markdown(f"<div style='font-size: 0.85rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;'>{c_summary}...</div>", unsafe_allow_html=True)

                    c_url = row.get('url', '#')
                    st.markdown(f"<a class='read-link' href='{c_url}' target='_blank'>לכתבה המקורית ←</a>", unsafe_allow_html=True)

# 3. אזור ארכיון וכל הדיווחים (בדיוק כמו אתר ספורט)
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
with st.expander("📂 ארכיון דיווחים וכל הידיעות מהעולם", expanded=False):
    st.markdown("##### כל הידיעות שנאגרו במערכת לפי סדר קליטה:")
    
    # טבלת ארכיון נוחה
    archive_df = df[['published_at', 'source_name', 'sentiment', 'title_hebrew', 'url']].copy()
    archive_df.columns = ['תאריך פרסום', 'ערוץ / מקור', 'תחום', 'כותרת הדיווח', 'קישור ישיר']
    st.dataframe(
        archive_df,
        column_config={
            "קישור ישיר": st.column_config.LinkColumn("קישור למקור")
        },
        hide_index=True,
        use_container_width=True
    )