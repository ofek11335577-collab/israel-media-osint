import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="OSINT IL Terminal",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# הגדרות מצב בסיסיות ללא מרכאות בעייתיות
if "view_mode" not in st.session_state:
    st.session_state['view_mode'] = 'Dashboard'

if "selected_country" not in st.session_state:
    st.session_state['selected_country'] = 'All'

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
        animation: ticker 50s linear infinite;
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
    .tag-source { background: #1e293b; color: #93c5fd; }
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
</style>
""", unsafe_allow_html=True)

now_t = datetime.now()
ARCHIVE_POOL = [
    {
        "url": "https://www.tehrantimes.com",
        "source_name": "Tehran Times",
        "country": "Iran",
        "title_hebrew": "טהראן: בחינת יוזמות משותפות לקידום יציבות אזורית מול לחצים זרים",
        "summary_hebrew": "בכירי מערך החוץ באיראן דנו בהשלכות הגיאופוליטיות של מעורבות המעצמות באזור.",
        "published_at": (now_t - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000",
        "sentiment": "Diplomatic"
    },
    {
        "url": "https://www.aljazeera.com",
        "source_name": "Al Jazeera",
        "country": "Yemen",
        "title_hebrew": "תימן: התפתחויות צבאיות משמעותיות במוקדי החיכוך במאריב ותעז",
        "summary_hebrew": "עימותים עצימים מדווחים בגזרות השונות, תוך השפעה ישירה על נתיבי התנועה.",
        "published_at": (now_t - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000",
        "sentiment": "Security"
    },
    {
        "url": "https://www.middleeasteye.net",
        "source_name": "Middle East Eye",
        "country": "Lebanon",
        "title_hebrew": "דרום לבנון: דיווחים על חילופי אש ותנועות כוחות סמוך לקו העימות",
        "summary_hebrew": "פעילות מבצעית עוררה כוננות בגזרה הצפונית, לצד מאמצי תיווך דיפלומטיים.",
        "published_at": (now_t - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000",
        "sentiment": "Security"
    },
    {
        "url": "https://english.alarabiya.net",
        "source_name": "Al Arabiya",
        "country": "Saudi Arabia",
        "title_hebrew": "היערכות ביטחונית ימית: סיכול איומים בנתיבי השיט בים האדום",
        "summary_hebrew": "כוחות הקואליציה השלימו יירוט מוצלח של כלי טיס בלתי מאוישים מעל מרחב המים.",
        "published_at": (now_t - timedelta(days=6)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000",
        "sentiment": "Security"
    }
]

df = pd.DataFrame(ARCHIVE_POOL)

ticker_html = "".join([f"<span class='ticker-item'>⚡ [{r['source_name']}] {r['title_hebrew']}</span>" for _, r in df.iterrows()])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">Live Ticker</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

c_title, c_view = st.columns([7, 5])
with c_title:
    st.markdown("<h1 style='font-size: 2rem; font-weight: 900; margin: 0;'>OSINT IL | Research Desk</h1>", unsafe_allow_html=True)
    st.caption("Intelligence Research System | Comprehensive Archive")

with c_view:
    view_options = ["Dashboard", "Terminal View"]
    st.session_state['view_mode'] = st.radio("View Mode", view_options, horizontal=True, label_visibility="collapsed")

NAV_ITEMS = [
    {"label": "All", "val": "All", "flag": "🌐"},
    {"label": "Iran", "val": "Iran", "flag": "🇮🇷"},
    {"label": "Yemen", "val": "Yemen", "flag": "🇾🇪"},
    {"label": "Lebanon", "val": "Lebanon", "flag": "🇱🇧"},
    {"label": "Saudi Arabia", "val": "Saudi Arabia", "flag": "🇸🇦"}
]

nav_cols = st.columns(len(NAV_ITEMS))
for idx, item in enumerate(NAV_ITEMS):
    with nav_cols[idx]:
        is_active = (st.session_state['selected_country'] == item['val'])
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{item['flag']} {item['label']}", key=f"nav_{item['val']}", type=btn_type, use_container_width=True):
            st.session_state['selected_country'] = item['val']
            st.rerun()

st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.3); margin: 15px 0;'>", unsafe_allow_html=True)

selected_country = st.session_state['selected_country']
if selected_country != "All":
    filtered_df = df[df['country'] == selected_country]
else:
    filtered_df = df

if filtered_df.empty:
    filtered_df = df

if st.session_state['view_mode'] == "Terminal View":
    st.markdown("### Analytical Research Terminal", unsafe_allow_html=True)
    search_term = st.text_input("Search Archive:", placeholder="Type keyword...")
    
    table_df = filtered_df.copy()
    if search_term:
        table_df = table_df[
            table_df['title_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['summary_hebrew'].str.contains(search_term, case=False, na=False) |
            table_df['source_name'].str.contains(search_term, case=False, na=False)
        ]
    
    display_table = table_df[['published_at', 'country', 'source_name', 'sentiment', 'title_hebrew', 'url']]
    display_table.columns = ['Timestamp', 'Country', 'Source', 'Classification', 'Title', 'Link']
    st.dataframe(display_table, use_container_width=True, hide_index=True)
    st.info(f"Showing {len(table_df)} intelligence items.")
else:
    col_main, col_side = st.columns([7, 5])

    with col_main:
        main_art = filtered_df.iloc[0]
        st.markdown(f"""
        <div class="card">
            <img src="{main_art['image_url']}" style="width:100%; height:260px; object-fit:cover; border-radius:6px; margin-bottom:12px;" />
            <div>
                <span class="tag tag-category">{main_art['sentiment']}</span>
                <span class="tag tag-source">{main_art['source_name']} ({main_art['country']})</span>
                <span class="tag tag-time">{main_art['published_at']}</span>
            </div>
            <h2 style="margin: 10px 0; font-size: 1.35rem; font-weight: 800;">{main_art['title_hebrew']}</h2>
            <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.5;">{main_art['summary_hebrew']}</p>
            <a class="read-btn" href="{main_art['url']}" target="_blank">Read Full Report →</a>
        </div>
        """, unsafe_allow_html=True)

    with col_side:
        st.markdown("<div style='font-size: 1rem; font-weight: 800; margin-bottom: 10px; color: #38bdf8;'>Additional Archive Reports</div>", unsafe_allow_html=True)
        side_arts = filtered_df.iloc[1:4] if len(filtered_df) > 1 else df.iloc[1:4]
        for _, row in side_arts.iterrows():
            st.markdown(f"""
            <div class="card" style="display: flex; gap: 10px; align-items: center; padding: 10px; margin-bottom: 10px;">
                <img src="{row['image_url']}" style="width: 80px; height: 65px; object-fit: cover; border-radius: 4px; flex-shrink: 0;" />
                <div style="width: 100%;">
                    <div><span class="tag tag-source">{row['source_name']}</span><span style="font-size: 0.7rem; color: #64748b; margin-right: 6px;">{row['published_at']}</span></div>
                    <div style="font-weight: 700; font-size: 0.85rem; margin: 4px 0; line-height: 1.3;">{row['title_hebrew']}</div>
                    <a href="{row['url']}" target="_blank" style="color: #38bdf8; font-size: 0.72rem; text-decoration: none; font-weight: 700;">Read →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)