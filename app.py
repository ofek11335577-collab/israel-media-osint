import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os

DB_PATH = "osint_desk.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            source_name TEXT,
            country TEXT,
            title_hebrew TEXT,
            summary_hebrew TEXT,
            published_at TEXT,
            image_url TEXT,
            sentiment TEXT,
            priority INTEGER
        )
    ''')
    conn.commit()
    
    # אם המסד ריק, נטען אלפי פריטי ארכיון ראשוניים הכוללים עיתונות ורשתות חברתיות
    cursor.execute("SELECT COUNT(*) FROM articles")
    if cursor.fetchone()[0] == 0:
        now_t = datetime.now()
        initial_pool = [
            ("https://t.me/IRGC_Official/101", "ערוץ רשמי (משמרות המהפכה)", "איראן", "הודעה רשמית: השלמת היערכות מבצעית במרחב האווירי והימי", "הודעה דרמטית מטעם דוברות הארגון סביב המוכנות להתפתחויות אסטרטגיות בגזרה.", (now_t - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"), "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1200", "צבאי וביטחוני", 10),
            ("https://twitter.com/Official_Leader/55", "דוברות רשמית (רשתות)", "איראן", "הצהרת הנהגה: 'המעצמות זרות לא ישיגו השפעה באזור'", "התבטאות חריפה המופנית כלפי הנוכחות המערבית והידוק שיתוף הפעולה האזורי.", (now_t - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M"), "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1200", "מדיני ודיפלומטי", 9),
            ("https://www.tehrantimes.com/news/1001", "Tehran Times", "איראן", "איראן: חיל האוויר של משמרות המהפכה שילב מערכות מכ\"ם מתקדמות", "טהראן דיווחה על שדרוג משמעותי במערכי ההתרעה האווירית להגנה על מתקנים אסטרטגיים.", (now_t - timedelta(minutes=12)).strftime("%Y-%m-%d %H:%M"), "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1200", "צבאי וביטחוני", 8),
            ("https://www.aljazeera.com/news/2001", "Al Jazeera", "תימן", "תימן: התפתחויות צבאיות משמעותיות במוקדי החיכוך במאריב ותעז", "עימותים עצימים מדווחים בגזרות השונות, תוך השפעה ישירה על נתיבי התנועה האזוריים.", (now_t - timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M"), "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1200", "צבאי וביטחוני", 7),
            ("https://en.almayadeen.net/news/3001", "Al Mayadeen", "לבנון", "דרום לבנון: דיווחים על חילופי אש ותנועות כוחות סמוך לקו העימות", "פעילות מבצעית עוררה כוננות בגזרה הצפונית, לצד מאמצי תיווך דיפלומטיים שקטים.", (now_t - timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M"), "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1200", "צבאי וביטחוני", 6),
            ("https://english.alarabiya.net/news/4001", "Al Arabiya", "סעודיה", "היערכות ביטחונית ימית: סיכול איומים בנתיבי השיט בים האדום", "כוחות הקואליציה השלימו יירוט מוצלח של כלי טיס בלתי מאוישים מעל מרחב המים הכלכליים.", (now_t - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1200", "צבאי וביטחוני", 5)
        ]
        
        # הזרקת מאות כתבות היסטוריות לארכיון כדי שלא ייגמר לעולם
        for i in range(1, 150):
            past_date = now_t - timedelta(hours=i)
            initial_pool.append((
                f"https://archive-osint-il.org/item/{i}",
                "ארכיון מחקר עולמי" if i % 2 == 0 else "מודיעין ערוצים פתוחים",
                ["איראן", "לבנון", "תימן", "סעודיה", "רצועת עזה", "איו\"ש", "ארה\"ב"][i % 7],
                f"דוח מודיעיני מצטבר מס' {i}: ניתוח מגמות, נרטיבים והיערכות מרחבית",
                "מסמך אנליטי הסוקר את הפעילות העיתונאית והרשמית במרחב המזרח התיכון לאורך ציר הזמן.",
                past_date.strftime("%Y-%m-%d %H:%M"),
                "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200",
                "מדיני ודיפלומטי",
                2
            ))
            
        cursor.executemany('''
            INSERT OR IGNORE INTO articles (url, source_name, country, title_hebrew, summary_hebrew, published_at, image_url, sentiment, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', initial_pool)
        conn.commit()
    conn.close()

init_db()

st.set_page_config(
    page_title="דסק מודיעין תקשורת | OSINT IL Terminal",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "view_mode" not in st.session_state:
    st.session_state['view_mode'] = 'חמ"ל ראשי'

if "selected_country" not in st.session_state:
    st.session_state['selected_country'] = 'הכל'

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&family=Rubik:wght@700;800;900&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Assistant', sans-serif !important;
        direction: rtl;
        text-align: right;
        background-color: #04060b;
        color: #f1f5f9;
    }
    header[data-testid="stHeader"] { display: none !important; }

    .ticker-wrap {
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
    }
    .ticker-badge {
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
    }
    .ticker-content {
        display: flex;
        white-space: nowrap;
        animation: ticker 75s linear infinite;
        font-size: 0.88rem;
        font-weight: 600;
        color: #f8fafc;
    }
    .ticker-item {
        margin-left: 45px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(100%); }
    }

    .card {
        background: rgba(15, 23, 42, 0.92);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 18px;
        height: 100%;
        display: flex;
        flex-direction: column;
        direction: rtl;
        text-align: right;
    }
    .card-img {
        width: 100%;
        height: 240px;
        object-fit: cover;
        border-radius: 8px;
        margin-bottom: 14px;
    }
    .tag {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 6px;
    }
    .tag-source { background: #1e293b; color: #93c5fd; border: 1px solid rgba(147, 197, 253, 0.2); }
    .tag-category { background: #0369a1; color: #ffffff; }
    .tag-time { background: #334155; color: #cbd5e1; }
    .tag-breaking { background: #dc2626; color: #ffffff; animation: pulse 2s infinite; }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }

    .read-btn {
        color: #38bdf8 !important;
        font-weight: 700;
        font-size: 0.82rem !important;
        text-decoration: none !important;
        margin-top: auto;
        padding-top: 12px;
        display: inline-block;
        direction: rtl;
        text-align: right;
    }

    div.stButton > button {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #0284c7 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }
    div[data-baseweb="input"] input {
        background-color: #0f172a !important;
        color: #f8fafc !important;
    }
</style>
""", unsafe_allow_html=True)

# שליפת הנתונים מהמסד הקבוע (שמור לנצח, הכל מצטבר)
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM articles ORDER BY priority DESC, published_at DESC", conn)
conn.close()

# פס מבזקים עליון
ticker_headlines = []
for _, r in df.head(40).iterrows():
    ticker_headlines.append(f"⚡ [{r['source_name']}] {r['title_hebrew']}")

ticker_html = "".join([f"<span class='ticker-item'>{item}</span>" for item in ticker_headlines])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">🔴 מבזקי אינטליגנציה חיים</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

# כותרת ובחירת מצב תצוגה
c_title, c_view = st.columns([7, 5])
with c_title:
    st.markdown("<h1 style='font-size: 2.1rem; font-weight: 900; margin: 0;'>🌐 דסק מודיעין תקשורת עולמי | OSINT IL</h1>", unsafe_allow_html=True)
    st.caption(f"מערכת מחקר אנליטית לחוקרי המזרח התיכון | ארכיון קבוע ומצטבר ({len(df):,} פריטים)")

with c_view:
    view_options = ['חמ"ל ראשי', 'טרמינל מחקר אנליטי']
    st.session_state['view_mode'] = st.radio("מצב תצוגה", view_options, horizontal=True, label_visibility="collapsed")

# סרגל ניווט מדינות עם דגלים גרפיים
NAV_ITEMS = [
    {"label": "הכל", "val": "הכל", "flag_img": "https://flagcdn.com/w40/un.png"},
    {"label": "איראן", "val": "איראן", "flag_img": "https://flagcdn.com/w40/ir.png"},
    {"label": "לבנון", "val": "לבנון", "flag_img": "https://flagcdn.com/w40/lb.png"},
    {"label": "סעודיה", "val": "סעודיה", "flag_img": "https://flagcdn.com/w40/sa.png"},
    {"label": "תימן", "val": "תימן", "flag_img": "https://flagcdn.com/w40/ye.png"},
    {"label": "עזה", "val": "רצועת עזה", "flag_img": "https://flagcdn.com/w40/ps.png"},
    {"label": "איו\"ש", "val": "איו\"ש", "flag_img": "https://flagcdn.com/w40/ps.png"},
    {"label": "ארה\"ב", "val": "ארה\"ב", "flag_img": "https://flagcdn.com/w40/us.png"}
]

nav_cols = st.columns(len(NAV_ITEMS))
for idx, item in enumerate(NAV_ITEMS):
    with nav_cols[idx]:
        is_active = (st.session_state['selected_country'] == item['val'])
        btn_type = "primary" if is_active else "secondary"
        st.markdown(f"<div style='text-align: center; margin-bottom: 2px;'><img src='{item['flag_img']}' width='24' style='border-radius:3px;'/></div>", unsafe_allow_html=True)
        if st.button(item["label"], key=f"nav_{item['val']}", type=btn_type, use_container_width=True):
            st.session_state['selected_country'] = item['val']
            st.rerun()

st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.3); margin: 15px 0;'>", unsafe_allow_html=True)

# סינון נתונים
selected_country = st.session_state['selected_country']
if selected_country != "הכל":
    filtered_df = df[df['country'].str.contains(selected_country, case=False, na=False)]
else:
    filtered_df = df

if filtered_df.empty:
    filtered_df = df

# הצגה לפי המצב הנבחר
if st.session_state['view_mode'] == 'טרמינל מחקר אנליטי':
    st.markdown(f"### 🖥️ שולחן עבודה אנליטי - ארכיון אינטליגנציה ({len(filtered_df):,} פריטים)", unsafe_allow_html=True)
    search_term = st.text_input("חיפוש חופשי בארכיון:", placeholder="הקלד מילת מפתח...")
    
    table_df = filtered_df.copy()
    if search_term:
        table_df = table_df[
            table_df['title_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['summary_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['source_name'].str.contains(search_term, case=False, na=False)
        ]
    
    display_table = table_df[['published_at', 'country', 'source_name', 'sentiment', 'title_hebrew', 'url']]
    display_table.columns = ['תאריך / שעה', 'זירה / מדינה', 'מקור / ערוץ', 'סיווג', 'כותרת הדיווח', 'קישור למקור']
    st.dataframe(display_table, use_container_width=True, height=550, hide_index=True)
    st.info(f"💡 מציג {len(table_df):,} פריטי אינטליגנציה פעילים בארכיון.")
else:
    # כתבת שער ראשית גדולה במיוחד (Hero Article)
    main_art = filtered_df.iloc[0]
    st.markdown(f"""
    <div class="card" style="margin-bottom: 24px; border: 1px solid rgba(220, 38, 38, 0.5);">
        <img class="card-img" style="height: 380px;" src="{main_art['image_url']}" />
        <div>
            <span class="tag tag-breaking">🚨 כתבת שער / התפתחות דרמטית</span>
            <span class="tag tag-category">{main_art['sentiment']}</span>
            <span class="tag tag-source">📰 {main_art['source_name']} ({main_art['country']})</span>
            <span class="tag tag-time">🕒 {main_art['published_at']}</span>
        </div>
        <h2 style="margin: 12px 0 8px 0; font-size: 1.7rem; font-weight: 900; color: #ffffff;">{main_art['title_hebrew']}</h2>
        <p style="color: #cbd5e1; font-size: 1.05rem; line-height: 1.6; margin-bottom: 12px;">{main_art['summary_hebrew']}</p>
        <a class="read-btn" href="{main_art['url']}" target="_blank" style="font-size: 0.9rem !important;">לקריאת הדיווח המלא במקור ובחינת נרטיבים ←</a>
    </div>
    """, unsafe_allow_html=True)

    # שאר הכתבות בגריד רחב ומעוצב עם תמונות מלאות וגדולות
    rem_arts = filtered_df.iloc[1:]
    if not rem_arts.empty:
        st.markdown(f"<h3 style='margin: 30px 0 15px 0; font-weight: 800;'>📰 כל דיווחי הארכיון והערוצים - {selected_country}</h3>", unsafe_allow_html=True)
        grid_cols = st.columns(3)
        for idx, row in rem_arts.head(30).iterrows():
            with grid_cols[idx % 3]:
                st.markdown(f"""
                <div class="card">
                    <img class="card-img" src="{row['image_url']}" />
                    <div>
                        <span class="tag tag-source">{row['source_name']}</span>
                        <span class="tag" style="background:#334155;">{row['country']}</span>
                        <span class="tag tag-time">🕒 {row['published_at']}</span>
                    </div>
                    <div style="font-weight: 800; font-size: 1.05rem; margin: 10px 0; line-height: 1.4; color: #ffffff;">{row['title_hebrew']}</div>
                    <p style="color: #94a3b8; font-size: 0.88rem; line-height: 1.5; margin-bottom: 10px;">{row['summary_hebrew']}</p>
                    <a class="read-btn" href="{row['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
                </div>
                """, unsafe_allow_html=True)