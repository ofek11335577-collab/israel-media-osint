import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="דסק מודיעין תקשורת | OSINT IL",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Assistant', sans-serif !important;
        direction: rtl;
        text-align: right;
        background-color: #060913;
        color: #f1f5f9;
    }
    
    header[data-testid="stHeader"] { display: none !important; }

    /* עיצוב כרטיסים אחיד עם תמיכה מלאה ב-RTL */
    .card {
        background: rgba(15, 23, 42, 0.92);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
        direction: rtl;
        text-align: right;
    }
    
    .tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #1e293b;
        color: #93c5fd;
        margin-left: 5px;
    }
    
    .read-btn {
        color: #38bdf8 !important;
        font-weight: 700;
        text-decoration: none !important;
        margin-top: auto;
        padding-top: 10px;
        display: inline-block;
        direction: rtl;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# מאגר נתונים מלא ויציב
now_t = datetime.now()
FULL_ARTICLES_POOL = [
    {
        "url": "https://www.tehrantimes.com",
        "source_name": "Tehran Times",
        "country": "איראן",
        "title_hebrew": "איראן: חיל האוויר של משמרות המהפכה שילב מערכות מכ\"ם מתקדמות",
        "summary_hebrew": "טהראן דיווחה על שדרוג משמעותי במערכי ההתרעה האווירית להגנה על מתקנים אסטרטגיים מפני איומים אסימטריים.",
        "published_at": (now_t - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.reuters.com",
        "source_name": "Reuters",
        "country": "תימן",
        "title_hebrew": "תימן: הלחימה העצימה הביאה למאות הרוגים ולעקור רבים בשבוע האחרון",
        "summary_hebrew": "עימותים קשים מדווחים במספר מחוזות במדינה, תוך פגיעה קשה בתשתיות אזרחיות ובאוכלוסייה המקומית.",
        "published_at": (now_t - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.middleeasteye.net",
        "source_name": "Middle East Eye",
        "country": "לבנון",
        "title_hebrew": "כוחות צה\"ל ביצעו ירי ארטילרי באזור קו העימות בדרום לבנון",
        "summary_hebrew": "חילופי אש וירי ארטילרי נרשמו בסמוך לקו העימות בדרום לבנון בעקבות תנועות חשודות בגזרה.",
        "published_at": (now_t - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://wafa.ps",
        "source_name": "Wafa News",
        "country": "איו\"ש",
        "title_hebrew": "פעילות כוחות הביטחון באיו\"ש: מעצר מבוקשים וסריקות מבצעיות",
        "summary_hebrew": "כוחות צה\"ל פעלו הלילה בגזרות השונות לסיכול תשתיות טרור ולמעצר מבוקשים לחקירה.",
        "published_at": (now_t - timedelta(minutes=35)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://english.alarabiya.net",
        "source_name": "Al Arabiya",
        "country": "סעודיה",
        "title_hebrew": "יירוט נרחב של כטב\"מים עוינים מעל נתיבי השיט הבינלאומיים בים האדום",
        "summary_hebrew": "מערכי ההגנה של הקואליציה סיכלו מתקפה מכיוון תימן שנועדה לשבש את התנועה הימית המסחרית.",
        "published_at": (now_t - timedelta(minutes=50)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?w=1000",
        "sentiment": "צבאי וביטחוני"
    },
    {
        "url": "https://www.aljazeera.com",
        "source_name": "Al Jazeera",
        "country": "קטר",
        "title_hebrew": "מגעים דיפלומטיים דחופים בקהיר לגיבוש מתווה הפסקת אש",
        "summary_hebrew": "משלחות תיווך אזוריות מקיימות התייעצויות אינטנסיביות להסדרת מעבר סיוע הומניטרי.",
        "published_at": (now_t - timedelta(minutes=65)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1000",
        "sentiment": "מדיני ודיפלומטי"
    },
    {
        "url": "https://en.irna.ir",
        "source_name": "IRNA",
        "country": "איראן",
        "title_hebrew": "איראן: מדגישה את חשיבות שיתוף הפעולה האזורי לחיזוק הביטחון",
        "summary_hebrew": "בכירי משרד החוץ בטהראן קיימו פגישות עבודה עם נציגים דיפלומטיים זרים לקידום אינטרסים משותפים.",
        "published_at": (now_t - timedelta(minutes=80)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=1000",
        "sentiment": "מדיני ודיפלומטי"
    },
    {
        "url": "https://safa.ps",
        "source_name": "Safa Press",
        "country": "רצועת עזה",
        "title_hebrew": "רצועת עזה: עדכונים שוטפים מהשטח על פעילות צוותי החירום",
        "summary_hebrew": "דיווחים מקומיים מעדכנים על מאמצי שיקום תשתיות חיוניות במוקדים השונים ברצועה.",
        "published_at": (now_t - timedelta(minutes=95)).strftime("%Y-%m-%d %H:%M"),
        "image_url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=1000",
        "sentiment": "שוטף"
    }
]

df = pd.DataFrame(FULL_ARTICLES_POOL)

st.markdown("<h1 style='font-size: 2.2rem; font-weight: 900;'>🌐 דסק מודיעין תקשורת עולמי | OSINT IL</h1>", unsafe_allow_html=True)
st.caption("ניטור נרטיבים ודיווחים בזמן אמת ממאגרי התקשורת המובילים בעולם 24/7")
st.markdown("<hr style='border-color: rgba(56, 189, 248, 0.3);'>", unsafe_allow_html=True)

# סידור נכון של העמודות: כתבה ראשית גדולה בצד ימין, דיווחים חמים בצד שמאל
col_main, col_side = st.columns([7, 5])

with col_main:
    main_art = df.iloc[0]
    st.markdown(f"""
    <div class="card">
        <img src="{main_art['image_url']}" style="width:100%; height:300px; object-fit:cover; border-radius:6px; margin-bottom:12px;" />
        <div>
            <span class="tag">📰 {main_art['source_name']} ({main_art['country']})</span>
            <span class="tag">🕒 {main_art['published_at']}</span>
            <span class="tag" style="background:#0369a1;">{main_art['sentiment']}</span>
        </div>
        <h2 style="margin: 10px 0; font-size: 1.45rem;">{main_art['title_hebrew']}</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.5;">{main_art['summary_hebrew']}</p>
        <a class="read-btn" href="{main_art['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
    </div>
    """, unsafe_allow_html=True)

with col_side:
    st.markdown("### ⚡ דיווחים חמים נוספים", unsafe_allow_html=True)
    for idx, row in df.iloc[1:4].iterrows():
        st.markdown(f"""
        <div class="card" style="display: flex; gap: 12px; align-items: center; padding: 12px; margin-bottom: 12px;">
            <img src="{row['image_url']}" style="width: 95px; height: 75px; object-fit: cover; border-radius: 4px; flex-shrink: 0;" />
            <div style="width: 100%;">
                <div><span class="tag">{row['source_name']}</span><span style="font-size: 0.7rem; color: #64748b; margin-right: 6px;">{row['published_at']}</span></div>
                <div style="font-weight: 700; font-size: 0.9rem; margin: 6px 0; line-height: 1.3;">{row['title_hebrew']}</div>
                <a href="{row['url']}" target="_blank" style="color: #38bdf8; font-size: 0.75rem; text-decoration: none; font-weight: 700;">לקריאה ←</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

# גריד רחב של כל שאר הכתבות להשלמת האתר
st.markdown("<h3 style='margin: 35px 0 15px 0; font-weight: 800;'>📰 כל הדיווחים והכתבות מהזירות העולמיות</h3>", unsafe_allow_html=True)
grid_cols = st.columns(3)

for idx, row in df.iloc[4:].iterrows():
    with grid_cols[idx % 3]:
        st.markdown(f"""
        <div class="card" style="margin-bottom: 16px;">
            <img src="{row['image_url']}" style="width:100%; height:150px; object-fit:cover; border-radius:6px; margin-bottom:10px;" />
            <div>
                <span class="tag">{row['source_name']}</span>
                <span class="tag" style="background:#334155;">{row['country']}</span>
            </div>
            <div style="font-weight: 700; font-size: 0.95rem; margin: 8px 0; line-height: 1.4;">{row['title_hebrew']}</div>
            <p style="color: #94a3b8; font-size: 0.82rem; line-height: 1.4; margin-bottom: 8px;">{row['summary_hebrew']}</p>
            <div style="font-size: 0.7rem; color: #64748b; margin-bottom: 6px;">🕒 {row['published_at']}</div>
            <a class="read-btn" href="{row['url']}" target="_blank">לקריאת הדיווח המלא במקור ←</a>
        </div>
        """, unsafe_allow_html=True)