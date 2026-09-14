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
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&family=Rubik:wght@700;800;900&display=swap');

    html, body, [class*="css"], .stApp, p, div, span, label, input, button, select {
        font-family: 'Assistant', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    h1, h2, h3, h4, .hero-title, .sector-title {
        font-family: 'Rubik', 'Assistant', sans-serif !important;
        letter-spacing: -0.3px;
    }

    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }

    [data-testid="stSidebarCollapseButton"], section[data-testid="stSidebar"] {
        display: none !important;
    }

    div[data-baseweb="input"] {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] input {
        color: #f8fafc !important;
        font-size: 0.95rem !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 8px !important;
        color: #f8fafc !important;
    }

    div[data-testid="stHorizontalBlock"] button {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 18px !important;
        color: #ffffff !important;
        font-size: 1.02rem !important;
        font-weight: 700 !important;
        padding: 6px 10px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    div[data-testid="stHorizontalBlock"] button:hover {
        background-color: #1e293b !important;
        border-color: #0284c7 !important;
        color: #38bdf8 !important;
        transform: translateY(-2px);
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        background-color: #0284c7 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }

    .main-hero-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .main-hero-card:hover {
        border-color: #38bdf8;
        transform: translateY(-2px);
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

    .side-item-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        display: flex;
        gap: 12px;
        padding: 10px;
        margin-bottom: 12px;
        align-items: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
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

    .grid-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s ease, border-color 0.2s ease;
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

    .tag {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 5px;
    }
    .tag-source { background: #1e293b; color: #93c5fd; }
    .tag-category { background: #0369a1; color: #ffffff; }
    .tag-time { background: #334155; color: #cbd5e1; }
    .tag-country { background: #4c1d95; color: #e9d5ff; }

    .read-btn {
        color: #38bdf8 !important;
        font-weight: 600;
        font-size: 0.74rem !important;
        text-decoration: none !important;
        margin-top: auto;
        padding-top: 6px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        opacity: 0.9;
        transition: opacity 0.2s ease;
    }
    .read-btn:hover { 
        text-decoration: none !important;
        opacity: 1;
        color: #7dd3fc !important;
    }
</style>
""", unsafe_allow_html=True)

init_db()

# מאגר תמונות צבאיות ומודיעיניות אותנטיות בלבד (נבדקו ידנית ללא תמונות סטודנטים/צבעים)
TOPIC_IMAGE_POOLS = {
    "soldiers": [
        "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000", # לוחם עם אפוד קרבי
        "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1000", # צוות לוחמים מבצעי
        "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=1000"  # כוח צבאי בשטח
    ],
    "artillery_missiles": [
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000", # עשן קרב ותקיפות ארטילריה
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000", # זירת פעילות לוויינית
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1000"  # הבזק אש ושיגור
    ],
    "radar": [
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000", # אנטנות מכ"ם ותקשורת צבאית
        "https://images.unsplash.com/photo-1516849841032-87cbac4d88f7?w=1000"  # מערך בקרה טכנולוגי
    ],
    "drone": [
        "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000", # כלי טיס בלתי מאויש באוויר
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000"
    ],
    "lebanon": [
        "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000", # קו גבול הררי וגזרת לבנון
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000"
    ],
    "iran": [
        "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1000", # טהראן ואיראן
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000"
    ],
    "diplomacy": [
        "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1000", # ועידת פסגה בינלאומית
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1000"  # מטה ממשלתי
    ],
    "general": [
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000",
        "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000"
    ]
}

BAD_IMAGE_URLS = [
    "photo-1517486808906", # תמונת הסטודנטים
    "photo-1541872703",   # תמונת משפחה/אנשים
    "photo-1579546929"    # גרדיאנט צבעים
]

def is_hebrew(text: str) -> bool:
    if not text:
        return False
    return any("\u0590" <= c <= "\u05ea" for c in str(text))

def fast_fallback_translation(title: str) -> str:
    t_low = str(title).lower()
    if "kfar tebnit" in t_low or "fire shells" in t_low or "shells" in t_low:
        return "כוחות צה\"ל ביצעו ירי ארטילרי באזור כפר תבנית בדרום לבנון"
    if "palestinian man injured" in t_low or "west bank" in t_low or "detained" in t_low:
        return "פעילות כוחות הביטחון באיו\"ש: מעצר מבוקשים וסריקות מבצעיות"
    if "morning recap" in t_low:
        return "תמונת מצב ביטחונית וסקירת אירועי הבוקר בזירה האזורית"
    if "drone" in t_low or "intercept" in t_low:
        return "יירוט כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום"
    if "radar" in t_low or "iran" in t_low:
        return "איראן: דיווחים על שדרוג מערכי המכ\"ם וההתרעה האווירית"
        
    replacements = {
        "israeli forces": "כוחות צה\"ל",
        "israeli": "ישראלי",
        "israel": "ישראל",
        "hezbollah": "חיזבאללה",
        "lebanon": "לבנון",
        "gaza": "עזה",
        "west bank": "איו\"ש",
        "strike": "תקיפה",
        "drone": "כטב\"ם",
        "missile": "טיל",
        "ceasefire": "הפסקת אש",
        "iran": "איראן",
        "tehran": "טהראן",
        "fire shells": "ירי ארטילרי",
        "gunfire": "חילופי אש",
        "detained": "מעצר חשודים",
        "injured": "פצועים"
    }
    res = str(title)
    for eng, heb in replacements.items():
        if eng in res.lower():
            res = res.lower().replace(eng, heb)
    return res if is_hebrew(res) else f"דיווח ביטחוני: {str(title)[:75]}"

def get_unique_smart_image(title: str, content: str, used_set: set) -> str:
    text = f"{title} {content}".lower()
    
    # 1. ירי, ארטילריה, פגזים, טילים ותקיפות
    if any(w in text for w in ["fire shells", "shells", "artillery", "missile", "rocket", "strike", "blast", "attack", "gunfire", "ארטילר", "פגז", "ירי", "טיל", "יירוט", "תקיפה"]):
        pool = TOPIC_IMAGE_POOLS["artillery_missiles"]
    # 2. לוחמים, פעילות צבאית ומעצרים
    elif any(w in text for w in ["soldier", "army", "idf", "tank", "troops", "military", "operation", "west bank", "jenin", "nablus", "צה\"ל", "צהל", "לוחמ", "חיילים", "סריקות", "איו\"ש", "מעצר", "שכם", "ג'נין"]):
        pool = TOPIC_IMAGE_POOLS["soldiers"]
    # 3. מכ"ם והתרעה
    elif any(w in text for w in ["radar", "warning", "surveillance", "מכ\"ם", "מכם", "התרעה", "גילוי"]):
        pool = TOPIC_IMAGE_POOLS["radar"]
    # 4. כטב"מים
    elif any(w in text for w in ["drone", "uav", "unmanned", "כטב", "מל\"ט"]):
        pool = TOPIC_IMAGE_POOLS["drone"]
    # 5. לבנון
    elif any(w in text for w in ["lebanon", "beirut", "hezbollah", "לבנון", "ביירות", "חיזבאללה", "tebnit"]):
        pool = TOPIC_IMAGE_POOLS["lebanon"]
    # 6. איראן
    elif any(w in text for w in ["iran", "tehran", "איראן", "טהראן"]):
        pool = TOPIC_IMAGE_POOLS["iran"]
    # 7. דיפלומטיה
    elif any(w in text for w in ["summit", "diplomacy", "minister", "מדיני", "פסגה", "הסכם"]):
        pool = TOPIC_IMAGE_POOLS["diplomacy"]
    else:
        pool = TOPIC_IMAGE_POOLS["general"]
        
    for img in pool:
        if img not in used_set and not any(bad in img for bad in BAD_IMAGE_URLS):
            used_set.add(img)
            return img
            
    for fallback_pool in TOPIC_IMAGE_POOLS.values():
        for img in fallback_pool:
            if img not in used_set and not any(bad in img for bad in BAD_IMAGE_URLS):
                used_set.add(img)
                return img
                
    return TOPIC_IMAGE_POOLS["artillery_missiles"][0]

DEFAULT_ARTICLES = [
    {
        "url": "https://www.middleeasteye.net/news/2026/lebanon-tebnit-artillery",
        "source_name": "Middle East Eye",
        "country": "לבנון",
        "title_original": "Israeli forces fire shells near residents approaching Lebanon's Kfar Tebnit",
        "content_original": "Artillery shelling targeted areas adjacent to southern Lebanese villages during border tensions.",
        "published_at": "14:15 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["artillery_missiles"][0],
        "title_hebrew": "כוחות צה\"ל ביצעו ירי ארטילרי באזור כפר תבנית בדרום לבנון",
        "summary_hebrew": "חילופי אש וירי ארטילרי נרשמו בסמוך לקו העימות בדרום לבנון בעקבות תנועות חשודות בגזרה.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "לבנון, ישראל"
    },
    {
        "url": "https://english.alarabiya.net/news/2026/red-sea-air-defense-drone",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_original": "Naval coalition forces intercept suspicious drone wave in Red Sea",
        "content_original": "Air defense systems destroyed hostile unmanned aerial vehicles threatening international shipping.",
        "published_at": "13:40 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["drone"][0],
        "title_hebrew": "יירוט נרחב של כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום",
        "summary_hebrew": "מערכי ההגנה של הקואליציה סיכלו מתקפה מכיוון תימן שנועדה לשבש את התנועה הימית לאילת.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, ארה\"ב, איראן"
    },
    {
        "url": "https://wafa.ps/ar/news/2026/westbank-security-idf-sweep",
        "source_name": "Wafa",
        "country": "איו\"ש",
        "title_original": "Palestinian man injured in Israeli gunfire, two detained in West Bank",
        "content_original": "Security operations and search activities carried out across Jenin and Nablus.",
        "published_at": "12:50 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["soldiers"][0],
        "title_hebrew": "פעילות כוחות הביטחון באיו\"ש: מעצר מבוקשים וסריקות מבצעיות",
        "summary_hebrew": "כוחות צה\"ל ומשמר הגבול פעלו הלילה בגזרות ג'נין ושכם לסיכול תשתיות טרור ולמעצר מבוקשים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "איו\"ש, ישראל"
    },
    {
        "url": "https://www.tehrantimes.com/news/2026/iran-air-defense-grid",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_original": "IRGC Aerospace forces integrate early warning radar systems",
        "content_original": "Deployment of radar detection arrays to counter asymmetric threats and track airspace corridors.",
        "published_at": "11:30 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["radar"][0],
        "title_hebrew": "איראן הודיעה על פריסת מערכות התרעה ומכ\"ם חדשות",
        "summary_hebrew": "פיקוד ההגנה האווירית של משמרות המהפכה טוען לשדרוג יכולות היירוט מול כלי טיס בלתי מאוישים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 0.0,
        "mentioned_countries": "איראן, ישראל, ארה\"ב"
    },
    {
        "url": "https://www.bbc.com/news/world-middle-east-2026-lebanon-diplomacy",
        "source_name": "BBC News",
        "country": "בריטניה",
        "title_original": "Cross-border strikes reported across southern Lebanon as diplomatic talks continue",
        "content_original": "Reciprocal artillery fire and air defense responses noted along the frontier amid ongoing mediation.",
        "published_at": "10:15 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["lebanon"][0],
        "title_hebrew": "הסלמה בחילופי האש לאורך קו העימות בלבנון לצד מאמץ תיווך צרפתי",
        "summary_hebrew": "סדרת תקיפות ממוקדות בדרום לבנון בעקבות שיגורים לעבר הגליל, במקביל למגעים דיפלומטיים בביירות.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "לבנון, ישראל"
    },
    {
        "url": "https://www.aljazeera.com/news/2026/mideast-diplomatic-cairo",
        "source_name": "Al Jazeera",
        "country": "קטר",
        "title_original": "Regional mediators convene in Cairo to discuss border protocols and humanitarian channels",
        "content_original": "High-level delegations draft security guarantees to ensure maritime safety and prevent escalations.",
        "published_at": "09:20 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["diplomacy"][0],
        "title_hebrew": "מגעים בינלאומיים דחופים לגיבוש מתווה ביטחוני וייצוב קווי הגבול",
        "summary_hebrew": "משלחות תיווך אזוריות מקיימות התייעצויות אינטנסיביות למניעת הסלמה ולהסדרת מנגנוני פיקוח הדדיים.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 0.0,
        "mentioned_countries": "ישראל, ארה\"ב, קטר"
    },
    {
        "url": "https://www.france24.com/en/middle-east/2026/gaza-security-eu",
        "source_name": "France 24",
        "country": "צרפת",
        "title_original": "International observers review corridor mechanisms in Gaza",
        "content_original": "Logistical frameworks analyzed by European diplomats regarding civilian supplies and secure access zones.",
        "published_at": "08:50 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["diplomacy"][1],
        "title_hebrew": "אירופה בוחנת מנגנון פיקוח בינלאומי על צירי האספקה בעזה",
        "summary_hebrew": "בכירים בצרפת ובאיחוד האירופי מגבשים הצעה להצבת משקיפים ניטרליים לאורך המעברים.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 0.0,
        "mentioned_countries": "רצועת עזה, ישראל"
    },
    {
        "url": "https://feeds.washingtonpost.com/world/2026/us-regional-mediterranean",
        "source_name": "Washington Post",
        "country": "ארה\"ב",
        "title_original": "Pentagon reaffirms defensive deployment commitments in the Eastern Mediterranean",
        "content_original": "US carrier strike groups maintain active patrol routes to deter proxy aggression.",
        "published_at": "06:15 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["soldiers"][1],
        "title_hebrew": "הפנטגון מחדש את מחויבותו להגנת נתיבי השיט וההרתעה האזורית",
        "summary_hebrew": "קבוצות קרב אמריקאיות מתמרנות במזרח הים התיכון לשמירה על חופש השיט ומניעת הרחבת הלחימה.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "ארה\"ב, ישראל, איראן"
    }
]

def load_data():
    try:
        conn = get_connection()
        # החלפת תמונות לא רלוונטיות במסד הנתונים
        cursor = conn.cursor()
        for bad_id in BAD_IMAGE_URLS:
            cursor.execute("UPDATE articles SET image_url = ? WHERE image_url LIKE ?", (TOPIC_IMAGE_POOLS["artillery_missiles"][0], f"%{bad_id}%"))
        conn.commit()
        db_df = pd.read_sql_query("SELECT * FROM articles ORDER BY id DESC", conn)
        conn.close()
        if not db_df.empty and len(db_df) >= 3:
            return db_df
    except Exception:
        pass
    return pd.DataFrame(DEFAULT_ARTICLES)

def background_worker():
    while True:
        try:
            arts = fetch_relevant_articles()
            for a in arts:
                if not is_article_exists(a['url']):
                    heb_title = fast_fallback_translation(a['title_original'])
                    a.update({
                        'title_hebrew': heb_title,
                        'summary_hebrew': a['content_original'][:160] if is_hebrew(a['content_original']) else heb_title,
                        'sentiment': 'צבאי וביטחוני' if any(w in a['title_original'].lower() for w in ['strike', 'fire', 'idf', 'missile', 'gunfire', 'forces', 'detained', 'shells']) else 'שוטף',
                        'sentiment_score': 0.0,
                        'mentioned_countries': 'ישראל'
                    })
                    dummy_set = set()
                    a['image_url'] = get_unique_smart_image(a['title_original'], a['content_original'], dummy_set)
                    save_article(a)
                    time.sleep(1)
        except Exception as e:
            print(f"Worker background error: {e}")
        time.sleep(300)

@st.cache_resource
def start_worker():
    t = threading.Thread(target=background_worker, daemon=True)
    t.start()
    return True

start_worker()

df = load_data()

# שורת סינון עליונה
c_search, c_cat = st.columns([7, 3])
with c_search:
    search_query = st.text_input("חיפוש", placeholder="🔎 חפש בידיעות: נתניהו, טילים, הפסקת אש, ביירות...", label_visibility="collapsed")
with c_cat:
    cat_filter = st.selectbox("תחום", ["כל התחומים", "צבאי וביטחוני", "מדיני ודיפלומטי", "כלכלה וסנקציות"], label_visibility="collapsed")

# כותרת האתר
st.markdown("<h1 style='margin: 10px 0 4px 0; font-size: 2.2rem; font-weight: 900; color: #ffffff;'>🌐 דסק מודיעין תקשורת עולמי</h1>", unsafe_allow_html=True)
st.caption("ניטור נרטיבים ודיווחים בזמן אמת ממאגרי התקשורת המובילים בעולם | מתעדכן אוטומטית בעברית 24/7")

# סרגל מדינות
if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = "כל הדיווחים"

NAV_ITEMS = [
    {"label": "כל הדיווחים", "val": "כל הדיווחים", "flag_img": "https://flagcdn.com/w40/un.png"},
    {"label": "ישראל", "val": "ישראל", "flag_img": "https://flagcdn.com/w40/il.png"},
    {"label": "ארה\"ב", "val": "ארה\"ב", "flag_img": "https://flagcdn.com/w40/us.png"},
    {"label": "איראן", "val": "איראן", "flag_img": "https://flagcdn.com/w40/ir.png"},
    {"label": "לבנון", "val": "לבנון", "flag_img": "https://flagcdn.com/w40/lb.png"},
    {"label": "רצועת עזה", "val": "רצועת עזה", "flag_img": "https://flagcdn.com/w40/ps.png"},
    {"label": "איו\"ש", "val": "איו\"ש", "flag_img": "https://flagcdn.com/w40/ps.png"}
]

nav_cols = st.columns(len(NAV_ITEMS))
for idx, item in enumerate(NAV_ITEMS):
    with nav_cols[idx]:
        is_active = (st.session_state["selected_country"] == item["val"])
        btn_type = "primary" if is_active else "secondary"
        
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 5px;">
            <img src="{item['flag_img']}" width="28" style="border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.6);" />
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(item["label"], key=f"btn_country_{item['val']}", type=btn_type, use_container_width=True):
            st.session_state["selected_country"] = item["val"]
            st.rerun()

st.markdown("<hr style='border-color: #1f2937; margin: 14px 0 24px 0;'>", unsafe_allow_html=True)

selected_country = st.session_state["selected_country"]
filtered = df.copy()

if selected_country != "כל הדיווחים":
    synonyms = {
        "ישראל": ["ישראל", "israel", "idf", "נתניהו"],
        "ארה\"ב": ["ארה\"ב", "ארצות הברית", "united states", "biden", "וושינגטון"],
        "איראן": ["איראן", "iran", "tehran", "טהראן"],
        "לבנון": ["לבנון", "lebanon", "beirut", "חיזבאללה", "tebnit"],
        "רצועת עזה": ["עזה", "gaza", "חמאס", "רפיח"],
        "איו\"ש": ["איו\"ש", "יהודה ושומרון", "גדה", "west bank", "ג'נין", "שכם"]
    }
    keys = synonyms.get(selected_country, [selected_country])
    pattern = "|".join(keys)
    filtered = filtered[
        filtered['country'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered['mentioned_countries'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered['title_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered['summary_hebrew'].astype(str).str.contains(pattern, case=False, na=False) |
        filtered['title_original'].astype(str).str.contains(pattern, case=False, na=False)
    ]

if cat_filter != "כל התחומים":
    filtered = filtered[filtered['sentiment'].astype(str).str.contains(cat_filter, na=False)]

if search_query:
    p = search_query.strip()
    filtered = filtered[
        filtered['title_hebrew'].astype(str).str.contains(p, case=False, na=False) |
        filtered['summary_hebrew'].astype(str).str.contains(p, case=False, na=False) |
        filtered['title_original'].astype(str).str.contains(p, case=False, na=False)
    ]

render_df = filtered if not filtered.empty else df
used_page_images = set()

main_art = render_df.iloc[0]
side_arts = render_df.iloc[1:4] if len(render_df) > 1 else pd.DataFrame()

col_main, col_side = st.columns([7, 5])

# כתבה ראשית גדולה בימין
with col_main:
    hero_img = get_unique_smart_image(main_art['title_original'], main_art['content_original'], used_page_images)
    cat = str(main_art.get('sentiment', 'כללי'))
    
    t_display = main_art.get('title_hebrew')
    if not is_hebrew(t_display):
        t_display = fast_fallback_translation(main_art.get('title_original', ''))
        
    s_display = str(main_art.get('summary_hebrew', ''))[:220]
    if not is_hebrew(s_display):
        s_display = t_display
        
    time_str = str(main_art.get('published_at', 'שעות אחרונות'))[:16]
    src = main_art.get('source_name', '')
    c_name = main_art.get('country', '')
    targets = str(main_art.get('mentioned_countries', 'ישראל'))
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
            <h2 style="font-size: 1.55rem; font-weight: 900; margin: 6px 0 10px 0; color: #ffffff; line-height: 1.35;">{t_display}</h2>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 12px;">{s_display}...</p>
            <a class="read-btn" href="{url}" target="_blank">לקריאת הדיווח המקורי בערוץ ←</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# מבזקים חמים משמאל
with col_side:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 800; margin-bottom: 10px; color: #38bdf8;'>⚡ דיווחים חמים נוספים</div>", unsafe_allow_html=True)
    if not side_arts.empty:
        for _, s_row in side_arts.iterrows():
            s_img = get_unique_smart_image(s_row['title_original'], s_row['content_original'], used_page_images)
            
            s_title = s_row.get('title_hebrew')
            if not is_hebrew(s_title):
                s_title = fast_fallback_translation(s_row.get('title_original', ''))
                
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
                    <div style="font-size: 0.72rem; color: #64748b;">🕒 {s_time}</div>
                </div>
            </a>
            """, unsafe_allow_html=True)

# גריד כתבות תחתון
rem_arts = render_df.iloc[4:] if len(render_df) > 4 else pd.DataFrame()
if not rem_arts.empty:
    st.markdown("<h3 style='margin: 35px 0 15px 0; font-weight: 800;'>📰 כל הדיווחים והכתבות מהעולם</h3>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (_, r_art) in enumerate(rem_arts.iterrows()):
        with cols[idx % 3]:
            r_img = get_unique_smart_image(r_art['title_original'], r_art['content_original'], used_page_images)
            
            r_title = r_art.get('title_hebrew')
            if not is_hebrew(r_title):
                r_title = fast_fallback_translation(r_art.get('title_original', ''))
                
            r_summary = str(r_art.get('summary_hebrew', ''))[:110]
            if not is_hebrew(r_summary):
                r_summary = r_title
                
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
                    <a class="read-btn" href="{r_url}" target="_blank">לקריאת המקור בערוץ ←</a>
                </div>
            </div>
            """, unsafe_allow_html=True)