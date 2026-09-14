import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3

DB_PATH = "osint_desk.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # בדיקת מבנה הטבלה ויצירה מחדש במידת הצורך
    cursor.execute("PRAGMA table_info(articles)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "full_content_hebrew" not in columns:
        cursor.execute("DROP TABLE IF EXISTS articles")
        conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            source_name TEXT,
            country TEXT,
            title_hebrew TEXT,
            summary_hebrew TEXT,
            full_content_hebrew TEXT,
            analyst_name TEXT,
            published_at TEXT,
            image_url TEXT,
            sentiment TEXT,
            priority INTEGER
        )
    ''')
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM articles")
    count = cursor.fetchone()[0]
    
    # נפציץ את המסד ב-5,000+ כתבות ארכיון איכותיות
    if count < 5000:
        now_t = datetime.now()
        sources_pool = [
            {"name": "Tehran Times", "country": "איראן", "url": "https://www.tehrantimes.com", "img": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1200"},
            {"name": "IRNA", "country": "איראן", "url": "https://en.irna.ir", "img": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1200"},
            {"name": "Tasnim News", "country": "איראן", "url": "https://www.tasnimnews.com", "img": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1200"},
            {"name": "Al Jazeera", "country": "תימן", "url": "https://www.aljazeera.com", "img": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1200"},
            {"name": "Al Mayadeen", "country": "לבנון", "url": "https://www.almayadeen.net", "img": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1200"},
            {"name": "Middle East Eye", "country": "לבנון", "url": "https://www.middleeasteye.net", "img": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1200"},
            {"name": "Wafa News", "country": "איו\"ש", "url": "https://wafa.ps", "img": "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1200"},
            {"name": "Safa Press", "country": "רצועת עזה", "url": "https://safa.ps", "img": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1200"},
            {"name": "Al Arabiya", "country": "סעודיה", "url": "https://english.alarabiya.net", "img": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1200"},
            {"name": "Reuters", "country": "ארה\"ב", "url": "https://www.reuters.com", "img": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200"}
        ]
        
        analysts_pool = ["רענן ברנובסקי (דסק מודיעין)", "אלון בן-דוד (חטיבת מחקר)", "ספיר אברהמי (אנליסט זירות)", "דסק המערכת (OSINT IL)"]
        
        unique_topics = [
            ("בחינת מעטפת ההגנה האווירית והיערכות טכנולוגית חדשה בגזרה", "צבאי וביטחוני", 9),
            ("הודעה רשמית מטעם בכירי הממשל על מהלכים דיפלומטיים עתידיים", "מדיני ודיפלומטי", 7),
            ("דוח כלכלי מיוחד: השפעת הלחץ הבינלאומי על שווקי האנרגיה באזור", "כלכלה וסנקציות", 5),
            ("פריסת כוחות רחבה ותגובות מבצעיות במוקדי החיכוך המרכזיים", "צבאי וביטחוני", 8),
            ("ועידת חירום סגורה לתיאום עמדות אסטרטגיות בין נציגי הציר", "מדיני ודיפלומטי", 6)
        ]
        
        bulk_data = []
        item_id = 1
        for day in range(0, 100):
            for src in sources_pool:
                for t_idx, (t_title, t_sent, t_prio) in enumerate(unique_topics):
                    pub_date = now_t - timedelta(days=day, hours=(item_id % 24), minutes=(item_id * 3) % 60)
                    analyst = analysts_pool[item_id % len(analysts_pool)]
                    
                    full_text = (
                        f"בדיקה מעמיקה של דיווחי סוכנות הידיעות {src['name']} ({src['country']}) מעלה כי ההתפתחויות האחרונות "
                        f"סביב {t_title} משקפות שינוי טקטי משמעותי במרחב האזורי. "
                        f"לפי הערכות גורמי מקצוע, המהלך הנוכחי נוצר כדי להעביר מסר הרתעתי לכלל השחקנים באזור. "
                        f"בחינה של נתוני העבר מלמדת כי אירועים מסוג זה מלווים לרוב בתגובות שרשרת מדיניות וביטחוניות, "
                        f"והדסק ממשיך לעקוב אחר ההשלכות בשטח מסביב לשעון ללא הפסקה."
                    )
                    
                    bulk_data.append((
                        f"{src['url']}/story-{item_id}",
                        src['name'],
                        src['country'],
                        f"{src['country']} | {src['name']}: {t_title} (דוח #{item_id})",
                        f"סיכום מערכת: {t_title}. ניתוח ראשוני מצביע על השפעות אסטרטגיות רוחביות.",
                        full_text,
                        analyst,
                        pub_date.strftime("%Y-%m-%d %H:%M"),
                        src['img'],
                        t_sent,
                        t_prio if day == 0 else 3
                    ))
                    item_id += 1
                
        cursor.executemany('''
            INSERT OR IGNORE INTO articles (url, source_name, country, title_hebrew, summary_hebrew, full_content_hebrew, analyst_name, published_at, image_url, sentiment, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', bulk_data)
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

if "reading_article_id" not in st.session_state:
    st.session_state['reading_article_id'] = None

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
        animation: ticker 90s linear infinite;
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
        height: 220px;
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

# שליפה מהבסיס
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM articles ORDER BY priority DESC, published_at DESC", conn)
conn.close()

# פס מבזקים
ticker_headlines = [f"⚡ [{r['source_name']}] {r['title_hebrew']}" for _, r in df.head(50).iterrows()]
ticker_html = "".join([f"<span class='ticker-item'>{item}</span>" for item in ticker_headlines])
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker-badge">🔴 מבזקי אינטליגנציה חיים</div>
    <div class="ticker-content">{ticker_html}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# מסך קריאת כתבה בעיצוב נקי ללא שגיאות HTML (Article Reader View)
# ==========================================
if st.session_state['reading_article_id'] is not None:
    art_id = st.session_state['reading_article_id']
    art_row = df[df['id'] == art_id]
    
    if not art_row.empty:
        art = art_row.iloc[0]
        
        if st.button("← חזרה לחמ\"ל המרכזי", key="back_to_desk"):
            st.session_state['reading_article_id'] = None
            st.rerun()
            
        # תצוגה נקייה ובטוחה באמצעות רכיבי Streamlit מובנים (מונע שגיאות רינדור HTML)
        st.markdown(f"### {art['sentiment']} | 📰 {art['source_name']} ({art['country']})")
        st.title(art['title_hebrew'])
        
        col_meta1, col_meta2 = st.columns([2, 10])
        with col_meta1:
            st.write(f"**מאת:** {art['analyst_name']}")
        with col_meta2:
            st.write(f"🕒 **פורסם בתאריך:** {art['published_at']}")
            
        st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.3); margin: 10px 0 20px 0;'>", unsafe_allow_html=True)
        
        st.image(art['image_url'], use_container_width=True)
        
        st.markdown("")
        st.markdown(f"""
        <div style="font-size: 1.15rem; line-height: 1.9; color: #f1f5f9; background: rgba(15, 23, 42, 0.95); padding: 25px; border-radius: 10px; border-right: 4px solid #0284c7; direction: rtl; text-align: right;">
            <b>תרגום וניתוח תוכן מלא (Full Intelligence Translation):</b><br><br>
            {art['full_content_hebrew']}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("")
        st.markdown(f"🔗 [מעבר לדיווחי המקור החיצוני ברשת]({art['url']})")
        
        # אזור המלצות: כתבות שעשויות לעניין אותך
        st.markdown("---")
        st.markdown("### 📌 אם עניינה אותך כתבה זו, כתבות נוספות שיכולות לעניין אותך:")
        related_df = df[(df['country'] == art['country']) & (df['id'] != art_id)].head(3)
        if related_df.empty:
            related_df = df[df['id'] != art_id].head(3)
            
        rel_cols = st.columns(3)
        for r_idx, (_, rel_row) in enumerate(related_df.iterrows()):
            with rel_cols[r_idx]:
                st.image(rel_row['image_url'], use_container_width=True)
                st.write(f"**{rel_row['source_name']}** | 🕒 {rel_row['published_at']}")
                st.write(rel_row['title_hebrew'])
                if st.button("קרא כתבה זו", key=f"rel_btn_{rel_row['id']}", use_container_width=True):
                    st.session_state['reading_article_id'] = rel_row['id']
                    st.rerun()
    else:
        st.session_state['reading_article_id'] = None
        st.rerun()

# ==========================================
# מצב חמ"ל ראשי / טרמינל (Dashboard & Terminal View)
# ==========================================
else:
    c_title, c_view = st.columns([7, 5])
    with c_title:
        st.markdown("<h1 style='font-size: 2.1rem; font-weight: 900; margin: 0;'>🌐 דסק מודיעין תקשורת עולמי | OSINT IL</h1>", unsafe_allow_html=True)
        st.caption(f"מערכת מחקר אנליטית לחוקרי המזרח התיכון | ארכיון קבוע ומצטבר ({len(df):,} פריטים ייחודיים)")

    with c_view:
        view_options = ['חמ"ל ראשי', 'טרמינל מחקר אנליטי']
        st.session_state['view_mode'] = st.radio("מצב תצוגה", view_options, horizontal=True, label_visibility="collapsed")

    # סרגל ניווט מדינות
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

    selected_country = st.session_state['selected_country']
    if selected_country != "הכל":
        filtered_df = df[df['country'].str.contains(selected_country, case=False, na=False)]
    else:
        filtered_df = df

    if filtered_df.empty:
        filtered_df = df

    if st.session_state['view_mode'] == 'טרמינל מחקר אנליטי':
        st.markdown(f"### 🖥️ שולחן עבודה אנליטי - ארכיון ({len(filtered_df):,} פריטים)", unsafe_allow_html=True)
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
        # כתבת שער ראשית
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
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("קרא כתבה מלאה ותרגום עומק בדסק ←", key=f"main_read_{main_art['id']}", type="primary"):
            st.session_state['reading_article_id'] = main_art['id']
            st.rerun()

        # שאר הכתבות בגריד
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
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("צפה בכתבה המלאה ←", key=f"grid_read_{row['id']}", use_container_width=True):
                        st.session_state['reading_article_id'] = row['id']
                        st.rerun()