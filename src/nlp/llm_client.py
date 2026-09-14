import os
import json
from google import genai
from google.genai import types

def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

def analyze_article(title: str, text: str) -> dict:
    client = get_client()
    
    prompt = f"""
אתה אנליסט דסק מודיעין תקשורת. נתח את הכתבה הבאה בצורה מדויקת:
כותרת: {title}
תוכן: {text}

החזר אך ורק פורמט JSON תקני ללא Markdown:
{{
  "title_hebrew": "כותרת קולעת ועניינית בעברית",
  "summary_hebrew": "תמצית הידיעה ב-2 משפטים בעברית ברורה ומקצועית",
  "category": "בחר אחד: צבאי וביטחוני | מדיני ודיפלומטי | כלכלה וסנקציות | פנים וחברה",
  "urgency": "בחר אחד: מתפרצת | שוטף | ניתוח עומק",
  "mentioned_countries": ["רשימת כל המדינות או הישויות המרכזיות שמוזכרות או שהכתבה נוגעת אליהן בעברית, למשל: ישראל, איראן, לבנון, ארה\"ב, סוריה, תימן, בריטניה"]
}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        data = json.loads(response.text)
        # הפיכת רשימת המדינות למחרוזת מופרדת בפסיקים
        countries = data.get("mentioned_countries", [])
        data["mentioned_countries_str"] = ", ".join(countries) if isinstance(countries, list) else str(countries)
        return data
    except Exception as e:
        print(f"LLM Processing error: {e}")
        return {
            "title_hebrew": title,
            "summary_hebrew": text[:180] if text else "תקציר אינו זמין",
            "category": "שוטף",
            "urgency": "שוטף",
            "mentioned_countries_str": "ישראל"
        }