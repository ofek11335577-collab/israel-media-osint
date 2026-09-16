import html
import textwrap
from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from database import init_db, get_db_connection
from ingestion.fetcher import fetch_live_web_articles
from services.translator import (
    ensure_hebrew_card_translations,
    ensure_hebrew_full_translation,
)


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="OSINT Global Desk",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()


# =========================================================
# SESSION
# =========================================================

if "language" not in st.session_state:
    st.session_state.language = "en"
if "selected_country" not in st.session_state:
    st.session_state.selected_country = "All"
if "reading_article_id" not in st.session_state:
    st.session_state.reading_article_id = None
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "dashboard"

LANG = st.session_state.language
IS_HE = LANG == "he"


# =========================================================
# UI COPY
# =========================================================

UI = {
    "en": {
        "desk_title": "Global Intelligence Desk",
        "desk_subtitle": "Real-time monitoring of strategic reporting across Israel, the Middle East and the world",
        "live": "LIVE INTEL",
        "dashboard": "Main Dashboard",
        "analytics": "Analytics Terminal",
        "sync": "Sync & Enrich Feeds",
        "syncing": "Synchronizing intelligence feeds...",
        "sync_done": "new reports added",
        "sync_failed": "Feed synchronization failed.",
        "search": "Search reports...",
        "search_hint": "Search missiles, protests, sanctions, nuclear, government, economy...",
        "all_topics": "All Topics",
        "latest_report": "LATEST INTELLIGENCE REPORT",
        "latest_reports": "Latest Intelligence Reports",
        "read": "Read Report",
        "source": "Open Original Source",
        "back": "Back to Newsroom",
        "no_reports": "No reports match the current filters.",
        "reports": "Reports",
        "sources": "Active Sources",
        "latest": "Latest Update",
        "archive": "Intelligence Archive",
        "published": "Published",
        "zone": "Zone",
        "topic": "Topic",
        "framing": "Israel Framing",
        "title": "Title",
        "url": "URL",
        "minutes_ago": "min ago",
        "hours_ago": "h ago",
        "days_ago": "d ago",
    },
    "he": {
        "desk_title": "דסק מודיעין תקשורת עולמי",
        "desk_subtitle": "ניטור בזמן אמת של דיווחים אסטרטגיים מישראל, המזרח התיכון והעולם",
        "live": "מבזקי מודיעין",
        "dashboard": "דסק ראשי",
        "analytics": "מסוף אנליטי",
        "sync": "סנכרון והעשרת מקורות",
        "syncing": "מסנכרן ומעדכן מקורות...",
        "sync_done": "דיווחים חדשים נוספו",
        "sync_failed": "סנכרון המקורות נכשל.",
        "search": "חיפוש בדיווחים...",
        "search_hint": "חפש טילים, מחאות, סנקציות, גרעין, ממשלה, כלכלה...",
        "all_topics": "כל הנושאים",
        "latest_report": "הדיווח המודיעיני האחרון",
        "latest_reports": "דיווחים אחרונים",
        "read": "קריאת הדיווח",
        "source": "פתיחת המקור",
        "back": "חזרה לדסק",
        "no_reports": "לא נמצאו דיווחים התואמים למסננים.",
        "reports": "דיווחים",
        "sources": "מקורות פעילים",
        "latest": "עדכון אחרון",
        "archive": "ארכיון מודיעיני",
        "published": "פורסם",
        "zone": "זירה",
        "topic": "נושא",
        "framing": "מסגור כלפי ישראל",
        "title": "כותרת",
        "url": "קישור",
        "minutes_ago": "דק׳",
        "hours_ago": "שע׳",
        "days_ago": "ימים",
    },
}[LANG]

TOPIC_TRANSLATIONS = {
    "Security / Military": "ביטחון / צבא",
    "Politics / Regime": "פוליטיקה / שלטון",
    "Strategic Economy": "כלכלה אסטרטגית",
    "Internal Stability": "יציבות פנימית",
    "Nuclear / Cyber / Technology": "גרעין / סייבר / טכנולוגיה",
    "Diplomacy": "דיפלומטיה",
    "Humanitarian": "הומניטרי",
    "General": "כללי",
}

COUNTRY_TRANSLATIONS = {
    "All": "כל הדיווחים",
    "Israel": "ישראל",
    "Iran": "איראן",
    "Lebanon": "לבנון",
    "Gaza & WB": "עזה והגדה",
    "Syria": "סוריה",
    "Iraq": "עיראק",
    "Saudi Arabia": "ערב הסעודית",
    "UAE": "איחוד האמירויות",
    "Yemen": "תימן",
    "US & Global": "ארה״ב ועולם",
}

COUNTRY_FLAGS = {
    "All": "🌐",
    "Israel": "🇮🇱",
    "Iran": "🇮🇷",
    "Lebanon": "🇱🇧",
    "Gaza & WB": "🇵🇸",
    "Syria": "🇸🇾",
    "Iraq": "🇮🇶",
    "Saudi Arabia": "🇸🇦",
    "UAE": "🇦🇪",
    "Yemen": "🇾🇪",
    "US & Global": "🇺🇸",
}

NAV_COUNTRIES = list(COUNTRY_FLAGS.keys())


# =========================================================
# HELPERS
# =========================================================

def render_html(content):
    cleaned = textwrap.dedent(content).strip()
    cleaned = " ".join(line.strip() for line in cleaned.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def safe(value):
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def translated_topic(topic):
    topic = topic or "General"
    if IS_HE:
        return TOPIC_TRANSLATIONS.get(topic, topic)
    return topic


def translated_country(country):
    country = country or "US & Global"
    if IS_HE:
        return COUNTRY_TRANSLATIONS.get(country, country)
    return country


def article_title(row):
    if IS_HE and row.get("title_he"):
        return row.get("title_he")
    return row.get("title") or ""


def article_summary(row):
    if IS_HE and row.get("summary_he"):
        return row.get("summary_he")
    return row.get("summary") or ""


def article_full_content(row):
    if IS_HE and row.get("full_content_he"):
        return row.get("full_content_he")
    return row.get("full_content") or row.get("summary") or ""


def image_html(image_url, height="235px"):
    image_url = (str(image_url).strip() if image_url else "")
    if not image_url:
        return ""
    return (
        f'<div class="article-image-wrap" style="height:{height};">'
        f'<img src="{safe(image_url)}" class="article-image" '
        f'onerror="this.parentElement.style.display=\'none\';">'
        f'</div>'
    )


def framing_badge(value):
    value = (value or "not_mentioned").strip().lower()

    if value in {"critical", "hostile"}:
        label = "מסגור ביקורתי כלפי ישראל" if IS_HE else "Israel Framing: Critical"
        css = "tag-framing-critical"
    elif value in {"supportive", "positive"}:
        label = "מסגור תומך כלפי ישראל" if IS_HE else "Israel Framing: Supportive"
        css = "tag-framing-supportive"
    elif value == "neutral":
        label = "מסגור ניטרלי כלפי ישראל" if IS_HE else "Israel Framing: Neutral"
        css = "tag-framing-neutral"
    else:
        label = "ישראל לא מוזכרת" if IS_HE else "Israel: Not Mentioned"
        css = "tag-framing-neutral"

    return f'<span class="tag {css}">{label}</span>'


def freshness(dt_value):
    if pd.isna(dt_value):
        return ""
    try:
        if hasattr(dt_value, "to_pydatetime"):
            dt_value = dt_value.to_pydatetime()
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt_value.astimezone(timezone.utc)
        minutes = max(0, int(delta.total_seconds() // 60))
        if minutes < 60:
            return f"{minutes} {UI['minutes_ago']}" if IS_HE else f"{minutes} {UI['minutes_ago']}"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} {UI['hours_ago']}"
        days = hours // 24
        return f"{days} {UI['days_ago']}"
    except Exception:
        return ""


def format_date(dt_value):
    if pd.isna(dt_value):
        return ""
    try:
        if hasattr(dt_value, "to_pydatetime"):
            dt_value = dt_value.to_pydatetime()
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        dt_value = dt_value.astimezone(timezone.utc)
        if IS_HE:
            return dt_value.strftime("%d.%m.%Y %H:%M UTC")
        return dt_value.strftime("%b %d, %Y · %H:%M UTC")
    except Exception:
        return str(dt_value)


# =========================================================
# FETCH STATE
# =========================================================

def should_fetch():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_state WHERE key = 'last_rss_fetch'")
    row = cursor.fetchone()
    if row is None:
        return True
    try:
        last_fetch = datetime.fromisoformat(row["value"])
        if last_fetch.tzinfo is None:
            last_fetch = last_fetch.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_fetch >= timedelta(minutes=5)
    except Exception:
        return True


def mark_fetch_complete():
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    cursor.execute(
        """
        INSERT INTO system_state(key, value)
        VALUES('last_rss_fetch', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (now,),
    )
    conn.commit()


# Refresh the page every five minutes while it is open.
st_autorefresh(interval=5 * 60 * 1000, key="rss_auto_refresh")

# Fast RSS-only automatic update. Heavy page/image enrichment is manual so it
# cannot block normal startup for minutes.
if should_fetch():
    try:
        fetch_live_web_articles(enrich=False)
        mark_fetch_complete()
        st.cache_data.clear()
    except Exception as exc:
        print(f"Automatic RSS sync failed: {exc}")


# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=30)
def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM articles
        ORDER BY published_at DESC, id DESC
        """,
        conn,
    )

    if df.empty:
        return df

    # Graceful fallback for legacy rows while the migration fills new columns.
    if "topic" not in df.columns:
        df["topic"] = df.get("sentiment", "General")
    else:
        df["topic"] = df["topic"].fillna(df.get("sentiment"))

    if "israel_framing" not in df.columns:
        df["israel_framing"] = df.get("analyst_name", "not_mentioned")
    else:
        df["israel_framing"] = df["israel_framing"].fillna(df.get("analyst_name"))

    df["_published_dt"] = pd.to_datetime(
        df["published_at"],
        errors="coerce",
        utc=True,
    )

    df = df.sort_values(
        by=["_published_dt", "id"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    return df


df = load_data()


# =========================================================
# CSS
# =========================================================

page_direction = "rtl" if IS_HE else "ltr"
text_align = "right" if IS_HE else "left"

render_html(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&family=Heebo:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: {'Heebo' if IS_HE else 'Inter'}, sans-serif !important;
    background: #07090e;
    color: #f1f5f9;
}}

.stApp {{ direction: {page_direction}; }}
header[data-testid="stHeader"] {{ display:none !important; }}
.block-container {{ padding-top: 1.1rem !important; max-width: 1680px; }}

.newsroom-header {{
    background: linear-gradient(100deg,#0f172a,#182338);
    border: 1px solid rgba(56,189,248,.18);
    border-bottom: 2px solid #0284c7;
    padding: 13px 20px;
    border-radius: 10px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:12px;
    color:#94a3b8;
    direction:ltr;
}}
.newsroom-logo {{ font:800 1.35rem 'JetBrains Mono',monospace; color:#fff; }}
.newsroom-logo span {{ color:#38bdf8; }}
.system-line {{ font-size:.8rem; }}

.ticker-wrap {{
    width:100%; height:40px; background:#111827;
    border:1px solid rgba(239,68,68,.45); border-radius:8px;
    overflow:hidden; display:flex; align-items:center; margin-bottom:16px;
    direction:ltr;
}}
.ticker-badge {{
    background:linear-gradient(90deg,#dc2626,#ef4444); color:#fff;
    font-weight:800; font-size:.74rem; padding:0 16px; height:100%;
    display:flex; align-items:center; flex-shrink:0; z-index:2;
}}
.ticker-track {{ overflow:hidden; flex:1; }}
.ticker-content {{
    display:inline-flex; min-width:max-content; white-space:nowrap;
    animation:ticker 75s linear infinite; color:#f8fafc; font-size:.82rem;
}}
.ticker-item {{ margin:0 34px; display:inline-flex; align-items:center; gap:7px; }}
.ticker-source {{ color:#7dd3fc; font-weight:700; }}
@keyframes ticker {{ from {{ transform:translateX(35%); }} to {{ transform:translateX(-100%); }} }}

.hero-heading {{
    padding:28px 2px 18px; text-align:{text_align};
}}
.hero-heading h1 {{ margin:0; color:#fff; font-size:2.35rem; font-weight:800; }}
.hero-heading p {{ margin:8px 0 0; color:#94a3b8; font-size:1rem; }}

.metric-card {{
    background:#101827; border:1px solid rgba(56,189,248,.13);
    border-radius:10px; padding:12px 15px; margin-bottom:10px;
}}
.metric-label {{ color:#64748b; font-size:.72rem; font-weight:700; text-transform:uppercase; }}
.metric-value {{ color:#f8fafc; font-size:1.05rem; font-weight:800; margin-top:2px; }}

.card {{
    background:#111827; border:1px solid rgba(56,189,248,.16);
    border-radius:12px; padding:18px; margin-bottom:14px;
    display:flex; flex-direction:column; overflow:hidden;
}}
.lead-card {{ border-color:rgba(239,68,68,.35); padding:20px; }}
.article-image-wrap {{ width:100%; overflow:hidden; border-radius:9px; margin-bottom:15px; background:#0b1220; }}
.article-image {{ width:100%!important; height:100%!important; display:block!important; object-fit:cover!important; object-position:center!important; }}

.tag {{
    display:inline-block; padding:4px 9px; border-radius:5px;
    font-size:.71rem; font-weight:750; margin:0 5px 5px 0;
}}
.tag-source {{ background:#1f2937; color:#60a5fa; }}
.tag-time {{ background:#374151; color:#cbd5e1; }}
.tag-topic {{ background:#0284c7; color:#fff; }}
.tag-breaking {{ background:#dc2626; color:#fff; }}
.tag-framing-critical {{ background:#dc2626; color:#fff; border:1px solid #ef4444; }}
.tag-framing-supportive {{ background:#0284c7; color:#fff; border:1px solid #38bdf8; }}
.tag-framing-neutral {{ background:#4b5563; color:#fff; border:1px solid #6b7280; }}

.article-title {{ font-weight:800; font-size:1.08rem; line-height:1.45; color:#fff; margin:8px 0; text-align:{text_align}; }}
.article-summary {{ color:#94a3b8; font-size:.91rem; line-height:1.62; text-align:{text_align}; }}
.lead-title {{ font-weight:850; font-size:2rem; line-height:1.25; color:#fff; margin:13px 0 9px; text-align:{text_align}; }}
.lead-summary {{ color:#a8b5c9; font-size:1.02rem; line-height:1.7; text-align:{text_align}; }}

div.stButton > button {{
    background:#1f2937!important; color:#f8fafc!important;
    border:1px solid rgba(56,189,248,.25)!important; border-radius:7px!important;
    font-weight:650!important;
}}
div.stButton > button[kind="primary"] {{ background:#0284c7!important; border-color:#38bdf8!important; color:#fff!important; }}
[data-testid="stLinkButton"] a {{ border-radius:7px!important; }}
</style>
""")


# =========================================================
# TOP HEADER + LANGUAGE
# =========================================================

header_left, header_lang = st.columns([9, 1.6])

with header_left:
    current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    render_html(f"""
    <div class="newsroom-header">
        <div class="newsroom-logo">OSINT <span>DESK</span></div>
        <div class="system-line">🟢 SYSTEM ONLINE &nbsp;|&nbsp; LIVE RSS &nbsp;|&nbsp; {current_utc}</div>
    </div>
    """)

with header_lang:
    if IS_HE:
        if st.button("🇺🇸 English", use_container_width=True, key="lang_en"):
            st.session_state.language = "en"
            st.rerun()
    else:
        if st.button("🇮🇱 עברית", use_container_width=True, key="lang_he"):
            st.session_state.language = "he"
            st.rerun()


# =========================================================
# TICKER - ALWAYS THE NEWEST ARTICLES
# =========================================================

if not df.empty:
    ticker_df = df.head(14)

    # In Hebrew mode, ensure the visible ticker/cards are translated once and cached.
    if IS_HE:
        ticker_ids = ticker_df["id"].tolist()
        missing = ticker_df[
            ticker_df["title_he"].fillna("").eq("")
            | ticker_df["summary_he"].fillna("").eq("")
        ]
        if not missing.empty:
            with st.spinner("מתרגם את הדיווחים האחרונים..."):
                ensure_hebrew_card_translations(ticker_ids[:14])
            st.cache_data.clear()
            df = load_data()
            ticker_df = df.head(14)

    ticker_items = []
    for _, row in ticker_df.iterrows():
        rowd = row.to_dict()
        ticker_items.append(
            f'<span class="ticker-item">⚡ '
            f'<span class="ticker-source">[{safe(rowd.get("source_name"))}]</span> '
            f'{safe(article_title(rowd))}</span>'
        )

    render_html(f"""
    <div class="ticker-wrap">
        <div class="ticker-badge">{UI['live']}</div>
        <div class="ticker-track"><div class="ticker-content">{''.join(ticker_items)}</div></div>
    </div>
    """)


# =========================================================
# ARTICLE READER
# =========================================================

if st.session_state.reading_article_id is not None:
    article_id = int(st.session_state.reading_article_id)

    if IS_HE:
        with st.spinner("מתרגם את הדיווח..."):
            ensure_hebrew_full_translation(article_id)
        st.cache_data.clear()
        df = load_data()

    article_df = df[df["id"] == article_id]
    if article_df.empty:
        st.session_state.reading_article_id = None
        st.rerun()

    row = article_df.iloc[0].to_dict()

    b1, b2 = st.columns(2)
    with b1:
        if st.button(f"← {UI['back']}", use_container_width=True):
            st.session_state.reading_article_id = None
            st.rerun()
    with b2:
        st.link_button(
            f"🔗 {UI['source']} ↗",
            row["url"],
            use_container_width=True,
        )

    tags = (
        f'<span class="tag tag-source">📰 {safe(row.get("source_name"))}</span>'
        f'<span class="tag tag-topic">{safe(translated_topic(row.get("topic")))}</span>'
        f'{framing_badge(row.get("israel_framing"))}'
        f'<span class="tag tag-source">{safe(translated_country(row.get("country")))}</span>'
        f'<span class="tag tag-time">🕒 {safe(format_date(row.get("_published_dt")))}</span>'
    )
    render_html(f'<div style="margin:12px 0 8px;">{tags}</div>')

    st.title(article_title(row))

    img = image_html(row.get("image_url"), "470px")
    if img:
        render_html(img)

    render_html(f"""
    <div style="font-size:1.08rem;line-height:1.85;color:#e2e8f0;background:#111827;
                padding:28px;border-radius:11px;border:1px solid rgba(56,189,248,.2);
                border-{'right' if IS_HE else 'left'}:4px solid #0284c7;white-space:pre-line;text-align:{text_align};">
        {safe(article_full_content(row))}
    </div>
    """)

    evidence = (row.get("framing_evidence") or "").strip()
    if evidence and row.get("israel_framing") not in {None, "", "not_mentioned"}:
        with st.expander("Framing signals" if not IS_HE else "סימני מסגור שזוהו"):
            st.write(evidence)

    st.stop()


# =========================================================
# CONTROLS
# =========================================================

control_search, control_topic, control_view, control_sync = st.columns([5, 2.5, 2.3, 2.4])

with control_search:
    search_query = st.text_input(
        UI["search"],
        placeholder=UI["search_hint"],
        label_visibility="collapsed",
    )

available_topics = ["All"] + sorted(
    {str(x) for x in df.get("topic", pd.Series(dtype=str)).dropna().tolist() if str(x).strip()}
)

def topic_label(topic):
    if topic == "All":
        return UI["all_topics"]
    return translated_topic(topic)

with control_topic:
    selected_topic = st.selectbox(
        UI["topic"],
        available_topics,
        format_func=topic_label,
        label_visibility="collapsed",
    )

with control_view:
    view_labels = [UI["dashboard"], UI["analytics"]]
    view_choice = st.selectbox(
        "View",
        view_labels,
        index=0 if st.session_state.view_mode == "dashboard" else 1,
        label_visibility="collapsed",
    )
    st.session_state.view_mode = "dashboard" if view_choice == UI["dashboard"] else "analytics"

with control_sync:
    if st.button(f"🔄 {UI['sync']}", use_container_width=True, type="primary"):
        with st.spinner(UI["syncing"]):
            try:
                added = fetch_live_web_articles(enrich=True)
                mark_fetch_complete()
                st.cache_data.clear()
                st.success(f"{added} {UI['sync_done']}")
            except Exception as exc:
                st.error(UI["sync_failed"])
                print(f"Manual sync failed: {exc}")
        st.rerun()


# =========================================================
# TITLE + METRICS
# =========================================================

render_html(f"""
<div class="hero-heading">
    <h1>🌐 {UI['desk_title']}</h1>
    <p>{UI['desk_subtitle']} · 24/7</p>
</div>
""")

metric_cols = st.columns(3)
active_sources = int(df["source_name"].nunique()) if not df.empty else 0
latest_dt = df.iloc[0]["_published_dt"] if not df.empty else pd.NaT
metric_values = [
    (UI["reports"], f"{len(df):,}"),
    (UI["sources"], str(active_sources)),
    (UI["latest"], freshness(latest_dt) or "—"),
]
for col, (label, value) in zip(metric_cols, metric_values):
    with col:
        render_html(
            f'<div class="metric-card"><div class="metric-label">{safe(label)}</div>'
            f'<div class="metric-value">{safe(value)}</div></div>'
        )


# =========================================================
# ZONE NAVIGATION - TWO ROWS TO STAY READABLE
# =========================================================

for start in range(0, len(NAV_COUNTRIES), 6):
    chunk = NAV_COUNTRIES[start:start + 6]
    cols = st.columns(len(chunk))
    for col, country in zip(cols, chunk):
        with col:
            label = COUNTRY_TRANSLATIONS.get(country, country) if IS_HE else country
            button_label = f"{COUNTRY_FLAGS[country]}  {label}"
            if st.button(
                button_label,
                key=f"zone_{country}",
                type="primary" if st.session_state.selected_country == country else "secondary",
                use_container_width=True,
            ):
                st.session_state.selected_country = country
                st.rerun()

st.markdown("---")


# =========================================================
# FILTER + SORT: NEWEST FIRST
# =========================================================

filtered = df.copy()
selected_country = st.session_state.selected_country

if selected_country != "All":
    filtered = filtered[
        filtered["country"].fillna("").str.casefold()
        == selected_country.casefold()
    ]

if selected_topic != "All":
    filtered = filtered[
        filtered["topic"].fillna("").str.casefold()
        == selected_topic.casefold()
    ]

if search_query.strip():
    q = search_query.strip()
    mask = (
        filtered["title"].fillna("").str.contains(q, case=False, regex=False)
        | filtered["summary"].fillna("").str.contains(q, case=False, regex=False)
        | filtered["source_name"].fillna("").str.contains(q, case=False, regex=False)
        | filtered["title_he"].fillna("").str.contains(q, case=False, regex=False)
        | filtered["summary_he"].fillna("").str.contains(q, case=False, regex=False)
    )
    filtered = filtered[mask]

filtered = filtered.sort_values(
    by=["_published_dt", "id"],
    ascending=[False, False],
    na_position="last",
).reset_index(drop=True)

# Translate only what the Hebrew user can actually see now. This keeps the
# English default fast and caches the Hebrew result for future visits.
if IS_HE and not filtered.empty:
    visible_ids = filtered.head(22)["id"].tolist()
    visible = filtered.head(22)
    missing = visible[
        visible["title_he"].fillna("").eq("")
        | visible["summary_he"].fillna("").eq("")
    ]
    if not missing.empty:
        with st.spinner("מתרגם את הדיווחים המוצגים..."):
            ensure_hebrew_card_translations(visible_ids)
        st.cache_data.clear()
        df = load_data()
        # Repeat the same filter after cache refresh.
        filtered = df.copy()
        if selected_country != "All":
            filtered = filtered[
                filtered["country"].fillna("").str.casefold()
                == selected_country.casefold()
            ]
        if selected_topic != "All":
            filtered = filtered[
                filtered["topic"].fillna("").str.casefold()
                == selected_topic.casefold()
            ]
        if search_query.strip():
            q = search_query.strip()
            mask = (
                filtered["title"].fillna("").str.contains(q, case=False, regex=False)
                | filtered["summary"].fillna("").str.contains(q, case=False, regex=False)
                | filtered["source_name"].fillna("").str.contains(q, case=False, regex=False)
                | filtered["title_he"].fillna("").str.contains(q, case=False, regex=False)
                | filtered["summary_he"].fillna("").str.contains(q, case=False, regex=False)
            )
            filtered = filtered[mask]
        filtered = filtered.sort_values(
            by=["_published_dt", "id"],
            ascending=[False, False],
            na_position="last",
        ).reset_index(drop=True)


# =========================================================
# ANALYTICS
# =========================================================

if st.session_state.view_mode == "analytics":
    st.markdown(f"### 🖥️ {UI['archive']} ({len(filtered):,})")

    if filtered.empty:
        st.info(UI["no_reports"])
    else:
        table = pd.DataFrame({
            UI["published"]: [format_date(x) for x in filtered["_published_dt"]],
            UI["zone"]: [translated_country(x) for x in filtered["country"]],
            "Source": filtered["source_name"],
            UI["topic"]: [translated_topic(x) for x in filtered["topic"]],
            UI["framing"]: filtered["israel_framing"].replace({
                "critical": "Critical" if not IS_HE else "ביקורתי",
                "supportive": "Supportive" if not IS_HE else "תומך",
                "neutral": "Neutral" if not IS_HE else "ניטרלי",
                "not_mentioned": "Not Mentioned" if not IS_HE else "לא מוזכרת",
            }),
            UI["title"]: [article_title(row.to_dict()) for _, row in filtered.iterrows()],
            UI["url"]: filtered["url"],
        })
        st.dataframe(table, use_container_width=True, height=620, hide_index=True)
    st.stop()


# =========================================================
# DASHBOARD
# =========================================================

if filtered.empty:
    st.info(UI["no_reports"])
    st.stop()

lead = filtered.iloc[0].to_dict()
lead_image = image_html(lead.get("image_url"), "420px")
lead_fresh = freshness(lead.get("_published_dt"))

render_html(f"""
<div class="card lead-card">
    {lead_image}
    <div>
        <span class="tag tag-breaking">{safe(UI['latest_report'])}</span>
        <span class="tag tag-topic">{safe(translated_topic(lead.get('topic')))}</span>
        {framing_badge(lead.get('israel_framing'))}
        <span class="tag tag-source">📰 {safe(lead.get('source_name'))}</span>
        <span class="tag tag-time">🕒 {safe(lead_fresh or format_date(lead.get('_published_dt')))}</span>
    </div>
    <div class="lead-title">{safe(article_title(lead))}</div>
    <div class="lead-summary">{safe(article_summary(lead))}</div>
</div>
""")

lead_btn1, lead_btn2 = st.columns(2)
with lead_btn1:
    if st.button(f"📖 {UI['read']} ←", key=f"lead_read_{lead['id']}", type="primary", use_container_width=True):
        st.session_state.reading_article_id = int(lead["id"])
        st.rerun()
with lead_btn2:
    st.link_button(f"🔗 {UI['source']} ↗", lead["url"], use_container_width=True)

remaining = filtered.iloc[1:]
if not remaining.empty:
    st.markdown(f"### ⚡ {UI['latest_reports']} ({len(filtered):,})")
    columns = st.columns(3)

    for idx, (_, series) in enumerate(remaining.head(30).iterrows()):
        row = series.to_dict()
        with columns[idx % 3]:
            img = image_html(row.get("image_url"), "235px")
            fresh = freshness(row.get("_published_dt"))

            render_html(f"""
            <div class="card">
                {img}
                <div>
                    <span class="tag tag-source">{safe(row.get('source_name'))}</span>
                    <span class="tag tag-topic">{safe(translated_topic(row.get('topic')))}</span>
                    {framing_badge(row.get('israel_framing'))}
                    <span class="tag tag-time">🕒 {safe(fresh or format_date(row.get('_published_dt')))}</span>
                </div>
                <div class="article-title">{safe(article_title(row))}</div>
                <div class="article-summary">{safe(article_summary(row))}</div>
            </div>
            """)

            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    f"{UI['read']} ←",
                    key=f"read_{row['id']}",
                    use_container_width=True,
                ):
                    st.session_state.reading_article_id = int(row["id"])
                    st.rerun()
            with c2:
                st.link_button(
                    f"{UI['source']} ↗",
                    row["url"],
                    use_container_width=True,
                )
