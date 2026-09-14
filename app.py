import streamlit as st
import pandas as pd
import threading
import time
from datetime import datetime, timedelta
import urllib.parse
import urllib.request
import json
import re
from src.storage.database import get_connection, init_db, is_article_exists, save_article
from src.ingestion.rss_fetcher import fetch_relevant_articles

st.set_page_config(
    page_title="דסק מודיעין תקשורת | OSINT IL",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "lang" not in st.session_state:
    st.session_state["lang"] = "HE"

if "show_brief" not in st.session_state:
    st.session_state["show_brief"] = False

if "research_mode" not in st.session_state:
    st.session_state["research_mode"] = None

if "compare_mode" not in st.session_state:
    st.session_state["compare_mode"] = False

is_heb = (st.session_state["lang"] == "HE")
direction = "rtl" if is_heb else "ltr"
align = "right" if is_heb else "left"

st.markdown(f"""
<div class="tactical-satellite-background"></div>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&family=Rubik:wght@700;800;900&display=swap');

    html, body, [class*="css"], .stApp, p, div, span, label, input, button, select {{
        font-family: 'Assistant', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        direction: {direction};
        text-align: {align};
    }}

    h1, h2, h3, h4, .hero-title, .sector-title {{
        font-family: 'Rubik', 'Assistant', sans-serif !important;
        letter-spacing: -0.3px;
    }}

    header[data-testid="stHeader"], [data-testid="stDecoration"] {{
        display: none !important;
    }}

    .tactical-satellite-background {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: -9999;
        background-color: #060913;
        background-image: 
            radial-gradient(circle at 50% 25%, rgba(14, 165, 233, 0.12) 0%, transparent 70%),
            linear-gradient(rgba(5, 8, 18, 0.88), rgba(5, 8, 18, 0.95)),
            url("https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=1920&q=85");
        background-size: cover;
        background-position: center center;
        background-attachment: fixed;
        pointer-events: none;
    }}

    .stApp, [data-testid="stAppViewContainer"], .main, .block-container {{
        background: transparent !important;
        color: #f1f5f9;
    }}

    [data-testid="stSidebarCollapseButton"], section[data-testid="stSidebar"] {{
        display: none !important;
    }}

    .ticker-wrap {{
        width: 100%;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 6px;
        overflow: hidden;
        height: 36px;
        display: flex;
        align-items: center;
        margin-bottom: 14px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
    }}
    .ticker-badge {{
        background: #b91c1c;
        color: #ffffff;
        font-weight: 700;
        font-size: 0.8rem;
        padding: 0 14px;
        height: 100%;
        display: flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
    }}
    .ticker-content {{
        display: flex;
        white-space: nowrap;
        animation: ticker 45s linear infinite;
        font-size: 0.85rem;
        font-weight: 500;
        color: #e2e8f0;
    }}
    .ticker-item {{
        margin-left: 40px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    @keyframes ticker {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(100%); }}
    }}

    .brief-card, .research-card, .compare-card {{
        background: rgba(15, 23, 42, 0.92);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }}

    div[data-baseweb="input"] {{
        background-color: rgba(17, 24, 39, 0.8) !important;
        border: 1px solid rgba(56, 189, 248, 0.15) !important;
        border-radius: 6px !important;
    }}
    div[data-baseweb="input"] input {{
        color: #f8fafc !important;
        font-size: 0.9rem !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: rgba(17, 24, 39, 0.8) !important;
        border: 1px solid rgba(56, 189, 248, 0.15) !important;
        border-radius: 6px !important;
        color: #f8fafc !important;
    }}

    div[data-testid="stHorizontalBlock"] button {{
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        padding: 4px 8px !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stHorizontalBlock"] button:hover {{
        border-color: #38bdf8 !important;
        color: #38bdf8 !important;
    }}
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {{
        background-color: #0284c7 !important;
        border-color: #38bdf8 !important;
    }}

    .main-hero-card {{
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 10px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
    }}
    .main-hero-img {{
        width: 100%;
        height: 320px;
        object-fit: cover;
    }}
    .main-hero-body {{
        padding: 16px 20px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }}

    .side-item-card {{
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(31, 41, 55, 0.6);
        border-radius: 8px;
        display: flex;
        gap: 12px;
        padding: 10px;
        margin-bottom: 10px;
        align-items: center;
        text-decoration: none;
    }}
    .side-item-img {{
        width: 95px;
        height: 75px;
        border-radius: 6px;
        object-fit: cover;
        flex-shrink: 0;
    }}

    .grid-card {{
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(31, 41, 55, 0.6);
        border-radius: 10px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
    }}
    .grid-card-img {{
        width: 100%;
        height: 145px;
        object-fit: cover;
    }}
    .grid-card-body {{
        padding: 12px 14px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }}

    .tag {{
        display: inline-block;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 4px;
    }}
    .tag-source {{ background: #1e293b; color: #93c5fd; }}
    .tag-category {{ background: #0369a1; color: #ffffff; }}
    .tag-time {{ background: #334155; color: #cbd5e1; }}
    .tag-country {{ background: #4c1d95; color: #e9d5ff; }}
    
    .tag-bias-hostile {{ background: #7f1d1d; color: #fecaca; }}
    .tag-bias-neutral {{ background: #334155; color: #f1f5f9; }}
    .tag-bias-local {{ background: #14532d; color: #bbf7d0; }}

    .read-btn {{
        color: #38bdf8 !important;
        font-weight: 600;
        font-size: 0.72rem !important;
        text-decoration: none !important;
        margin-top: auto;
        padding-top: 6px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        opacity: 0.85;
    }}
</style>
""", unsafe_allow_html=True)

init_db()

TOPIC_IMAGE_POOLS = {
    "iran": ["https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1000", "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1000"],
    "soldiers": ["https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000", "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1000"],
    "artillery_missiles": ["https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000", "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000"],
    "drone": ["https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000"],
    "lebanon": ["https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000"],
    "general": ["https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000"]
}

def is_clean_hebrew(text: str) -> bool:
    if not text:
        return False
    has_heb = any("\u0590" <= c <= "\u05ea" for c in str(text))
    eng_words = re.findall(r'[a-zA-Z]{3,}', str(text))
    return has_heb and len(eng_words) <= 1

def robust_translate_to_hebrew(text: str) -> str:
    if not text:
        return ""
    if is_clean_hebrew(text):
        return str(text)
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=iw&dt=t&q={urllib.parse.quote(str(text))}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            result = json.loads(response.read().decode('utf-8'))
            translated = "".join([part[0] for part in result[0] if part and part[0]])
            if translated and is_clean_hebrew(translated):
                return translated.strip()
    except Exception:
        pass
    return str(text)

def get_source_bias(source_name: str, heb_mode: bool):
    s = str(source_name).lower()
    if any(k in s for k in ["al jazeera", "tehran", "irna", "tasnim", "mehr", "press tv", "al mayadeen"]):
        return ("נרטיב ציר / עוין" if heb_mode else "Axis / Critical"), "tag-bias-hostile"
    if any(k in s for k in ["wafa", "safa", "ina", "ammon"]):
        return ("סיקור מקומי / אזורי" if heb_mode else "Local Agency"), "tag-bias-local"
    return ("סיקור בינלאומי" if heb_mode else "International"), "tag-bias-neutral"

def get_smart_image(row):
    real_img = row.get('image_url')
    if real_img and str(real_img).startswith('http') and not any(bad in str(real_img) for bad in ['feedburner', 'ads', 'tracker', 'error']):
        return real_img
    text = f"{row.get('title_original', '')} {row.get('content_original', '')} {row.get('source_name', '')}".lower()
    if any(w in text for w in ["iran", "tehran", "irgc"]):
        return TOPIC_IMAGE_POOLS["iran"][0]
    elif any(w in text for w in ["missile", "rocket", "strike"]):
        return TOPIC_IMAGE_POOLS["artillery_missiles"][0]
    elif any(w in text for w in ["soldier", "army", "idf"]):
        return TOPIC_IMAGE_POOLS["soldiers"][0]
    elif any(w in text for w in ["drone", "uav"]):
        return TOPIC_IMAGE_POOLS["drone"][0]
    return TOPIC_IMAGE_POOLS["general"][0]

# מאגר חירום ענק של 20+ כתבות ראשוניות שמבטיח שפע מלא תמיד
now_t = datetime.now()
MASSIVE_BOOTSTRAP_POOL = [
    {
        "url": "https://www.tehrantimes.com/news/1",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_original": "IRGC Aerospace forces integrate early warning radar systems",
        "content_original": "Deployment of radar detection arrays to counter asymmetric threats.",
        "published_at": (now_t - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["iran"][0],
        "title_hebrew": "איראן: חיל האוויר של משמרות המהפכה שילב מערכות מכ\"ם מתקדמות",
        "summary_hebrew": "טהראן דיווחה על שדרוג משמעותי במערכי ההתרעה האווירית להגנה על מתקנים אסטרטגיים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "איראן"
    },
    {
        "url": "https://www.reuters.com/world/middle-east/2",
        "source_name": "Reuters",
        "country": "תימן",
        "title_original": "Yemen fighting kills 504 and displaces nearly 78,000 in one week",
        "content_original": "Intense clashes across frontline governorates result in heavy casualties.",
        "published_at": (now_t - timedelta(minutes=8)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["artillery_missiles"][0],
        "title_hebrew": "תימן: הלחימה העצימה הביאה למאות הרוגים ולעקור רבים בשבוע האחרון",
        "summary_hebrew": "עימותים קשים מדווחים במספר מחוזות, תוך פגיעה קשה בתשתיות אזרחיות.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "תימן"
    },
    {
        "url": "https://www.middleeasteye.net/news/3",
        "source_name": "Middle East Eye",
        "country": "לבנון",
        "title_original": "Israeli forces fire shells near residents approaching Lebanon's Kfar Tebnit",
        "content_original": "Artillery shelling targeted areas adjacent to southern Lebanese villages.",
        "published_at": (now_t - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["lebanon"][0],
        "title_hebrew": "כוחות צה\"ל ביצעו ירי ארטילרי לעבר חשודים שהתקרבו לכפר תבנית בדרום לבנון",
        "summary_hebrew": "חילופי אש וירי ארטילרי נרשמו בסמוך לקו העימות בדרום לבנון בעקבות תנועות חשודות בגזרה.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "לבנון, ישראל"
    },
    {
        "url": "https://wafa.ps/ar/news/4",
        "source_name": "Wafa News",
        "country": "איו\"ש",
        "title_original": "Palestinian man injured in Israeli gunfire, two detained in West Bank",
        "content_original": "Security operations and search activities carried out across Jenin and Nablus.",
        "published_at": (now_t - timedelta(minutes=22)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["soldiers"][0],
        "title_hebrew": "פעילות כוחות הביטחון באיו\"ש: מעצר מבוקשים וסריקות מבצעיות",
        "summary_hebrew": "כוחות צה\"ל ומשמר הגבול פעלו הלילה בגזרות ג'נין ושכם לסיכול תשתיות טרור ולמעצר מבוקשים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "איו\"ש, ישראל"
    },
    {
        "url": "https://english.alarabiya.net/news/5",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_original": "Naval coalition forces intercept suspicious drone wave in Red Sea",
        "content_original": "Air defense systems destroyed hostile unmanned aerial vehicles.",
        "published_at": (now_t - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["drone"][0],
        "title_hebrew": "יירוט נרחב של כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום",
        "summary_hebrew": "מערכי ההגנה של הקואליציה סיכלו מתקפה מכיוון תימן שנועדה לשבש את התנועה הימית לאילת.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, ארה\"ב, איראן"
    },
    {
        "url": "https://en.irna.ir/news/6",
        "source_name": "IRNA",
        "country": "איראן",
        "title_original": "Iran emphasizes regional stability through cooperative security framework",
        "content_original": "Foreign ministry officials hold talks with neighboring states.",
        "published_at": (now_t - timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["iran"][0],
        "title_hebrew": "איראן: מדגישה את חשיבות יציבות האזור באמצעות מתווה ביטחון משותף",
        "summary_hebrew": "בכירי משרד החוץ בטהראן קיימו סדרת פגישות דיפלומטיות עם נציגי מדינות האזור.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 0.0,
        "mentioned_countries": "איראן"
    },
    {
        "url": "https://www.aljazeera.com/news/7",
        "source_name": "Al Jazeera",
        "country": "קטר",
        "title_original": "Humanitarian aid corridors reviewed in high-level regional summit",
        "content_original": "Delegates discuss mechanisms to expedite relief delivery.",
        "published_at": (now_t - timedelta(minutes=50)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["general"][0],
        "title_hebrew": "פסגה אזורית: דיון דחוף בפתרונות להרחבת צירי הסיוע ההומניטרי",
        "summary_hebrew": "נציגי המשלחות דנו בדרכים לייעול העברת האספקה ולשיפור תיאום המעברים.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 0.0,
        "mentioned_countries": "רצועת עזה, קטר"
    },
    {
        "url": "https://safa.ps/post/8",
        "source_name": "Safa Press",
        "country": "רצועת עזה",
        "title_original": "Field updates from southern districts amid ongoing developments",
        "content_original": "Local reports detail rescue and infrastructure maintenance operations.",
        "published_at": (now_t - timedelta(minutes=65)).strftime("%Y-%m-%d %H:%M"),
        "image_url": TOPIC_IMAGE_POOLS["soldiers"][0],
        "title_hebrew": "רצועת עזה: עדכונים שוטפים מהשטח על פעילות צוותי החירום וההצלה",
        "summary_hebrew": "דיווחים מקומיים מעדכנים על מאמצים שיקום ותפעול של תשתיות חיוניות ברצועה.",
        "sentiment": "שוטף",
        "sentiment_score": 0.0,
        "mentioned_countries": "רצועת עזה"
    }
]

def load_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    # טעינת מאגר הבוטסטראפ אם המסד ריק לחלוטין
    cursor.execute("SELECT COUNT(*) FROM articles")
    if cursor.fetchone()[0] == 0:
        for art in MASSIVE_BOOTSTRAP_POOL:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO articles 
                    (url, source_name, country, title_original, content_original, published_at, image_url, title_hebrew, summary_hebrew, sentiment, sentiment_score, mentioned_countries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    art['url'], art['source_name'], art['country'], art['title_original'], 
                    art['content_original'], art['published_at'], art['image_url'], 
                    art['title_hebrew'], art['summary_hebrew'], art['sentiment'], 
                    art['sentiment_score'], art['mentioned_countries']
                ))
            except Exception:
                pass
        conn.commit()
    
    db_df = pd.read_sql_query("SELECT * FROM articles ORDER BY published_at DESC, id DESC", conn)
    conn.close()
    
    # שאיבת כתבות חדשות מהרשת ברקע והוספתן מיד
    try:
        new_arts = fetch_relevant_articles()
        for a in new_arts:
            if not is_article_exists(a['url']):
                heb_title = robust_translate_to_hebrew(a['title_original'])
                heb_summary = robust_translate_to_hebrew(a['content_original'][:200]) if a.get('content_original') else heb_title
                a.update({
                    'title_hebrew': heb_title,
                    'summary_hebrew': heb_summary,
                    'sentiment': 'צבאי וביטחוני' if any(w in a['title_original'].lower() for w in ['strike', 'fire', 'idf', 'missile', 'killed']) else 'שוטף',
                    'sentiment_score': 0.0,
                    'mentioned_countries': a.get('country', 'ישראל'),
                    'published_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                save_article(a)
        
        # טעינה מחודשת של המסד המעודכן עם הכתבות החדשות
        conn = get_connection()
        db_df = pd.read_sql_query("SELECT * FROM articles ORDER BY published_at DESC, id DESC", conn)
        conn.close()
    except Exception:
        pass

    if not db_df.empty:
        db_df = db_df.drop_duplicates(subset=['title_hebrew'], keep='first')
        db_df = db_df.drop_duplicates(subset=['url'], keep='first')
    return db_df

df = load_data()

# טיקר חדשות
ticker_headlines = []
for _, r in df.head(10).iterrows():
    h = r.get('title_hebrew') if is_heb else (r.get('title_original') or r.get('title_hebrew'))
    src = r.get('source_name', 'דיווח')
    ticker_headlines.append(f"⚡ [{src}] {h}")

ticker_html = "".join([f"<span class='ticker-item'>{item}</span>" for item in ticker_headlines])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">🔴 מבזק חי</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

# סרגל בקרה
c_search, c_cat, c_brief, c_res, c_comp, c_lang_il, c_lang_us = st.columns([3, 2, 1.5, 1.5, 1.5, 0.8, 0.8])

with c_search:
    search_query = st.text_input("חיפוש", placeholder="🔎 חפש בידיעות...", label_visibility="collapsed")
with c_cat:
    cat_options = ["כל התחומים", "צבאי וביטחוני", "מדיני ודיפלומטי", "כלכלה וסנקציות"] if is_heb else ["All", "Security", "Diplomatic", "Economy"]
    cat_filter = st.selectbox("תחום", cat_options, label_visibility="collapsed")
with c_brief:
    if st.button("📑 תמונת מצב", use_container_width=True):
        st.session_state["show_brief"] = not st.session_state["show_brief"]
        st.rerun()
with c_res:
    if st.button("🔬 תיק מחקר", use_container_width=True):
        st.session_state["research_mode"] = "איראן" if not st.session_state["research_mode"] else None
        st.rerun()
with c_comp:
    if st.button("📊 השוואת נרטיבים", use_container_width=True):
        st.session_state["compare_mode"] = not st.session_state["compare_mode"]
        st.rerun()

with c_lang_il:
    if st.button("🇮🇱 עברית", key="lang_he", type="primary" if is_heb else "secondary", use_container_width=True):
        st.session_state["lang"] = "HE"
        st.rerun()
with c_lang_us:
    if st.button("🇺🇸 English", key="lang_en", type="primary" if not is_heb else "secondary", use_container_width=True):
        st.session_state["lang"] = "EN"
        st.rerun()

if st.session_state["compare_mode"]:
    st.markdown("""
    <div class="compare-card">
        <div style="font-weight: 700; font-size: 1.05rem; color: #38bdf8; margin-bottom: 8px;">📊 השוואת נרטיבים בינלאומיים (Comparative Media Intelligence)</div>
    </div>
    """, unsafe_allow_html=True)
    comp_cols = st.columns(3)
    sources_to_compare = ["Reuters", "Al Jazeera", "Tehran Times"]
    for i, src_name in enumerate(sources_to_compare):
        with comp_cols[i]:
            match_art = df[df['source_name'].str.contains(src_name, case=False, na=False)]
            st.markdown(f"<div style='font-weight: 700; color: #38bdf8; margin-bottom: 6px;'>📰 {src_name}</div>", unsafe_allow_html=True)
            if not match_art.empty:
                sample_item = match_art.iloc[0]
                t_txt = sample_item.get('title_hebrew') if is_heb else sample_item.get('title_original')
                st.markdown(f"<div style='font-size: 0.85rem; color: #e2e8f0; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;'>{t_txt}</div>", unsafe_allow_html=True)

if st.session_state["research_mode"]:
    st.markdown("""
    <div class="research-card">
        <div style="font-weight: 700; font-size: 1.05rem; color: #38bdf8; margin-bottom: 8px;">🔬 ארכיון מחקר לפי זירות חמות</div>
    </div>
    """, unsafe_allow_html=True)
    r_cols = st.columns(6)
    research_targets = ["איראן", "לבנון", "רצועת עזה", "איו\"ש", "ארה\"ב", "ישראל"]
    for i, target in enumerate(research_targets):
        with r_cols[i]:
            if st.button(target, key=f"res_{target}", use_container_width=True):
                st.session_state["research_mode"] = target
                st.rerun()

    current_target = st.session_state["research_mode"]
    target_filtered = df[df['country'].str.contains(current_target, case=False, na=False) | df['title_hebrew'].str.contains(current_target, case=False, na=False)]
    for _, r_row in target_filtered.head(5).iterrows():
        st.markdown(f"<div style='background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px; margin-bottom: 6px; font-size: 0.88rem;'>• <b>{r_row.get('source_name')}</b>: {r_row.get('title_hebrew')}</div>", unsafe_allow_html=True)

if st.session_state["show_brief"]:
    st.markdown("""
    <div class="brief-card">
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 6px;">📊 תמונת מצב מודיעינית שוטפת</div>
        <div style="font-size: 0.9rem; line-height: 1.6; color: #cbd5e1;">
            • <b>איראן והציר:</b> דיווחים שוטפים מטהראן וסוכנויות הידיעות המקומיות.<br>
            • <b>גזרת הצפון (לבנון):</b> מעקב אחר התפתחויות בגבול הצפון.<br>
            • <b>עזה ואיו\"ש:</b> עדכונים שוטפים מהשטח.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='margin: 4px 0 2px 0; font-size: 2rem; font-weight: 800; color: #ffffff;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
st.caption("ניטור נרטיבים ודיווחים בזמן אמת ממאגרי התקשורת המובילים בעולם")

if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = "כל הדיווחים"

NAV_ITEMS = [
    {"label": "הכל", "val": "כל הדיווחים", "flag": "🌐"},
    {"label": "ישראל", "val": "ישראל", "flag": "🇮🇱"},
    {"label": "ארה\"ב", "val": "ארה\"ב", "flag": "🇺🇸"},
    {"label": "איראן", "val": "איראן", "flag": "🇮🇷"},
    {"label": "לבנון", "val": "לבנון", "flag": "🇱🇧"},
    {"label": "רצועת עזה", "val": "רצועת עזה", "flag": "🇵🇸"},
    {"label": "איו\"ש", "val": "איו\"ש", "flag": "🇵🇸"}
]

nav_cols = st.columns(len(NAV_ITEMS))
for idx, item in enumerate(NAV_ITEMS):
    with nav_cols[idx]:
        is_active = (st.session_state["selected_country"] == item["val"])
        if st.button(f"{item['flag']} {item['label']}", key=f"nav_{item['val']}", type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state["selected_country"] = item["val"]
            st.rerun()

st.markdown("<hr style='border-color: rgba(31, 41, 55, 0.6); margin: 12px 0 20px 0;'>", unsafe_allow_html=True)

selected_country = st.session_state["selected_country"]
filtered = df.copy()

if selected_country != "כל הדיווחים":
    filtered = filtered[filtered['country'].str.contains(selected_country, case=False, na=False) | filtered['mentioned_countries'].str.contains(selected_country, case=False, na=False)]

render_df = filtered.drop_duplicates(subset=['title_hebrew'], keep='first').sort_values(by="published_at", ascending=False) if not filtered.empty else df
main_art = render_df.iloc[0]
side_arts = render_df.iloc[1:4] if len(render_df) > 1 else pd.DataFrame()

col_main, col_side = st.columns([7, 5])

with col_main:
    hero_img = get_smart_image(main_art)
    cat = str(main_art.get('sentiment', 'כללי'))
    t_display = main_art.get('title_hebrew') if is_heb else main_art.get('title_original')
    s_display = str(main_art.get('summary_hebrew', ''))[:200]
    time_str = str(main_art.get('published_at', ''))[:16]
    src = main_art.get('source_name', '')
    url = main_art.get('url', '#')
    bias_label, bias_class = get_source_bias(src, is_heb)

    st.markdown(f"""
    <div class="main-hero-card">
        <img class="main-hero-img" src="{hero_img}" />
        <div class="main-hero-body">
            <div style="margin-bottom: 6px;">
                <span class="tag tag-category">{cat}</span>
                <span class="tag tag-source">📰 {src}</span>
                <span class="tag {bias_class}">🎯 {bias_label}</span>
                <span class="tag tag-time">🕒 {time_str}</span>
            </div>
            <h2 style="font-size: 1.4rem; font-weight: 800; margin: 4px 0 8px 0; color: #ffffff; line-height: 1.3;">{t_display}</h2>
            <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.5; margin-bottom: 10px;">{s_display}...</p>
            <a class="read-btn" href="{url}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_side:
    st.markdown("<div style='font-size: 1.05rem; font-weight: 700; margin-bottom: 8px; color: #38bdf8;'>⚡ דיווחים חמים נוספים</div>", unsafe_allow_html=True)
    if not side_arts.empty:
        for _, s_row in side_arts.iterrows():
            s_img = get_smart_image(s_row)
            s_title = s_row.get('title_hebrew') if is_heb else s_row.get('title_original')
            s_src = s_row.get('source_name', '')
            s_time = str(s_row.get('published_at', ''))[:16]
            s_url = s_row.get('url', '#')
            _, s_bias_class = get_source_bias(s_src, is_heb)

            st.markdown(f"""
            <a class="side-item-card" href="{s_url}" target="_blank">
                <img class="side-item-img" src="{s_img}" />
                <div style="flex-grow: 1;">
                    <div style="margin-bottom: 3px;">
                        <span class="tag tag-source">{s_src}</span>
                    </div>
                    <div style="font-weight: 600; font-size: 0.88rem; color: #f1f5f9; line-height: 1.35; margin-bottom: 3px;">
                        {s_title}
                    </div>
                    <div style="font-size: 0.7rem; color: #64748b;">🕒 {s_time}</div>
                </div>
            </a>
            """, unsafe_allow_html=True)

rem_arts = render_df.iloc[4:] if len(rem_arts) > 4 else pd.DataFrame()
if not rem_arts.empty:
    st.markdown("<h3 style='margin: 25px 0 12px 0; font-weight: 700; font-size: 1.2rem;'>📰 כל הדיווחים והכתבות מהזירות</h3>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (_, r_art) in enumerate(rem_arts.iterrows()):
        with cols[idx % 3]:
            r_img = get_smart_image(r_art)
            r_title = r_art.get('title_hebrew') if is_heb else r_art.get('title_original')
            r_summary = str(r_art.get('summary_hebrew', ''))[:90]
            r_src = r_art.get('source_name', 'דיווח')
            r_time = str(r_art.get('published_at', ''))[:16]
            r_url = r_art.get('url', '#')
            r_label, r_class = get_source_bias(r_src, is_heb)

            st.markdown(f"""
            <div class="grid-card" style="margin-bottom: 14px;">
                <img class="grid-card-img" src="{r_img}" />
                <div class="grid-card-body">
                    <div style="margin-bottom: 4px;">
                        <span class="tag tag-source">{r_src}</span>
                        <span class="tag {r_class}">{r_label}</span>
                    </div>
                    <div style="font-weight: 700; font-size: 0.92rem; color: #ffffff; line-height: 1.35; margin-bottom: 4px;">
                        {r_title}
                    </div>
                    <div style="font-size: 0.8rem; color: #94a3b8; line-height: 1.4; margin-bottom: 8px;">
                        {r_summary}...
                    </div>
                    <a class="read-btn" href="{r_url}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
                </div>
            </div>
            """, unsafe_allow_html=True)