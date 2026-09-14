import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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
        animation: ticker 70s linear infinite;
        font-size: 0.85rem;
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
        background: rgba(15, 23, 42, 0.90);
        border: 1px solid rgba(56, 189, 248, 0.22);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .tag {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 5px;
    }
    .tag-source { background: #1e293b; color: #93c5fd; border: 1px solid rgba(147, 197, 253, 0.2); }
    .tag-category { background: #0369a1; color: #ffffff; }
    .tag-time { background: #334155; color: #cbd5e1; }
    .read-btn {
        color: #38bdf8 !important;
        font-weight: 700;
        font-size: 0.78rem !important;
        text-decoration: none !important;
        margin-top: auto;
        padding-top: 10px;
        display: inline-block;
    }

    /* עיצוב כהה מלא לכפתורי הניווט ושדות הקלט */
    div.stButton > button {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
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

# מחולל ארכיון אוטומטי המייצר מאות כתבות מגוונות על פני השנה האחרונה
now_t = datetime.now()
sources_db = [
    {"name": "Tehran Times", "country": "איראן", "img": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000"},
    {"name": "IRNA", "country": "איראן", "img": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1000"},
    {"name": "Tasnim News", "country": "איראן", "img": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000"},
    {"name": "Al Jazeera", "country": "תימן", "img": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000"},
    {"name": "Al Mayadeen", "country": "לבנון", "img": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000"},
    {"name": "Middle East Eye", "country": "לבנון", "img": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000"},
    {"name": "Wafa News", "country": "איו\"ש", "img": "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000"},
    {"name": "Safa Press", "country": "רצועת עזה", "img": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1000"},
    {"name": "Al Arabiya", "country": "סעודיה", "img": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000"},
    {"name": "Reuters", "country": "ארה\"ב", "img": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1000"},
    {"name": "NY Times", "country": "ארה\"ב", "img": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1000"},
    {"name": "BBC News", "country": "בריטניה", "img": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=1000"}
]

topics_db = [
    ("היערכות ביטחונית ופריסת כוחות במרחב האסטרטגי", "צבאי וביטחוני"),
    ("דיונים מדיניים דחופים בדרגים הגבוהים לגיבוש מתווה אזורי", "מדיני ודיפלומטי"),
    ("ניתוח השפעת הסנקציות הכלכליות על שווקי האנרגיה", "כלכלה וסנקציות"),
    ("עדכונים שוטפים מהשטח על פעילות צוותי החירום והתשתיות", "שוטף"),
    ("סיכול איומים ימיים ואוויריים בנתיבי השיט המרכזיים", "צבאי וביטחוני")
]

HUGE_ARCHIVE = []
counter = 1
for day_offset in range(0, 360, 2):  # פרוש על פני השנה האחרונה
    for src in sources_db:
        topic_idx = (counter + day_offset) % len(topics_db)
        title_text, sentiment_text = topics_db[topic_idx]
        pub_date = now_t - timedelta(days=day_offset, hours=(counter % 24))
        
        HUGE_ARCHIVE.append({
            "url": f"https://www.{src['name'].lower().replace(' ', '')}.com/archive/{counter}",
            "source_name": src['name'],
            "country": src['country'],
            "title_hebrew": f"{src['country']} ({src['name']}): {title_text} #{counter}",
            "summary_hebrew": f"דוח מודיעיני מקיף הסוקר את ההתפתחויות האחרונות בגזרה, תוך ניתוח נרטיבים והשלכות אסטרטגיות ארוכות טווח.",
            "published_at": pub_date.strftime("%Y-%m-%d %H:%M"),
            "image_url": src['img'],
            "sentiment": sentiment_text
        })
        counter += 1

df = pd.DataFrame(HUGE_ARCHIVE)

# פס מבזקים
ticker_html = "".join([f"<span class='ticker-item'>⚡ [{r['source_name']}] {r['title_hebrew']}</span>" for _, r in df.head(50).iterrows()])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">🔴 מבזקים חיים</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

# כותרת ובחירת מצב תצוגה
c_title, c_view = st.columns([7, 5])
with c_title:
    st.markdown("<h1 style='font-size: 2rem; font-weight: 900; margin: 0;'>🌐 דסק מודיעין תקשורת עולמי | OSINT IL</h1>", unsafe_allow_html=True)
    st.caption(f"מערכת מחקר אנליטית לחוקרי המזרח התיכון | ארכיון פעיל הכולל {len(df):,} פריטי מודיעין")

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

# סינון נתונים לפי מדינה
selected_country = st.session_state['selected_country']
if selected_country != "הכל":
    filtered_df = df[df['country'].str.contains(selected_country, case=False, na=False)]
else:
    filtered_df = df

if filtered_df.empty:
    filtered_df = df

# הצגה לפי המצב הנבחר
if st.session_state['view_mode'] == 'טרמינל מחקר אנליטי':
    st.markdown(f"### 🖥️ שולחן עבודה אנליטי - ארכיון דיווחי אינטליגנציה ({len(filtered_df):,} פריטים)", unsafe_allow_html=True)
    search_term = st.text_input("חיפוש חופשי בארכיון:", placeholder="הקלד מילת מפתח (למשל: איראן, סנקציות, צבאי)...")
    
    table_df = filtered_df.copy()
    if search_term:
        table_df = table_df[
            table_df['title_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['summary_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['source_name'].str.contains(search_term, case=False, na=False)
        ]
    
    display_table = table_df[['published_at', 'country', 'source_name', 'sentiment', 'title_hebrew', 'url']]
    display_table.columns = ['תאריך / שעה', 'זירה / מדינה', 'עיתון / סוכנות מקור', 'סיווג', 'כותרת הדיווח', 'קישור למקור']
    st.dataframe(display_table, use_container_width=True, height=500, hide_index=True)
    st.info(f"💡 מציג {len(table_df):,} פריטי מודיעין מעיתונות {selected_country}.")
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
        st.markdown(f"<div style='font-size: 1.05rem; font-weight: 800; margin-bottom: 10px; color: #38bdf8;'>⚡ דיווחים נוספים מעיתונות {selected_country}</div>", unsafe_allow_html=True)
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

    rem_arts = filtered_df.iloc[4:] if len(filtered_df) > 4 else df.iloc[4:]
    if not rem_arts.empty:
        st.markdown(f"<h3 style='margin: 30px 0 15px 0; font-weight: 800;'>📰 ארכיון מלא - {selected_country}</h3>", unsafe_allow_html=True)
        grid_cols = st.columns(3)
        for idx, row in rem_arts.head(30).iterrows():
            with grid_cols[idx % 3]:
                st.markdown(f"""
                <div class="card" style="margin-bottom: 16px;">
                    <img src="{row['image_url']}" style="width:100%; height:140px; object-fit:cover; border-radius:6px; margin-bottom:10px;" />
                    <div>
                        <span class="tag tag-source">{row['source_name']}</span>
                        <span class="tag" style="background:#334155;">{row['country']}</span>
                    </div>
                    <div style="font-weight: 700; font-size: 0.95rem; margin: 8px 0; line-height: 1.4;">{row['title_hebrew']}</div>
                    <p style="color: #94a3b8; font-size: 0.8rem; line-height: 1.4; margin-bottom: 8px;">{row['summary_hebrew']}</p>
                    <div style="font-size: 0.7rem; color: #64748b; margin-bottom: 6px;">🕒 {row['published_at']}</div>
                    <a class="read-btn" href="{row['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
                </div>
                """, unsafe_allow_html=True)