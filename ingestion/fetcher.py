# ingestion/fetcher.py

import concurrent.futures
import email.utils
import html
import re
import urllib.request
import xml.etree.ElementTree as ET

from datetime import timezone
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

from database import (
    get_db_connection,
    utc_now_iso,
)


# =========================================================
# SOURCES
# =========================================================

RSS_CHANNELS = [

    {
        "name": "Reuters World",
        "url": (
            "https://www.reuters.com/"
            "arc/outboundfeeds/v1/output/rss/"
            "?outputType=xml"
        ),
        "source_type": "international",
        "domestic_country": None,
    },

    {
        "name": "Al Jazeera English",
        "url": (
            "https://www.aljazeera.com/"
            "xml/rss/all.xml"
        ),
        "source_type": "international",
        "domestic_country": None,
    },

    {
        "name": "BBC Middle East",
        "url": (
            "https://feeds.bbci.co.uk/"
            "news/world/middle_east/rss.xml"
        ),
        "source_type": "international",
        "domestic_country": None,
    },

    {
        "name": "The Guardian Middle East",
        "url": (
            "https://www.theguardian.com/"
            "world/middleeast/rss"
        ),
        "source_type": "international",
        "domestic_country": None,
    },

    {
        "name": "IRNA English",
        "url": "https://en.irna.ir/rss",
        "source_type": "domestic",
        "domestic_country": "Iran",
    },

    {
        "name": "Saudi Press Agency",
        "url": "https://www.spa.gov.sa/rss.xml",
        "source_type": "domestic",
        "domestic_country": "Saudi Arabia",
    },

    {
        "name": "SANA English",
        "url": (
            "https://www.sana.sy/"
            "en/syria/feed/"
        ),
        "source_type": "domestic",
        "domestic_country": "Syria",
    },
]


# =========================================================
# CONFIG
# =========================================================

RSS_TIMEOUT = 6

ARTICLE_TIMEOUT = 3

MAX_ITEMS_PER_SOURCE = 30

MAX_IMAGE_ENRICHMENTS_PER_SYNC = 15

IMAGE_WORKERS = 6

MIN_RELEVANCE_SCORE = 35


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_html(raw_html):

    if not raw_html:
        return ""

    text = raw_html


    for _ in range(2):

        text = html.unescape(
            text
        )


    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )


    text = html.unescape(
        text
    )


    text = re.sub(
        r"\s+",
        " ",
        text,
    )


    return text.strip()


# =========================================================
# URL
# =========================================================

def normalize_url(url):

    if not url:
        return ""


    try:

        parts = urlsplit(
            url.strip()
        )


        return urlunsplit(
            (
                parts.scheme,
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                parts.query,
                "",
            )
        )


    except Exception:

        return url.strip()


# =========================================================
# TITLE
# =========================================================

def normalize_title(title):

    if not title:
        return ""


    text = html.unescape(
        title
    ).lower()


    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )


    text = re.sub(
        r"\s+",
        " ",
        text,
    )


    return text.strip()


# =========================================================
# DATE
# =========================================================

def parse_rss_date(
    pub_date_elem,
):

    if (
        pub_date_elem is not None
        and pub_date_elem.text
    ):

        try:

            parsed = (
                email.utils
                .parsedate_to_datetime(
                    pub_date_elem.text
                )
            )


            if parsed is not None:

                if parsed.tzinfo is None:

                    parsed = parsed.replace(
                        tzinfo=timezone.utc
                    )


                parsed = parsed.astimezone(
                    timezone.utc
                )


                return (
                    parsed
                    .replace(
                        microsecond=0
                    )
                    .isoformat()
                )


        except Exception:

            pass


    return utc_now_iso()


# =========================================================
# SPORTS / NOISE
# =========================================================

SPORTS_KEYWORDS = [

    "football",
    "footballer",
    "footballers",
    "soccer",

    "premier league",
    "champions league",
    "europa league",
    "conference league",

    "world cup",

    "football fans",
    "stadium",

    " var ",
    "var decision",
    "var controversy",

    "derby",

    "goalkeeper",
    "striker",
    "midfielder",

    "red card",
    "yellow card",

    "penalty shootout",

    "kick-off",
    "kickoff",

    "matchday",
    "fixture",

    "transfer window",

    "manchester united",
    "manchester city",

    "chelsea",
    "arsenal",
    "liverpool",
    "tottenham",

    "real madrid",
    "barcelona",

    "psg",
    "bayern",

    "mbappe",
    "vinicius",
    "ronaldo",
    "messi",
]


OTHER_NOISE_KEYWORDS = [

    "celebrity gossip",

    "fashion show",

    "recipe",

    "restaurant review",

    "movie review",

    "film review",

    "album review",

    "horoscope",

    "lottery",

    "travel tips",
]


def is_noise_article(
    title,
    summary,
):

    text = (
        f" {title or ''} "
        f"{summary or ''} "
    ).lower()


    if any(
        term in text
        for term in SPORTS_KEYWORDS
    ):

        return True


    if any(
        term in text
        for term in OTHER_NOISE_KEYWORDS
    ):

        return True


    return False


# =========================================================
# CLEAN OLD NOISE
# =========================================================

def cleanup_existing_noise(
    cursor,
):

    cursor.execute("""
        SELECT
            id,
            title,
            summary
        FROM articles
    """)


    rows = cursor.fetchall()

    ids_to_delete = []


    for row in rows:

        if is_noise_article(
            row["title"],
            row["summary"],
        ):

            ids_to_delete.append(
                (
                    row["id"],
                )
            )


    if not ids_to_delete:

        return 0


    cursor.executemany(
        """
        DELETE FROM articles
        WHERE id = ?
        """,
        ids_to_delete,
    )


    return len(
        ids_to_delete
    )


# =========================================================
# COUNTRY
# =========================================================

COUNTRY_KEYWORDS = {

    "Iran": [
        "iran",
        "iranian",
        "tehran",
        "khamenei",
        "pezeshkian",
        "irgc",
        "revolutionary guard",
    ],

    "Saudi Arabia": [
        "saudi",
        "riyadh",
        "jeddah",
        "bin salman",
        "mohammed bin salman",
    ],

    "UAE": [
        "uae",
        "united arab emirates",
        "emirati",
        "dubai",
        "abu dhabi",
    ],

    "Yemen": [
        "yemen",
        "yemeni",
        "houthi",
        "houthis",
        "sanaa",
        "sana'a",
    ],

    "Syria": [
        "syria",
        "syrian",
        "damascus",
    ],

    "Iraq": [
        "iraq",
        "iraqi",
        "baghdad",
        "basra",
        "kurdistan",
    ],

    "Gaza & WB": [
        "gaza",
        "palestin",
        "west bank",
        "ramallah",
        "jenin",
        "nablus",
    ],

    "Israel": [
        "israel",
        "israeli",
        "jerusalem",
        "tel aviv",
        "idf",
    ],
}


TARGET_COUNTRIES = {

    "Iran",

    "Saudi Arabia",

    "UAE",

    "Yemen",

    "Syria",

    "Iraq",

    "Gaza & WB",

    "Israel",
}


REGIONAL_KEYWORDS = [

    "iran",

    "israel",

    "gaza",

    "palestin",

    "west bank",

    "saudi",

    "yemen",

    "houthi",

    "syria",

    "iraq",

    "uae",

    "middle east",

    "red sea",

    "gulf",

    "hezbollah",

    "hamas",

    "irgc",
]


def classify_country(
    title,
    summary,
    domestic_country=None,
):

    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()


    best_country = None

    best_score = 0


    for (
        country,
        keywords,
    ) in COUNTRY_KEYWORDS.items():


        score = sum(
            1
            for keyword in keywords
            if keyword in text
        )


        if score > best_score:

            best_country = country

            best_score = score


    if best_country:

        return best_country


    if domestic_country:

        return domestic_country


    return "US & Global"


# =========================================================
# TOPICS
# =========================================================

TOPIC_KEYWORDS = {

    "Security / Military": [

        "military",

        "army",

        "missile",

        "ballistic",

        "air defense",

        "air defence",

        "airstrike",

        "air strike",

        "drone",

        "armed forces",

        "navy",

        "naval",

        "weapon",

        "weapons",

        "security forces",

        "irgc",

        "revolutionary guard",

        "militia",

        "border security",
    ],


    "Politics / Regime": [

        "president",

        "prime minister",

        "government",

        "cabinet",

        "parliament",

        "minister",

        "election",

        "elections",

        "political",

        "leadership",

        "supreme leader",

        "resignation",

        "resigns",

        "appointed",

        "appointment",

        "dismissed",

        "opposition",

        "constitution",
    ],


    "Strategic Economy": [

        "oil",

        "gas",

        "currency",

        "rial",

        "inflation",

        "sanction",

        "sanctions",

        "central bank",

        "trade",

        "exports",

        "imports",

        "energy",

        "economic crisis",

        "budget",

        "debt",

        "opec",

        "refinery",

        "production",
    ],


    "Internal Stability": [

        "protest",

        "protests",

        "demonstration",

        "demonstrations",

        "riot",

        "riots",

        "unrest",

        "clashes",

        "arrest",

        "arrests",

        "detained",

        "ethnic",

        "minority",

        "separatist",

        "state of emergency",
    ],


    "Nuclear / Cyber / Technology": [

        "nuclear",

        "uranium",

        "enrichment",

        "centrifuge",

        "iaea",

        "cyber",

        "cyberattack",

        "cyber attack",

        "hacking",

        "military technology",

        "satellite",

        "space program",
    ],


    "Diplomacy": [

        "diplomatic",

        "diplomacy",

        "foreign minister",

        "foreign ministry",

        "negotiation",

        "negotiations",

        "agreement",

        "summit",

        "delegation",

        "ambassador",

        "relations",

        "ceasefire",

        "truce",
    ],
}


def classify_topic(
    title,
    summary,
):

    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()


    best_topic = "General"

    best_score = 0


    for (
        topic,
        keywords,
    ) in TOPIC_KEYWORDS.items():


        score = sum(
            1
            for keyword in keywords
            if keyword in text
        )


        if score > best_score:

            best_topic = topic

            best_score = score


    return best_topic


# =========================================================
# RELEVANCE
# =========================================================

HIGH_IMPACT_KEYWORDS = [

    "war",

    "attack",

    "missile",

    "airstrike",

    "nuclear",

    "sanctions",

    "government crisis",

    "resignation",

    "protest",

    "unrest",

    "coup",

    "election",

    "ceasefire",

    "currency crisis",

    "oil production",

    "central bank",

    "irgc",
]


def calculate_relevance_score(
    title,
    summary,
    country,
    topic,
    source_type,
):

    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()


    score = 0


    if country in TARGET_COUNTRIES:

        score += 25


    if source_type == "domestic":

        score += 15


    topic_scores = {

        "Security / Military":
            40,

        "Politics / Regime":
            32,

        "Strategic Economy":
            28,

        "Internal Stability":
            35,

        "Nuclear / Cyber / Technology":
            38,

        "Diplomacy":
            27,

        "General":
            0,
    }


    score += topic_scores.get(
        topic,
        0,
    )


    regional_hits = sum(
        1
        for keyword in REGIONAL_KEYWORDS
        if keyword in text
    )


    if regional_hits:

        score += min(
            regional_hits * 8,
            24,
        )


    impact_hits = sum(
        1
        for keyword in HIGH_IMPACT_KEYWORDS
        if keyword in text
    )


    score += min(
        impact_hits * 6,
        18,
    )


    if (
        country == "US & Global"
        and regional_hits == 0
    ):

        score -= 35


    if (
        country == "US & Global"
        and topic == "General"
    ):

        score -= 30


    return max(
        0,
        min(
            score,
            100,
        ),
    )


# =========================================================
# ISRAEL FRAMING CLASSIFIER
# =========================================================

ISRAEL_REFERENCES = [

    "israel",

    "israeli",

    "idf",

    "israel defense forces",

    "israel defence forces",

    "netanyahu",

    "jerusalem",

    "tel aviv",

    "zionist",
]


# Weighted hostile framing.
#
# Strong ideological / accusatory language
# receives more weight than ordinary reporting.

HOSTILE_PHRASES = {

    "ethnic cleansing": 6,

    "genocide": 5,

    "genocidal": 5,

    "apartheid": 5,

    "collective punishment": 5,

    "war crimes": 4,

    "war crime": 4,

    "israeli aggression": 4,

    "zionist regime": 4,

    "israeli atrocities": 5,

    "israeli crimes": 4,

    "israeli massacre": 5,

    "massacre by israel": 5,

    "brutal occupation": 4,

    "illegal occupation": 3,

    "occupation forces": 3,

    "deliberate attack on civilians": 5,

    "deliberately targeting civilians": 5,

    "indiscriminate attacks": 4,

    "indiscriminate bombing": 4,

    "starvation as a weapon": 5,

    "forced displacement": 3,

    "colonial occupation": 4,

    "settler violence": 3,
}


# Weighted supportive framing.

POSITIVE_PHRASES = {

    "right to defend itself": 6,

    "right to self-defense": 6,

    "right to self defence": 6,

    "israel's right to exist": 6,

    "israel has the right to exist": 6,

    "legitimate security concerns": 5,

    "israel's security needs": 5,

    "israeli security needs": 5,

    "defending israel": 4,

    "defend israel": 4,

    "protect israeli civilians": 5,

    "protecting israeli civilians": 5,

    "terror attack against israel": 4,

    "terrorist attack against israel": 4,

    "terror attack on israel": 4,

    "terrorist attack on israel": 4,

    "hostages rescued": 3,

    "rescued hostages": 3,

    "hostage rescue": 3,

    "intercepted missiles": 2,

    "intercepted rockets": 2,

    "thwarted an attack": 3,

    "thwarted attack": 3,
}


HOSTILE_CONTEXT_TERMS = {

    "aggression": 3,

    "atrocity": 3,

    "atrocities": 3,

    "massacre": 3,

    "occupation": 2,

    "occupying": 2,

    "brutal": 2,

    "illegal": 1,

    "unlawful": 2,

    "indiscriminate": 3,

    "oppression": 3,

    "oppressive": 3,

    "colonial": 2,

    "siege": 2,

    "besieged": 2,

    "starvation": 3,
}


POSITIVE_CONTEXT_TERMS = {

    "self-defense": 4,

    "self defence": 4,

    "defending": 2,

    "security": 1,

    "protecting": 2,

    "protect": 2,

    "intercept": 2,

    "intercepted": 2,

    "rescue": 2,

    "rescued": 2,

    "thwart": 2,

    "thwarted": 2,

    "terrorist": 1,

    "terror attack": 2,

    "hostage": 1,

    "hostages": 1,
}


# Phrases indicating that strong language is being
# reported as an allegation or explicitly rejected.

REJECTION_PATTERNS = [

    r"reject(?:s|ed|ing)?\s+(?:the\s+)?"
    r"(?:claim|claims|accusation|accusations|allegation|allegations)"
    r".{0,40}",

    r"den(?:y|ies|ied|ying)\s+(?:the\s+)?"
    r"(?:claim|claims|accusation|accusations|allegation|allegations)"
    r".{0,40}",

    r"disput(?:e|es|ed|ing)\s+(?:the\s+)?"
    r"(?:claim|claims|accusation|accusations)"
    r".{0,40}",
]


ATTRIBUTION_WORDS = [

    "accused",

    "accuses",

    "accusing",

    "alleged",

    "alleges",

    "claimed",

    "claims",

    "according to",

    "rights group says",

    "un says",

    "critics say",
]


def is_israel_related(
    title,
    summary,
):

    text = (
        f"{title or ''} "
        f"{summary or ''}"
    ).lower()


    return any(
        reference in text
        for reference
        in ISRAEL_REFERENCES
    )


def phrase_weight_score(
    text,
    phrase_weights,
):

    score = 0


    for phrase, weight in phrase_weights.items():

        if phrase in text:

            score += weight


    return score


def israel_context_windows(
    text,
    window_size=140,
):

    windows = []


    for reference in ISRAEL_REFERENCES:

        start = 0


        while True:

            index = text.find(
                reference,
                start,
            )


            if index == -1:

                break


            left = max(
                0,
                index - window_size,
            )


            right = min(
                len(text),
                index
                + len(reference)
                + window_size,
            )


            windows.append(
                text[
                    left:right
                ]
            )


            start = (
                index
                + len(reference)
            )


    return windows


def context_score(
    windows,
    weighted_terms,
):

    score = 0


    for window in windows:

        for term, weight in weighted_terms.items():

            if term in window:

                score += weight


    return score


def rejection_adjustment(
    text,
    phrases,
):

    adjustment = 0


    for phrase in phrases:

        phrase_index = text.find(
            phrase
        )


        if phrase_index == -1:

            continue


        context_start = max(
            0,
            phrase_index - 90,
        )


        context = text[
            context_start:
            phrase_index
            + len(phrase)
            + 20
        ]


        for pattern in REJECTION_PATTERNS:

            if re.search(
                pattern,
                context,
                flags=re.IGNORECASE,
            ):

                adjustment += 4

                break


    return adjustment


def attribution_count(
    text,
    phrases,
):

    count = 0


    for phrase in phrases:

        index = text.find(
            phrase
        )


        if index == -1:

            continue


        context = text[
            max(
                0,
                index - 80,
            ):
            min(
                len(text),
                index
                + len(phrase)
                + 80,
            )
        ]


        if any(
            attribution
            in context
            for attribution
            in ATTRIBUTION_WORDS
        ):

            count += 1


    return count


def classify_israel_framing(
    title,
    summary,
):
    """
    Returns:

        hostile
        positive
        neutral
        ""

    Empty string means Israel is not meaningfully
    referenced in the article text.

    This is a framing classifier, not a claim
    about the journalist's private beliefs.
    """

    if not is_israel_related(
        title,
        summary,
    ):

        return ""


    title_text = (
        title or ""
    ).lower()


    summary_text = (
        summary or ""
    ).lower()


    full_text = (
        f"{title_text}. "
        f"{summary_text}"
    )


    # -----------------------------------------------------
    # BASE PHRASE SCORES
    # -----------------------------------------------------

    hostile_score = (
        phrase_weight_score(
            full_text,
            HOSTILE_PHRASES,
        )
    )


    positive_score = (
        phrase_weight_score(
            full_text,
            POSITIVE_PHRASES,
        )
    )


    # -----------------------------------------------------
    # HEADLINE HAS MORE INFLUENCE
    # -----------------------------------------------------

    hostile_title_score = (
        phrase_weight_score(
            title_text,
            HOSTILE_PHRASES,
        )
    )


    positive_title_score = (
        phrase_weight_score(
            title_text,
            POSITIVE_PHRASES,
        )
    )


    hostile_score += (
        hostile_title_score
    )


    positive_score += (
        positive_title_score
    )


    # -----------------------------------------------------
    # LOCAL CONTEXT AROUND ISRAEL REFERENCES
    # -----------------------------------------------------

    windows = (
        israel_context_windows(
            full_text
        )
    )


    hostile_score += (
        context_score(
            windows,
            HOSTILE_CONTEXT_TERMS,
        )
    )


    positive_score += (
        context_score(
            windows,
            POSITIVE_CONTEXT_TERMS,
        )
    )


    # -----------------------------------------------------
    # DO NOT OVERREACT TO REJECTED ACCUSATIONS
    #
    # Example:
    # "Israel rejects accusations of genocide"
    # -----------------------------------------------------

    hostile_rejections = (
        rejection_adjustment(
            full_text,
            HOSTILE_PHRASES.keys(),
        )
    )


    positive_rejections = (
        rejection_adjustment(
            full_text,
            POSITIVE_PHRASES.keys(),
        )
    )


    hostile_score = max(
        0,
        hostile_score
        - hostile_rejections,
    )


    positive_score = max(
        0,
        positive_score
        - positive_rejections,
    )


    # -----------------------------------------------------
    # ALLEGATIONS GET SLIGHTLY LOWER CONFIDENCE
    # -----------------------------------------------------

    hostile_attributions = (
        attribution_count(
            full_text,
            HOSTILE_PHRASES.keys(),
        )
    )


    positive_attributions = (
        attribution_count(
            full_text,
            POSITIVE_PHRASES.keys(),
        )
    )


    hostile_score = max(
        0,
        hostile_score
        - hostile_attributions,
    )


    positive_score = max(
        0,
        positive_score
        - positive_attributions,
    )


    # -----------------------------------------------------
    # DECISION
    # -----------------------------------------------------

    if (
        hostile_score >= 3
        and
        hostile_score
        >= positive_score + 2
    ):

        return "hostile"


    if (
        positive_score >= 3
        and
        positive_score
        >= hostile_score + 2
    ):

        return "positive"


    return "neutral"


# =========================================================
# IMAGE QUALITY
# =========================================================

def image_candidate_score(
    url,
    width=None,
    height=None,
):

    score = 0


    if width:

        try:

            score += min(
                int(width),
                2000,
            )

        except Exception:

            pass


    if height:

        try:

            score += (
                min(
                    int(height),
                    1200,
                )
                // 2
            )

        except Exception:

            pass


    low_url = (
        url or ""
    ).lower()


    bad_markers = [

        "thumbnail",

        "thumb",

        "small",

        "tiny",

        "120x",

        "150x",

        "200x",

        "240x",

        "300x",

        "320x",
    ]


    for marker in bad_markers:

        if marker in low_url:

            score -= 600


    good_markers = [

        "1200",

        "1600",

        "1920",

        "2048",

        "large",

        "original",
    ]


    for marker in good_markers:

        if marker in low_url:

            score += 400


    return score


def upgrade_common_image_url(
    image_url,
):

    if not image_url:

        return image_url


    try:

        parts = urlsplit(
            image_url
        )


        query = dict(
            parse_qsl(
                parts.query,
                keep_blank_values=True,
            )
        )


        changed = False


        for key in [

            "w",

            "width",

            "imgWidth",

            "imageWidth",
        ]:


            if key in query:

                try:

                    current = int(
                        query[key]
                    )


                    if current < 1000:

                        query[key] = "1200"

                        changed = True


                except Exception:

                    pass


        if changed:

            return urlunsplit(
                (
                    parts.scheme,
                    parts.netloc,
                    parts.path,
                    urlencode(query),
                    parts.fragment,
                )
            )


    except Exception:

        pass


    return image_url


# =========================================================
# RSS IMAGE
# =========================================================

def extract_feed_image(
    item,
    raw_description,
):

    candidates = []


    for media in item.findall(
        "{http://search.yahoo.com/mrss/}content"
    ):

        url = media.get(
            "url"
        )


        if url:

            candidates.append(
                {
                    "url":
                        url,

                    "width":
                        media.get(
                            "width"
                        ),

                    "height":
                        media.get(
                            "height"
                        ),
                }
            )


    for media in item.findall(
        "{http://search.yahoo.com/mrss/}thumbnail"
    ):

        url = media.get(
            "url"
        )


        if url:

            candidates.append(
                {
                    "url":
                        url,

                    "width":
                        media.get(
                            "width"
                        ),

                    "height":
                        media.get(
                            "height"
                        ),
                }
            )


    enclosure = item.find(
        "enclosure"
    )


    if enclosure is not None:

        url = enclosure.get(
            "url"
        )


        if url:

            candidates.append(
                {
                    "url":
                        url,

                    "width":
                        None,

                    "height":
                        None,
                }
            )


    if raw_description:


        img_matches = re.findall(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            raw_description,
            flags=re.IGNORECASE,
        )


        for url in img_matches:

            candidates.append(
                {
                    "url":
                        url,

                    "width":
                        None,

                    "height":
                        None,
                }
            )


        srcset_matches = re.findall(
            r'srcset=["\']([^"\']+)["\']',
            raw_description,
            flags=re.IGNORECASE,
        )


        for srcset in srcset_matches:


            for piece in srcset.split(
                ","
            ):


                piece = piece.strip()


                if not piece:

                    continue


                parts = piece.split()


                url = parts[0]

                width = None


                if (
                    len(parts) > 1
                    and parts[1].endswith(
                        "w"
                    )
                ):

                    try:

                        width = int(
                            parts[1][:-1]
                        )

                    except Exception:

                        pass


                candidates.append(
                    {
                        "url":
                            url,

                        "width":
                            width,

                        "height":
                            None,
                    }
                )


    cleaned_candidates = []


    for candidate in candidates:


        url = html.unescape(
            candidate[
                "url"
            ].strip()
        )


        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):

            continue


        url = upgrade_common_image_url(
            url
        )


        candidate[
            "url"
        ] = url


        candidate[
            "score"
        ] = image_candidate_score(
            url,
            candidate.get(
                "width"
            ),
            candidate.get(
                "height"
            ),
        )


        cleaned_candidates.append(
            candidate
        )


    if not cleaned_candidates:

        return None


    best = max(
        cleaned_candidates,
        key=lambda x:
            x["score"],
    )


    return best[
        "url"
    ]


# =========================================================
# ORIGINAL ARTICLE IMAGE
# =========================================================

def extract_original_article_image(
    article_url,
):

    if not article_url:

        return None


    try:

        request = (
            urllib.request.Request(
                article_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; "
                        "Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/120.0 "
                        "Safari/537.36"
                    ),
                },
            )
        )


        with urllib.request.urlopen(
            request,
            timeout=ARTICLE_TIMEOUT,
        ) as response:


            page_html = (
                response
                .read(
                    400_000
                )
                .decode(
                    "utf-8",
                    errors="ignore",
                )
            )


        candidates = []


        patterns = [

            (
                r'<meta[^>]*'
                r'property=["\']'
                r'og:image:secure_url'
                r'["\'][^>]*'
                r'content=["\']'
                r'([^"\']+)'
                r'["\']'
            ),

            (
                r'<meta[^>]*'
                r'property=["\']'
                r'og:image'
                r'["\'][^>]*'
                r'content=["\']'
                r'([^"\']+)'
                r'["\']'
            ),

            (
                r'<meta[^>]*'
                r'name=["\']'
                r'twitter:image'
                r'["\'][^>]*'
                r'content=["\']'
                r'([^"\']+)'
                r'["\']'
            ),

            (
                r'<meta[^>]*'
                r'content=["\']'
                r'([^"\']+)'
                r'["\'][^>]*'
                r'property=["\']'
                r'og:image'
                r'["\']'
            ),
        ]


        for pattern in patterns:


            matches = re.findall(
                pattern,
                page_html,
                flags=re.IGNORECASE,
            )


            for image_url in matches:


                image_url = (
                    html.unescape(
                        image_url.strip()
                    )
                )


                if image_url.startswith(
                    "//"
                ):

                    image_url = (
                        "https:"
                        + image_url
                    )


                elif image_url.startswith(
                    "/"
                ):

                    image_url = (
                        urljoin(
                            article_url,
                            image_url,
                        )
                    )


                if not image_url.startswith(
                    (
                        "http://",
                        "https://",
                    )
                ):

                    continue


                image_url = (
                    upgrade_common_image_url(
                        image_url
                    )
                )


                candidates.append(
                    image_url
                )


        if not candidates:

            return None


        return max(
            candidates,
            key=lambda url:
                image_candidate_score(
                    url
                ),
        )


    except Exception as error:


        print(
            "Image enrichment error "
            f"({article_url}): "
            f"{error}"
        )


    return None


# =========================================================
# LOW QUALITY IMAGE
# =========================================================

def image_looks_low_quality(
    image_url,
):

    if not image_url:

        return True


    low = (
        image_url.lower()
    )


    low_quality_markers = [

        "thumbnail",

        "thumb",

        "tiny",

        "small",

        "120x",

        "150x",

        "180x",

        "200x",

        "240x",

        "300x",

        "320x",
    ]


    if any(
        marker in low
        for marker
        in low_quality_markers
    ):

        return True


    try:

        query = dict(
            parse_qsl(
                urlsplit(
                    image_url
                ).query
            )
        )


        for key in [

            "w",

            "width",

            "imgWidth",

            "imageWidth",
        ]:


            if key not in query:

                continue


            try:

                if int(
                    query[key]
                ) < 700:

                    return True


            except Exception:

                pass


    except Exception:

        pass


    return False


# =========================================================
# DUPLICATE CHECK
# =========================================================

def article_exists(
    cursor,
    url,
    title,
):

    cursor.execute(
        """
        SELECT id
        FROM articles
        WHERE url = ?
        LIMIT 1
        """,
        (
            url,
        ),
    )


    if cursor.fetchone():

        return True


    normalized_title = (
        normalize_title(
            title
        )
    )


    if not normalized_title:

        return False


    cursor.execute(
        """
        SELECT title
        FROM articles
        ORDER BY id DESC
        LIMIT 500
        """
    )


    for row in cursor.fetchall():


        existing_title = (
            normalize_title(
                row[
                    "title"
                ]
            )
        )


        if (
            existing_title
            and
            existing_title
            ==
            normalized_title
        ):

            return True


    return False


# =========================================================
# RSS DOWNLOAD
# =========================================================

def fetch_feed_xml(
    source,
):

    try:

        request = (
            urllib.request.Request(
                source["url"],
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; "
                        "OSINTGlobalDesk/7.0)"
                    )
                },
            )
        )


        with urllib.request.urlopen(
            request,
            timeout=RSS_TIMEOUT,
        ) as response:


            return (
                source,
                response.read(),
                None,
            )


    except Exception as error:


        return (
            source,
            None,
            error,
        )


# =========================================================
# IMAGE ENRICHMENT
# =========================================================

def enrich_images(
    conn,
    articles_to_enrich,
):

    if not articles_to_enrich:

        return 0


    articles_to_enrich = (
        articles_to_enrich[
            :MAX_IMAGE_ENRICHMENTS_PER_SYNC
        ]
    )


    updates = []


    with (
        concurrent.futures
        .ThreadPoolExecutor(
            max_workers=IMAGE_WORKERS
        )
    ) as executor:


        future_map = {

            executor.submit(
                extract_original_article_image,
                article[
                    "url"
                ],
            ):
            article

            for article
            in articles_to_enrich
        }


        for future in (
            concurrent.futures
            .as_completed(
                future_map
            )
        ):


            article = (
                future_map[
                    future
                ]
            )


            try:


                better_image = (
                    future.result()
                )


                if better_image:


                    updates.append(
                        (
                            better_image,
                            article[
                                "id"
                            ],
                        )
                    )


            except Exception:

                pass


    if not updates:

        return 0


    cursor = (
        conn.cursor()
    )


    cursor.executemany(
        """
        UPDATE articles
        SET image_url = ?
        WHERE id = ?
        """,
        updates,
    )


    conn.commit()


    return len(
        updates
    )


# =========================================================
# BACKFILL ISRAEL FRAMING
# =========================================================

def backfill_israel_framing(
    conn,
):

    cursor = (
        conn.cursor()
    )


    cursor.execute(
        """
        SELECT
            id,
            title,
            summary
        FROM articles
        """
    )


    rows = (
        cursor.fetchall()
    )


    updates = []


    for row in rows:


        framing = (
            classify_israel_framing(
                row[
                    "title"
                ],
                row[
                    "summary"
                ],
            )
        )


        updates.append(
            (
                framing,
                row[
                    "id"
                ],
            )
        )


    cursor.executemany(
        """
        UPDATE articles
        SET analyst_name = ?
        WHERE id = ?
        """,
        updates,
    )


    conn.commit()


    return len(
        updates
    )


# =========================================================
# MAIN FETCH
# =========================================================

def fetch_live_web_articles():

    conn = (
        get_db_connection()
    )

    cursor = (
        conn.cursor()
    )


    # =====================================================
    # CLEAN OLD SPORTS
    # =====================================================

    deleted_noise = (
        cleanup_existing_noise(
            cursor
        )
    )


    conn.commit()


    total_added = 0

    total_duplicates = 0

    total_noise = 0

    total_low_relevance = 0


    images_to_enrich = []


    # =====================================================
    # FETCH FEEDS
    # =====================================================

    with (
        concurrent.futures
        .ThreadPoolExecutor(
            max_workers=min(
                len(
                    RSS_CHANNELS
                ),
                8,
            )
        )
    ) as executor:


        futures = [

            executor.submit(
                fetch_feed_xml,
                source,
            )

            for source
            in RSS_CHANNELS
        ]


        feed_results = [

            future.result()

            for future
            in futures
        ]


    # =====================================================
    # PARSE FEEDS
    # =====================================================

    for (
        source,
        xml_data,
        feed_error,
    ) in feed_results:


        if feed_error is not None:


            print(
                f"Feed error "
                f"({source['name']}): "
                f"{feed_error}"
            )


            continue


        try:


            root = (
                ET.fromstring(
                    xml_data
                )
            )


        except Exception as error:


            print(
                f"XML error "
                f"({source['name']}): "
                f"{error}"
            )


            continue


        items = (
            root.findall(
                ".//item"
            )
        )


        for item in items[
            :MAX_ITEMS_PER_SOURCE
        ]:


            title_elem = (
                item.find(
                    "title"
                )
            )


            link_elem = (
                item.find(
                    "link"
                )
            )


            pub_date_elem = (
                item.find(
                    "pubDate"
                )
            )


            description_elem = (
                item.find(
                    "description"
                )
            )


            # TITLE

            title = (

                clean_html(
                    title_elem.text
                )

                if (
                    title_elem
                    is not None
                    and
                    title_elem.text
                )

                else ""
            )


            if not title:

                continue


            # URL

            raw_url = (

                link_elem
                .text
                .strip()

                if (
                    link_elem
                    is not None
                    and
                    link_elem.text
                )

                else ""
            )


            if not raw_url:

                continue


            url = (
                normalize_url(
                    raw_url
                )
            )


            # SUMMARY

            raw_description = (

                description_elem.text

                if (
                    description_elem
                    is not None
                    and
                    description_elem.text
                )

                else ""
            )


            summary = (
                clean_html(
                    raw_description
                )
            )


            if not summary:

                summary = (
                    title
                )


            summary = (
                summary[
                    :500
                ]
            )


            # NOISE

            if is_noise_article(
                title,
                summary,
            ):


                total_noise += 1


                continue


            # DUPLICATE

            if article_exists(
                cursor,
                url,
                title,
            ):


                total_duplicates += 1


                continue


            # COUNTRY

            country = (
                classify_country(
                    title,
                    summary,
                    source.get(
                        "domestic_country"
                    ),
                )
            )


            # TOPIC

            topic = (
                classify_topic(
                    title,
                    summary,
                )
            )


            # RELEVANCE

            relevance_score = (
                calculate_relevance_score(
                    title=title,
                    summary=summary,
                    country=country,
                    topic=topic,
                    source_type=source[
                        "source_type"
                    ],
                )
            )


            if (
                relevance_score
                <
                MIN_RELEVANCE_SCORE
            ):


                total_low_relevance += 1


                continue


            # ISRAEL FRAMING

            israel_framing = (
                classify_israel_framing(
                    title,
                    summary,
                )
            )


            # IMAGE

            image_url = (
                extract_feed_image(
                    item,
                    raw_description,
                )
            )


            # TIME

            published_at = (
                parse_rss_date(
                    pub_date_elem
                )
            )


            created_at = (
                utc_now_iso()
            )


            # INSERT

            cursor.execute(
                """
                INSERT OR IGNORE INTO articles
                (
                    url,
                    source_name,
                    country,
                    title,
                    summary,
                    full_content,
                    analyst_name,
                    published_at,
                    image_url,
                    sentiment,
                    priority,
                    created_at
                )

                VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (
                    url,

                    source[
                        "name"
                    ],

                    country,

                    title,

                    summary,

                    summary,

                    israel_framing,

                    published_at,

                    image_url,

                    topic,

                    relevance_score,

                    created_at,
                ),
            )


            if (
                cursor.rowcount
                >
                0
            ):


                article_id = (
                    cursor.lastrowid
                )


                total_added += 1


                if (
                    not image_url
                    or
                    image_looks_low_quality(
                        image_url
                    )
                ):


                    images_to_enrich.append(
                        {
                            "id":
                                article_id,

                            "url":
                                url,
                        }
                    )


        conn.commit()


    # =====================================================
    # UPGRADE EXISTING IMAGES
    # =====================================================

    if (
        len(
            images_to_enrich
        )
        <
        MAX_IMAGE_ENRICHMENTS_PER_SYNC
    ):


        cursor.execute(
            """
            SELECT
                id,
                url,
                image_url

            FROM articles

            ORDER BY id DESC

            LIMIT 120
            """
        )


        existing_rows = (
            cursor.fetchall()
        )


        queued_ids = {

            article[
                "id"
            ]

            for article
            in images_to_enrich
        }


        for row in existing_rows:


            if (
                len(
                    images_to_enrich
                )
                >=
                MAX_IMAGE_ENRICHMENTS_PER_SYNC
            ):

                break


            if (
                row[
                    "id"
                ]
                in
                queued_ids
            ):

                continue


            if (
                not row[
                    "image_url"
                ]
                or
                image_looks_low_quality(
                    row[
                        "image_url"
                    ]
                )
            ):


                images_to_enrich.append(
                    {
                        "id":
                            row[
                                "id"
                            ],

                        "url":
                            row[
                                "url"
                            ],
                    }
                )


    images_updated = (
        enrich_images(
            conn,
            images_to_enrich,
        )
    )


    # =====================================================
    # RECLASSIFY ALL EXISTING ARTICLES
    # =====================================================

    framing_rows_updated = (
        backfill_israel_framing(
            conn
        )
    )


    # =====================================================
    # LOG
    # =====================================================

    print(
        "RSS sync complete | "
        f"new={total_added} | "
        f"duplicates={total_duplicates} | "
        f"sports/noise={total_noise} | "
        f"low_relevance={total_low_relevance} | "
        f"old_noise_removed={deleted_noise} | "
        f"images_upgraded={images_updated} | "
        f"framing_updated={framing_rows_updated}"
    )


    return total_added