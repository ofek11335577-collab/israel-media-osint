# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import init_db, get_db_connection
from ingestion.fetcher import fetch_live_web_articles

init_db()

st.set_page_config(
    page_title="OSINT Global Desk | Tactical Intelligence Terminal",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# שאיבה ראשונית אוטומטית בעליית הסשן
if "initialized_fetch" not in st.session_state:
    with st.spinner("Connecting to live intelligence feeds..."):
        fetch_live_web_articles()
    st.session_state["initialized_fetch"] = True

# --- STATE MANAGEMENT ---
if "view_mode" not in st.session_state:
    st.session_state['view_mode'] = 'Main Dashboard'
if "selected_country" not in st.session_state:
    st.session_state['selected_country'] = 'All'
if "reading_article_id" not in st.session_state:
    st.session_state['reading_article_id'] = None

# --- UI STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: #07090e;
        color: #f1f5f9;
    }
    header[data-testid="stHeader"] { display: none !important; }

    .newsroom-header {
        background: linear-gradient(90deg, #0f172a, #1e293b);
        border-bottom: 2px solid #0284c7;
        padding: 14px 24px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .newsroom-logo {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
        font-size: 1.4rem;
        color: #ffffff;
    }
    .newsroom-logo span { color: #38bdf8; }

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
    }
    .ticker-badge {
        background: #dc2626;
        color: #ffffff;
        font-weight: 700;
        font-size: 0.78rem;
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
        font-weight: 500;
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

    .card {
        background: #111827;
        border: 1px solid rgba(56, 189, 248, 0.15);
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 18px;
        height: 100%;
        display: flex;
        flex-direction: column;
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
        font-weight: 600;
        margin-right: 6px;
    }
    .tag-source { background: #1f2937; color: #60a5fa; }
    .tag-time { background: #374151; color: #9ca3af; }
    .tag-breaking { background: #dc2626; color: #ffffff; }

    div.stButton > button {
        background-color: #1f2937 !important;
        color: #f8fafc !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #0284c7 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)
def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM articles ORDER BY published_at DESC, id DESC", conn)
    return df

df = load_data()

# --- TOP HEADER ---
st.markdown(f"""
<div class="newsroom-header">
    <div class="newsroom-logo">OSINT <span>DESK</span></div>
    <div>🟢 SYSTEM STATUS: SECURE &nbsp;|&nbsp; PIPELINE: LIVE RSS &nbsp;|&nbsp; {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</div>
</div>
""", unsafe_allow_html=True)

# --- TICKER ---
if not df.empty:
    ticker_headlines = [f"⚡ [{row['source_name']}] {row['title']}" for _, row in df.head(30).iterrows()]
    ticker_html = "".join([f"<span class='ticker-item'>{h}</span>" for h in ticker_headlines])
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker-badge">LIVE INTEL</div>
        <div class="ticker-content">{ticker_html}</div>
    </div>
    """, unsafe_allow_html=True)

# --- ARTICLE READING VIEW ---
if st.session_state['reading_article_id'] is not None:
    aid = st.session_state['reading_article_id']
    row = df[df['id'] == aid]
    
    if not row.empty:
        art = row.iloc[0]
        c_back, c_link = st.columns([6, 6])
        with c_back:
            if st.button("← Back to Newsroom"):
                st.session_state['reading_article_id'] = None
                st.rerun()
        with c_link:
            st.link_button("🔗 Open Original Source ↗", art['url'], use_container_width=True)
            
        st.markdown(f"<span class='tag tag-source'>📰 {art['source_name']}</span> <span class='tag tag-time'>🕒 {art['published_at']}</span> <span class='tag' style='background:#0369a1; color:#fff;'>{art['country']}</span>", unsafe_allow_html=True)
        st.title(art['title'])
        st.image(art['image_url'], use_container_width=True)
        
        st.markdown(f"""
        <div style="font-size: 1.12rem; line-height: 1.8; color: #e2e8f0; background: #111827; padding: 30px; border-radius: 10px; border-left: 4px solid #0284c7; margin-top: 20px; border: 1px solid rgba(56, 189, 248, 0.2);">
            {art['full_content']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.session_state['reading_article_id'] = None
        st.rerun()

# --- MAIN DASHBOARD ---
else:
    c_title, c_view, c_sync = st.columns([5, 4, 3])
    with c_title:
        st.markdown(f"<h2 style='font-weight: 800; margin: 0;'>Global Intelligence Desk</h2>", unsafe_allow_html=True)
        st.caption(f"Monitoring {len(df):,} verified live reports")

    with c_view:
        selected_view = st.radio("View", ['Main Dashboard', 'Analytics Terminal'], index=0 if st.session_state['view_mode'] == 'Main Dashboard' else 1, horizontal=True, label_visibility="collapsed")
        st.session_state['view_mode'] = selected_view

    with c_sync:
        if st.button("🔄 Sync & Refresh Feeds", use_container_width=True):
            with st.spinner("Fetching live intelligence feeds..."):
                new_count = fetch_live_web_articles()
                st.cache_data.clear()
            st.success(f"Synced successfully! Added {new_count} new reports.")
            st.rerun()

    # --- ZONES NAV ---
    NAV_ZONES = [
        {"label": "All", "val": "All", "flag": "https://flagcdn.com/w40/un.png"},
        {"label": "Iran", "val": "Iran", "flag": "https://flagcdn.com/w40/ir.png"},
        {"label": "Saudi Arabia", "val": "Saudi Arabia", "flag": "https://flagcdn.com/w40/sa.png"},
        {"label": "UAE", "val": "UAE", "flag": "https://flagcdn.com/w40/ae.png"},
        {"label": "Yemen", "val": "Yemen", "flag": "https://flagcdn.com/w40/ye.png"},
        {"label": "Syria", "val": "Syria", "flag": "https://flagcdn.com/w40/sy.png"},
        {"label": "Iraq", "val": "Iraq", "flag": "https://flagcdn.com/w40/iq.png"},
        {"label": "Gaza & WB", "val": "Gaza & WB", "flag": "https://flagcdn.com/w40/ps.png"},
        {"label": "US & Global", "val": "US & Global", "flag": "https://flagcdn.com/w40/us.png"}
    ]

    nav_cols = st.columns(len(NAV_ZONES))
    for idx, zone in enumerate(NAV_ZONES):
        with nav_cols[idx]:
            is_active = (st.session_state['selected_country'] == zone['val'])
            st.markdown(f"<div style='text-align: center; margin-bottom: 2px;'><img src='{zone['flag']}' width='24' style='border-radius:3px;'/></div>", unsafe_allow_html=True)
            if st.button(zone["label"], key=f"zone_{zone['val']}", type="primary" if is_active else "secondary", use_container_width=True):
                st.session_state['selected_country'] = zone['val']
                st.rerun()

    st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.2); margin: 15px 0;'>", unsafe_allow_html=True)

    # --- FILTERING ---
    selected_zone = st.session_state['selected_country']
    if selected_zone == "All":
        filtered_df = df
    else:
        filtered_df = df[df['country'].str.strip().str.lower() == selected_zone.strip().lower()]

    if st.session_state['view_mode'] == 'Analytics Terminal':
        st.markdown(f"### 🖥️ Analytics Archive ({len(filtered_df):,} items for zone: {selected_zone})")
        search_q = st.text_input("Search archive:")
        table_df = filtered_df.copy()
        if search_q:
            table_df = table_df[table_df['title'].str.contains(search_q, case=False, na=False) | table_df['source_name'].str.contains(search_q, case=False, na=False)]
        
        display_table = table_df[['published_at', 'country', 'source_name', 'sentiment', 'title', 'url']]
        display_table.columns = ['Date', 'Zone', 'Source', 'Sentiment', 'Title', 'URL']
        st.dataframe(display_table, use_container_width=True, height=550, hide_index=True)
    else:
        if filtered_df.empty:
            st.info(f"No active intelligence reports found for zone: {selected_zone}. Click 'Sync & Refresh Feeds' above to fetch latest updates.")
        else:
            # --- LEAD STORY ---
            lead = filtered_df.iloc[0]
            st.markdown(f"""
            <div class="card" style="margin-bottom: 24px; border: 1px solid rgba(220, 38, 38, 0.4);">
                <img class="card-img" style="height: 380px;" src="{lead['image_url']}" />
                <div>
                    <span class="tag tag-breaking">TOP LEAD STORY ({selected_zone.upper()})</span>
                    <span class="tag" style="background:#0369a1; color:#fff;">{lead['sentiment']}</span>
                    <span class="tag tag-source">📰 {lead['source_name']} ({lead['country']})</span>
                    <span class="tag tag-time">🕒 {lead['published_at']}</span>
                </div>
                <h2 style="margin: 12px 0 8px 0; font-size: 1.8rem; font-weight: 800; color: #ffffff;">{lead['title']}</h2>
                <p style="color: #94a3b8; font-size: 1.05rem; line-height: 1.6; margin-bottom: 15px;">{lead['summary']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c_b1, c_b2 = st.columns([6, 6])
            with c_b1:
                if st.button("📖 Read Full Intelligence Report ←", key=f"lead_read_{lead['id']}", type="primary", use_container_width=True):
                    st.session_state['reading_article_id'] = lead['id']
                    st.rerun()
            with c_b2:
                st.link_button("🔗 Open External Source ↗", lead['url'], use_container_width=True)

            # --- GRID ---
            rem = filtered_df[filtered_df['id'] != lead['id']]
            if not rem.empty:
                st.markdown(f"<h3 style='margin: 35px 0 15px 0; font-weight: 700;'>Zone Feed & Reports ({len(filtered_df)})</h3>", unsafe_allow_html=True)
                grid_cols = st.columns(3)
                for idx, row in rem.head(30).iterrows():
                    with grid_cols[idx % 3]:
                        st.markdown(f"""
                        <div class="card">
                            <img class="card-img" src="{row['image_url']}" />
                            <div>
                                <span class="tag tag-source">{row['source_name']}</span>
                                <span class="tag tag-time">🕒 {row['published_at']}</span>
                            </div>
                            <div style="font-weight: 700; font-size: 1.02rem; margin: 10px 0; line-height: 1.4; color: #ffffff;">{row['title']}</div>
                            <p style="color: #94a3b8; font-size: 0.85rem; line-height: 1.5; margin-bottom: 12px;">{row['summary']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        cb1, cb2 = st.columns(2)
                        with cb1:
                            if st.button("Read ←", key=f"grid_read_{row['id']}", use_container_width=True):
                                st.session_state['reading_article_id'] = row['id']
                                st.rerun()
                        with cb2:
                            st.link_button("Source ↗", row['url'], use_container_width=True)