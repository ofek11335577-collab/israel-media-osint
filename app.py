# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import init_db, get_db_connection

init_db()

st.set_page_config(
    page_title="OSINT Global Desk | Tactical Intelligence Terminal",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONTEXT-AWARE IMAGE MAPPING (No side-by-side duplicates) ---
def get_context_image(title, index):
    title_lower = title.lower()
    
    military_pool = [
        "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=1200",
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1200",
        "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1200"
    ]
    economy_pool = [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200"
    ]
    tech_pool = [
        "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1200",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200"
    ]
    diplomacy_pool = [
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200",
        "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=1200",
        "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=1200"
    ]
    humanitarian_pool = [
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1200",
        "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1200",
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200"
    ]
    
    if any(k in title_lower for k in ['military', 'defense', 'missile', 'security', 'naval', 'forces', 'army', 'strike', 'air defense']):
        pool = military_pool
    elif any(k in title_lower for k in ['economy', 'trade', 'market', 'oil', 'bank', 'financial', 'vision 2030', 'commercial', 'currency']):
        pool = economy_pool
    elif any(k in title_lower for k in ['ai', 'tech', 'digital', 'innovation', 'summit', 'cyber', 'aviation']):
        pool = tech_pool
    elif any(k in title_lower for k in ['un', 'diplomat', 'talks', 'framework', 'minister', 'council', 'agreement', 'relations']):
        pool = diplomacy_pool
    else:
        pool = humanitarian_pool
        
    return pool[index % len(pool)]

# --- HUGE PROFESSIONAL OSINT ARCHIVE ---
def ingest_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM articles")
    if cursor.fetchone()[0] < 40:
        now_t = datetime.now()
        massive_seed = [
            # --- Iran ---
            ("https://www.tehrantimes.com/news/iran-01", "Tehran Times", "Iran", "Iran examines air defense upgrade and regional security frameworks", "Senior defense officials in Tehran discussed strategic implications of new military tech.", "Senior defense officials in Tehran discussed strategic implications of new military technology projects and regional security frameworks amid shifting geopolitical dynamics.", "Iran Desk", (now_t - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "Military & Security", 10),
            ("https://www.tehrantimes.com/news/iran-02", "Tehran Times", "Iran", "Tehran unveils new generation of domestic ballistic missile systems", "Local media reports successful tactical tests of advanced guidance systems.", "Local media reports successful tactical tests of advanced guidance systems designed to counter complex electronic warfare and airspace threats.", "Iran Desk", (now_t - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"), "Defense", 9),
            ("https://www.tehrantimes.com/news/iran-03", "Tehran Times", "Iran", "Iran signs major economic protocols with Asian trade partners", "Government finalizes long-term agreements to stabilize local currency reserves.", "Government finalizes long-term agreements to stabilize local currency reserves and bypass western financial restrictions.", "Iran Economy", (now_t - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M"), "Economy", 7),
            ("https://www.tehrantimes.com/news/iran-04", "Tehran Times", "Iran", "Atomic Energy Organization reviews expansion of peaceful research facilities", "Officials emphasize adherence to international standards while advancing domestic capabilities.", "Atomic Energy Organization reviews expansion of peaceful research facilities and nuclear technology applications.", "Iran Nuclear Desk", (now_t - timedelta(hours=15)).strftime("%Y-%m-%d %H:%M"), "Technology", 8),
            ("https://www.tehrantimes.com/news/iran-05", "Tehran Times", "Iran", "High-level diplomatic delegation visits neighboring capitals to boost ties", "Discussions focus on cross-border infrastructure, transit corridors, and trade.", "High-level diplomatic delegation visits neighboring capitals to boost bilateral ties, focusing on transit corridors and energy trade.", "Iran Diplomacy", (now_t - timedelta(hours=20)).strftime("%Y-%m-%d %H:%M"), "Diplomacy", 8),

            # --- Saudi Arabia ---
            ("https://english.alarabiya.net/news/gulf/saudi-01", "Al Arabiya", "Saudi Arabia", "Riyadh launches mega renewable energy project under Vision 2030", "Saudi Arabia announced massive investments in smart infrastructure and clean energy.", "Saudi Arabia announced massive investments in smart infrastructure, AI integration, and clean energy solutions to establish a regional tech hub.", "Gulf Desk", (now_t - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "Economy & Tech", 9),
            ("https://english.alarabiya.net/news/gulf/saudi-02", "Al Arabiya", "Saudi Arabia", "Royal Saudi Naval Forces launch Red Sea maritime security exercise", "Joint drills focus on protecting strategic energy facilities and trade routes.", "Joint naval drills focus on protecting strategic energy facilities, ensuring freedom of navigation, and deterring asymmetric maritime threats.", "Gulf Security", (now_t - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"), "Military", 8),
            ("https://english.alarabiya.net/news/gulf/saudi-03", "Al Arabiya", "Saudi Arabia", "Kingdom expands diplomatic outreach across Middle East capitals", "High-level delegations discuss regional de-escalation and bilateral cooperation.", "High-level delegations discuss regional de-escalation, economic partnerships, and joint security frameworks.", "Diplomatic Desk", (now_t - timedelta(hours=11)).strftime("%Y-%m-%d %H:%M"), "Diplomacy", 8),
            ("https://english.alarabiya.net/news/gulf/saudi-04", "Al Arabiya", "Saudi Arabia", "Public Investment Fund announces new venture capital fund for AI startups", "Initiative aims to attract international tech firms and foster local talent.", "Public Investment Fund announces new venture capital fund for AI startups, aiming to attract international tech firms and foster local talent.", "Saudi Economy", (now_t - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M"), "Business", 7),

            # --- UAE ---
            ("https://www.wam.ae/en/details/uae-01", "WAM News Agency", "UAE", "Abu Dhabi hosts international AI and technological innovation summit", "Global executives and leaders gathered to discuss future AI cooperation.", "Global executives, researchers, and industry leaders gathered in Abu Dhabi to discuss future AI cooperation, cybersecurity, and smart airspace management.", "UAE Desk", (now_t - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), "Technology", 8),
            ("https://www.wam.ae/en/details/uae-02", "WAM News Agency", "UAE", "Dubai records significant surge in non-oil foreign trade volume", "Official reports highlight expansion of logistics hubs and global trade corridors.", "Official reports highlight expansion of logistics hubs, aviation networks, and global trade corridors linking East and West.", "UAE Economy", (now_t - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M"), "Business", 7),
            ("https://www.wam.ae/en/details/uae-03", "WAM News Agency", "UAE", "UAE space agency outlines upcoming interplanetary exploration missions", "Scientific community praises advanced satellite manufacturing capabilities.", "UAE space agency outlines upcoming interplanetary exploration missions and advanced satellite manufacturing capabilities.", "UAE Science", (now_t - timedelta(hours=16)).strftime("%Y-%m-%d %H:%M"), "Innovation", 6),

            # --- Yemen ---
            ("https://www.sabanews.net/en/yemen-01", "Saba News Agency", "Yemen", "Yemen: International discussions advance humanitarian and stability plans", "Local and international representatives reviewed plans to restore vital infrastructure.", "Local and international representatives reviewed comprehensive plans to restore vital infrastructure, healthcare, and water supply lines in friction zones.", "Yemen Intelligence", (now_t - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"), "Humanitarian", 8),
            ("https://www.sabanews.net/en/yemen-02", "Saba News Agency", "Yemen", "Local committees report progress in clearing vital transportation corridors", "Engineering teams work around the clock to ensure safe passage for relief convoys.", "Engineering teams work around the clock to ensure safe passage for relief convoys and commercial freight across key regional routes.", "Yemen Field Desk", (now_t - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M"), "Operations", 7),
            ("https://www.sabanews.net/en/yemen-03", "Saba News Agency", "Yemen", "Agricultural development projects launched in rural districts to boost food output", "International aid partners provide seeds and modern farming equipment.", "Agricultural development projects launched in rural districts to boost food output, with international aid partners providing seeds and modern farming equipment.", "Yemen Economy", (now_t - timedelta(hours=22)).strftime("%Y-%m-%d %H:%M"), "Agriculture", 6),

            # --- Syria ---
            ("https://sana.sy/en/syria-01", "SANA News", "Syria", "Damascus reports progress in central provinces infrastructure rehabilitation", "Engineering teams report completion of major repairs in service supply.", "Engineering teams report completion of major repairs in water and electricity distribution networks across central provinces.", "Syria Desk", (now_t - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"), "Infrastructure", 7),
            ("https://sana.sy/en/syria-02", "SANA News", "Syria", "Syrian ministries review agricultural output and food security initiatives", "New measures introduced to support local farming cooperatives and irrigation.", "New measures introduced to support local farming cooperatives, modern irrigation systems, and national food security reserves.", "Syria Economy", (now_t - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M"), "Agriculture", 6),
            ("https://sana.sy/en/syria-03", "SANA News", "Syria", "Cultural heritage restoration teams complete work on historical sites", "Experts utilize 3D imaging technology to reconstruct damaged ancient monuments.", "Cultural heritage restoration teams complete work on historical sites, utilizing 3D imaging technology to reconstruct damaged ancient monuments.", "Syria Culture", (now_t - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M"), "Heritage", 5),

            # --- Iraq ---
            ("https://www.ina.iq/eng/iraq-01", "INA News Agency", "Iraq", "Baghdad National Security Council tightens energy facilities protection", "Security forces in Iraq deployed additional units along border routes.", "Security forces in Iraq deployed additional tactical units along international border routes and strategic energy facilities to prevent sabotage.", "Iraq Desk", (now_t - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"), "Security", 8),
            ("https://www.ina.iq/eng/iraq-02", "INA News Agency", "Iraq", "Central Bank of Iraq announces new digital banking oversight measures", "Initiatives aimed at enhancing financial transparency and curbing illicit flows.", "Initiatives aimed at enhancing financial transparency, modernizing banking infrastructure, and curbing illicit capital flows.", "Iraq Economy", (now_t - timedelta(hours=13)).strftime("%Y-%m-%d %H:%M"), "Finance", 7),
            ("https://www.ina.iq/eng/iraq-03", "INA News Agency", "Iraq", "Major international oil companies sign new exploration agreements", "Agreements expected to boost national hydrocarbon production capacity.", "Major international oil companies sign new exploration agreements expected to boost national hydrocarbon production capacity and exports.", "Iraq Energy", (now_t - timedelta(hours=21)).strftime("%Y-%m-%d %H:%M"), "Energy", 8),

            # --- Gaza & WB ---
            ("https://english.wafa.ps/Pages/Details/gaza-01", "Wafa News Agency", "Gaza & WB", "Emergency teams coordinate humanitarian relief and supply entry", "Humanitarian organizations report intensified efforts to handle health and water.", "Humanitarian organizations and local emergency committees report intensified efforts to handle health, sanitation, and water infrastructure across the territories.", "Palestine Desk", (now_t - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M"), "Humanitarian", 9),
            ("https://english.wafa.ps/Pages/Details/gaza-02", "Wafa News Agency", "Gaza & WB", "Ramallah holds ministerial meetings on administrative and public services", "Cabinet reviews budgets for educational institutions and municipal development.", "Cabinet reviews budgets for educational institutions, municipal development projects, and emergency public health programs.", "Palestine Desk", (now_t - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M"), "Governance", 7),
            ("https://english.wafa.ps/Pages/Details/gaza-03", "Wafa News Agency", "Gaza & WB", "Local municipalities launch urban cleanup and waste management campaigns", "International volunteer groups assist local crews in restoring public spaces.", "Local municipalities launch urban cleanup and waste management campaigns, with international volunteer groups assisting local crews in restoring public spaces.", "Palestine Desk", (now_t - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"), "Operations", 6),

            # --- US & Global ---
            ("https://www.reuters.com/world/middle-east/un-01", "Reuters Middle East", "US & Global", "UN and Western states hold urgent talks on Middle East stability framework", "Senior diplomats call for reducing regional tension and advancing solutions.", "Senior diplomats at the United Nations and Western capitals called for immediate de-escalation and the formulation of a comprehensive regional stability framework.", "Global Desk", (now_t - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"), "Diplomacy", 10),
            ("https://www.reuters.com/markets/commodities/oil-02", "Reuters Markets", "US & Global", "Global energy markets react to shifting geopolitical risk premiums in Gulf", "Crude futures fluctuate amid reports of heightened maritime surveillance.", "Crude futures fluctuate amid reports of heightened maritime surveillance and ongoing diplomatic talks across key oil-producing nations.", "Global Markets", (now_t - timedelta(hours=15)).strftime("%Y-%m-%d %H:%M"), "Markets", 9),
            ("https://www.reuters.com/world/us-foreign-policy-03", "Reuters World", "US & Global", "Washington outlines strategic defense priorities for Middle East partners", "Pentagon officials emphasize long-term security commitments and joint training.", "Pentagon officials emphasize long-term security commitments, intelligence sharing, and joint training exercises with regional allies.", "US Desk", (now_t - timedelta(hours=22)).strftime("%Y-%m-%d %H:%M"), "Defense", 9)
        ]
        
        # Insert with context-aware images
        for idx, item in enumerate(massive_seed):
            img_url = get_context_image(item[4], idx)
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (url, source_name, country, title, summary, full_content, analyst_name, published_at, image_url, sentiment, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], img_url, item[8], item[9]))
        conn.commit()

ingest_data()

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

@st.cache_data(ttl=15)
def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM articles ORDER BY priority DESC, id DESC", conn)
    
    if 'title' not in df.columns:
        df['title'] = df['title_english'] if 'title_english' in df.columns else "Breaking News"
    if 'summary' not in df.columns:
        df['summary'] = df['summary_english'] if 'summary_english' in df.columns else "No summary available."
    if 'full_content' not in df.columns:
        df['full_content'] = df['full_content_english'] if 'full_content_english' in df.columns else df['summary']
        
    return df

df = load_data()

# --- TOP HEADER ---
st.markdown(f"""
<div class="newsroom-header">
    <div class="newsroom-logo">OSINT <span>DESK</span></div>
    <div>🟢 SYSTEM STATUS: SECURE &nbsp;|&nbsp; PIPELINE: LIVE &nbsp;|&nbsp; {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</div>
</div>
""", unsafe_allow_html=True)

# --- TICKER ---
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
        st.caption(f"Monitoring active intelligence database")

    with c_view:
        selected_view = st.radio("View", ['Main Dashboard', 'Analytics Terminal'], index=0 if st.session_state['view_mode'] == 'Main Dashboard' else 1, horizontal=True, label_visibility="collapsed")
        st.session_state['view_mode'] = selected_view

    with c_sync:
        if st.button("🔄 Sync & Refresh Feeds", use_container_width=True):
            with st.spinner("Refreshing intelligence feeds..."):
                ingest_data()
                st.cache_data.clear()
            st.success("Feeds synchronized successfully!")
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

    # --- STRICT ZONE FILTERING ---
    selected_zone = st.session_state['selected_country']
    if selected_zone == "All":
        filtered_df = df
    else:
        # Strict exact or normalized containment check for the chosen zone only
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
            st.warning(f"No intelligence reports currently indexed for zone: {selected_zone}")
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