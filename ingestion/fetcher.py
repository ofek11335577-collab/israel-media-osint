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
MAX_ARTICLE_ENRICHMENTS = 12
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
            "https://www.france24.com/en/tag/middle-east/rss",
        ],
        "source_type": "international",
        "source_country": "France",
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
        "name": "IRNA English",
        "urls": ["https://en.irna.ir/rss"],
        "source_type": "domestic",
        "source_country": "Iran",
        "domestic_country": "Iran",
    },
    {
        "name": "Mehr News English",
        "urls": ["https://en.mehrnews.com/rss"],
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
        "urls": ["https://www.sana.sy/en/syria/feed/"],
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
        "name": "Haaretz",
        "urls": [google_news_feed("haaretz.com", 2)],
        "source_type": "domestic",
        "source_country": "Israel",
        "domestic_country": "Israel",
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
# The classifier describes textual framing signals in the article. It does not
# assign a fixed political stance to an outlet and does not infer a journalist's
# private beliefs from the publisher alone.

ISRAEL_REFERENCES = [
    "israel", "israeli", "idf", "israel defense forces", "israel defence forces",
    "netanyahu", "jerusalem", "tel aviv", "zionist",
]

CRITICAL_PHRASES = {
    "ethnic cleansing": 7,
    "genocide": 6,
    "genocidal": 6,
    "apartheid": 6,
    "collective punishment": 6,
    "war crimes": 5,
    "war crime": 5,
    "israeli aggression": 5,
    "israeli atrocities": 6,
    "israeli crimes": 5,
    "israeli massacre": 6,
    "massacre by israel": 6,
    "brutal occupation": 5,
    "illegal occupation": 4,
    "occupation forces": 4,
    "deliberately targeting civilians": 6,
    "deliberate attack on civilians": 6,
    "indiscriminate bombing": 5,
    "indiscriminate attacks": 5,
    "starvation as a weapon": 6,
    "forced displacement": 4,
    "settler violence": 4,
    "illegal settlements": 4,
    "siege of gaza": 4,
    "blockade of gaza": 4,
    "annexation": 3,
    "far-right israeli": 3,
}

SUPPORTIVE_PHRASES = {
    "right to defend itself": 7,
    "right to self-defense": 7,
    "right to self defence": 7,
    "israel's right to exist": 7,
    "israel has the right to exist": 7,
    "legitimate security concerns": 6,
    "israel's security needs": 5,
    "israeli security needs": 5,
    "defending israel": 5,
    "protect israeli civilians": 6,
    "protecting israeli civilians": 6,
    "terrorist attack on israel": 5,
    "terror attack on israel": 5,
    "terrorist attack against israel": 5,
    "rocket fire on israel": 4,
    "missile attack on israel": 4,
    "hamas-led attack": 4,
    "october 7 attack": 4,
    "hostages rescued": 4,
    "rescued hostages": 4,
    "hostage rescue": 4,
    "intercepted missiles": 3,
    "intercepted rockets": 3,
    "thwarted attack": 4,
}

CRITICAL_CONTEXT = {
    "occupation": 2,
    "siege": 2,
    "blockade": 2,
    "starvation": 3,
    "displacement": 2,
    "settler violence": 3,
    "civilian deaths": 2,
    "killed civilians": 3,
    "human rights abuses": 3,
    "annexation": 2,
    "unlawful": 2,
    "indiscriminate": 3,
}

SUPPORTIVE_CONTEXT = {
    "terrorist": 2,
    "terror attack": 3,
    "security threat": 3,
    "self-defense": 4,
    "self defence": 4,
    "hostage": 2,
    "hostages": 2,
    "rocket fire": 2,
    "missile fire": 2,
    "intercepted": 2,
    "militants": 1,
    "armed attackers": 2,
}

ATTRIBUTION_MARKERS = [
    "accused", "accuses", "according to", "alleged", "alleges", "claimed", "claims",
    "rights group says", "un says", "officials say", "ministry says", "report says",
]

REJECTION_MARKERS = [
    "rejects", "rejected", "denies", "denied", "disputes", "disputed", "dismisses", "dismissed",
]


def _weighted_phrase_score(text, weighted_phrases):
    return sum(weight for phrase, weight in weighted_phrases.items() if phrase in text)


def _reference_windows(text, radius=180):
    windows = []
    for ref in ISRAEL_REFERENCES:
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
        idx = text.find(phrase)
        if idx == -1:
            continue
        context = text[max(0, idx - 100): min(len(text), idx + len(phrase) + 80)]
        if any(marker in context for marker in REJECTION_MARKERS):
            discount += weight
        elif any(marker in context for marker in ATTRIBUTION_MARKERS):
            discount += max(1, weight // 2)
    return discount


def classify_israel_framing(title, summary, full_content=""):
    text = f"{title or ''}. {summary or ''}. {full_content or ''}".lower()
    title_text = (title or "").lower()

    if not any(ref in text for ref in ISRAEL_REFERENCES):
        return "not_mentioned", ""

    critical = _weighted_phrase_score(text, CRITICAL_PHRASES)
    supportive = _weighted_phrase_score(text, SUPPORTIVE_PHRASES)

    # Headline framing has extra weight because it is editorially prominent.
    critical += _weighted_phrase_score(title_text, CRITICAL_PHRASES)
    supportive += _weighted_phrase_score(title_text, SUPPORTIVE_PHRASES)

    windows = _reference_windows(text)
    critical += _context_score(windows, CRITICAL_CONTEXT)
    supportive += _context_score(windows, SUPPORTIVE_CONTEXT)

    critical = max(0, critical - _discount_attributed_or_rejected(text, CRITICAL_PHRASES))
    supportive = max(0, supportive - _discount_attributed_or_rejected(text, SUPPORTIVE_PHRASES))

    # Provide auditable evidence rather than relying on an outlet-level prior.
    critical_hits = [p for p in CRITICAL_PHRASES if p in text][:4]
    supportive_hits = [p for p in SUPPORTIVE_PHRASES if p in text][:4]

    if critical >= 4 and critical >= supportive + 2:
        evidence = ", ".join(critical_hits) or "critical framing terms near Israel references"
        return "critical", evidence

    if supportive >= 4 and supportive >= critical + 2:
        evidence = ", ".join(supportive_hits) or "security/supportive framing terms near Israel references"
        return "supportive", evidence

    return "neutral", "mixed or primarily descriptive wording"


# =========================================================
# IMAGE HELPERS
# =========================================================

def image_candidate_score(url, width=None, height=None):
    score = 0
    try:
        if width:
            score += min(int(width), 2200)
        if height:
            score += min(int(height), 1400) // 2
    except Exception:
        pass

    low = (url or "").lower()
    for marker in ["thumbnail", "thumb", "small", "tiny", "120x", "150x", "200x", "240x", "300x", "320x"]:
        if marker in low:
            score -= 700
    for marker in ["1200", "1600", "1920", "2048", "large", "original", "master"]:
        if marker in low:
            score += 450
    return score


def upgrade_common_image_url(image_url):
    if not image_url:
        return image_url
    try:
        parts = urlsplit(image_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        changed = False
        for key in ["w", "width", "imgWidth", "imageWidth"]:
            if key in query:
                try:
                    if int(query[key]) < 1200:
                        query[key] = "1200"
                        changed = True
                except Exception:
                    pass
        if changed:
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    except Exception:
        pass
    return image_url


def extract_feed_image(item, raw_description):
    candidates = []

    for media in item.findall("{http://search.yahoo.com/mrss/}content"):
        if media.get("url"):
            candidates.append((media.get("url"), media.get("width"), media.get("height")))

    for media in item.findall("{http://search.yahoo.com/mrss/}thumbnail"):
        if media.get("url"):
            candidates.append((media.get("url"), media.get("width"), media.get("height")))

    enclosure = item.find("enclosure")
    if enclosure is not None and enclosure.get("url"):
        candidates.append((enclosure.get("url"), None, None))

    if raw_description:
        for url in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', raw_description, flags=re.I):
            candidates.append((url, None, None))
        for srcset in re.findall(r'srcset=["\']([^"\']+)["\']', raw_description, flags=re.I):
            for piece in srcset.split(","):
                bits = piece.strip().split()
                if not bits:
                    continue
                width = None
                if len(bits) > 1 and bits[1].endswith("w"):
                    try:
                        width = int(bits[1][:-1])
                    except Exception:
                        pass
                candidates.append((bits[0], width, None))

    cleaned = []
    for url, width, height in candidates:
        url = upgrade_common_image_url(html.unescape((url or "").strip()))
        if url.startswith(("http://", "https://")):
            cleaned.append((image_candidate_score(url, width, height), url))

    return max(cleaned)[1] if cleaned else None


def image_looks_low_quality(image_url):
    if not image_url:
        return True
    low = image_url.lower()
    if any(marker in low for marker in ["thumbnail", "thumb", "tiny", "small", "120x", "150x", "180x", "200x", "240x", "300x", "320x"]):
        return True
    try:
        query = dict(parse_qsl(urlsplit(image_url).query))
        for key in ["w", "width", "imgWidth", "imageWidth"]:
            if key in query and int(query[key]) < 700:
                return True
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
    candidates = []

    selectors = [
        ('meta[property="og:image:secure_url"]', "content"),
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('meta[name="twitter:image:src"]', "content"),
    ]

    for selector, attr in selectors:
        for node in soup.select(selector):
            value = node.get(attr)
            if value:
                value = urljoin(article_url, html.unescape(value.strip()))
                candidates.append((image_candidate_score(value), value))

    article = soup.find("article") or soup.find("main")
    if article:
        for img in article.find_all("img")[:12]:
            value = img.get("src") or img.get("data-src")
            if not value:
                continue
            value = urljoin(article_url, html.unescape(value.strip()))
            width = img.get("width")
            height = img.get("height")
            candidates.append((image_candidate_score(value, width, height), value))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return upgrade_common_image_url(candidates[0][1])


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
        SELECT id, url, title, summary, full_content, image_url
        FROM articles
        WHERE url IS NOT NULL AND url != ''
          AND (
              image_url IS NULL OR image_url = ''
              OR full_content IS NULL OR LENGTH(full_content) < 700
          )
        ORDER BY published_at DESC, id DESC
        LIMIT ?
        """,
        (int(limit),),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    if not rows:
        return 0

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
            "SELECT title, summary, full_content, image_url FROM articles WHERE id = ?",
            (result["id"],),
        )
        existing = cursor.fetchone()
        if existing is None:
            continue

        new_content = result["full_content"] or existing["full_content"] or existing["summary"] or ""
        new_image = result["image_url"] or existing["image_url"]

        framing, evidence = classify_israel_framing(
            existing["title"],
            existing["summary"],
            new_content,
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
        SELECT id, title, summary, full_content, country, source_type
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

            framing, framing_evidence = classify_israel_framing(title, summary)
            image_url = extract_feed_image(item, raw_description)
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

    enriched = 0
    if enrich:
        enriched = enrich_recent_articles(conn)

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
