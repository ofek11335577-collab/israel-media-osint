import concurrent.futures
import email.utils
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from database import get_db_connection, utc_now_iso


# =========================================================
# CONFIG
# =========================================================

RSS_TIMEOUT = 6
ARTICLE_TIMEOUT = 4
MAX_ITEMS_PER_SOURCE = 22
MAX_FEED_WORKERS = 10
MAX_ARTICLE_ENRICHMENTS = 18
AUTO_ARTICLE_ENRICHMENTS = 3
ARTICLE_ENRICH_WORKERS = 6
MIN_RELEVANCE_SCORE = 34
MAX_FULL_CONTENT_CHARS = 8000


def google_news_feed(domain, days=2):
    query = quote_plus(f"site:{domain} when:{days}d")
    return (
        "https://news.google.com/rss/search?"
        f"q={query}&hl=en-US&gl=US&ceid=US:en"
    )


# Direct feeds are preferred. Some publishers block cloud IPs, so a Google News
# site-query fallback keeps the desk fresh without making a single publisher a
# hard dependency.
RSS_CHANNELS = [
    {
        "name": "Reuters World",
        "urls": [
            "https://www.reuters.com/arc/outboundfeeds/v1/output/rss/?outputType=xml",
            google_news_feed("reuters.com", 2),
        ],
        "source_type": "international",
        "source_country": "Global",
        "domestic_country": None,
    },
    {
        "name": "Associated Press",
        "urls": [google_news_feed("apnews.com", 2)],
        "source_type": "international",
        "source_country": "United States",
        "domestic_country": None,
    },
    {
        "name": "Al Jazeera English",
        "urls": ["https://www.aljazeera.com/xml/rss/all.xml"],
        "source_type": "international",
        "source_country": "Qatar",
        "domestic_country": None,
    },
    {
        "name": "BBC Middle East",
        "urls": ["https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"],
        "source_type": "international",
        "source_country": "United Kingdom",
        "domestic_country": None,
    },
    {
        "name": "The Guardian Middle East",
        "urls": ["https://www.theguardian.com/world/middleeast/rss"],
        "source_type": "international",
        "source_country": "United Kingdom",
        "domestic_country": None,
    },
    {
        "name": "France 24 Middle East",
        "urls": [
            "https://www.france24.com/en/middle-east/rss",
            google_news_feed("france24.com", 2),
        ],
        "source_type": "international",
        "source_country": "France",
        "domestic_country": None,
    },
    {
        "name": "Deutsche Welle",
        "urls": [google_news_feed("dw.com", 2)],
        "source_type": "international",
        "source_country": "Germany",
        "domestic_country": None,
    },
    {
        "name": "Middle East Eye",
        "urls": [google_news_feed("middleeasteye.net", 2)],
        "source_type": "regional",
        "source_country": "United Kingdom",
        "domestic_country": None,
    },
    {
        "name": "Asharq Al-Awsat English",
        "urls": [google_news_feed("english.aawsat.com", 2)],
        "source_type": "regional",
        "source_country": "Saudi Arabia",
        "domestic_country": None,
    },
    {
        "name": "Anadolu English",
        "urls": [google_news_feed("aa.com.tr", 2)],
        "source_type": "regional",
        "source_country": "Turkey",
        "domestic_country": None,
    },
    {
        "name": "Jerusalem Post",
        "urls": ["https://www.jpost.com/rss/rssfeedsheadlines.aspx"],
        "source_type": "domestic",
        "source_country": "Israel",
        "domestic_country": "Israel",
    },
    {
        "name": "Ynetnews",
        "urls": [
            "https://www.ynetnews.com/Integration/StoryRss3089.xml",
            google_news_feed("ynetnews.com", 2),
        ],
        "source_type": "domestic",
        "source_country": "Israel",
        "domestic_country": "Israel",
    },
    {
        "name": "The Times of Israel",
        "urls": [
            "https://www.timesofisrael.com/feed/",
            google_news_feed("timesofisrael.com", 2),
        ],
        "source_type": "domestic",
        "source_country": "Israel",
        "domestic_country": "Israel",
    },
    {
        "name": "Haaretz",
        "urls": [google_news_feed("haaretz.com", 2)],
        "source_type": "domestic",
        "source_country": "Israel",
        "domestic_country": "Israel",
    },
    {
        "name": "IRNA English",
        "urls": ["https://en.irna.ir/rss", google_news_feed("en.irna.ir", 2)],
        "source_type": "domestic",
        "source_country": "Iran",
        "domestic_country": "Iran",
    },
    {
        "name": "Mehr News English",
        "urls": ["https://en.mehrnews.com/rss", google_news_feed("en.mehrnews.com", 2)],
        "source_type": "domestic",
        "source_country": "Iran",
        "domestic_country": "Iran",
    },
    {
        "name": "Iran International",
        "urls": [google_news_feed("iranintl.com", 2)],
        "source_type": "regional",
        "source_country": "International",
        "domestic_country": "Iran",
    },
    {
        "name": "SANA English",
        "urls": ["https://www.sana.sy/en/syria/feed/", google_news_feed("sana.sy", 2)],
        "source_type": "domestic",
        "source_country": "Syria",
        "domestic_country": "Syria",
    },
    {
        "name": "Saudi Press Agency",
        "urls": [
            "https://www.spa.gov.sa/rss.xml",
            google_news_feed("spa.gov.sa", 3),
        ],
        "source_type": "domestic",
        "source_country": "Saudi Arabia",
        "domestic_country": "Saudi Arabia",
    },
    {
        "name": "Arab News",
        "urls": [google_news_feed("arabnews.com", 2)],
        "source_type": "domestic",
        "source_country": "Saudi Arabia",
        "domestic_country": "Saudi Arabia",
    },
    {
        "name": "Al Arabiya English",
        "urls": [google_news_feed("english.alarabiya.net", 2)],
        "source_type": "regional",
        "source_country": "UAE",
        "domestic_country": None,
    },
    {
        "name": "The National",
        "urls": [google_news_feed("thenationalnews.com", 2)],
        "source_type": "regional",
        "source_country": "UAE",
        "domestic_country": "UAE",
    },
    {
        "name": "WAFA English",
        "urls": [google_news_feed("english.wafa.ps", 2)],
        "source_type": "domestic",
        "source_country": "Palestinian Territories",
        "domestic_country": "Gaza & WB",
    },
    {
        "name": "Rudaw English",
        "urls": [google_news_feed("rudaw.net", 2)],
        "source_type": "domestic",
        "source_country": "Iraq",
        "domestic_country": "Iraq",
    },
]



# =========================================================
# TEXT / URL HELPERS
# =========================================================

def clean_html(raw_html):
    if not raw_html:
        return ""
    text = html.unescape(html.unescape(str(raw_html)))
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(url):
    if not url:
        return ""
    url = html.unescape(str(url).strip())
    try:
        parts = urlsplit(url)
        query_pairs = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")
            and k.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}
        ]
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                urlencode(query_pairs),
                "",
            )
        )
    except Exception:
        return url


def normalize_title(title):
    text = clean_html(title).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_rss_date(pub_date_elem):
    if pub_date_elem is not None and pub_date_elem.text:
        raw = pub_date_elem.text.strip()
        try:
            parsed = email.utils.parsedate_to_datetime(raw)
            if parsed:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except Exception:
            pass
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except Exception:
            pass
    return utc_now_iso()


# =========================================================
# NOISE FILTER
# =========================================================

SPORTS_TERMS = [
    "football", "footballer", "soccer", "premier league", "champions league",
    "europa league", "conference league", "world cup", "stadium closure",
    " var ", "var decision", "derby", "goalkeeper", "striker", "midfielder",
    "red card", "yellow card", "penalty shootout", "kick-off", "matchday",
    "fixture", "transfer window", "manchester united", "manchester city",
    "chelsea", "arsenal", "liverpool", "tottenham", "real madrid",
    "barcelona", "psg", "bayern", "mbappe", "vinicius", "ronaldo", "messi",
]

LIFESTYLE_NOISE = [
    "celebrity gossip", "fashion show", "recipe", "restaurant review",
    "movie review", "film review", "album review", "horoscope", "lottery",
    "travel tips", "beauty tips",
]


def is_noise_article(title, summary):
    text = f" {title or ''} {summary or ''} ".lower()
    return any(term in text for term in SPORTS_TERMS + LIFESTYLE_NOISE)


def cleanup_existing_noise(cursor):
    cursor.execute("SELECT id, title, summary FROM articles")
    ids = [
        (row["id"],)
        for row in cursor.fetchall()
        if is_noise_article(row["title"], row["summary"])
    ]
    if not ids:
        return 0
    cursor.executemany("DELETE FROM articles WHERE id = ?", ids)
    return len(ids)


# =========================================================
# COUNTRY + TOPIC
# =========================================================

COUNTRY_KEYWORDS = {
    "Iran": ["iran", "iranian", "tehran", "khamenei", "pezeshkian", "irgc", "revolutionary guard"],
    "Saudi Arabia": ["saudi", "riyadh", "jeddah", "bin salman", "mohammed bin salman"],
    "UAE": ["uae", "united arab emirates", "emirati", "dubai", "abu dhabi"],
    "Yemen": ["yemen", "yemeni", "houthi", "houthis", "sanaa", "sana'a"],
    "Syria": ["syria", "syrian", "damascus", "latakia"],
    "Iraq": ["iraq", "iraqi", "baghdad", "basra", "kurdistan"],
    "Gaza & WB": ["gaza", "palestin", "west bank", "ramallah", "jenin", "nablus"],
    "Israel": ["israel", "israeli", "jerusalem", "tel aviv", "idf", "netanyahu"],
    "Lebanon": ["lebanon", "lebanese", "beirut", "hezbollah"],
}

TARGET_COUNTRIES = set(COUNTRY_KEYWORDS)

TOPIC_KEYWORDS = {
    "Security / Military": [
        "military", "army", "missile", "ballistic", "air defense", "air defence",
        "airstrike", "air strike", "drone", "armed forces", "navy", "naval",
        "weapon", "weapons", "security forces", "irgc", "revolutionary guard",
        "militia", "border security", "explosion", "attack", "strike",
    ],
    "Politics / Regime": [
        "president", "prime minister", "government", "cabinet", "parliament",
        "minister", "election", "elections", "political", "leadership",
        "supreme leader", "resignation", "resigns", "appointed", "appointment",
        "dismissed", "opposition", "constitution", "coalition",
    ],
    "Strategic Economy": [
        "oil", "gas", "currency", "rial", "inflation", "sanction", "sanctions",
        "central bank", "trade", "exports", "imports", "energy", "economic crisis",
        "budget", "debt", "opec", "refinery", "production", "shipping", "pipeline",
    ],
    "Internal Stability": [
        "protest", "protests", "demonstration", "demonstrations", "riot", "riots",
        "unrest", "clashes", "arrest", "arrests", "detained", "ethnic", "minority",
        "separatist", "state of emergency", "crackdown", "strike action",
    ],
    "Nuclear / Cyber / Technology": [
        "nuclear", "uranium", "enrichment", "centrifuge", "iaea", "cyber",
        "cyberattack", "cyber attack", "hacking", "military technology", "satellite",
        "space program", "artificial intelligence", "ai system",
    ],
    "Diplomacy": [
        "diplomatic", "diplomacy", "foreign minister", "foreign ministry",
        "negotiation", "negotiations", "agreement", "summit", "delegation",
        "ambassador", "relations", "ceasefire", "truce", "mediator", "talks",
    ],
    "Humanitarian": [
        "humanitarian", "aid", "famine", "hospital", "displaced", "refugee",
        "food shortage", "water shortage", "civilian casualties", "rescue workers",
    ],
}

REGIONAL_KEYWORDS = [
    "iran", "israel", "gaza", "palestin", "west bank", "saudi", "yemen", "houthi",
    "syria", "iraq", "uae", "lebanon", "middle east", "red sea", "gulf", "hezbollah",
    "hamas", "irgc",
]

HIGH_IMPACT_KEYWORDS = [
    "war", "attack", "missile", "airstrike", "nuclear", "sanctions", "government crisis",
    "resignation", "protest", "unrest", "coup", "election", "ceasefire", "currency crisis",
    "oil production", "central bank", "irgc", "hostage", "pipeline", "shipping lane",
]


def classify_country(title, summary, domestic_country=None):
    text = f"{title or ''} {summary or ''}".lower()
    scored = []
    for country, keywords in COUNTRY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            scored.append((score, country))
    if scored:
        scored.sort(reverse=True)
        return scored[0][1]
    return domestic_country or "US & Global"


def classify_topic(title, summary, full_content=""):
    text = f"{title or ''} {summary or ''} {full_content or ''}".lower()
    scores = {
        topic: sum(1 for keyword in keywords if keyword in text)
        for topic, keywords in TOPIC_KEYWORDS.items()
    }
    best_topic = max(scores, key=scores.get)
    return best_topic if scores[best_topic] > 0 else "General"


def calculate_relevance_score(title, summary, country, topic, source_type):
    text = f"{title or ''} {summary or ''}".lower()
    score = 0

    if country in TARGET_COUNTRIES:
        score += 24
    if source_type == "domestic":
        score += 8

    score += {
        "Security / Military": 38,
        "Politics / Regime": 29,
        "Strategic Economy": 26,
        "Internal Stability": 31,
        "Nuclear / Cyber / Technology": 36,
        "Diplomacy": 24,
        "Humanitarian": 23,
        "General": 0,
    }.get(topic, 0)

    regional_hits = sum(1 for keyword in REGIONAL_KEYWORDS if keyword in text)
    impact_hits = sum(1 for keyword in HIGH_IMPACT_KEYWORDS if keyword in text)
    score += min(regional_hits * 7, 21)
    score += min(impact_hits * 5, 20)

    if country == "US & Global" and regional_hits == 0:
        score -= 32
    if country == "US & Global" and topic == "General":
        score -= 25

    return max(0, min(score, 100))


# =========================================================
# ISRAEL FRAMING SIGNALS
# =========================================================
# This classifier describes the framing present in the text. It does not infer
# a journalist's private political beliefs and it does not hard-code an outlet
# as supportive/critical. Source type only affects confidence slightly; the
# direction still has to come from words in the article itself.

ISRAEL_DIRECT_REFERENCES = [
    "israel", "israeli", "idf", "israel defense forces", "israel defence forces",
    "netanyahu", "jerusalem", "tel aviv", "zionist",
]

ISRAEL_LINKED_ENTITIES = [
    "gaza", "west bank", "hamas", "hezbollah", "settler", "settlers",
    "hostage", "hostages", "october 7", "7 october", "golan heights",
]

ISRAEL_LINKED_ACTIONS = [
    "war", "strike", "airstrike", "attack", "bombing", "bombardment", "ceasefire",
    "raid", "military", "rocket", "missile", "killed", "wounded", "displaced",
    "occupation", "blockade", "siege", "annexation", "border", "hostage",
]

CRITICAL_PHRASES = {
    "ethnic cleansing": 8,
    "genocide": 7,
    "genocidal": 7,
    "apartheid": 7,
    "collective punishment": 7,
    "war crimes": 6,
    "war crime": 6,
    "israeli aggression": 6,
    "israeli atrocities": 7,
    "israeli crimes": 6,
    "israeli massacre": 7,
    "massacre by israel": 7,
    "brutal occupation": 6,
    "illegal occupation": 5,
    "occupation forces": 5,
    "deliberately targeting civilians": 7,
    "deliberate attack on civilians": 7,
    "indiscriminate bombing": 6,
    "indiscriminate attacks": 6,
    "starvation as a weapon": 7,
    "forced displacement": 5,
    "settler violence": 5,
    "illegal settlements": 5,
    "siege of gaza": 5,
    "blockade of gaza": 5,
    "war on gaza": 4,
    "far-right israeli": 4,
    "israeli-hit": 4,
    "israeli strike killed": 5,
    "israeli strikes killed": 5,
    "israeli forces killed": 5,
    "israeli forces shot": 5,
    "israeli bombardment": 5,
    "israeli siege": 5,
}

SUPPORTIVE_PHRASES = {
    "right to defend itself": 8,
    "right to self-defense": 8,
    "right to self defence": 8,
    "israel's right to exist": 8,
    "israel has the right to exist": 8,
    "legitimate security concerns": 7,
    "israel's security needs": 6,
    "israeli security needs": 6,
    "defending israel": 6,
    "protect israeli civilians": 7,
    "protecting israeli civilians": 7,
    "terrorist attack on israel": 6,
    "terror attack on israel": 6,
    "terrorist attack against israel": 6,
    "rocket fire on israel": 5,
    "missile attack on israel": 5,
    "missiles fired at israel": 5,
    "rockets fired at israel": 5,
    "hamas attack on israel": 5,
    "hamas-led attack": 5,
    "october 7 attack": 5,
    "7 october attack": 5,
    "hostages held by hamas": 5,
    "hostages kidnapped": 5,
    "hostages rescued": 5,
    "rescued hostages": 5,
    "intercepted missiles": 4,
    "intercepted rockets": 4,
    "thwarted attack": 4,
    "targeted militants": 3,
    "hamas militants": 3,
}

CRITICAL_CONTEXT = {
    "occupation": 2,
    "siege": 2,
    "blockade": 2,
    "starvation": 3,
    "displacement": 2,
    "displaced": 2,
    "settler violence": 3,
    "civilian deaths": 3,
    "civilians killed": 3,
    "killed civilians": 3,
    "children killed": 3,
    "human rights abuses": 3,
    "annexation": 2,
    "unlawful": 2,
    "indiscriminate": 3,
    "bombardment": 2,
    "destroyed": 1,
    "devastation": 2,
    "aid restrictions": 2,
    "aid blocked": 3,
    "killed": 1,
}

SUPPORTIVE_CONTEXT = {
    "terrorist": 3,
    "terror attack": 4,
    "security threat": 3,
    "self-defense": 5,
    "self defence": 5,
    "hostage": 2,
    "hostages": 2,
    "rocket fire": 3,
    "missile fire": 3,
    "intercepted": 3,
    "militants": 2,
    "armed attackers": 3,
    "hamas fighters": 2,
    "october 7": 2,
    "7 october": 2,
}

ATTRIBUTION_MARKERS = [
    "accused", "accuses", "according to", "alleged", "alleges", "claimed", "claims",
    "rights group says", "un says", "officials say", "ministry says", "report says",
    "prosecutors say", "critics say", "activists say",
]

REJECTION_MARKERS = [
    "rejects", "rejected", "denies", "denied", "disputes", "disputed",
    "dismisses", "dismissed", "calls the allegation false", "says the allegation is false",
]


def _is_israel_related(text):
    if any(ref in text for ref in ISRAEL_DIRECT_REFERENCES):
        return True

    entity_hit = any(entity in text for entity in ISRAEL_LINKED_ENTITIES)
    action_hit = any(action in text for action in ISRAEL_LINKED_ACTIONS)
    return entity_hit and action_hit


def _weighted_phrase_score(text, weighted_phrases):
    return sum(weight for phrase, weight in weighted_phrases.items() if phrase in text)


def _reference_windows(text, radius=220):
    windows = []
    refs = ISRAEL_DIRECT_REFERENCES + ISRAEL_LINKED_ENTITIES
    for ref in refs:
        start = 0
        while True:
            idx = text.find(ref, start)
            if idx == -1:
                break
            windows.append(text[max(0, idx - radius): min(len(text), idx + len(ref) + radius)])
            start = idx + len(ref)
    return windows


def _context_score(windows, weighted_terms):
    total = 0
    for window in windows:
        total += sum(weight for term, weight in weighted_terms.items() if term in window)
    return total


def _discount_attributed_or_rejected(text, weighted_phrases):
    discount = 0
    for phrase, weight in weighted_phrases.items():
        search_from = 0
        while True:
            idx = text.find(phrase, search_from)
            if idx == -1:
                break
            context = text[max(0, idx - 120): min(len(text), idx + len(phrase) + 100)]
            if any(marker in context for marker in REJECTION_MARKERS):
                # Explicit rejection/denial should cancel both the normal
                # phrase score and the extra headline weight when applicable.
                discount += weight * 2
            elif any(marker in context for marker in ATTRIBUTION_MARKERS):
                discount += max(1, weight // 3)
            search_from = idx + len(phrase)
    return discount


def classify_israel_framing(
    title,
    summary,
    full_content="",
    source_name="",
    source_type="international",
    source_country="",
):
    text = f"{title or ''}. {summary or ''}. {full_content or ''}".lower()
    title_text = (title or "").lower()

    if not _is_israel_related(text):
        return "not_mentioned", ""

    critical = _weighted_phrase_score(text, CRITICAL_PHRASES)
    supportive = _weighted_phrase_score(text, SUPPORTIVE_PHRASES)

    # Headline framing is editorially prominent, so explicit signals in a
    # headline count twice.
    critical += _weighted_phrase_score(title_text, CRITICAL_PHRASES)
    supportive += _weighted_phrase_score(title_text, SUPPORTIVE_PHRASES)

    windows = _reference_windows(text)
    critical += _context_score(windows, CRITICAL_CONTEXT)
    supportive += _context_score(windows, SUPPORTIVE_CONTEXT)

    critical = max(0, critical - _discount_attributed_or_rejected(text, CRITICAL_PHRASES))
    supportive = max(0, supportive - _discount_attributed_or_rejected(text, SUPPORTIVE_PHRASES))

    # Source type is used only as a confidence adjustment. We deliberately do
    # not say "outlet X is automatically critical/supportive" because an outlet
    # can publish straight news, analysis, interviews and opinion pieces.
    threshold = 5
    if source_type == "domestic" and max(critical, supportive) >= 4:
        threshold = 4

    critical_hits = [p for p in CRITICAL_PHRASES if p in text][:5]
    supportive_hits = [p for p in SUPPORTIVE_PHRASES if p in text][:5]

    if critical >= threshold and critical >= supportive + 2:
        evidence = ", ".join(critical_hits) or "critical wording around Israel-linked entities"
        return "critical", evidence

    if supportive >= threshold and supportive >= critical + 2:
        evidence = ", ".join(supportive_hits) or "security/supportive wording around Israel-linked entities"
        return "supportive", evidence

    return "neutral", "mixed or primarily descriptive wording"


# =========================================================
# IMAGE HELPERS
# =========================================================
# Important: image URLs are never rewritten to a guessed width anymore. Some
# news CDNs sign their URLs, and changing ?w=... can break an otherwise valid
# image. We prefer the largest candidate supplied by the feed and replace it
# with the publisher's og:image during enrichment.


def image_candidate_score(url, width=None, height=None):
    score = 0
    try:
        if width:
            score += min(int(width), 2400)
        if height:
            score += min(int(height), 1600) // 2
    except Exception:
        pass

    low = (url or "").lower()
    for marker in [
        "thumbnail", "thumb", "tiny", "small", "120x", "150x", "180x",
        "200x", "240x", "300x", "320x", "400x",
    ]:
        if marker in low:
            score -= 800
    for marker in ["1200", "1600", "1920", "2048", "large", "original", "master"]:
        if marker in low:
            score += 350
    return score


def _clean_image_url(url, base_url=""):
    url = html.unescape((url or "").strip())
    if not url or url.startswith(("data:", "blob:")):
        return ""
    if base_url:
        url = urljoin(base_url, url)
    return url if url.startswith(("http://", "https://")) else ""


def extract_feed_image(item, raw_description, used_feed_url=""):
    candidates = []

    # Google News RSS usually does not expose the publisher's real article
    # image. Avoid treating logos/thumbnails from that wrapper as final images.
    if "news.google.com" in (used_feed_url or ""):
        return None

    for media in item.findall("{http://search.yahoo.com/mrss/}content"):
        url = _clean_image_url(media.get("url"))
        if url:
            candidates.append((image_candidate_score(url, media.get("width"), media.get("height")), url))

    for media in item.findall("{http://search.yahoo.com/mrss/}thumbnail"):
        url = _clean_image_url(media.get("url"))
        if url:
            candidates.append((image_candidate_score(url, media.get("width"), media.get("height")), url))

    enclosure = item.find("enclosure")
    if enclosure is not None:
        url = _clean_image_url(enclosure.get("url"))
        if url and (enclosure.get("type") or "").lower().startswith("image"):
            candidates.append((image_candidate_score(url), url))

    if raw_description:
        for url in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', raw_description, flags=re.I):
            url = _clean_image_url(url)
            if url:
                candidates.append((image_candidate_score(url), url))

        for srcset in re.findall(r'srcset=["\']([^"\']+)["\']', raw_description, flags=re.I):
            for piece in srcset.split(","):
                bits = piece.strip().split()
                if not bits:
                    continue
                url = _clean_image_url(bits[0])
                if not url:
                    continue
                width = None
                if len(bits) > 1 and bits[1].endswith("w"):
                    try:
                        width = int(bits[1][:-1])
                    except Exception:
                        pass
                candidates.append((image_candidate_score(url, width, None), url))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def image_looks_low_quality(image_url):
    if not image_url:
        return True

    low = image_url.lower()
    if any(marker in low for marker in [
        "thumbnail", "thumb", "tiny", "small", "120x", "150x", "180x",
        "200x", "240x", "300x", "320x", "400x",
    ]):
        return True

    try:
        query = dict(parse_qsl(urlsplit(image_url).query))
        for key in ["w", "width", "imgWidth", "imageWidth"]:
            if key in query:
                try:
                    if int(query[key]) < 700:
                        return True
                except Exception:
                    pass
    except Exception:
        pass

    return False


# =========================================================
# DUPLICATION
# =========================================================

def article_exists(cursor, url, title):
    cursor.execute("SELECT id FROM articles WHERE url = ? LIMIT 1", (url,))
    if cursor.fetchone():
        return True

    normalized = normalize_title(title)
    if not normalized:
        return False

    cursor.execute("SELECT title FROM articles ORDER BY id DESC LIMIT 350")
    for row in cursor.fetchall():
        existing = normalize_title(row["title"])
        if not existing:
            continue
        if existing == normalized:
            return True
        if len(existing) >= 40 and len(normalized) >= 40:
            if SequenceMatcher(None, existing, normalized).ratio() >= 0.965:
                return True
    return False


# =========================================================
# FEED FETCHING
# =========================================================

def _download_url(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=RSS_TIMEOUT) as response:
        return response.read()


def fetch_feed_xml(source):
    errors = []
    for url in source["urls"]:
        try:
            return source, _download_url(url), url, None
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    return source, None, None, " | ".join(errors)


# =========================================================
# ARTICLE PAGE ENRICHMENT
# =========================================================

def _best_page_image(soup, article_url):
    # Publisher og:image is normally the canonical high-resolution card image.
    selectors = [
        ('meta[property="og:image:secure_url"]', "content"),
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image:src"]', "content"),
        ('meta[name="twitter:image"]', "content"),
    ]

    for selector, attr in selectors:
        for node in soup.select(selector):
            value = _clean_image_url(node.get(attr), article_url)
            if value:
                return value

    # Fallback: choose the largest-looking image inside the article itself.
    candidates = []
    article = soup.find("article") or soup.find("main")
    if article:
        for img in article.find_all("img")[:20]:
            srcset = img.get("srcset") or ""
            if srcset:
                for piece in srcset.split(","):
                    bits = piece.strip().split()
                    if not bits:
                        continue
                    value = _clean_image_url(bits[0], article_url)
                    width = None
                    if len(bits) > 1 and bits[1].endswith("w"):
                        try:
                            width = int(bits[1][:-1])
                        except Exception:
                            pass
                    if value:
                        candidates.append((image_candidate_score(value, width, None), value))

            value = _clean_image_url(img.get("src") or img.get("data-src"), article_url)
            if value:
                candidates.append((image_candidate_score(value, img.get("width"), img.get("height")), value))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _extract_article_text(soup):
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()

    container = soup.find("article") or soup.find("main")
    if container is None:
        container = soup.body
    if container is None:
        return ""

    paragraphs = []
    seen = set()
    for p in container.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip()
        if len(text) < 45 or text in seen:
            continue
        seen.add(text)
        paragraphs.append(text)
        if sum(len(x) for x in paragraphs) >= MAX_FULL_CONTENT_CHARS:
            break

    return "\n\n".join(paragraphs)[:MAX_FULL_CONTENT_CHARS].strip()


def extract_article_enrichment(article):
    article_id = article["id"]
    article_url = article["url"]

    try:
        req = urllib.request.Request(
            article_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=ARTICLE_TIMEOUT) as response:
            page = response.read(1_500_000)
            final_url = response.geturl()

        soup = BeautifulSoup(page, "html.parser")
        image_url = _best_page_image(soup, final_url or article_url)
        full_content = _extract_article_text(soup)

        return {
            "id": article_id,
            "image_url": image_url,
            "full_content": full_content,
        }
    except Exception:
        return {
            "id": article_id,
            "image_url": None,
            "full_content": "",
        }


def enrich_recent_articles(conn, limit=MAX_ARTICLE_ENRICHMENTS):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, url, title, summary, full_content, image_url,
               source_name, source_type, source_country
        FROM articles
        WHERE url IS NOT NULL AND url != ''
        ORDER BY published_at DESC, id DESC
        LIMIT 36
        """
    )
    rows = [dict(row) for row in cursor.fetchall()]
    if not rows:
        return 0

    def enrichment_priority(row):
        missing_image = not (row.get("image_url") or "").strip()
        low_image = image_looks_low_quality(row.get("image_url"))
        short_body = len((row.get("full_content") or "").strip()) < 700

        if missing_image:
            return 0
        if low_image:
            return 1
        if short_body:
            return 2
        return 3

    rows.sort(key=enrichment_priority)
    rows = rows[:int(limit)]

    results = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(ARTICLE_ENRICH_WORKERS, len(rows))
    ) as executor:
        futures = [executor.submit(extract_article_enrichment, row) for row in rows]
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                pass

    updated = 0
    now = utc_now_iso()
    for result in results:
        cursor.execute(
            """
            SELECT title, summary, full_content, image_url,
                   source_name, source_type, source_country
            FROM articles WHERE id = ?
            """,
            (result["id"],),
        )
        existing = cursor.fetchone()
        if existing is None:
            continue

        new_content = result["full_content"] or existing["full_content"] or existing["summary"] or ""
        # A page-level og:image wins over the feed thumbnail. If extraction
        # fails, keep the existing feed image.
        new_image = result["image_url"] or existing["image_url"]

        framing, evidence = classify_israel_framing(
            existing["title"],
            existing["summary"],
            new_content,
            existing["source_name"],
            existing["source_type"] or "international",
            existing["source_country"] or "",
        )
        topic = classify_topic(existing["title"], existing["summary"], new_content)

        cursor.execute(
            """
            UPDATE articles
            SET full_content = ?,
                image_url = ?,
                topic = ?,
                sentiment = ?,
                israel_related = ?,
                israel_framing = ?,
                analyst_name = ?,
                framing_evidence = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_content,
                new_image,
                topic,
                topic,
                0 if framing == "not_mentioned" else 1,
                framing,
                framing,
                evidence,
                now,
                result["id"],
            ),
        )
        updated += 1

    conn.commit()
    return updated


# =========================================================
# BACKFILL CLASSIFICATION
# =========================================================

def backfill_classification(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, summary, full_content, country, source_type, source_name, source_country
        FROM articles
        ORDER BY published_at DESC, id DESC
        LIMIT 500
        """
    )

    updates = []
    for row in cursor.fetchall():
        topic = classify_topic(row["title"], row["summary"], row["full_content"])
        framing, evidence = classify_israel_framing(
            row["title"],
            row["summary"],
            row["full_content"],
            row["source_name"],
            row["source_type"] or "international",
            row["source_country"] or "",
        )
        source_type = row["source_type"] or "international"
        relevance = calculate_relevance_score(
            row["title"], row["summary"], row["country"] or "US & Global", topic, source_type
        )
        updates.append(
            (
                topic,
                topic,
                relevance,
                relevance,
                0 if framing == "not_mentioned" else 1,
                framing,
                framing,
                evidence,
                utc_now_iso(),
                row["id"],
            )
        )

    cursor.executemany(
        """
        UPDATE articles
        SET topic = ?,
            sentiment = ?,
            relevance_score = ?,
            priority = ?,
            israel_related = ?,
            israel_framing = ?,
            analyst_name = ?,
            framing_evidence = ?,
            updated_at = ?
        WHERE id = ?
        """,
        updates,
    )
    conn.commit()
    return len(updates)


# =========================================================
# MAIN INGESTION
# =========================================================

def fetch_live_web_articles(enrich=False):
    """
    Fast path (enrich=False): download RSS feeds concurrently, filter/deduplicate,
    classify, and store. No article pages are opened, so app startup stays fast.

    Manual/deeper path (enrich=True): after the fast ingest, enrich a bounded
    number of recent articles with original-page image/full text and reclassify.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    deleted_noise = cleanup_existing_noise(cursor)
    conn.commit()

    total_added = 0
    total_duplicates = 0
    total_noise = 0
    total_low_relevance = 0
    source_success = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_FEED_WORKERS) as executor:
        futures = [executor.submit(fetch_feed_xml, source) for source in RSS_CHANNELS]
        feed_results = [future.result() for future in futures]

    for source, xml_data, used_url, feed_error in feed_results:
        if feed_error is not None or not xml_data:
            print(f"Feed error ({source['name']}): {feed_error}")
            continue

        try:
            root = ET.fromstring(xml_data)
        except Exception as exc:
            print(f"XML error ({source['name']}): {exc}")
            continue

        source_success += 1
        items = root.findall(".//item")

        for item in items[:MAX_ITEMS_PER_SOURCE]:
            title_elem = item.find("title")
            link_elem = item.find("link")
            date_elem = item.find("pubDate")
            if date_elem is None:
                date_elem = item.find("{http://purl.org/dc/elements/1.1/}date")
            desc_elem = item.find("description")

            title = clean_html(title_elem.text if title_elem is not None else "")
            raw_url = (link_elem.text or "").strip() if link_elem is not None else ""
            if not title or not raw_url:
                continue

            url = normalize_url(raw_url)
            raw_description = desc_elem.text if desc_elem is not None and desc_elem.text else ""
            summary = clean_html(raw_description) or title
            summary = summary[:650]

            if is_noise_article(title, summary):
                total_noise += 1
                continue

            if article_exists(cursor, url, title):
                total_duplicates += 1
                continue

            country = classify_country(title, summary, source.get("domestic_country"))
            topic = classify_topic(title, summary)
            relevance = calculate_relevance_score(
                title,
                summary,
                country,
                topic,
                source["source_type"],
            )

            if relevance < MIN_RELEVANCE_SCORE:
                total_low_relevance += 1
                continue

            framing, framing_evidence = classify_israel_framing(
                title,
                summary,
                "",
                source["name"],
                source["source_type"],
                source["source_country"],
            )
            image_url = extract_feed_image(item, raw_description, used_url or "")
            if image_looks_low_quality(image_url):
                image_url = None
            published_at = parse_rss_date(date_elem)
            now = utc_now_iso()

            cursor.execute(
                """
                INSERT OR IGNORE INTO articles (
                    url,
                    source_name,
                    source_type,
                    source_country,
                    country,
                    title,
                    summary,
                    full_content,
                    analyst_name,
                    published_at,
                    image_url,
                    sentiment,
                    priority,
                    topic,
                    relevance_score,
                    israel_related,
                    israel_framing,
                    framing_evidence,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    url,
                    source["name"],
                    source["source_type"],
                    source["source_country"],
                    country,
                    title,
                    summary,
                    summary,
                    framing,
                    published_at,
                    image_url,
                    topic,
                    relevance,
                    topic,
                    relevance,
                    0 if framing == "not_mentioned" else 1,
                    framing,
                    framing_evidence,
                    now,
                    now,
                ),
            )

            if cursor.rowcount > 0:
                total_added += 1

        conn.commit()

    # Manual sync enriches a larger recent batch. Automatic five-minute sync
    # enriches only three newest rows concurrently, keeping startup bounded
    # while still giving the newest lead stories a real publisher image.
    if enrich:
        enriched = enrich_recent_articles(conn, limit=MAX_ARTICLE_ENRICHMENTS)
    elif total_added > 0:
        enriched = enrich_recent_articles(conn, limit=AUTO_ARTICLE_ENRICHMENTS)
    else:
        enriched = 0

    reclassified = backfill_classification(conn)

    print(
        "RSS sync complete | "
        f"sources_ok={source_success}/{len(RSS_CHANNELS)} | "
        f"new={total_added} | duplicates={total_duplicates} | "
        f"sports_noise={total_noise} | low_relevance={total_low_relevance} | "
        f"old_noise_removed={deleted_noise} | enriched={enriched} | "
        f"reclassified={reclassified}"
    )

    return total_added
