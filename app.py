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

# עיצוב מתקדם בסגנון פורטל ספורט/חדשות כהה
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;900&display=swap');

    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Heebo', sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    [data-testid="stSidebarCollapseButton"], section[data-testid="stSidebar"] {
        display: none !important;
    }

    /* תיבת חיפוש וסינון עליונה מעוצבת */
    .filter-wrapper {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 20px;
    }

    /* כרטיס ראשי ענק בסגנון אתר ספורט */
    .main-hero-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: border-color 0.2s;
    }
    .main-hero-card:hover {
        border-color: #38bdf8;
    }
    .main-hero-img {
        width: 100%;
        height: 340px;
        object-fit: cover;
    }
    .main-hero-body {
        padding: 18px 22px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    /* כרטיסי הרשימה הצדדית (3 כתבות לצד הראשית) */
    .side-item-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        display: flex;
        gap: 12px;
        padding: 10px;
        margin-bottom: 12px;
        align-items: center;
        transition: transform 0.2s, border-color 0.2s;
        text-decoration: none;
    }
    .side-item-card:hover {
        border-color: #0284c7;
        transform: translateX(-4px);
    }
    .side-item-img {
        width: 105px;
        height: 80px;
        border-radius: 6px;
        object-fit: cover;
        flex-shrink: 0;
    }

    /* כרטיסי גריד תחתונים */
    .grid-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s, border-color 0.2s;
    }
    .grid-card:hover {
        border-color: #0284c7;
        transform: translateY(-3px);
    }
    .grid-card-img {
        width: 100%;
        height: 155px;
        object-fit: cover;
    }
    .grid-card-body {
        padding: 14px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    /* תגים */
    .tag {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 5px;
    }
    .tag-source { background: #1e293b; color: #93c5fd; }
    .tag-category { background: #0369a1; color: #ffffff; }
    .tag-time { background: #334155; color: #cbd5e1; }
    .tag-country { background: #4c1d95; color: #e9d5ff; }

    .read-btn {
        color: #38bdf8 !important;
        font-weight: 700;
        font-size: 0.82rem;
        text-decoration: none;
        margin-top: auto;
        padding-top: 8px;
        display: inline-block;
    }
    .read-btn:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

init_db()

# פונקציה לבחירת תמונה חכמה לפי תוכן הכתבה
def get_smart_image(title: str, content: str, default_img: str) -> str:
    text = f"{title} {content}".lower()
    if any(w in text for w in ["missile", "rocket", "strike", "drone", "blast", "attack", "טיל", "יירוט", "תקיפה", "כטב", "פיצוץ"]):
        return "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?w=1000"
    if any(w in text for w in ["soldier", "army", "idf", "tank", "troops", "military", "צבא", "צהל", "לוחמ"]):
        return "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=1000"
    if any(w in text for w in ["iran", "tehran", "nuclear", "איראן", "טהראן", "גרעין"]):
        return "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1000"
    if any(w in text for w in ["lebanon", "beirut", "hezbollah", "לבנון", "ביירות", "חיזבאללה"]):
        return "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000"
    if any(w in text for w in ["gaza", "hamas", "עזה", "חמאס", "רפיח"]):
        return "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1000"
    if any(w in text for w in ["summit", "biden", "white house", "diplomacy", "minister", "מדיני", "ארה\"ב", "פסגה", "בלינקן"]):
        return "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1000"
    if default_img and "unsplash" not in default_img and "http" in default_img:
        return default_img
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000"

# נתוני אתחול מעודכנים
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
SEED_DATA = [
    {
        "url": "https://www.aljazeera.com/news/liveblog/2026/mideast-security",
        "source_name": "Al Jazeera",
        "country": "קטר",
        "title_original": "Regional security summits address border stabilization and maritime protocols",
        "content_original": "Mediators assemble to coordinate ceasefire conditions and security mechanisms across frontiers.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1000",
        "title_hebrew": "מגעים בינלאומיים דחופים לגיבוש מתווה ביטחוני וייצוב קווי הגבול",
        "summary_hebrew": "משלחות תיווך אזוריות מקיימות התייעצויות אינטנסיביות למניעת הסלמה ולהסדרת מנגנוני פיקוח הדדיים.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, ארה\"ב, קטר"
    },
    {
        "url": "https://english.alarabiya.net/news/2026/red-sea-defense",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_original": "Coalition naval forces engage aerial targets over international shipping routes",
        "content_original": "Naval systems shoot down hostile drone salvos launched toward navigation corridors.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?w=1000",
        "title_hebrew": "יירוט נרחב של כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום",
        "summary_hebrew": "מערכי ההגנה של הקואליציה סיכלו מתקפה מכיוון תימן שנועדה לשבש את התנועה הימית לאילת.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, ארה\"ב, איראן"
    },
    {
        "url": "https://www.bbc.com/news/world-middle-east-2026-lebanon",
        "source_name": "BBC News",
        "country": "בריטניה",
        "title_original": "Northern border exchanges intensify amid diplomatic efforts in Beirut",
        "content_original": "Field intelligence reports track reciprocal fire and air defense responses across border communities.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000",
        "title_hebrew": "הסלמה בחילופי האש לאורך קו העימות בלבנון לצד מאמץ תיווך צרפתי",
        "summary_hebrew": "סדרת תקיפות ממוקדות בדרום לבנון בעקבות שיגורים לעבר הגליל, במקביל למגעים דיפלומטיים בביירות.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "לבנון, ישראל"
    },
    {
        "url": "https://www.tehrantimes.com/news/2026/iran-tactical-aerospace",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_original": "Tehran unveils integrated air surveillance grid",
        "content_original": "Aerospace commanders declare activation of early-warning radar arrays and mobile deterrent batteries.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1000",
        "title_hebrew": "איראן הודיעה על פריסת מערכות התרעה ומכ\"ם חדשות",
        "summary_hebrew": "פיקוד ההגנה האווירית של משמרות המהפכה טוען לשדרוג יכולות היירוט מול כלי טיס בלתי מאוישים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 0.0,
        "mentioned_countries": "איראן, ישראל, ארה\"ב"
    },
    {
        "url": "https://wafa.ps/ar/news/2026/west-bank-reports",
        "source_name": "Wafa",
        "country": "איו\"ש",
        "title_original": "Security operations and movement regulations across northern sectors",
        "content_original": "Field reports on checkpoints and logistical routes around commercial hubs in Nablus and Jenin.",
        "published_at": now_str,
        "image_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=1000",
        "title_hebrew": "פעילות ביטחונית וסריקות צה\"ל במוקדי חיכוך באיו\"ש",
        "summary_hebrew": "כוחות הביטחון פעלו הלילה בגזרות ג'נין ושכם לסיכול תשתיות טרור ולמעצר מבוקשים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 0.0,
        "mentioned_countries": "איו\"ש, ישראל"
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

# מנוע איסוף ברקע כל 10 דקות
def background_worker():
    while True:
        try:
            arts = fetch_relevant_articles()
            for a in arts:
                if not is_article_exists(a['url']):
                    try:
                        res = analyze_article(a['title_original'], a['content_original'])
                        smart_img = get_smart_image(a['title_original'], a['content_original'], a.get('image_url'))
                        a.update({
                            'title_hebrew': res.get('title_hebrew'),
                            'summary_hebrew': res.get('summary_hebrew'),
                            'sentiment': res.get('category'),
                            'sentiment_score': 1.0 if res.get('urgency') == 'מתפרצת' else 0.0,
                            'mentioned_countries': res.get('mentioned_countries_str', 'ישראל'),
                            'image_url': smart_img
                        })
                    except Exception:
                        a.update({
                            'title_hebrew': a['title_original'],
                            'summary_hebrew': a['content_original'][:160],
                            'sentiment': 'שוטף',
                            'sentiment_score': 0.0,
                            'mentioned_countries': 'ישראל',
                            'image_url': get_smart_image(a['title_original'], a['content_original'], a.get('image_url'))
                        })
                    save_article(a)
                    time.sleep(4)
        except Exception as e:
            print(f"Worker background error: {e}")
        time.sleep(600)

@st.cache_resource
def start_worker():
    t = threading.Thread(target=background_worker, daemon=True)
    t.start()
    return True

start_worker()

# --- 1. שורת סינון וחיפוש עליונה מעוצבת ---
c_search, c_cat = st.columns([7, 3])
with c_search:
    search_query = st.text_input("חיפוש", placeholder="🔎 חפש בידיעות: נתניהו, טילים, הפסקת אש, ביירות...", label_visibility="collapsed")
with c_cat:
    cat_filter = st.selectbox("תחום", ["כל התחומים", "צבאי וביטחוני", "מדיני ודיפלומטי", "כלכלה וסנקציות"], label_visibility="collapsed")

# --- 2. כותרת האתר ---
st.markdown("<h1 style='margin: 10px 0 4px 0; font-size: 2.2rem; font-weight: 900; color: #ffffff;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
st.caption("ניטור נרטיבים ודיווחים בזמן אמת ממאגרי התקשורת המובילים בעולם")

# --- 3. תפריט מדינות עליון בסגנון ערוץ ספורט (Sport 1 Navbar) ---
COUNTRIES_NAV = ["כל הדיווחים", "ישראל", "ארה\"ב", "איראן", "לבנון", "רצועת עזה", "איו\"ש"]
selected_country = st.radio(
    "בחר מדינה",
    COUNTRIES_NAV,
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("<hr style='border-color: #1f2937; margin: 12px 0 24px 0;'>", unsafe_allow_html=True)

# סינון הנתונים
filtered = df.copy()

# סינון מדינה (כולל איפה פורסם וגם על מי זה נוגע!)
if selected_country != "כל הדיווחים":
    synonyms = {
        "ישראל": ["ישראל", "israel", "idf", "נתניהו"],
        "ארה\"ב": ["ארה\"ב", "ארצות הברית", "united states", "biden", "וושינגטון"],
        "איראן": ["איראן", "iran", "tehran", "טהראן"],
        "לבנון": ["לבנון", "lebanon", "beirut", "חיזבאללה"],
        "רצועת עזה": ["עזה", "gaza", "חמאס", "רפיח"],
        "איו\"ש": ["איו\"ש", "יהודה ושומרון", "גדה", "west bank", "ג'נין", "שכם"]
    }
    keys = synonyms.get(selected_country, [selected_country])
    pattern = "|".join(keys)
    filtered = filtered[
        filtered['country'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered['mentioned_countries'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered['title_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered['summary_hebrew'].astype(str).str.contains(pattern, case=False, na=False)
    ]

if cat_filter != "כל התחומים":
    filtered = filtered[filtered['sentiment'] == cat_filter]

if search_query:
    p = search_query.strip()
    filtered = filtered[
        filtered['title_hebrew'].astype(str).str.contains(p, case=False, na=False) |
        filtered['summary_hebrew'].astype(str).str.contains(p, case=False, na=False) |
        filtered['title_original'].astype(str).str.contains(p, case=False, na=False)
    ]

# --- 4. מבנה דף הבית (Main Hero + Side Feed) בדיוק כמו ספורט 1 ---
if filtered.empty:
    st.info(f"לא נמצאו דיווחים התואמים לקריטריון עבור '{selected_country}'.")
else:
    main_art = filtered.iloc[0]
    side_arts = filtered.iloc[1:4] if len(filtered) > 1 else pd.DataFrame()

    col_main, col_side = st.columns([7, 5])

    # כתבה ראשית גדולה (מימין)
    with col_main:
        hero_img = get_smart_image(main_art['title_original'], main_art['content_original'], main_art.get('image_url'))
        cat = str(main_art.get('sentiment', 'כללי'))
        t_heb = main_art.get('title_hebrew') or main_art.get('title_original')
        s_heb = str(main_art.get('summary_hebrew', ''))[:220]
        time_str = str(main_art.get('published_at', 'שעות אחרונות'))[:16]
        src = main_art.get('source_name', '')
        c_name = main_art.get('country', '')
        targets = str(main_art.get('mentioned_countries', ''))
        url = main_art.get('url', '#')

        st.markdown(f"""
        <div class="main-hero-card">
            <img class="main-hero-img" src="{hero_img}" alt="Main story" />
            <div class="main-hero-body">
                <div style="margin-bottom: 8px;">
                    <span class="tag tag-category">{cat}</span>
                    <span class="tag tag-source">📰 {src} ({c_name})</span>
                    <span class="tag tag-country">🎯 נוגע ל: {targets}</span>
                    <span class="tag tag-time">🕒 {time_str}</span>
                </div>
                <h2 style="font-size: 1.55rem; font-weight: 900; margin: 6px 0 10px 0; color: #ffffff; line-height: 1.35;">{t_heb}</h2>
                <p style="color: #94a3b8; font-size: 0.98rem; line-height: 1.6; margin-bottom: 14px;">{s_heb}...</p>
                <a class="read-btn" href="{url}" target="_blank">לקריאת הדיווח המקורי בערוץ ←</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 3 מבזקים צדדיים עם תמונות (משמאל)
    with col_side:
        st.markdown("<div style='font-size: 1.15rem; font-weight: 800; margin-bottom: 10px; color: #38bdf8;'>⚡ דיווחים חמים נוספים</div>", unsafe_allow_html=True)
        if not side_arts.empty:
            for _, s_row in side_arts.iterrows():
                s_img = get_smart_image(s_row['title_original'], s_row['content_original'], s_row.get('image_url'))
                s_title = s_row.get('title_hebrew') or s_row.get('title_original')
                s_src = s_row.get('source_name', '')
                s_time = str(s_row.get('published_at', ''))[:16]
                s_cat = str(s_row.get('sentiment', 'כללי'))
                s_url = s_row.get('url', '#')

                st.markdown(f"""
                <a class="side-item-card" href="{s_url}" target="_blank">
                    <img class="side-item-img" src="{s_img}" />
                    <div style="flex-grow: 1;">
                        <div style="margin-bottom: 4px;">
                            <span class="tag tag-source">{s_src}</span>
                            <span class="tag tag-category">{s_cat}</span>
                        </div>
                        <div style="font-weight: 700; font-size: 0.92rem; color: #f1f5f9; line-height: 1.4; margin-bottom: 4px;">
                            {s_title}
                        </div>
                        <div style="font-size: 0.75rem; color: #64748b;">🕒 {s_time}</div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

    # --- 5. גריד דיווחים נוספים מהעולם ---
    rem_arts = filtered.iloc[4:] if len(filtered) > 4 else pd.DataFrame()
    if not rem_arts.empty:
        st.markdown("<h3 style='margin: 35px 0 15px 0; font-weight: 800;'>📰 כל הדיווחים והכתבות</h3>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, (_, r_art) in enumerate(rem_arts.iterrows()):
            with cols[idx % 3]:
                r_img = get_smart_image(r_art['title_original'], r_art['content_original'], r_art.get('image_url'))
                r_title = r_art.get('title_hebrew') or r_art.get('title_original')
                r_summary = str(r_art.get('summary_hebrew', ''))[:110]
                r_cat = str(r_art.get('sentiment', 'כללי'))
                r_src = r_art.get('source_name', '')
                r_time = str(r_art.get('published_at', ''))[:16]
                r_url = r_art.get('url', '#')

                st.markdown(f"""
                <div class="grid-card" style="margin-bottom: 18px;">
                    <img class="grid-card-img" src="{r_img}" />
                    <div class="grid-card-body">
                        <div style="margin-bottom: 6px;">
                            <span class="tag tag-source">{r_src}</span>
                            <span class="tag tag-category">{r_cat}</span>
                            <span class="tag tag-time">🕒 {r_time}</span>
                        </div>
                        <div style="font-weight: 700; font-size: 0.98rem; color: #ffffff; line-height: 1.4; margin-bottom: 6px;">
                            {r_title}
                        </div>
                        <div style="font-size: 0.84rem; color: #94a3b8; line-height: 1.5; margin-bottom: 10px;">
                            {r_summary}...
                        </div>
                        <a class="read-btn" href="{r_url}" target="_blank">לכתבה המלאה ←</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)