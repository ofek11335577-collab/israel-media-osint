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
אתה אנליסט דסק מודיעין תקשורת. נתח את הכתבה הבאה:
כותרת: {title}
תוכן: {text}

החזר תשובה אך ורק בפורמט JSON תקני במבנה הבא (ללא Markdown מסביב):
{{
  "title_hebrew": "כותרת קולעת בעברית",
  "summary_hebrew": "תמצית הידיעה ב-2-3 משפטים בעברית ברורה",
  "category": "בחר אחד בלבד: צבאי וביטחוני | מדיני ודיפלומטי | כלכלה וסנקציות | פנים וחברה",
  "urgency": "בחר אחד בלבד: מתפרצת | שוטף | ניתוח עומק"
}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Processing error: {e}")
        return {
            "title_hebrew": title,
            "summary_hebrew": text[:200] if text else "לא ניתן לחלץ תקציר",
            "category": "שוטף",
            "urgency": "שוטף"
        }