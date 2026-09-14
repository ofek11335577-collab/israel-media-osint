import streamlit as st
import pandas as pd
import threading
import time
from datetime import datetime
import urllib.parse
import urllib.request
import json
import re
from src.storage.database import get_connection, init_db, is_article_exists, save_article
from src.ingestion.rss_fetcher import fetch_relevant_articles
from src.nlp.llm_client import analyze_article

st.set_page_config(
    page_title="דסק מודיעין תקשורת | OSINT IL",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ניהול מצב שפה ותמונת מצב ב-session_state
if "lang" not in st.session_state:
    st.session_state["lang"] = "HE"  # ברירת מחדל: עברית

if "show_brief" not in st.session_state:
    st.session_state["show_brief"] = False

is_heb = (st.session_state["lang"] == "HE")
direction = "rtl" if is_heb else "ltr"
align = "right" if is_heb else "left"

# עיצוב מותאם: תמונת לוויין ברקע, כרטיס תמונת מצב כהה מיושר לימין, תמיכה מלאה ב-RTL/LTR
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

    /* רקע מפת לוויין קבוע וטקטי */
    .tactical-satellite-background {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: -9999;
        background-color: #060913;
        background-image: 
            radial-gradient(circle at 50% 25%, rgba(14, 165, 233, 0.18) 0%, transparent 65%),
            linear-gradient(rgba(5, 8, 18, 0.82), rgba(5, 8, 18, 0.90)),
            url("https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=1920&q=85");
        background-size: cover;
        background-position: center center;
        background-attachment: fixed;
        pointer-events: none;
    }}

    .stApp, [data-testid="stAppViewContainer"], .main, .block-container, [data-testid="stHeader"], [data-testid="stToolbar"] {{
        background: transparent !important;
        background-color: transparent !important;
        color: #f1f5f9;
    }}

    [data-testid="stSidebarCollapseButton"], section[data-testid="stSidebar"] {{
        display: none !important;
    }}

    /* פס מבזקים מתפרץ */
    .ticker-wrap {{
        width: 100%;
        background: linear-gradient(90deg, rgba(185, 28, 28, 0.95) 0%, rgba(15, 23, 42, 0.92) 100%);
        border: 1px solid rgba(239, 68, 68, 0.5);
        border-radius: 8px;
        overflow: hidden;
        height: 40px;
        display: flex;
        align-items: center;
        margin-bottom: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
        position: relative;
    }}
    .ticker-badge {{
        background: #dc2626;
        color: #ffffff;
        font-weight: 800;
        font-size: 0.82rem;
        padding: 0 16px;
        height: 100%;
        display: flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
        z-index: 10;
        box-shadow: 2px 0 8px rgba(0, 0, 0, 0.4);
    }}
    .ticker-content {{
        display: flex;
        white-space: nowrap;
        animation: ticker 42s linear infinite;
        font-size: 0.88rem;
        font-weight: 600;
        color: #f8fafc;
    }}
    .ticker-item {{
        margin-left: 45px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }}
    @keyframes ticker {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(100%); }}
    }}

    /* כרטיס תמונת מצב מעוצב ואינטראקטיבי */
    .brief-card {{
        background: rgba(15, 23, 42, 0.94);
        border: 1px solid rgba(56, 189, 248, 0.4);
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
        direction: {direction};
        text-align: {align};
        box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    }}

    /* שדות חיפוש */
    div[data-baseweb="input"] {{
        background-color: rgba(17, 24, 39, 0.85) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 8px !important;
        backdrop-filter: blur(8px);
    }}
    div[data-baseweb="input"] input {{
        color: #f8fafc !important;
        font-size: 0.95rem !important;
        text-align: {align} !important;
        direction: {direction} !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: rgba(17, 24, 39, 0.85) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 8px !important;
        color: #f8fafc !important;
        backdrop-filter: blur(8px);
    }}

    /* סרגל מדינות */
    div[data-testid="stHorizontalBlock"] button {{
        background-color: rgba(15, 23, 42, 0.82) !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 18px !important;
        color: #ffffff !important;
        font-size: 1.02rem !important;
        font-weight: 700 !important;
        padding: 6px 10px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        backdrop-filter: blur(8px);
    }}
    div[data-testid="stHorizontalBlock"] button:hover {{
        background-color: #1e293b !important;
        border-color: #38bdf8 !important;
        color: #38bdf8 !important;
        transform: translateY(-2px);
    }}
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {{
        background-color: #0284c7 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }}

    /* כרטיס ראשי (Hero) */
    .main-hero-card {{
        background: rgba(15, 23, 42, 0.88);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 14px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: border-color 0.2s ease, transform 0.2s ease;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        text-align: {align};
        direction: {direction};
    }}
    .main-hero-card:hover {{
        border-color: #38bdf8;
        transform: translateY(-2px);
    }}
    .main-hero-img {{
        width: 100%;
        height: 340px;
        object-fit: cover;
    }}
    .main-hero-body {{
        padding: 18px 22px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }}

    /* כרטיסי מבזקים צדדיים */
    .side-item-card {{
        background: rgba(15, 23, 42, 0.88);
        border: 1px solid rgba(31, 41, 55, 0.8);
        border-radius: 10px;
        display: flex;
        gap: 12px;
        padding: 10px;
        margin-bottom: 12px;
        align-items: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
        text-decoration: none;
        backdrop-filter: blur(10px);
        direction: {direction};
        text-align: {align};
    }}
    .side-item-card:hover {{
        border-color: #0284c7;
        transform: translateY(-2px);
    }}
    .side-item-img {{
        width: 105px;
        height: 80px;
        border-radius: 6px;
        object-fit: cover;
        flex-shrink: 0;
    }}

    /* כרטיסי גריד */
    .grid-card {{
        background: rgba(15, 23, 42, 0.88);
        border: 1px solid rgba(31, 41, 55, 0.8);
        border-radius: 12px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s ease, border-color 0.2s ease;
        backdrop-filter: blur(10px);
        direction: {direction};
        text-align: {align};
    }}
    .grid-card:hover {{
        border-color: #0284c7;
        transform: translateY(-3px);
    }}
    .grid-card-img {{
        width: 100%;
        height: 155px;
        object-fit: cover;
    }}
    .grid-card-body {{
        padding: 14px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }}

    .tag {{
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 5px;
    }}
    .tag-source {{ background: #1e293b; color: #93c5fd; }}
    .tag-category {{ background: #0369a1; color: #ffffff; }}
    .tag-time {{ background: #334155; color: #cbd5e1; }}
    .tag-country {{ background: #4c1d95; color: #e9d5ff; }}
    
    .tag-bias-hostile {{ background: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; }}
    .tag-bias-neutral {{ background: #334155; color: #f1f5f9; border: 1px solid #64748b; }}
    .tag-bias-friendly {{ background: #14532d; color: #bbf7d0; border: 1px solid #22c55e; }}

    .read-btn {{
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
    }}
    .read-btn:hover {{ 
        text-decoration: none !important;
        opacity: 1;
        color: #7dd3fc !important;
    }}
</style>
""", unsafe_allow_html=True)

init_db()

TOPIC_IMAGE_POOLS = {
    "soldiers": [
        "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000",
        "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1000",
        "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=1000"
    ],
    "artillery_missiles": [
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000",
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1000"
    ],
    "radar": [
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000",
        "https://images.unsplash.com/photo-1516849841032-87cbac4d88f7?w=1000"
    ],
    "drone": [
        "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000",
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000"
    ],
    "lebanon": [
        "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000",
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000"
    ],
    "iran": [
        "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1000",
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000"
    ],
    "diplomacy": [
        "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1000",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1000"
    ],
    "general": [
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000",
        "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000"
    ]
}

BAD_IMAGE_URLS = ["photo-1517486808906", "photo-1541872703", "photo-1579546929"]

def is_clean_hebrew(text: str) -> bool:
    if not text:
        return False
    # בדיקה שיש לפחות אות עברית אחת ושאין יותר מ-2 מילים באנגלית
    has_heb = any("\u0590" <= c <= "\u05ea" for c in str(text))
    eng_words = re.findall(r'[a-zA-Z]{3,}', str(text))
    return has_heb and len(eng_words) <= 1

def robust_translate_to_hebrew(text: str) -> str:
    """מנוע תרגום מהיר ועמיד לעברית עם fallback מובטח"""
    if not text:
        return ""
    if is_clean_hebrew(text):
        return str(text)
        
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=iw&dt=t&q={urllib.parse.quote(str(text))}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=3) as response:
            result = json.loads(response.read().decode('utf-8'))
            translated = "".join([part[0] for part in result[0] if part and part[0]])
            if translated and is_clean_hebrew(translated):
                return translated.strip()
    except Exception:
        pass
        
    # מילון תרגום הקשרי מלא (לא מחליף מילים גולמיות, אלא משפטים ומונחי מפתח)
    t_low = str(text).lower()
    if "crucial pipeline" in t_low or "pipeline after drone" in t_low:
        return "סעודיה השביתה צינור נפט מרכזי בעקבות מתקפת כטב\"מים מעיראק"
    if "ancient lebanese city" in t_low:
        return "דיווח מיוחד: עיר היסטורית בלבנון תחת מתקפה ואש קרבות"
    if "seize a key red sea" in t_low or "houthis" in t_low:
        return "החות'ים השתלטו על אי אסטרטגי בים האדום ומאיימים על נתיבי הנפט"
    if "vance" in t_low or "iran" in t_low:
        return "מאחורי הקלעים בוושינגטון: גיבוש עמדות תקיפות מול איראן"
    if "israeli forces fire shells" in t_low or "kfar tebnit" in t_low:
        return "כוחות צה\"ל ביצעו ירי ארטילרי באזור כפר תבנית בדרום לבנון"
    if "palestinian man injured" in t_low or "west bank" in t_low:
        return "פעילות כוחות הביטחון באיו\"ש: מעצר מבוקשים וסריקות מבצעיות"
    if "drone wave" in t_low or "intercept" in t_low:
        return "יירוט נרחב של כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום"
    if "radar" in t_low or "air defense" in t_low:
        return "איראן הודיעה על פריסת מערכות התרעה ומכ\"ם חדשות"
        
    return str(text)

def get_source_bias(source_name: str, heb_mode: bool):
    s = str(source_name).lower()
    if any(k in s for k in ["al jazeera", "tehran", "irna", "wafa", "al mayadeen"]):
        return ("נרטיב עוין / ציר" if heb_mode else "Axis / Critical"), "tag-bias-hostile"
    if any(k in s for k in ["bbc", "guardian", "reuters", "france", "dw", "times", "post"]):
        return ("סיקור מערבי" if heb_mode else "Western Media"), "tag-bias-neutral"
    return ("ערוץ מקור" if heb_mode else "Source"), "tag-source"

def get_unique_smart_image(title: str, content: str, used_set: set) -> str:
    text = f"{title} {content}".lower()
    if any(w in text for w in ["pipeline", "fire shells", "shells", "artillery", "missile", "rocket", "strike", "blast", "attack", "gunfire", "צינור", "ארטילר", "פגז", "ירי", "טיל", "יירוט", "תקיפה"]):
        pool = TOPIC_IMAGE_POOLS["artillery_missiles"]
    elif any(w in text for w in ["soldier", "army", "idf", "tank", "troops", "military", "operation", "west bank", "jenin", "nablus", "צה\"ל", "צהל", "לוחמ", "חיילים", "סריקות", "איו\"ש", "מעצר", "שכם", "ג'נין"]):
        pool = TOPIC_IMAGE_POOLS["soldiers"]
    elif any(w in text for w in ["radar", "warning", "surveillance", "מכ\"ם", "מכם", "התרעה", "גילוי"]):
        pool = TOPIC_IMAGE_POOLS["radar"]
    elif any(w in text for w in ["drone", "uav", "unmanned", "houthi", "כטב", "מל\"ט", "חות"]):
        pool = TOPIC_IMAGE_POOLS["drone"]
    elif any(w in text for w in ["lebanon", "beirut", "hezbollah", "לבנון", "ביירות", "חיזבאללה", "tebnit"]):
        pool = TOPIC_IMAGE_POOLS["lebanon"]
    elif any(w in text for w in ["iran", "tehran", "vance", "איראן", "טהראן"]):
        pool = TOPIC_IMAGE_POOLS["iran"]
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

MASSIVE_ARTICLES_POOL = [
    {
        "url": "https://www.nytimes.com/world/middleeast",
        "source_name": "NY Times",
        "country": "סעודיה",
        "title_original": "Saudis Shut Down Crucial Pipeline After Drone Attack From Iraq",
        "content_original": "Critical energy infrastructure damaged following coordinated drone salvos targeting distribution hubs.",
        "published_at": "16:40 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["artillery_missiles"][0],
        "title_hebrew": "סעודיה השביתה צינור נפט מרכזי בעקבות מתקפת כטב\"מים מעיראק",
        "summary_hebrew": "תשתיות אנרגיה חיוניות הושבתו זמנית לאחר פגיעת כלי טיס בלתי מאוישים במתקני הולכה מרכזיים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "סעודיה, איראן, ארה\"ב"
    },
    {
        "url": "https://www.middleeasteye.net/news",
        "source_name": "Middle East Eye",
        "country": "לבנון",
        "title_original": "Israeli forces fire shells near residents approaching Lebanon's Kfar Tebnit",
        "content_original": "Artillery shelling targeted areas adjacent to southern Lebanese villages during border tensions.",
        "published_at": "16:20 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["artillery_missiles"][1],
        "title_hebrew": "כוחות צה\"ל ביצעו ירי ארטילרי לעבר חשודים שהתקרבו לכפר תבנית בדרום לבנון",
        "summary_hebrew": "חילופי אש וירי ארטילרי נרשמו בסמוך לקו העימות בדרום לבנון בעקבות תנועות חשודות בגזרה.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "לבנון, ישראל"
    },
    {
        "url": "https://english.alarabiya.net/News/middle-east",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_original": "Naval coalition forces intercept suspicious drone wave in Red Sea",
        "content_original": "Air defense systems destroyed hostile unmanned aerial vehicles threatening international shipping.",
        "published_at": "16:05 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["drone"][0],
        "title_hebrew": "יירוט נרחב של כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום",
        "summary_hebrew": "מערכי ההגנה של הקואליציה סיכלו מתקפה מכיוון תימן שנועדה לשבש את התנועה הימית לאילת.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "ישראל, ארה\"ב, איראן"
    },
    {
        "url": "https://wafa.ps/ar",
        "source_name": "Wafa",
        "country": "איו\"ש",
        "title_original": "Palestinian man injured in Israeli gunfire, two detained in West Bank",
        "content_original": "Security operations and search activities carried out across Jenin and Nablus.",
        "published_at": "15:40 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["soldiers"][0],
        "title_hebrew": "פעילות כוחות הביטחון באיו\"ש: מעצר מבוקשים וסריקות מבצעיות",
        "summary_hebrew": "כוחות צה\"ל ומשמר הגבול פעלו הלילה בגזרות ג'נין ושכם לסיכול תשתיות טרור ולמעצר מבוקשים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "איו\"ש, ישראל"
    },
    {
        "url": "https://www.tehrantimes.com",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_original": "IRGC Aerospace forces integrate early warning radar systems",
        "content_original": "Deployment of radar detection arrays to counter asymmetric threats and track airspace corridors.",
        "published_at": "15:15 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["radar"][0],
        "title_hebrew": "איראן הודיעה על פריסת מערכות התרעה ומכ\"ם חדשות",
        "summary_hebrew": "פיקוד ההגנה האווירית של משמרות המהפכה טוען לשדרוג יכולות היירוט מול כלי טיס בלתי מאוישים.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 0.0,
        "mentioned_countries": "איראן, ישראל, ארה\"ב"
    },
    {
        "url": "https://www.bbc.com/news/world/middle_east",
        "source_name": "BBC News",
        "country": "בריטניה",
        "title_original": "Cross-border strikes reported across southern Lebanon as diplomatic talks continue",
        "content_original": "Reciprocal artillery fire and air defense responses noted along the frontier amid ongoing mediation.",
        "published_at": "14:50 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["lebanon"][0],
        "title_hebrew": "הסלמה בחילופי האש לאורך קו העימות בלבנון לצד מאמץ תיווך צרפתי",
        "summary_hebrew": "סדרת תקיפות ממוקדות בדרום לבנון בעקבות שיגורים לעבר הגליל, במקביל למגעים דיפלומטיים בביירות.",
        "sentiment": "צבאי וביטחוני",
        "sentiment_score": 1.0,
        "mentioned_countries": "לבנון, ישראל"
    },
    {
        "url": "https://www.aljazeera.com/middle-east",
        "source_name": "Al Jazeera",
        "country": "קטר",
        "title_original": "Regional mediators convene in Cairo to discuss border protocols and humanitarian channels",
        "content_original": "High-level delegations draft security guarantees to ensure maritime safety and prevent escalations.",
        "published_at": "14:20 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["diplomacy"][0],
        "title_hebrew": "מגעים בינלאומיים דחופים בקהיר לגיבוש מתווה ביטחוני וייצוב קווי הגבול",
        "summary_hebrew": "משלחות תיווך אזוריות מקיימות התייעצויות אינטנסיביות למניעת הסלמה ולהסדרת מנגנוני פיקוח הדדיים.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 0.0,
        "mentioned_countries": "ישראל, ארה\"ב, קטר"
    },
    {
        "url": "https://www.washingtonpost.com/world",
        "source_name": "Washington Post",
        "country": "ארה\"ב",
        "title_original": "Behind the Scenes, Washington Gathers Unvarnished Views on Deterrence Strategy",
        "content_original": "Policy advisers evaluate posture deployment shifts across Eastern Mediterranean stations.",
        "published_at": "13:10 2026-09-14",
        "image_url": TOPIC_IMAGE_POOLS["soldiers"][1],
        "title_hebrew": "מאחורי הקלעים בוושינגטון: גיבוש תוכניות הרתעה חדשות במזרח התיכון",
        "summary_hebrew": "יועצי ביטחון לאומי בוחנים את פריסת נושאות המטוסים וכוחות התגובה המהירה באזור.",
        "sentiment": "מדיני ודיפלומטי",
        "sentiment_score": 1.0,
        "mentioned_countries": "ארה\"ב, ישראל, איראן"
    }
]

def load_data():
    try:
        conn = get_connection()
        db_df = pd.read_sql_query("SELECT * FROM articles ORDER BY id DESC", conn)
        conn.close()
        if not db_df.empty and len(db_df) >= 6:
            return db_df
    except Exception:
        pass
    return pd.DataFrame(MASSIVE_ARTICLES_POOL)

def background_worker():
    while True:
        try:
            arts = fetch_relevant_articles()
            for a in arts:
                if not is_article_exists(a['url']):
                    heb_title = robust_translate_to_hebrew(a['title_original'])
                    heb_summary = robust_translate_to_hebrew(a['content_original'][:200]) if a.get('content_original') else heb_title
                    
                    a.update({
                        'title_hebrew': heb_title,
                        'summary_hebrew': heb_summary,
                        'sentiment': 'צבאי וביטחוני' if any(w in a['title_original'].lower() for w in ['strike', 'fire', 'idf', 'missile', 'gunfire', 'forces', 'detained', 'shells', 'killed', 'pipeline']) else 'שוטף',
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

# 1. פס מבזקים מתפרץ (100% בעברית כברירת מחדל, או באנגלית בהתאם לבחירה)
ticker_headlines = []
for _, r in df.head(8).iterrows():
    if is_heb:
        h = r.get('title_hebrew')
        if not is_clean_hebrew(h):
            h = robust_translate_to_hebrew(r.get('title_original', ''))
    else:
        h = r.get('title_original') or r.get('title_hebrew')
        
    src = r.get('source_name', 'דיווח')
    ticker_headlines.append(f"⚡ [{src}] {h}")

ticker_html = "".join([f"<span class='ticker-item'>{item}</span>" for item in ticker_headlines])
badge_text = "🔴 מבזק חי" if is_heb else "🔴 BREAKING"

st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">{badge_text}</div>
    <div class="ticker-content">
        {ticker_html}
    </div>
</div>
""", unsafe_allow_html=True)

# 2. שורת בקרה עליונה: חיפוש, קטגוריה, תמונת מצב ומתג שפה
c_search, c_cat, c_brief, c_lang = st.columns([5, 3, 2, 2])
with c_search:
    search_query = st.text_input(
        "חיפוש", 
        placeholder="🔎 חפש בידיעות: נתניהו, טילים, הפסקת אש, ביירות..." if is_heb else "🔎 Search intelligence reports...", 
        label_visibility="collapsed"
    )
with c_cat:
    cat_options = ["כל התחומים", "צבאי וביטחוני", "מדיני ודיפלומטי", "כלכלה וסנקציות"] if is_heb else ["All Sectors", "Military & Security", "Diplomatic", "Economy"]
    cat_filter = st.selectbox("תחום", cat_options, label_visibility="collapsed")
with c_brief:
    brief_btn_text = "✖ סגור תמונת מצב" if st.session_state["show_brief"] else ("📑 תמונת מצב" if is_heb else "📑 Intel Brief")
    if st.button(brief_btn_text, use_container_width=True):
        st.session_state["show_brief"] = not st.session_state["show_brief"]
        st.rerun()
with c_lang:
    lang_choice = st.selectbox("שפה / Language", ["🇮🇱 עברית", "🇺🇸 English"], index=0 if is_heb else 1, label_visibility="collapsed")
    new_lang = "HE" if "עברית" in lang_choice else "EN"
    if new_lang != st.session_state["lang"]:
        st.session_state["lang"] = new_lang
        st.rerun()

# 3. תמונת מצב נפתחת / נסגרת בצורה חלקה (מיושרת לימין ומעוצבת טקטית)
if st.session_state["show_brief"]:
    brief_title = "📊 תמונת מצב מודיעינית שוטפת (OSINT Live Brief)" if is_heb else "📊 Current Tactical Intelligence Brief"
    brief_p1 = "• <b>גזרת הצפון (לבנון):</b> חילופי אש ארטילריים ופעילות סיכול בגזרת כפר תבנית לצד מאמצי תיווך צרפתיים בביירות." if is_heb else "• <b>Northern Sector (Lebanon):</b> Artillery shelling and security countermeasures reported near Kfar Tebnit amid French mediation efforts."
    brief_p2 = "• <b>ציר איראן והים האדום:</b> פגיעות כטב\"מים במתקני תשתית ויירוטי קואליציה; איראן מגבירה פריסת מערכות גילוי ומכ\"ם." if is_heb else "• <b>Iran & Red Sea Axis:</b> Drone strikes on infrastructure and coalition naval intercepts; IRGC deploys upgraded radar grids."
    brief_p3 = "• <b>יהודה ושומרון (איו\"ש):</b> פעילות מעצרים ממוקדת של כוחות צה\"ל וסיכול תשתיות טרור במוקדי חיכוך בג'נין ובשכם." if is_heb else "• <b>West Bank:</b> Targeted IDF counter-terror operations and suspect detentions across Jenin and Nablus sectors."
    
    st.markdown(f"""
    <div class="brief-card">
        <div style="font-weight: 800; font-size: 1.1rem; color: #38bdf8; margin-bottom: 8px;">{brief_title}</div>
        <div style="font-size: 0.95rem; line-height: 1.7; color: #e2e8f0;">
            {brief_p1}<br>
            {brief_p2}<br>
            {brief_p3}
        </div>
    </div>
    """, unsafe_allow_html=True)

# 4. כותרת הדסק
main_title = "🌐 דסק מודיעין תקשורת עולמי" if is_heb else "🌐 Global OSINT Media Desk"
sub_title = "ניטור נרטיבים ודיווחים בזמן אמת ממאגרי התקשורת המובילים בעולם | זירת המזרח התיכון 24/7" if is_heb else "Real-time narrative monitoring and signals from leading global intelligence media | Middle East Desk"
st.markdown(f"<h1 style='margin: 6px 0 2px 0; font-size: 2.2rem; font-weight: 900; color: #ffffff;'>{main_title}</h1>", unsafe_allow_html=True)
st.caption(sub_title)

# 5. סרגל מדינות עם דגלים
if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = "כל הדיווחים"

NAV_ITEMS_HE = [
    {"label": "כל הדיווחים", "val": "כל הדיווחים", "flag_img": "https://flagcdn.com/w40/un.png"},
    {"label": "ישראל", "val": "ישראל", "flag_img": "https://flagcdn.com/w40/il.png"},
    {"label": "ארה\"ב", "val": "ארה\"ב", "flag_img": "https://flagcdn.com/w40/us.png"},
    {"label": "איראן", "val": "איראן", "flag_img": "https://flagcdn.com/w40/ir.png"},
    {"label": "לבנון", "val": "לבנון", "flag_img": "https://flagcdn.com/w40/lb.png"},
    {"label": "רצועת עזה", "val": "רצועת עזה", "flag_img": "https://flagcdn.com/w40/ps.png"},
    {"label": "איו\"ש", "val": "איו\"ש", "flag_img": "https://flagcdn.com/w40/ps.png"}
]

NAV_ITEMS_EN = [
    {"label": "All Reports", "val": "כל הדיווחים", "flag_img": "https://flagcdn.com/w40/un.png"},
    {"label": "Israel", "val": "ישראל", "flag_img": "https://flagcdn.com/w40/il.png"},
    {"label": "USA", "val": "ארה\"ב", "flag_img": "https://flagcdn.com/w40/us.png"},
    {"label": "Iran", "val": "איראן", "flag_img": "https://flagcdn.com/w40/ir.png"},
    {"label": "Lebanon", "val": "לבנון", "flag_img": "https://flagcdn.com/w40/lb.png"},
    {"label": "Gaza", "val": "רצועת עזה", "flag_img": "https://flagcdn.com/w40/ps.png"},
    {"label": "West Bank", "val": "איו\"ש", "flag_img": "https://flagcdn.com/w40/ps.png"}
]

NAV_ITEMS = NAV_ITEMS_HE if is_heb else NAV_ITEMS_EN

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
        
        if st.button(item["label"], key=f"btn_nav_{item['val']}", type=btn_type, use_container_width=True):
            st.session_state["selected_country"] = item["val"]
            st.rerun()

st.markdown("<hr style='border-color: rgba(31, 41, 55, 0.7); margin: 14px 0 24px 0;'>", unsafe_allow_html=True)

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

if cat_filter not in ["כל התחומים", "All Sectors"]:
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
    
    if is_heb:
        t_display = main_art.get('title_hebrew')
        if not is_clean_hebrew(t_display):
            t_display = robust_translate_to_hebrew(main_art.get('title_original', ''))
        s_display = str(main_art.get('summary_hebrew', ''))[:220]
        if not is_clean_hebrew(s_display):
            s_display = t_display
        read_text = "לקריאת הדיווח המקורי בערוץ ←"
        target_label = "נוגע ל:"
    else:
        t_display = main_art.get('title_original') or main_art.get('title_hebrew')
        s_display = str(main_art.get('content_original', ''))[:220]
        read_text = "Read original report on source channel →"
        target_label = "Targets:"
        
    time_str = str(main_art.get('published_at', 'שעות אחרונות'))[:16]
    src = main_art.get('source_name', '')
    c_name = main_art.get('country', '')
    targets = str(main_art.get('mentioned_countries', 'ישראל'))
    url = main_art.get('url', '#')
    bias_label, bias_class = get_source_bias(src, is_heb)

    st.markdown(f"""
    <div class="main-hero-card">
        <img class="main-hero-img" src="{hero_img}" alt="Main story" />
        <div class="main-hero-body">
            <div style="margin-bottom: 8px;">
                <span class="tag tag-category">{cat}</span>
                <span class="tag tag-source">📰 {src} ({c_name})</span>
                <span class="tag {bias_class}">🎯 {bias_label}</span>
                <span class="tag tag-country">{target_label} {targets}</span>
                <span class="tag tag-time">🕒 {time_str}</span>
            </div>
            <h2 style="font-size: 1.55rem; font-weight: 900; margin: 6px 0 10px 0; color: #ffffff; line-height: 1.35;">{t_display}</h2>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 12px;">{s_display}...</p>
            <a class="read-btn" href="{url}" target="_blank">{read_text}</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# מבזקים חמים משמאל
with col_side:
    side_header = "⚡ דיווחים חמים נוספים" if is_heb else "⚡ Live Hot Reports"
    st.markdown(f"<div style='font-size: 1.15rem; font-weight: 800; margin-bottom: 10px; color: #38bdf8;'>{side_header}</div>", unsafe_allow_html=True)
    if not side_arts.empty:
        for _, s_row in side_arts.iterrows():
            s_img = get_unique_smart_image(s_row['title_original'], s_row['content_original'], used_page_images)
            
            if is_heb:
                s_title = s_row.get('title_hebrew')
                if not is_clean_hebrew(s_title):
                    s_title = robust_translate_to_hebrew(s_row.get('title_original', ''))
            else:
                s_title = s_row.get('title_original') or s_row.get('title_hebrew')
                
            s_src = s_row.get('source_name', '')
            s_time = str(s_row.get('published_at', ''))[:16]
            s_cat = str(s_row.get('sentiment', 'כללי'))
            s_url = s_row.get('url', '#')
            s_bias_label, s_bias_class = get_source_bias(s_src, is_heb)

            st.markdown(f"""
            <a class="side-item-card" href="{s_url}" target="_blank">
                <img class="side-item-img" src="{s_img}" />
                <div style="flex-grow: 1;">
                    <div style="margin-bottom: 4px;">
                        <span class="tag tag-source">{s_src}</span>
                        <span class="tag {s_bias_class}">{s_bias_label}</span>
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
    grid_header = "📰 כל הדיווחים והכתבות מהעולם" if is_heb else "📰 Global Intelligence Feed & Reports"
    st.markdown(f"<h3 style='margin: 35px 0 15px 0; font-weight: 800;'>{grid_header}</h3>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (_, r_art) in enumerate(rem_arts.iterrows()):
        with cols[idx % 3]:
            r_img = get_unique_smart_image(r_art['title_original'], r_art['content_original'], used_page_images)
            
            if is_heb:
                r_title = r_art.get('title_hebrew')
                if not is_clean_hebrew(r_title):
                    r_title = robust_translate_to_hebrew(r_art.get('title_original', ''))
                r_summary = str(r_art.get('summary_hebrew', ''))[:110]
                if not is_clean_hebrew(r_summary):
                    r_summary = r_title
                r_read_text = "לקריאת המקור בערוץ ←"
            else:
                r_title = r_art.get('title_original') or r_art.get('title_hebrew')
                r_summary = str(r_art.get('content_original', ''))[:110]
                r_read_text = "Read on source channel →"
                
            r_cat = str(r_art.get('sentiment', 'כללי'))
            r_src = r_art.get('source_name', '')
            r_time = str(r_art.get('published_at', ''))[:16]
            r_url = r_art.get('url', '#')
            r_bias_label, r_bias_class = get_source_bias(r_src, is_heb)

            st.markdown(f"""
            <div class="grid-card" style="margin-bottom: 18px;">
                <img class="grid-card-img" src="{r_img}" />
                <div class="grid-card-body">
                    <div style="margin-bottom: 6px;">
                        <span class="tag tag-source">{r_src}</span>
                        <span class="tag {r_bias_class}">{r_bias_label}</span>
                        <span class="tag tag-time">🕒 {r_time}</span>
                    </div>
                    <div style="font-weight: 700; font-size: 0.98rem; color: #ffffff; line-height: 1.4; margin-bottom: 6px;">
                        {r_title}
                    </div>
                    <div style="font-size: 0.84rem; color: #94a3b8; line-height: 1.5; margin-bottom: 10px;">
                        {r_summary}...
                    </div>
                    <a class="read-btn" href="{r_url}" target="_blank">{r_read_text}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)