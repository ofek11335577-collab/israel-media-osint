# app.py

import html
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from database import init_db, get_db_connection
from ingestion.fetcher import fetch_live_web_articles


# =========================================================
# STREAMLIT CONFIG
# חייב להגיע לפני שימושים אחרים ב-Streamlit
# =========================================================

st.set_page_config(
    page_title="OSINT Global Desk | Tactical Intelligence Terminal",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# DATABASE
# =========================================================

init_db()


# =========================================================
# INITIAL LIVE FETCH
# מתבצע פעם אחת לכל session ולא בכל rerun
# =========================================================

if "initialized_fetch" not in st.session_state:
    with st.spinner("Connecting to live intelligence feeds..."):
        try:
            fetch_live_web_articles()
        except Exception as e:
            print(f"Initial feed fetch error: {e}")

    st.session_state["initialized_fetch"] = True


# =========================================================
# STATE MANAGEMENT
# =========================================================

if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "Main Dashboard"

if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = "All"

if "reading_article_id" not in st.session_state:
    st.session_state["reading_article_id"] = None


# =========================================================
# HELPERS
# =========================================================

def safe(value):
    """
    Escapes externally sourced text before embedding inside HTML.
    """
    if value is None:
        return ""

    return html.escape(str(value))


# =========================================================
# UI STYLING
# =========================================================

st.markdown(
    """
    <style>

        @import url(
            'https://fonts.googleapis.com/css2?'
            'family=Inter:wght@300;400;500;600;700;800&'
            'family=JetBrains+Mono:wght@400;600&display=swap'
        );

        html, body, [class*="css"], .stApp {
            font-family: 'Inter', sans-serif !important;
            background-color: #07090e;
            color: #f1f5f9;
        }

        header[data-testid="stHeader"] {
            display: none !important;
        }


        /* =========================
           TOP HEADER
        ========================= */

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

        .newsroom-logo span {
            color: #38bdf8;
        }


        /* =========================
           LIVE TICKER
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
            0% {
                transform: translateX(0);
            }

            100% {
                transform: translateX(100%);
            }
        }


        /* =========================
           ARTICLE CARDS
        ========================= */

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


        /* =========================
           TAGS
        ========================= */

        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
            margin-right: 6px;
        }

        .tag-source {
            background: #1f2937;
            color: #60a5fa;
        }

        .tag-time {
            background: #374151;
            color: #9ca3af;
        }

        .tag-breaking {
            background: #dc2626;
            color: #ffffff;
        }


        /* =========================
           BUTTONS
        ========================= */

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
    """,
    unsafe_allow_html=True
)


# =========================================================
# DATA LOADING
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
        conn
    )

    return df


df = load_data()


# =========================================================
# HEADER
# =========================================================

current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

st.markdown(
    f"""
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
    """,
    unsafe_allow_html=True
)


# =========================================================
# LIVE TICKER
# =========================================================

if not df.empty:

    ticker_items = []

    for _, row in df.head(30).iterrows():

        source = safe(row["source_name"])
        title = safe(row["title"])

        ticker_items.append(
            f"<span class='ticker-item'>"
            f"⚡ [{source}] {title}"
            f"</span>"
        )

    ticker_html = "".join(ticker_items)

    st.markdown(
        f"""
        <div class="ticker-wrap">

            <div class="ticker-badge">
                LIVE FEEDS
            </div>

            <div class="ticker-content">
                {ticker_html}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# ARTICLE READER
# =========================================================

if st.session_state["reading_article_id"] is not None:

    article_id = st.session_state["reading_article_id"]

    article_df = df[df["id"] == article_id]

    if not article_df.empty:

        article = article_df.iloc[0]


        # -------------------------
        # BACK / SOURCE BUTTONS
        # -------------------------

        col_back, col_source = st.columns([6, 6])

        with col_back:

            if st.button(
                "← Back to Newsroom",
                use_container_width=True
            ):

                st.session_state["reading_article_id"] = None

                st.rerun()


        with col_source:

            st.link_button(
                "🔗 Open Original Source ↗",
                article["url"],
                use_container_width=True
            )


        # -------------------------
        # ARTICLE METADATA
        # -------------------------

        source_name = safe(article["source_name"])
        published_at = safe(article["published_at"])
        country = safe(article["country"])

        st.markdown(
            f"""
            <span class="tag tag-source">
                📰 {source_name}
            </span>

            <span class="tag tag-time">
                🕒 {published_at}
            </span>

            <span
                class="tag"
                style="
                    background:#0369a1;
                    color:#fff;
                "
            >
                {country}
            </span>
            """,
            unsafe_allow_html=True
        )


        # -------------------------
        # TITLE
        # Streamlit handles text escaping here
        # -------------------------

        st.title(str(article["title"]))


        # -------------------------
        # IMAGE
        # -------------------------

        if article["image_url"]:

            try:
                st.image(
                    article["image_url"],
                    use_container_width=True
                )

            except Exception:
                pass


        # -------------------------
        # CONTENT
        # -------------------------

        article_content = safe(
            article["full_content"]
        )

        st.markdown(
            f"""
            <div
                style="
                    font-size: 1.12rem;
                    line-height: 1.8;
                    color: #e2e8f0;
                    background: #111827;
                    padding: 30px;
                    border-radius: 10px;
                    border-left: 4px solid #0284c7;
                    margin-top: 20px;
                    border: 1px solid rgba(56, 189, 248, 0.2);
                    white-space: pre-line;
                "
            >
                {article_content}
            </div>
            """,
            unsafe_allow_html=True
        )


    else:

        st.session_state["reading_article_id"] = None

        st.rerun()


# =========================================================
# MAIN DASHBOARD
# =========================================================

else:

    col_title, col_view, col_sync = st.columns(
        [5, 4, 3]
    )


    # -------------------------
    # TITLE
    # -------------------------

    with col_title:

        st.markdown(
            """
            <h2
                style="
                    font-weight: 800;
                    margin: 0;
                "
            >
                Global Intelligence Desk
            </h2>
            """,
            unsafe_allow_html=True
        )

        st.caption(
            f"{len(df):,} reports ingested from live feeds"
        )


    # -------------------------
    # VIEW SELECTOR
    # -------------------------

    with col_view:

        selected_view = st.radio(
            "View",
            [
                "Main Dashboard",
                "Analytics Terminal"
            ],
            index=(
                0
                if st.session_state["view_mode"]
                == "Main Dashboard"
                else 1
            ),
            horizontal=True,
            label_visibility="collapsed"
        )

        st.session_state["view_mode"] = (
            selected_view
        )


    # -------------------------
    # MANUAL FEED SYNC
    # -------------------------

    with col_sync:

        if st.button(
            "🔄 Sync & Refresh Feeds",
            use_container_width=True
        ):

            with st.spinner(
                "Fetching latest live feeds..."
            ):

                try:

                    new_count = (
                        fetch_live_web_articles()
                    )

                    st.cache_data.clear()

                    st.success(
                        f"Sync complete. "
                        f"{new_count} new reports added."
                    )

                except Exception as e:

                    st.error(
                        "Feed synchronization failed."
                    )

                    print(
                        f"Manual sync error: {e}"
                    )

            st.rerun()


    # =====================================================
    # ZONE NAVIGATION
    # =====================================================

    NAV_ZONES = [

        {
            "label": "All",
            "val": "All",
            "flag": "https://flagcdn.com/w40/un.png"
        },

        {
            "label": "Iran",
            "val": "Iran",
            "flag": "https://flagcdn.com/w40/ir.png"
        },

        {
            "label": "Saudi Arabia",
            "val": "Saudi Arabia",
            "flag": "https://flagcdn.com/w40/sa.png"
        },

        {
            "label": "UAE",
            "val": "UAE",
            "flag": "https://flagcdn.com/w40/ae.png"
        },

        {
            "label": "Yemen",
            "val": "Yemen",
            "flag": "https://flagcdn.com/w40/ye.png"
        },

        {
            "label": "Syria",
            "val": "Syria",
            "flag": "https://flagcdn.com/w40/sy.png"
        },

        {
            "label": "Iraq",
            "val": "Iraq",
            "flag": "https://flagcdn.com/w40/iq.png"
        },

        {
            "label": "Gaza & WB",
            "val": "Gaza & WB",
            "flag": "https://flagcdn.com/w40/ps.png"
        },

        {
            "label": "US & Global",
            "val": "US & Global",
            "flag": "https://flagcdn.com/w40/us.png"
        }

    ]


    nav_columns = st.columns(
        len(NAV_ZONES)
    )


    for index, zone in enumerate(
        NAV_ZONES
    ):

        with nav_columns[index]:

            is_active = (
                st.session_state["selected_country"]
                == zone["val"]
            )

            st.markdown(
                f"""
                <div
                    style="
                        text-align:center;
                        margin-bottom:2px;
                    "
                >
                    <img
                        src="{zone['flag']}"
                        width="24"
                        style="
                            border-radius:3px;
                        "
                    />
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                zone["label"],
                key=f"zone_{zone['val']}",
                type=(
                    "primary"
                    if is_active
                    else "secondary"
                ),
                use_container_width=True
            ):

                st.session_state[
                    "selected_country"
                ] = zone["val"]

                st.rerun()


    st.markdown(
        """
        <hr
            style="
                border-color:
                rgba(56,189,248,0.2);
                margin:15px 0;
            "
        >
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # FILTERING
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
    # ANALYTICS TERMINAL
    # =====================================================

    if (
        st.session_state["view_mode"]
        == "Analytics Terminal"
    ):

        st.markdown(
            f"""
            ### 🖥️ Analytics Archive
            {len(filtered_df):,}
            reports for zone:
            {selected_zone}
            """
        )


        search_query = st.text_input(
            "Search archive:",
            placeholder=(
                "Search title, source or summary..."
            )
        )


        table_df = filtered_df.copy()


        if search_query:

            query = str(search_query)

            table_df = table_df[

                table_df["title"]
                .fillna("")
                .str.contains(
                    query,
                    case=False,
                    na=False
                )

                |

                table_df["source_name"]
                .fillna("")
                .str.contains(
                    query,
                    case=False,
                    na=False
                )

                |

                table_df["summary"]
                .fillna("")
                .str.contains(
                    query,
                    case=False,
                    na=False
                )

            ]


        display_table = table_df[
            [
                "published_at",
                "country",
                "source_name",
                "sentiment",
                "title",
                "url"
            ]
        ].copy()


        display_table.columns = [

            "Published",

            "Zone",

            "Source",

            "Category",

            "Title",

            "URL"

        ]


        st.dataframe(
            display_table,
            use_container_width=True,
            height=550,
            hide_index=True
        )


        st.caption(
            f"{len(table_df):,} matching reports"
        )


    # =====================================================
    # MAIN NEWSROOM VIEW
    # =====================================================

    else:

        if filtered_df.empty:

            st.info(
                f"No live reports currently indexed "
                f"for zone: {selected_zone}. "
                f"Click 'Sync & Refresh Feeds' "
                f"to fetch latest reports."
            )


        else:

            # =================================================
            # LEAD STORY
            # =================================================

            lead = filtered_df.iloc[0]


            lead_image = safe(
                lead["image_url"]
            )

            lead_source = safe(
                lead["source_name"]
            )

            lead_country = safe(
                lead["country"]
            )

            lead_time = safe(
                lead["published_at"]
            )

            lead_category = safe(
                lead["sentiment"]
            )

            lead_title = safe(
                lead["title"]
            )

            lead_summary = safe(
                lead["summary"]
            )


            st.markdown(
                f"""
                <div
                    class="card"
                    style="
                        margin-bottom:24px;
                        border:
                        1px solid
                        rgba(220,38,38,0.4);
                    "
                >

                    <img
                        class="card-img"
                        style="height:380px;"
                        src="{lead_image}"
                    />

                    <div>

                        <span
                            class="tag tag-breaking"
                        >
                            TOP LEAD STORY
                            ({safe(selected_zone.upper())})
                        </span>

                        <span
                            class="tag"
                            style="
                                background:#0369a1;
                                color:#fff;
                            "
                        >
                            {lead_category}
                        </span>

                        <span
                            class="tag tag-source"
                        >
                            📰
                            {lead_source}
                            ({lead_country})
                        </span>

                        <span
                            class="tag tag-time"
                        >
                            🕒 {lead_time}
                        </span>

                    </div>


                    <h2
                        style="
                            margin:12px 0 8px 0;
                            font-size:1.8rem;
                            font-weight:800;
                            color:#ffffff;
                        "
                    >
                        {lead_title}
                    </h2>


                    <p
                        style="
                            color:#94a3b8;
                            font-size:1.05rem;
                            line-height:1.6;
                            margin-bottom:15px;
                        "
                    >
                        {lead_summary}
                    </p>

                </div>
                """,
                unsafe_allow_html=True
            )


            # -------------------------
            # LEAD BUTTONS
            # -------------------------

            button_col_1, button_col_2 = (
                st.columns([6, 6])
            )


            with button_col_1:

                if st.button(
                    "📖 Read Report ←",
                    key=(
                        f"lead_read_"
                        f"{lead['id']}"
                    ),
                    type="primary",
                    use_container_width=True
                ):

                    st.session_state[
                        "reading_article_id"
                    ] = lead["id"]

                    st.rerun()


            with button_col_2:

                st.link_button(
                    "🔗 Open Original Source ↗",
                    lead["url"],
                    use_container_width=True
                )


            # =================================================
            # ARTICLE GRID
            # =================================================

            remaining_articles = filtered_df[
                filtered_df["id"]
                != lead["id"]
            ]


            if not remaining_articles.empty:

                st.markdown(
                    f"""
                    <h3
                        style="
                            margin:
                            35px 0 15px 0;
                            font-weight:700;
                        "
                    >
                        Zone Feed & Reports
                        ({len(filtered_df)})
                    </h3>
                    """,
                    unsafe_allow_html=True
                )


                grid_columns = st.columns(3)


                for grid_index, (
                    _,
                    article
                ) in enumerate(
                    remaining_articles
                    .head(30)
                    .iterrows()
                ):

                    with grid_columns[
                        grid_index % 3
                    ]:

                        article_image = safe(
                            article["image_url"]
                        )

                        article_source = safe(
                            article["source_name"]
                        )

                        article_time = safe(
                            article["published_at"]
                        )

                        article_title = safe(
                            article["title"]
                        )

                        article_summary = safe(
                            article["summary"]
                        )


                        st.markdown(
                            f"""
                            <div class="card">

                                <img
                                    class="card-img"
                                    src="{article_image}"
                                />

                                <div>

                                    <span
                                        class="
                                        tag
                                        tag-source
                                        "
                                    >
                                        {article_source}
                                    </span>

                                    <span
                                        class="
                                        tag
                                        tag-time
                                        "
                                    >
                                        🕒
                                        {article_time}
                                    </span>

                                </div>


                                <div
                                    style="
                                        font-weight:700;
                                        font-size:1.02rem;
                                        margin:10px 0;
                                        line-height:1.4;
                                        color:#ffffff;
                                    "
                                >
                                    {article_title}
                                </div>


                                <p
                                    style="
                                        color:#94a3b8;
                                        font-size:0.85rem;
                                        line-height:1.5;
                                        margin-bottom:12px;
                                    "
                                >
                                    {article_summary}
                                </p>

                            </div>
                            """,
                            unsafe_allow_html=True
                        )


                        grid_button_1, grid_button_2 = (
                            st.columns(2)
                        )


                        with grid_button_1:

                            if st.button(
                                "Read ←",
                                key=(
                                    f"grid_read_"
                                    f"{article['id']}"
                                ),
                                use_container_width=True
                            ):

                                st.session_state[
                                    "reading_article_id"
                                ] = article["id"]

                                st.rerun()


                        with grid_button_2:

                            st.link_button(
                                "Source ↗",
                                article["url"],
                                use_container_width=True
                            )