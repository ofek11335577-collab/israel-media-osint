# app.py

import html
import textwrap
from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from database import init_db, get_db_connection
from ingestion.fetcher import fetch_live_web_articles


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="OSINT Global Desk",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# HELPERS
# =========================================================

def render_html(content):
    cleaned = textwrap.dedent(content).strip()

    cleaned = " ".join(
        line.strip()
        for line in cleaned.splitlines()
        if line.strip()
    )

    st.markdown(
        cleaned,
        unsafe_allow_html=True,
    )


def safe(value):
    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )


def image_html(image_url, height="230px"):
    if image_url is None:
        return ""

    image_url = str(image_url).strip()

    if not image_url:
        return ""

    safe_url = safe(image_url)

    return (
        f'<div class="article-image-wrap" '
        f'style="height:{height};">'
        f'<img '
        f'src="{safe_url}" '
        f'class="article-image" '
        f'onerror="this.parentElement.style.display=\'none\';"'
        f'>'
        f'</div>'
    )


def israel_tone_html(value):
    """
    Israel framing badge.

    hostile  -> red
    positive -> blue
    neutral  -> gray
    empty    -> gray "Israel: Not Mentioned"
    """

    if value is None:
        value = ""

    value = str(value).strip().lower()

    if value == "hostile":
        return (
            '<span class="tag tag-israel-hostile">'
            'Israel Tone: Hostile'
            '</span>'
        )

    if value == "positive":
        return (
            '<span class="tag tag-israel-positive">'
            'Israel Tone: Positive'
            '</span>'
        )

    if value == "neutral":
        return (
            '<span class="tag tag-israel-neutral">'
            'Israel Tone: Neutral'
            '</span>'
        )

    return (
        '<span class="tag tag-israel-neutral">'
        'Israel: Not Mentioned'
        '</span>'
    )


# =========================================================
# DATABASE
# =========================================================

init_db()


# =========================================================
# FETCH TIMER
# =========================================================

def should_fetch():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT value
        FROM system_state
        WHERE key = 'last_rss_fetch'
    """)

    row = cursor.fetchone()

    if row is None:
        return True

    try:
        last_fetch = datetime.fromisoformat(
            row["value"]
        )

        if last_fetch.tzinfo is None:
            last_fetch = last_fetch.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(timezone.utc)

        return (
            now - last_fetch
            >= timedelta(minutes=5)
        )

    except Exception:
        return True


def mark_fetch_complete():
    conn = get_db_connection()
    cursor = conn.cursor()

    now = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )

    cursor.execute("""
        INSERT INTO system_state (key, value)
        VALUES ('last_rss_fetch', ?)

        ON CONFLICT(key)
        DO UPDATE SET
            value = excluded.value
    """, (now,))

    conn.commit()


# =========================================================
# AUTO REFRESH
# =========================================================

st_autorefresh(
    interval=5 * 60 * 1000,
    key="rss_auto_refresh",
)


# =========================================================
# AUTOMATIC RSS SYNC
# =========================================================

if should_fetch():
    try:
        new_count = fetch_live_web_articles()

        mark_fetch_complete()

        st.cache_data.clear()

        print(
            f"Automatic RSS sync complete: "
            f"{new_count} new reports."
        )

    except Exception as error:
        print(
            f"Automatic RSS sync failed: "
            f"{error}"
        )


# =========================================================
# SESSION STATE
# =========================================================

if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "Main Dashboard"

if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = "All"

if "reading_article_id" not in st.session_state:
    st.session_state["reading_article_id"] = None


# =========================================================
# CSS
# =========================================================

render_html("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html,
body,
[class*="css"],
.stApp {
    font-family: 'Inter', sans-serif !important;
    background-color: #07090e;
    color: #f1f5f9;
}

header[data-testid="stHeader"] {
    display: none !important;
}


/* =========================
   HEADER
========================= */

.newsroom-header {
    background: linear-gradient(
        90deg,
        #0f172a,
        #1e293b
    );

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

.newsroom-logo span {
    color: #38bdf8;
}


/* =========================
   TICKER
========================= */

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
    color: white;

    font-weight: 700;
    font-size: 0.78rem;

    padding: 0 16px;
    height: 100%;

    display: flex;
    align-items: center;

    flex-shrink: 0;
}

.ticker-content {
    display: flex;
    white-space: nowrap;

    animation: ticker 70s linear infinite;

    color: #f1f5f9;
    font-size: 0.85rem;
}

.ticker-item {
    margin-left: 50px;

    display: inline-flex;
    align-items: center;
}

@keyframes ticker {
    from {
        transform: translateX(0);
    }

    to {
        transform: translateX(100%);
    }
}


/* =========================
   CARDS
========================= */

.card {
    background: #111827;

    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 10px;

    padding: 18px;
    margin-bottom: 18px;

    display: flex;
    flex-direction: column;
}


/* =========================
   IMAGES
========================= */

.article-image-wrap {
    width: 100%;
    overflow: hidden;

    border-radius: 8px;
    margin-bottom: 16px;

    background: #0f172a;
}

.article-image {
    width: 100% !important;
    height: 100% !important;

    display: block !important;

    object-fit: cover !important;
    object-position: center center !important;

    max-width: none !important;
}


/* =========================
   TAGS
========================= */

.tag {
    display: inline-block;

    padding: 4px 9px;
    border-radius: 5px;

    font-size: 0.72rem;
    font-weight: 700;

    margin-right: 6px;
    margin-bottom: 5px;
}

.tag-source {
    background: #1f2937;
    color: #60a5fa;
}

.tag-time {
    background: #374151;
    color: #cbd5e1;
}

.tag-topic {
    background: #0284c7;
    color: #ffffff;
}

.tag-breaking {
    background: #dc2626;
    color: #ffffff;
}


/* =========================
   ISRAEL TONE
========================= */

.tag-israel-hostile {
    background: #dc2626;
    color: #ffffff;

    border: 1px solid #ef4444;
}

.tag-israel-positive {
    background: #0284c7;
    color: #ffffff;

    border: 1px solid #38bdf8;
}

.tag-israel-neutral {
    background: #4b5563;
    color: #ffffff;

    border: 1px solid #6b7280;
}


/* =========================
   BUTTONS
========================= */

div.stButton > button {
    background-color: #1f2937 !important;
    color: #f8fafc !important;

    border:
        1px solid
        rgba(56,189,248,0.25)
        !important;

    border-radius: 6px !important;

    font-weight: 600 !important;
}

div.stButton > button[kind="primary"] {
    background-color: #0284c7 !important;
    border-color: #38bdf8 !important;
    color: white !important;
}

</style>
""")


# =========================================================
# DATA
# =========================================================

@st.cache_data(ttl=30)
def load_data():
    conn = get_db_connection()

    return pd.read_sql_query(
        """
        SELECT *
        FROM articles
        ORDER BY
            priority DESC,
            published_at DESC,
            id DESC
        """,
        conn,
    )


df = load_data()


# =========================================================
# HEADER
# =========================================================

current_utc = (
    datetime.now(timezone.utc)
    .strftime("%Y-%m-%d %H:%M UTC")
)


render_html(f"""
<div class="newsroom-header">

    <div class="newsroom-logo">
        OSINT <span>DESK</span>
    </div>

    <div>
        🟢 SYSTEM STATUS: ONLINE
        &nbsp;|&nbsp;
        PIPELINE: LIVE RSS
        &nbsp;|&nbsp;
        {current_utc}
    </div>

</div>
""")


# =========================================================
# TICKER
# =========================================================

if not df.empty:

    ticker_items = []

    for _, row in df.head(30).iterrows():

        ticker_items.append(
            f"<span class='ticker-item'>"
            f"⚡ [{safe(row['source_name'])}] "
            f"{safe(row['title'])}"
            f"</span>"
        )


    render_html(f"""
    <div class="ticker-wrap">

        <div class="ticker-badge">
            LIVE INTEL
        </div>

        <div class="ticker-content">
            {''.join(ticker_items)}
        </div>

    </div>
    """)


# =========================================================
# ARTICLE READER
# =========================================================

if st.session_state["reading_article_id"] is not None:

    article_id = st.session_state["reading_article_id"]

    article_df = df[
        df["id"] == article_id
    ]

    if article_df.empty:

        st.session_state[
            "reading_article_id"
        ] = None

        st.rerun()


    article = article_df.iloc[0]


    back_col, source_col = st.columns(2)


    with back_col:

        if st.button(
            "← Back to Newsroom",
            use_container_width=True,
        ):

            st.session_state[
                "reading_article_id"
            ] = None

            st.rerun()


    with source_col:

        st.link_button(
            "🔗 Open Original Source ↗",
            article["url"],
            use_container_width=True,
        )


    article_israel_tone = israel_tone_html(
        article["analyst_name"]
    )


    render_html(f"""
    <div style="
        margin-top:12px;
        margin-bottom:10px;
    ">

        <span class="tag tag-source">
            📰 {safe(article['source_name'])}
        </span>

        <span class="tag tag-topic">
            {safe(article['sentiment'])}
        </span>

        {article_israel_tone}

        <span class="tag tag-source">
            {safe(article['country'])}
        </span>

        <span class="tag tag-time">
            🕒 {safe(article['published_at'])}
        </span>

    </div>
    """)


    st.title(
        str(article["title"])
    )


    reader_image = image_html(
        article["image_url"],
        height="460px",
    )


    if reader_image:
        render_html(
            reader_image
        )


    render_html(f"""
    <div style="
        font-size:1.12rem;
        line-height:1.8;

        color:#e2e8f0;
        background:#111827;

        padding:30px;

        border-radius:10px;

        border:
            1px solid
            rgba(56,189,248,0.2);

        border-left:
            4px solid #0284c7;

        white-space:pre-line;
    ">
        {safe(article['full_content'])}
    </div>
    """)


# =========================================================
# DASHBOARD
# =========================================================

else:

    title_col, view_col, sync_col = (
        st.columns([5, 4, 3])
    )


    with title_col:

        st.markdown(
            "## Global Intelligence Desk"
        )

        st.caption(
            f"{len(df):,} "
            f"intelligence reports indexed"
        )


    with view_col:

        selected_view = st.radio(
            "View",
            [
                "Main Dashboard",
                "Analytics Terminal",
            ],
            index=(
                0
                if (
                    st.session_state[
                        "view_mode"
                    ]
                    == "Main Dashboard"
                )
                else 1
            ),
            horizontal=True,
            label_visibility="collapsed",
        )

        st.session_state[
            "view_mode"
        ] = selected_view


    with sync_col:

        if st.button(
            "🔄 Sync & Refresh Feeds",
            use_container_width=True,
        ):

            with st.spinner(
                "Synchronizing feeds..."
            ):

                try:

                    new_count = (
                        fetch_live_web_articles()
                    )

                    mark_fetch_complete()

                    st.cache_data.clear()

                    st.success(
                        f"{new_count} "
                        f"new reports added."
                    )

                except Exception as error:

                    st.error(
                        "Feed sync failed."
                    )

                    print(
                        f"Manual sync error: "
                        f"{error}"
                    )


            st.rerun()


    # =====================================================
    # NAVIGATION
    # =====================================================

    NAV_ZONES = [

        (
            "All",
            "All",
            "https://flagcdn.com/w40/un.png",
        ),

        (
            "Iran",
            "Iran",
            "https://flagcdn.com/w40/ir.png",
        ),

        (
            "Saudi Arabia",
            "Saudi Arabia",
            "https://flagcdn.com/w40/sa.png",
        ),

        (
            "UAE",
            "UAE",
            "https://flagcdn.com/w40/ae.png",
        ),

        (
            "Yemen",
            "Yemen",
            "https://flagcdn.com/w40/ye.png",
        ),

        (
            "Syria",
            "Syria",
            "https://flagcdn.com/w40/sy.png",
        ),

        (
            "Iraq",
            "Iraq",
            "https://flagcdn.com/w40/iq.png",
        ),

        (
            "Gaza & WB",
            "Gaza & WB",
            "https://flagcdn.com/w40/ps.png",
        ),

        (
            "Israel",
            "Israel",
            "https://flagcdn.com/w40/il.png",
        ),

        (
            "US & Global",
            "US & Global",
            "https://flagcdn.com/w40/us.png",
        ),
    ]


    nav_columns = st.columns(
        len(NAV_ZONES)
    )


    for index, (
        label,
        value,
        flag,
    ) in enumerate(
        NAV_ZONES
    ):

        with nav_columns[index]:

            render_html(
                f"""
                <div style="
                    text-align:center;
                    margin-bottom:2px;
                ">
                    <img
                        src="{flag}"
                        width="24"
                    >
                </div>
                """
            )


            if st.button(
                label,
                key=f"zone_{value}",
                type=(
                    "primary"
                    if (
                        st.session_state[
                            "selected_country"
                        ]
                        == value
                    )
                    else "secondary"
                ),
                use_container_width=True,
            ):

                st.session_state[
                    "selected_country"
                ] = value

                st.rerun()


    st.markdown("---")


    # =====================================================
    # FILTER
    # =====================================================

    selected_zone = (
        st.session_state[
            "selected_country"
        ]
    )


    if selected_zone == "All":

        filtered_df = df

    else:

        filtered_df = df[
            df["country"]
            .fillna("")
            .str.strip()
            .str.lower()
            ==
            selected_zone
            .strip()
            .lower()
        ]


    # =====================================================
    # ANALYTICS
    # =====================================================

    if (
        st.session_state[
            "view_mode"
        ]
        == "Analytics Terminal"
    ):

        st.markdown(
            f"### 🖥️ Analytics Archive "
            f"({len(filtered_df):,})"
        )


        search = st.text_input(
            "Search archive:",
            placeholder=(
                "Search title, source, summary..."
            ),
        )


        table_df = filtered_df.copy()


        if search:

            mask = (

                table_df["title"]
                .fillna("")
                .str.contains(
                    search,
                    case=False,
                    na=False,
                )

                |

                table_df["summary"]
                .fillna("")
                .str.contains(
                    search,
                    case=False,
                    na=False,
                )

                |

                table_df["source_name"]
                .fillna("")
                .str.contains(
                    search,
                    case=False,
                    na=False,
                )
            )

            table_df = table_df[
                mask
            ]


        display_df = table_df[
            [
                "published_at",
                "country",
                "source_name",
                "sentiment",
                "analyst_name",
                "title",
                "url",
            ]
        ].copy()


        display_df.columns = [
            "Published",
            "Zone",
            "Source",
            "Topic",
            "Israel Tone",
            "Title",
            "URL",
        ]


        st.dataframe(
            display_df,
            use_container_width=True,
            height=600,
            hide_index=True,
        )


    # =====================================================
    # NEWS FEED
    # =====================================================

    else:

        if filtered_df.empty:

            st.info(
                f"No reports indexed "
                f"for {selected_zone}."
            )


        else:

            # =============================================
            # LEAD STORY
            # =============================================

            lead = filtered_df.iloc[0]


            lead_image = image_html(
                lead["image_url"],
                height="400px",
            )


            lead_israel_tone = (
                israel_tone_html(
                    lead["analyst_name"]
                )
            )


            render_html(f"""
            <div
                class="card"
                style="
                    border:
                        1px solid
                        rgba(220,38,38,0.4);

                    margin-bottom:24px;
                "
            >

                {lead_image}

                <div>

                    <span
                        class="
                            tag
                            tag-breaking
                        "
                    >
                        TOP INTELLIGENCE REPORT
                    </span>

                    <span
                        class="
                            tag
                            tag-topic
                        "
                    >
                        {safe(lead['sentiment'])}
                    </span>

                    {lead_israel_tone}

                    <span
                        class="
                            tag
                            tag-source
                        "
                    >
                        📰
                        {safe(lead['source_name'])}
                    </span>

                    <span
                        class="
                            tag
                            tag-time
                        "
                    >
                        🕒
                        {safe(lead['published_at'])}
                    </span>

                </div>


                <h2 style="
                    margin:12px 0 8px 0;

                    font-size:1.8rem;
                    font-weight:800;

                    color:white;
                ">
                    {safe(lead['title'])}
                </h2>


                <p style="
                    color:#94a3b8;

                    font-size:1.05rem;
                    line-height:1.6;
                ">
                    {safe(lead['summary'])}
                </p>

            </div>
            """)


            lead_b1, lead_b2 = (
                st.columns(2)
            )


            with lead_b1:

                if st.button(
                    "📖 Read Report ←",
                    key=(
                        f"lead_read_"
                        f"{lead['id']}"
                    ),
                    type="primary",
                    use_container_width=True,
                ):

                    st.session_state[
                        "reading_article_id"
                    ] = lead["id"]

                    st.rerun()


            with lead_b2:

                st.link_button(
                    "🔗 Open Original Source ↗",
                    lead["url"],
                    use_container_width=True,
                )


            # =============================================
            # GRID
            # =============================================

            remaining = filtered_df[
                filtered_df["id"]
                != lead["id"]
            ]


            if not remaining.empty:

                st.markdown(
                    f"### Zone Feed & Reports "
                    f"({len(filtered_df)})"
                )


                grid_columns = (
                    st.columns(3)
                )


                for position, (
                    _,
                    article_row,
                ) in enumerate(
                    remaining
                    .head(30)
                    .iterrows()
                ):


                    with grid_columns[
                        position % 3
                    ]:


                        card_image = image_html(
                            article_row[
                                "image_url"
                            ],
                            height="230px",
                        )


                        card_israel_tone = (
                            israel_tone_html(
                                article_row[
                                    "analyst_name"
                                ]
                            )
                        )


                        render_html(f"""
                        <div class="card">

                            {card_image}

                            <div>

                                <span
                                    class="
                                        tag
                                        tag-source
                                    "
                                >
                                    {safe(
                                        article_row[
                                            'source_name'
                                        ]
                                    )}
                                </span>

                                <span
                                    class="
                                        tag
                                        tag-topic
                                    "
                                >
                                    {safe(
                                        article_row[
                                            'sentiment'
                                        ]
                                    )}
                                </span>

                                {card_israel_tone}

                                <span
                                    class="
                                        tag
                                        tag-time
                                    "
                                >
                                    🕒
                                    {safe(
                                        article_row[
                                            'published_at'
                                        ]
                                    )}
                                </span>

                            </div>


                            <div style="
                                font-weight:700;

                                font-size:1.05rem;

                                margin:10px 0;

                                line-height:1.4;

                                color:white;
                            ">
                                {safe(
                                    article_row[
                                        'title'
                                    ]
                                )}
                            </div>


                            <p style="
                                color:#94a3b8;

                                font-size:0.9rem;

                                line-height:1.55;
                            ">
                                {safe(
                                    article_row[
                                        'summary'
                                    ]
                                )}
                            </p>

                        </div>
                        """)


                        button_1, button_2 = (
                            st.columns(2)
                        )


                        with button_1:

                            if st.button(
                                "Read ←",
                                key=(
                                    f"read_"
                                    f"{article_row['id']}"
                                ),
                                use_container_width=True,
                            ):

                                st.session_state[
                                    "reading_article_id"
                                ] = (
                                    article_row[
                                        "id"
                                    ]
                                )

                                st.rerun()


                        with button_2:

                            st.link_button(
                                "Source ↗",
                                article_row[
                                    "url"
                                ],
                                use_container_width=True,
                            )