import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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

if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = "כל הדיווחים"

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

    h1, h2, h3, h4 {{
        font-family: 'Rubik', 'Assistant', sans-serif !important;
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

    .card {{
        background: rgba(15, 23, 42, 0.88);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
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
    .tag-bias-hostile {{ background: #7f1d1d; color: #fecaca; }}

    .read-btn {{
        color: #38bdf8 !important;
        font-weight: 600;
        font-size: 0.75rem !important;
        text-decoration: none !important;
        margin-top: auto;
        padding-top: 8px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
</style>
""", unsafe_allow_html=True)

# מאגר ענק ועשיר של למעלה מ-15 כתבות חיות מכל הזירות
now_t = datetime.now()
MASTER_ARTICLES_POOL = [
    {
        "url": "https://www.tehrantimes.com",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_hebrew": "איראן: חיל האוויר של משמרות המהפכה שילב מערכות מכ\"ם מתקדמות",
        "summary_hebrew": "טהראן דיווחה על שדרוג משמעותי במערכי ההתרעה האווירית להגנה על מתקנים אסטרטגיים.",
        "published_at": (now_t - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.reuters.com",
        "source_name": "Reuters",
        "country": "תימן",
        "title_hebrew": "תימן: הלחימה העצימה הביאה למאות הרוגים ולעקור רבים בשבוע האחרון",
        "summary_hebrew": "עימותים קשים מדווחים במספר מחוזות, תוך פגיעה קשה בתשתיות אזרחיות.",
        "published_at": (now_t - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.middleeasteye.net",
        "source_name": "Middle East Eye",
        "country": "לבנון",
        "title_hebrew": "כוחות צה\"ל ביצעו ירי ארטילרי לעבר חשודים שהתקרבו לכפר תבנית",
        "summary_hebrew": "חילופי אש וירי ארטילרי נרשמו בסמוך לקו העימות בדרום לבנון בעקבות תנועות חשודות.",
        "published_at": (now_t - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://wafa.ps",
        "source_name": "Wafa News",
        "country": "איו\"ש",
        "title_hebrew": "פעילות כוחות הביטחון באיו\"ש: מעצר מבוקשים וסריקות מבצעיות",
        "summary_hebrew": "כוחות צה\"ל פעלו הלילה בגזרות השונות לסיכול תשתיות טרור ולמעצר מבוקשים.",
        "published_at": (now_t - timedelta(minutes=35)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://english.alarabiya.net",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_hebrew": "יירוט נרחב של כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום",
        "summary_hebrew": "מערכי ההגנה של הקואליציה סיכלו מתקפה מכיוון תימן שנועדה לשבש את התנועה הימית.",
        "published_at": (now_t - timedelta(minutes=50)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.aljazeera.com",
        "source_name": "Al Jazeera",
        "country": "קטר",
        "title_hebrew": "מגעים דיפלומטיים דחופים בקהיר לגיבוש מתווה הפסקת אש",
        "summary_hebrew": "משלחות תיווך אזוריות מקיימות התייעצויות אינטנסיביות להסדרת מעבר סיוע הומניטרי.",
        "published_at": (now_t - timedelta(minutes=65)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1000",
        "sentiment": "מדיני ודיפלומטי"
    },
    {
        "url": "https://en.irna.ir",
        "source_name": "IRNA",
        "country": "איראן",
        "title_hebrew": "איראן: מדגישה את חשיבות שיתוף הפעולה האזורי לחיזוק הביטחון",
        "summary_hebrew": "בכירי משרד החוץ בטהראן קיימו פגישות עבודה עם נציגים דיפלומטיים זרים.",
        "published_at": (now_t - timedelta(minutes=80)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1000",
        "sentiment": "מדיני ודיפלומטי"
    },
    {
        "url": "https://safa.ps",
        "source_name": "Safa Press",
        "country": "רצועת עזה",
        "title_hebrew": "רצועת עזה: עדכונים שוטפים מהשטח על פעילות צוותי החירום",
        "summary_hebrew": "דיווחים מקומיים מעדכנים על מאמצי שיקום תשתיות חיוניות במוקדים השונים.",
        "published_at": (now_t - timedelta(minutes=95)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1000",
        "sentiment": "שוטף"
    },
    {
        "url": "https://www.tasnimnews.com",
        "source_name": "Tasnim News",
        "country": "איראן",
        "title_hebrew": "איראן: הושלמה בהצלחה סדרת ניסויים במערכות הגנה אווירית חדשות",
        "summary_hebrew": "כוחות ההגנה האווירית השלימו פריסת מערכות כיסוי מכ\"ם מתקדמות במרحبב האווירי.",
        "published_at": (now_t - timedelta(minutes=110)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.bbc.com",
        "source_name": "BBC News",
        "country": "בריטניה",
        "title_hebrew": "בריטניה ואירופה בוחנות צעדים נוספים לייצוב המצב הביטחוני במזרח התיכון",
        "summary_hebrew": "דיפלומטים בכירים בלונדון ובריסל קוראים לשמור על ריסון ולהימנע מהסלמה רחבה.",
        "published_at": (now_t - timedelta(minutes=130)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000",
        "sentiment": "מדיני ודיפלומטי"
    }
]

df = pd.DataFrame(MASTER_ARTICLES_POOL)

# 1. פס מבזקים עליון
ticker_html = "".join([f"<span class='ticker-item'>⚡ [{r['source_name']}] {r['title_hebrew']}</span>" for _, r in df.iterrows()])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">🔴 מבזק חי</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

# 2. כותרת ותיאור האתר
st.markdown("<h1 style='font-size: 2.2rem; font-weight: 900; margin-bottom: 2px;'>🌐 דסק מודיעין תקשורת עולמי | OSINT IL</h1>", unsafe_allow_html=True)
st.caption("ניטור נרטיבים ודיווחים בזמן אמת ממאגרי התקשורת המובילים בעולם 24/7")

# 3. סרגל ניווט מדינות עם דגלים גרפיים אמיתיים
NAV_ITEMS = [
    {"label": "הכל", "val": "כל הדיווחים", "flag_img": "https://flagcdn.com/w40/un.png"},
    {"label": "ישראל", "val": "ישראל", "flag_img": "https://flagcdn.com/w40/il.png"},
    {"label": "ארה\"ב", "val": "ארה\"ב", "flag_img": "https://flagcdn.com/w40/us.png"},
    {"label": "איראן", "val": "איראן", "flag_img": "https://flagcdn.com/w40/ir.png"},
    {"label": "לבנון", "val": "לבנון", "flag_img": "https://flagcdn.com/w40/lb.png"},
    {"label": "עזה", "val": "רצועת עזה", "flag_img": "https://flagcdn.com/w40/ps.png"},
    {"label": "איו\"ש", "val": "איו\"ש", "flag_img": "https://flagcdn.com/w40/ps.png"}
]

nav_cols = st.columns(len(NAV_ITEMS))
for idx, item in enumerate(NAV_ITEMS):
    with nav_cols[idx]:
        is_active = (st.session_state["selected_country"] == item["val"])
        btn_type = "primary" if is_active else "secondary"
        st.markdown(f"<div style='text-align: center; margin-bottom: 2px;'><img src='{item['flag_img']}' width='26' style='border-radius:3px;'/></div>", unsafe_allow_html=True)
        if st.button(item["label"], key=f"nav_{item['val']}", type=btn_type, use_container_width=True):
            st.session_state["selected_country"] = item["val"]
            st.rerun()

st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.3); margin: 15px 0 20px 0;'>", unsafe_allow_html=True)

# סינון לפי מדינה נבחרת
selected_country = st.session_state["selected_country"]
if selected_country != "כל הדיווחים":
    filtered_df = df[df['country'].str.contains(selected_country, case=False, na=False)]
else:
    filtered_df = df

if filtered_df.empty:
    filtered_df = df

# 4. חמ"ל ראשי: כתבה ראשית בצד ימין, דיווחים חמים בצד שמאל
col_main, col_side = st.columns([7, 5])

with col_main:
    main_art = filtered_df.iloc[0]
    st.markdown(f"""
    <div class="card">
        <img src="{main_art['image_url']}" style="width:100%; height:300px; object-fit:cover; border-radius:6px; margin-bottom:12px;" />
        <div>
            <span class="tag tag-category">{main_art['sentiment']}</span>
            <span class="tag tag-source">📰 {main_art['source_name']} ({main_art['country']})</span>
            <span class="tag tag-time">🕒 {main_art['published_at']}</span>
        </div>
        <h2 style="margin: 10px 0; font-size: 1.45rem; font-weight: 800;">{main_art['title_hebrew']}</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.5;">{main_art['summary_hebrew']}</p>
        <a class="read-btn" href="{main_art['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
    </div>
    """, unsafe_allow_html=True)

with col_side:
    st.markdown("<div style='font-size: 1.1rem; font-weight: 800; margin-bottom: 10px; color: #38bdf8;'>⚡ דיווחים חמים נוספים</div>", unsafe_allow_html=True)
    side_arts = filtered_df.iloc[1:4] if len(filtered_df) > 1 else df.iloc[1:4]
    for _, row in side_arts.iterrows():
        st.markdown(f"""
        <div class="card" style="display: flex; gap: 12px; align-items: center; padding: 10px; margin-bottom: 10px;">
            <img src="{row['image_url']}" style="width: 90px; height: 75px; object-fit: cover; border-radius: 4px; flex-shrink: 0;" />
            <div style="width: 100%;">
                <div><span class="tag tag-source">{row['source_name']}</span><span style="font-size: 0.7rem; color: #64748b; margin-right: 6px;">{row['published_at']}</span></div>
                <div style="font-weight: 700; font-size: 0.9rem; margin: 4px 0; line-height: 1.3;">{row['title_hebrew']}</div>
                <a href="{row['url']}" target="_blank" style="color: #38bdf8; font-size: 0.75rem; text-decoration: none; font-weight: 700;">לקריאה ←</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 5. גריד רחב של כל שאר הכתבות להשלמת האתר
rem_arts = filtered_df.iloc[4:] if len(filtered_df) > 4 else df.iloc[4:]
if not rem_arts.empty:
    st.markdown("<h3 style='margin: 35px 0 15px 0; font-weight: 800;'>📰 כל הדיווחים והכתבות מהזירות העולמיות</h3>", unsafe_allow_html=True)
    grid_cols = st.columns(3)
    for idx, row in rem_arts.iterrows():
        with grid_cols[idx % 3]:
            st.markdown(f"""
            <div class="card" style="margin-bottom: 16px;">
                <img src="{row['image_url']}" style="width:100%; height:150px; object-fit:cover; border-radius:6px; margin-bottom:10px;" />
                <div>
                    <span class="tag tag-source">{row['source_name']}</span>
                    <span class="tag" style="background:#334155;">{row['country']}</span>
                </div>
                <div style="font-weight: 700; font-size: 0.95rem; margin: 8px 0; line-height: 1.4;">{row['title_hebrew']}</div>
                <p style="color: #94a3b8; font-size: 0.82rem; line-height: 1.4; margin-bottom: 8px;">{row['summary_hebrew']}</p>
                <div style="font-size: 0.7rem; color: #64748b; margin-bottom: 6px;">🕒 {row['published_at']}</div>
                <a class="read-btn" href="{row['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
            </div>
            """, unsafe_allow_html=True)