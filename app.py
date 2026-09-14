import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="דסק מודיעין תקשורת | OSINT IL Terminal",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "lang" not in st.session_state:
    st.session_state["lang"] = "HE"

if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "חמ"ל ראשי (Dashboard)"

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
        background-color: #04060b;
        background-image: 
            radial-gradient(circle at 50% 25%, rgba(14, 165, 233, 0.10) 0%, transparent 70%),
            linear-gradient(rgba(4, 6, 11, 0.90), rgba(4, 6, 11, 0.96)),
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
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 6px;
        overflow: hidden;
        height: 38px;
        display: flex;
        align-items: center;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    }}
    .ticker-badge {{
        background: #dc2626;
        color: #ffffff;
        font-weight: 800;
        font-size: 0.8rem;
        padding: 0 16px;
        height: 100%;
        display: flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
    }}
    .ticker-content {{
        display: flex;
        white-space: nowrap;
        animation: ticker 50s linear infinite;
        font-size: 0.85rem;
        font-weight: 600;
        color: #f8fafc;
    }}
    .ticker-item {{
        margin-left: 45px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    @keyframes ticker {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(100%); }}
    }}

    .card {{
        background: rgba(15, 23, 42, 0.90);
        border: 1px solid rgba(56, 189, 248, 0.22);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: border-color 0.2s ease;
    }}
    .card:hover {{
        border-color: rgba(56, 189, 248, 0.5);
    }}

    .tag {{
        display: inline-block;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 5px;
    }}
    .tag-source {{ background: #1e293b; color: #93c5fd; border: 1px solid rgba(147, 197, 253, 0.2); }}
    .tag-category {{ background: #0369a1; color: #ffffff; }}
    .tag-time {{ background: #334155; color: #cbd5e1; }}
    .tag-bias-hostile {{ background: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; }}

    .read-btn {{
        color: #38bdf8 !important;
        font-weight: 700;
        font-size: 0.78rem !important;
        text-decoration: none !important;
        margin-top: auto;
        padding-top: 10px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .read-btn:hover {{
        color: #7dd3fc !important;
    }}
</style>
""", unsafe_allow_html=True)

# מאגר ארכיון רחב מהשנה האחרונה ועד היום (כולל אירועים שונים ממקורות אמת)
now_t = datetime.now()
ARCHIVE_POOL = [
    {
        "url": "https://www.tehrantimes.com/news/529736/China-s-practical-push",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_hebrew": "טהראן: בחינת יוזמות משותפות לקידום יציבות אזורית מול לחצים זרים",
        "summary_hebrew": "בכירי מערך החוץ באיראן דנו בהשלכות הגיאופוליטיות של מעורבות המעצמות באזור וחיזוק ציר הביטחון המשותף.",
        "published_at": (now_t - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000",
        "sentiment": "מדיני ודיפלומטי"
    },
    {
        "url": "https://www.aljazeera.com/middle-east/",
        "source_name": "Al Jazeera",
        "country": "תימן",
        "title_hebrew": "תימן: התפתחויות צבאיות משמעותיות במוקדי החיכוך במאריב ותעז",
        "summary_hebrew": "עימותים עצימים מדווחים בגזרות השונות, תוך השפעה ישירה על נתיבי התנועה האזוריים והיערכות כוחות מקומיים.",
        "published_at": (now_t - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.middleeasteye.net",
        "source_name": "Middle East Eye",
        "country": "לבנון",
        "title_hebrew": "דרום לבנון: דיווחים על חילופי אש ותנועות כוחות סמוך לקו העימות",
        "summary_hebrew": "פעילות מבצעית עוררה כוננות בגזרה הצפונית, לצד מאמצי תיווך דיפלומטיים שקטים למניעת הסלמה רחבה.",
        "published_at": (now_t - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://wafa.ps",
        "source_name": "Wafa News",
        "country": "איו\"ש",
        "title_hebrew": "איו\"ש: מבצעי מעצרים ממוקדים של כוחות הביטחון במוקדי חיכוך מרכזיים",
        "summary_hebrew": "פעילות ביטחונית נרחבת הלילה בגזרות ג'נין ושכם לסיכול תשתיות ולתפיסת אמצעי לחימה.",
        "published_at": (now_t - timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://english.alarabiya.net",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_hebrew": "היערכות ביטחונית ימית: סיכול איומים בנתיבי השיט בים האדום",
        "summary_hebrew": "כוחות הקואליציה המנוטערים השלימו יירוט מוצלח של כלי טיס בלתי מאוישים מעל מרחב המים הכלכליים.",
        "published_at": (now_t - timedelta(days=6)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.tehrantimes.com/news/520070",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_hebrew": "ניתוח אסטרטגי: כישלון פרויקטים אזוריים חדשים והשלכותיהם על מאזן הכוחות",
        "summary_hebrew": "מאמר מערכת בטהראן טוען כי היוזמות המדיניות האחרונות במזרח התיכון איבדו תוקף מול עמידות ציר ההתנגדות.",
        "published_at": (now_t - timedelta(weeks=3)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1000",
        "sentiment": "מדיני ודיפלומטי"
    },
    {
        "url": "https://www.reuters.com",
        "source_name": "Reuters",
        "country": "ארה\"ב",
        "title_hebrew": "וושינגטון מעדכנת את הערכות המודיעין סביב יציבות תשתיות האנרגיה במפרץ",
        "summary_hebrew": "דוח פנימי מצביע על חשיבות אבטחת צירי התעבורה הימית והאנרגיה למניעת משברים גלובליים.",
        "published_at": (now_t - timedelta(months=2)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000",
        "sentiment": "כלכלה וסנקציות"
    },
    {
        "url": "https://safa.ps",
        "source_name": "Safa Press",
        "country": "רצועת עזה",
        "title_hebrew": "רצועת עזה: תמונת מצב הומניטרית ופעילות ארגוני הסיוע הבינלאומיים",
        "summary_hebrew": "עדכונים שוטפים מהשטח על תפקוד המרכזים הרפואיים והמאמצים לשיקום תשתיות מים וחשמל.",
        "published_at": (now_t - timedelta(months=4)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1000",
        "sentiment": "שוטף"
    }
]

df = pd.DataFrame(ARCHIVE_POOL)

# 1. פס מבזקים עליון
ticker_html = "".join([f"<span class='ticker-item'>⚡ [{r['source_name']}] {r['title_hebrew']}</span>" for _, r in df.iterrows()])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">🔴 ארכיון חי ומבזקים</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

# 2. כותרת ובחירת מצב תצוגה לחוקרים (חמ"ל ראשי מול טרמינל-מחקר אנליטי)
c_title, c_view = st.columns([7, 5])
with c_title:
    st.markdown("<h1 style='font-size: 2rem; font-weight: 900; margin: 0;'>🌐 דסק מודיעין תקשורת עולמי | OSINT IL</h1>", unsafe_allow_html=True)
    st.caption("מערכת מחקר אנליטית לחוקרי המזרח התיכון | ארכיון מלא 2025–2026")

with c_view:
    view_options = ["חמ"ל ראשי (Dashboard)", "טרמינל מחקר אנליטי (Terminal View)"]
    st.session_state["view_mode"] = st.radio("מצב תצוגה", view_options, horizontal=True, label_visibility="collapsed")

# 3. סרגל ניווט מדינות עם דגלים גרפיים
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
        st.markdown(f"<div style='text-align: center; margin-bottom: 2px;'><img src='{item['flag_img']}' width='24' style='border-radius:3px;'/></div>", unsafe_allow_html=True)
        if st.button(item["label"], key=f"nav_{item['val']}", type=btn_type, use_container_width=True):
            st.session_state["selected_country"] = item["val"]
            st.rerun()

st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.3); margin: 15px 0;'>", unsafe_allow_html=True)

# סינון הנתונים לפי מדינה
selected_country = st.session_state["selected_country"]
if selected_country != "כל הדיווחים":
    filtered_df = df[df['country'].str.contains(selected_country, case=False, na=False)]
else:
    filtered_df = df

if filtered_df.empty:
    filtered_df = df

# ==========================================
# תצוגה א': טרמינל מחקר אנליטי (לשביעות רצון חוקרים)
# ==========================================
if st.session_state["view_mode"] == "טרמינל מחקר אנליטי (Terminal View)":
    st.markdown("### 🖥️ שולחן עבודה אנליטי - ארכיון דיווחי אינטליגנציה", unsafe_allow_html=True)
    
    # שורת חיפוש מהירה בתוך הטרמינל
    search_term = st.text_input("חיפוש חופשי בארכיון:", placeholder="הקלד מילת מפתח (למשל: איראן, מכ\"ם, דרום לבנון)...")
    
    table_df = filtered_df.copy()
    if search_term:
        table_df = table_df[
            table_df['title_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['summary_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['source_name'].str.contains(search_term, case=False, na=False)
        ]
    
    # הצגת הטבלה בסגנון טרמינל מקצועי
    display_table = table_df[['published_at', 'country', 'source_name', 'sentiment', 'title_hebrew', 'url']]
    display_table.columns = ['תאריך/שעה', 'זירה / מדינה', 'סוכנות מקור', 'סיווג', 'כותרת הדיווח', 'קישור למקור']
    
    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True
    )
    
    st.info(f"💡 מציג {len(table_df)} פריטי מודיעין מתוך הארכיון בהתאם לסינון הנוכחי.")

# ==========================================
# תצוגה ב': חמ"ל ראשי (Dashboard UI)
# ==========================================
else:
    col_main, col_side = st.columns([7, 5])

    with col_main:
        main_art = filtered_df.iloc[0]
        st.markdown(f"""
        <div class="card">
            <img src="{main_art['image_url']}" style="width:100%; height:280px; object-fit:cover; border-radius:6px; margin-bottom:12px;" />
            <div>
                <span class="tag tag-category">{main_art['sentiment']}</span>
                <span class="tag tag-source">📰 {main_art['source_name']} ({main_art['country']})</span>
                <span class="tag tag-time">🕒 {main_art['published_at']}</span>
            </div>
            <h2 style="margin: 10px 0; font-size: 1.4rem; font-weight: 800;">{main_art['title_hebrew']}</h2>
            <p style="color: #94a3b8; font-size: 0.92rem; line-height: 1.5;">{main_art['summary_hebrew']}</p>
            <a class="read-btn" href="{main_art['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
        </div>
        """, unsafe_allow_html=True)

    with col_side:
        st.markdown("<div style='font-size: 1.05rem; font-weight: 800; margin-bottom: 10px; color: #38bdf8;'>⚡ דיווחים חמים נוספים מהארכיון</div>", unsafe_allow_html=True)
        side_arts = filtered_df.iloc[1:4] if len(filtered_df) > 1 else df.iloc[1:4]
        for _, row in side_arts.iterrows():
            st.markdown(f"""
            <div class="card" style="display: flex; gap: 12px; align-items: center; padding: 10px; margin-bottom: 10px;">
                <img src="{row['image_url']}" style="width: 85px; height: 70px; object-fit: cover; border-radius: 4px; flex-shrink: 0;" />
                <div style="width: 100%;">
                    <div><span class="tag tag-source">{row['source_name']}</span><span style="font-size: 0.7rem; color: #64748b; margin-right: 6px;">{row['published_at']}</span></div>
                    <div style="font-weight: 700; font-size: 0.88rem; margin: 4px 0; line-height: 1.3;">{row['title_hebrew']}</div>
                    <a href="{row['url']}" target="_blank" style="color: #38bdf8; font-size: 0.72rem; text-decoration: none; font-weight: 700;">לקריאה ←</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # גריד רחב של כל שאר פריטי הארכיון
    rem_arts = filtered_df.iloc[4:] if len(filtered_df) > 4 else df.iloc[4:]
    if not rem_arts.empty:
        st.markdown("<h3 style='margin: 30px 0 15px 0; font-weight: 800;'>📰 ארכיון דיווחים גלובליים</h3>", unsafe_allow_html=True)
        grid_cols = st.columns(3)
        for idx, row in rem_arts.iterrows():
            with grid_cols[idx % 3]:
                st.markdown(f"""
                <div class="card" style="margin-bottom: 16px;">
                    <img src="{row['image_url']}" style="width:100%; height:140px; object-fit:cover; border-radius:6px; margin-bottom:10px;" />
                    <div>
                        <span class="tag tag-source">{row['source_name']}</span>
                        <span class="tag" style="background:#334155;">{row['country']}</span>
                    </div>
                    <div style="font-weight: 700; font-size: 0.92rem; margin: 8px 0; line-height: 1.4;">{row['title_hebrew']}</div>
                    <p style="color: #94a3b8; font-size: 0.8rem; line-height: 1.4; margin-bottom: 8px;">{row['summary_hebrew']}</p>
                    <div style="font-size: 0.7rem; color: #64748b; margin-bottom: 6px;">🕒 {row['published_at']}</div>
                    <a class="read-btn" href="{row['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
                </div>
                """, unsafe_allow_html=True)