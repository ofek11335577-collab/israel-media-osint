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
    .badge-target { background-color: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #a855f7; }

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

# נתוני אתחול עשירים ומעודכנים מראש
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
SEED_DATA = [
    {
        "url": "https://www.bbc.com/news/world-middle-east-2026-regional-diplomacy",
        "source_name": "BBC News",
        "country": "בריטניה",
        "title_original": "Intense security consultations held regarding northern border escalation",
        "content_original": "International envoys coordinate with Israel and Lebanon to contain border hostilities and preserve maritime stability.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000",
        "title_hebrew": "מגעים בינלאומיים דחופים למניעת התרחבות הלחימה בצפון",
        "summary_hebrew": "שליחים מארה\"ב ומאירופה מקיימים התייעצויות ביטחוניות בירושלים ובביירות במאמץ למנוע הידרדרות אזורית כוללת.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, לבנון, ארה\"ב"
    },
    {
        "url": "https://www.aljazeera.com/news/2026/gaza-humanitarian-talks",
        "source_name": "Al Jazeera",
        "country": "קטר",
        "title_original": "Negotiation delegations assemble in Cairo regarding aid protocols",
        "content_original": "Regional mediators present revised mechanisms regarding security guarantees and civilian logistics in Gaza.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1000",
        "title_hebrew": "משלחות משא ומתן התכנסו בקהיר לגיבוש מתווה ביטחוני וסיוע",
        "summary_hebrew": "מתווכים מקטר ומצרים מגבשים מסמך עקרונות להסדרת המעברים והפסקת אש זמנית תחת ערבויות בינלאומיות.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, מצרים, קטר"
    },
    {
        "url": "https://english.alarabiya.net/news/2026/gulf-shipping-safety",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_original": "Coalition naval forces track maritime threats in the Red Sea corridor",
        "content_original": "Naval task forces intercept suspicious drone arrays threatening commercial transit routes.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1000",
        "title_hebrew": "כוחות קואליציה ימיים יירטו מערך כטב\"מים בים האדום",
        "summary_hebrew": "כוחות הצי המערבי הדפו מתקפת כטב\"מים של החות'ים שנועדה לשבש את תנועת כלי השיט לעבר מפרץ אילת.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, תימן, סעודיה, ארה\"ב"
    },
    {
        "url": "https://www.tehrantimes.com/news/2026/iran-strategic-announcement",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_original": "Defense officials review strategic deterrence against Western sanctions",
        "content_original": "Iranian commanders warn against any coalition measures impacting domestic infrastructure.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1000",
        "title_hebrew": "איראן מאיימת במענה צבאי מול צעדים כלכליים של המערב",
        "summary_hebrew": "בכירים בטהראן מזהירים מפני השלכות של החמרת הסנקציות וטוענים כי מערכי הטילים ערוכים לתגובה מהירה.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 0.0,
        "mentioned_countries": "איראן, ישראל, ארה\"ב"
    },
    {
        "url": "https://www.france24.com/en/middle-east/2026/europe-diplomatic-initiative",
        "source_name": "France 24",
        "country": "צרפת",
        "title_original": "European Union drafts joint resolution on Middle East stability",
        "content_original": "EU foreign ministers convene in Brussels to discuss diplomatic initiatives and funding for regional recovery.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=1000",
        "title_hebrew": "האיחוד האירופי מקדם יוזמה מדינית להסדרה אזורית",
        "summary_hebrew": "שרי החוץ בבריסל דנים בהצעת החלטה משותפת הקוראת לחידוש המו\"מ המדיני והרחבת הסיוע ההומניטרי.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 0.0,
        "mentioned_countries": "צרפת, ישראל"
    }
]

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM articles ORDER BY id DESC", conn)
    conn.close()
    return df

df = load_data()
if df.empty:
    for art in SEED_DATA:
        save_article(art)
    df = load_data()

# מנוע איסוף רציף ברקע
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
                            'sentiment_score': 1.0 if res.get('urgency') == 'מתפרצת' else 0.0,
                            'mentioned_countries': res.get('mentioned_countries_str', 'ישראל')
                        })
                    except Exception:
                        a.update({
                            'title_hebrew': a['title_original'],
                            'summary_hebrew': a['content_original'][:160],
                            'sentiment': 'שוטף',
                            'sentiment_score': 0.0,
                            'mentioned_countries': 'ישראל'
                        })
                    save_article(a)
                    time.sleep(4)
        except Exception as e:
            print(f"Worker background error: {e}")
        time.sleep(300)

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
    st.caption("ניטור רב-זירתי 24/7 | סריקה של 15+ סוכנויות בינלאומיות מובילות")
with top_c2:
    st.metric("סה\"כ דיווחים במערכת", len(df))
with top_c3:
    military_cnt = len(df[df['sentiment'].astype(str).str.contains('צבאי', na=False)])
    st.metric("דיווחים ביטחוניים", military_cnt)

st.markdown("<hr style='border-color: #1e293b; margin: 15px 0 20px 0;'>", unsafe_allow_html=True)

# --- אזור סינון וחיפוש מתקדם ---
st.markdown("##### 🔍 סינון מודיעיני ממוקד")
f_col1, f_col2, f_col3 = st.columns([3, 3, 4])

# איסוף רשימת מדינות מקור
source_countries = ["הכל"] + sorted(list(df['country'].dropna().unique()))

# איסוף רשימת כל המדינות המוזכרות מתוך השדה
all_targets = set()
for item in df['mentioned_countries'].dropna():
    for c in str(item).split(","):
        c_clean = c.strip()
        if c_clean:
            all_targets.add(c_clean)
target_countries = ["הכל"] + sorted(list(all_targets))

with f_col1:
    sel_source = st.selectbox("🌍 מדינה שבה פורסם:", source_countries)

with f_col2:
    sel_target = st.selectbox("🎯 מדינה שנוגעת לכתבה:", target_countries)

with f_col3:
    search_txt = st.text_input("🔎 חיפוש חופשי בכותרת או בתוכן:", placeholder="למשל: נתניהו, טילים, סנקציות, ביירות...")

# החלת הסינונים
filtered_df = df.copy()

if sel_source != "הכל":
    filtered_df = filtered_df[filtered_df['country'] == sel_source]

if sel_target != "הכל":
    filtered_df = filtered_df[filtered_df['mentioned_countries'].astype(str).str.contains(sel_target, case=False, na=False)]

if search_txt:
    pattern = search_txt.strip()
    filtered_df = filtered_df[
        filtered_df['title_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered_df['summary_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered_df['title_original'].astype(str).str.contains(pattern, case=False, na=False)
    ]

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

if filtered_df.empty:
    st.warning("לא נמצאו דיווחים התואמים לסינון שנבחר. נסה לבחור קריטריון אחר.")
else:
    # 1. דיווחי מוקד חמים
    st.markdown("### 🔥 דיווחי מוקד")
    hero_df = filtered_df.head(2)
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
                targets = str(row.get('mentioned_countries', 'ישראל'))
                
                st.markdown(f"""
                <div style="margin: 8px 0;">
                    <span class="badge badge-src">📰 {row.get('source_name', '')} ({row.get('country', '')})</span>
                    <span class="badge badge-cat">{cat}</span>
                    <span class="badge badge-target">🎯 נוגע ל: {targets}</span>
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
        {"title": "לבנון וחיזבאללה", "icon": "🇱🇧", "keys": ["lebanon", "hezbollah", "beirut", "לבנון", "חיזבאללה", "Al Mayadeen", "L'Orient"]},
        {"title": "רצועת עזה והעולם הערבי", "icon": "⚡", "keys": ["gaza", "hamas", "עזה", "חמאס", "Al Jazeera", "Al Arabiya", "מצרים", "קטר"]},
        {"title": "יהודה ושומרון", "icon": "🛡️", "keys": ["west bank", "settler", "jenin", "איו\"ש", "גדה", "Wafa", "שומרון"]},
        {"title": "מעצמות וזירה בינלאומית", "icon": "🌍", "keys": ["United States", "BBC", "NY Times", "France 24", "The Guardian", "אירופה", "DW", "Washington"]}
    ]

    for sec in SECTORS:
        pattern = "|".join(sec["keys"])
        sec_df = filtered_df[
            filtered_df['country'].astype(str).str.contains(pattern, case=False, na=False) |
            filtered_df['source_name'].astype(str).str.contains(pattern, case=False, na=False) |
            filtered_df['title_original'].astype(str).str.contains(pattern, case=False, na=False) |
            filtered_df['title_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
            filtered_df['summary_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
            filtered_df['mentioned_countries'].astype(str).str.contains(pattern, case=False, na=False)
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
                        targets = str(row.get('mentioned_countries', 'ישראל'))
                        
                        st.markdown(f"""
                        <div style="margin: 6px 0;">
                            <span class="badge badge-src">📰 {row.get('source_name', '')}</span>
                            <span class="badge badge-cat">{cat}</span>
                            <span class="badge badge-target">🎯 {targets}</span>
                            <span class="badge badge-time">🕒 {pub_time}</span>
                        </div>
                        """, unsafe_allow_html=True)

                        c_title = row.get('title_hebrew') or row.get('title_original')
                        st.markdown(f"<div style='font-weight: 700; color: #fff; font-size: 1.02rem; margin-bottom: 6px; line-height: 1.4;'>{c_title}</div>", unsafe_allow_html=True)

                        c_summary = str(row.get('summary_hebrew', ''))[:120]
                        st.markdown(f"<div style='font-size: 0.85rem; color: #94a3b8; line-height: 1.5; margin-bottom: 12px;'>{c_summary}...</div>", unsafe_allow_html=True)

                        c_url = row.get('url', '#')
                        st.markdown(f"<a class='read-link' href='{c_url}' target='_blank'>לכתבה המקורית ←</a>", unsafe_allow_html=True)

# 3. ארכיון מלא עם תמיכה במדינות
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
with st.expander("📂 ארכיון וכל הדיווחים מהעולם", expanded=False):
    archive_df = filtered_df[['published_at', 'source_name', 'country', 'mentioned_countries', 'sentiment', 'title_hebrew', 'url']].copy()
    archive_df.columns = ['תאריך פרסום', 'ערוץ / מקור', 'מדינת פרסום', 'נוגע למדינות', 'תחום', 'כותרת הדיווח', 'קישור ישיר']
    st.dataframe(
        archive_df,
        column_config={
            "קישור ישיר": st.column_config.LinkColumn("קישור למקור")
        },
        hide_index=True,
        use_container_width=True
    )