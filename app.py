# app.py
import streamlit as st
import pandas as pd
from database import init_db, get_db_connection
from ingestion.fetcher import ingest_live_feeds
from datetime import datetime

init_db()
ingest_live_feeds()

st.set_page_config(
    page_title="דסק מודיעין תקשורת | OSINT Global Newsroom",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "view_mode" not in st.session_state:
    st.session_state['view_mode'] = 'חמ"ל ראשי'

if "selected_country" not in st.session_state:
    st.session_state['selected_country'] = 'הכל'

if "reading_article_id" not in st.session_state:
    st.session_state['reading_article_id'] = None

if "lang" not in st.session_state:
    st.session_state['lang'] = 'עברית'

# עיצוב Newsroom פרימיום (Dark Tactical News Portal)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&family=Rubik:wght@700;800;900&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Assistant', sans-serif !important;
        background-color: #0b0f19;
        color: #f8fafc;
    }
    header[data-testid="stHeader"] { display: none !important; }

    /* Newsroom Top Status Bar */
    .newsroom-header {
        background: linear-gradient(90deg, #0f172a, #1e293b);
        border-bottom: 2px solid #0284c7;
        padding: 12px 20px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .newsroom-logo {
        font-family: 'Rubik', sans-serif;
        font-weight: 900;
        font-size: 1.5rem;
        color: #ffffff;
        letter-spacing: -0.5px;
    }
    .newsroom-logo span { color: #0284c7; }

    /* Breaking News Ticker */
    .ticker-wrap {
        width: 100%;
        background: #0f172a;
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-radius: 6px;
        overflow: hidden;
        height: 38px;
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
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
        color: #f1f5f9;
    }
    .ticker-item {
        margin-left: 50px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(100%); }
    }

    /* Editorial Cards */
    .card {
        background: #111827;
        border: 1px solid rgba(56, 189, 248, 0.18);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 18px;
        height: 100%;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .card:hover {
        border-color: rgba(56, 189, 248, 0.5);
        transform: translateY(-2px);
    }
    .card-img {
        width: 100%;
        height: 200px;
        object-fit: cover;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-left: 6px;
    }
    .tag-source { background: #1f2937; color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.2); }
    .tag-time { background: #374151; color: #9ca3af; }
    .tag-breaking { background: #dc2626; color: #ffffff; animation: pulse 2s infinite; }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }

    div.stButton > button {
        background-color: #1f2937 !important;
        color: #f8fafc !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #0284c7 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }
    div[data-baseweb="input"] input {
        background-color: #111827 !important;
        color: #f8fafc !important;
    }
</style>
""", unsafe_allow_html=True)

is_he = (st.session_state['lang'] == 'עברית')
lang_dir = "rtl" if is_he else "ltr"
st.markdown(f"<div style='direction: {lang_dir}; text-align: {'right' if is_he else 'left'};'>", unsafe_allow_html=True)

@st.cache_data(ttl=15)
def load_data():
    conn = get_db_connection()
    return pd.read_sql_query("SELECT * FROM articles ORDER BY priority DESC, id DESC", conn)

df = load_data()

# טיפול בנתונים ריקים
df['title_english'] = df['title_english'].fillna("Breaking News")
df['title_hebrew'] = df['title_hebrew'].fillna(df['title_english'])
df['summary_english'] = df['summary_english'].fillna("No summary available.")
df['summary_hebrew'] = df['summary_hebrew'].fillna(df['summary_english'])

# פריסת Newsroom Header עליון
st.markdown(f"""
<div class="newsroom-header">
    <div class="newsroom-logo">OSINT <span>DESK</span></div>
    <div>🟢 SYSTEM STATUS: SECURE &nbsp;|&nbsp; DATA PIPELINE: ACTIVE &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC</div>
</div>
""", unsafe_allow_html=True)

# פס מבזקים
t_col = 'title_hebrew' if is_he else 'title_english'
ticker_headlines = [f"⚡ [{r['source_name']}] {r[t_col]}" for _, r in df.head(30).iterrows()]
ticker_html = "".join([f"<span class='ticker-item'>{item}</span>" for item in ticker_headlines])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">{"🔴 מבזקים חיים" if is_he else "🔴 LIVE FEED"}</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# מצב קריאת כתבה פנימי (Editorial Article Page)
# ==========================================
if st.session_state['reading_article_id'] is not None:
    art_id = st.session_state['reading_article_id']
    art_row = df[df['id'] == art_id]
    
    if not art_row.empty:
        art = art_row.iloc[0]
        
        c_back, c_link = st.columns([6, 6])
        with c_back:
            if st.button("← חזרה לעמוד הבית" if is_he else "← Back to Newsroom"):
                st.session_state['reading_article_id'] = None
                st.rerun()
        with c_link:
            st.link_button("🔗 מעבר ישיר לכתבה המקורית ↗" if is_he else "🔗 Open Original Source ↗", art['url'], use_container_width=True)
            
        title_display = art['title_hebrew'] if is_he else art['title_english']
        content_display = art['full_content_hebrew'] if is_he else art['full_content_english']
        
        st.markdown(f"<span class='tag tag-source'>📰 {art['source_name']}</span> <span class='tag tag-time'>🕒 {art['published_at']}</span>", unsafe_allow_html=True)
        st.title(title_display)
        
        st.image(art['image_url'], use_container_width=True)
        
        st.markdown(f"""
        <div style="font-size: 1.15rem; line-height: 1.9; color: #e2e8f0; background: #111827; padding: 30px; border-radius: 10px; border-left: {'none' if is_he else '4px solid #0284c7'}; border-right: {'4px solid #0284c7' if is_he else 'none'}; margin-top: 20px; border: 1px solid rgba(56, 189, 248, 0.2);">
            {content_display}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.session_state['reading_article_id'] = None
        st.rerun()

# ==========================================
# חמ"ל ראשי / פורטל חדשות
# ==========================================
else:
    c_title, c_view, c_lang = st.columns([5, 4, 3])
    with c_title:
        st.markdown(f"<h2 style='font-weight: 900; margin: 0;'>🌐 {'דסק מודיעין עולמי' if is_he else 'Global Intelligence Desk'}</h2>", unsafe_allow_html=True)
        st.caption(f"ניטור שוטף של {len(df):,} פריטי אינטליגנציה" if is_he else f"Monitoring {len(df):,} items")

    with c_view:
        view_options = ['חמ"ל ראשי', 'טרמינל מחקר אנליטי'] if is_he else ['Main Dashboard', 'Analytics Terminal']
        current_view_idx = 0 if st.session_state['view_mode'] in ['חמ"ל ראשי', 'Main Dashboard'] else 1
        selected_view = st.radio("View", view_options, index=current_view_idx, horizontal=True, label_visibility="collapsed")
        st.session_state['view_mode'] = 'חמ"ל ראשי' if selected_view in ['חמ"ל ראשי', 'Main Dashboard'] else 'טרמינל מחקר אנליטי'

    with c_lang:
        lang_choice = st.selectbox("Language", ["עברית (HE)", "English (EN)"], index=0 if is_he else 1, label_visibility="collapsed")
        new_lang = 'עברית' if "HE" in lang_choice else 'English'
        if new_lang != st.session_state['lang']:
            st.session_state['lang'] = new_lang
            st.rerun()

    # סרגל ניווט מדינות וזירות מורחב
    NAV_ITEMS = [
        {"label": "הכל", "val": "הכל", "flag_img": "https://flagcdn.com/w40/un.png"},
        {"label": "איראן", "val": "איראן", "flag_img": "https://flagcdn.com/w40/ir.png"},
        {"label": "סעודיה", "val": "סעודיה", "flag_img": "https://flagcdn.com/w40/sa.png"},
        {"label": "האמירויות", "val": "איחוד האמירויות", "flag_img": "https://flagcdn.com/w40/ae.png"},
        {"label": "תימן", "val": "תימן", "flag_img": "https://flagcdn.com/w40/ye.png"},
        {"label": "סוריה", "val": "סוריה", "flag_img": "https://flagcdn.com/w40/sy.png"},
        {"label": "עיראק", "val": "עיראק", "flag_img": "https://flagcdn.com/w40/iq.png"},
        {"label": "עזה ואיו\"ש", "val": "רצועת עזה", "flag_img": "https://flagcdn.com/w40/ps.png"},
        {"label": "ארה\"ב ועולם", "val": "ארה\"ב", "flag_img": "https://flagcdn.com/w40/us.png"}
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

    st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.2); margin: 15px 0;'>", unsafe_allow_html=True)

    selected_country = st.session_state['selected_country']
    filtered_df = df[df['country'].str.contains(selected_country, case=False, na=False)] if selected_country != "הכל" else df
    if filtered_df.empty:
        filtered_df = df

    if st.session_state['view_mode'] in ['טרמינל מחקר אנליטי', 'Analytics Terminal']:
        st.markdown(f"### 🖥️ {'ארכיון נתונים אנליטי' if is_he else 'Analytics Table'} ({len(filtered_df):,} items)")
        search_term = st.text_input("חיפוש חופשי בארכיון:" if is_he else "Search archive:")
        
        table_df = filtered_df.copy()
        if search_term:
            table_df = table_df[table_df['title_hebrew'].str.contains(search_term, case=False, na=False) | table_df['source_name'].str.contains(search_term, case=False, na=False)]
        
        t_col_name = 'title_hebrew' if is_he else 'title_english'
        disp_cols = ['published_at', 'country', 'source_name', 'sentiment', t_col_name, 'url']
        display_table = table_df[disp_cols]
        display_table.columns = ['תאריך', 'זירה', 'מקור', 'סיווג', 'כותרת', 'קישור'] if is_he else ['Date', 'Zone', 'Source', 'Sentiment', 'Title', 'URL']
        st.dataframe(display_table, use_container_width=True, height=550, hide_index=True)
    else:
        # כתבת שער ראשית (Lead Story)
        main_art = filtered_df.iloc[0]
        main_title = main_art['title_hebrew'] if is_he else main_art['title_english']
        main_summ = main_art['summary_hebrew'] if is_he else main_art['summary_english']
        
        st.markdown(f"""
        <div class="card" style="margin-bottom: 24px; border: 1px solid rgba(220, 38, 38, 0.4);">
            <img class="card-img" style="height: 380px;" src="{main_art['image_url']}" />
            <div>
                <span class="tag tag-breaking">{'🚨 ידיעת שער מרכזית' if is_he else '🚨 Top Lead Story'}</span>
                <span class="tag tag-category">{main_art['sentiment']}</span>
                <span class="tag tag-source">📰 {main_art['source_name']} ({main_art['country']})</span>
                <span class="tag tag-time">🕒 {main_art['published_at']}</span>
            </div>
            <h2 style="margin: 12px 0 8px 0; font-size: 1.8rem; font-weight: 900; color: #ffffff;">{main_title}</h2>
            <p style="color: #94a3b8; font-size: 1.05rem; line-height: 1.6; margin-bottom: 15px;">{main_summ}</p>
        </div>
        """, unsafe_allow_html=True)
        
        c_btn1, c_btn2 = st.columns([6, 6])
        with c_btn1:
            if st.button("📖 קרא כתבה מלאה בדסק ←" if is_he else "📖 Read Full Story ←", key=f"main_read_{main_art['id']}", type="primary", use_container_width=True):
                st.session_state['reading_article_id'] = main_art['id']
                st.rerun()
        with c_btn2:
            st.link_button("🔗 מעבר למקור החיצוני ↗" if is_he else "🔗 Open Original Source ↗", main_art['url'], use_container_width=True)

        # שאר הכתבות בגריד חדשותי נקי
        rem_arts = filtered_df[filtered_df['id'] != main_art['id']]
        if not rem_arts.empty:
            st.markdown(f"<h3 style='margin: 35px 0 15px 0; font-weight: 800;'>{'📰 כל חדשות הזירה והדיווחים' if is_he else '📰 Zone Feed & Reports'}</h3>", unsafe_allow_html=True)
            grid_cols = st.columns(3)
            for idx, row in rem_arts.head(30).iterrows():
                with grid_cols[idx % 3]:
                    r_title = row['title_hebrew'] if is_he else row['title_english']
                    r_summ = row['summary_hebrew'] if is_he else row['summary_english']
                    st.markdown(f"""
                    <div class="card">
                        <img class="card-img" src="{row['image_url']}" />
                        <div>
                            <span class="tag tag-source">{row['source_name']}</span>
                            <span class="tag tag-time">🕒 {row['published_at']}</span>
                        </div>
                        <div style="font-weight: 800; font-size: 1.05rem; margin: 10px 0; line-height: 1.4; color: #ffffff;">{r_title}</div>
                        <p style="color: #94a3b8; font-size: 0.85rem; line-height: 1.5; margin-bottom: 12px;">{r_summ}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_card_btn1, c_card_btn2 = st.columns(2)
                    with c_card_btn1:
                        if st.button("קרא ←" if is_he else "Read ←", key=f"grid_read_{row['id']}", use_container_width=True):
                            st.session_state['reading_article_id'] = row['id']
                            st.rerun()
                    with c_card_btn2:
                        st.link_button("למקור ↗" if is_he else "Source ↗", row['url'], use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)