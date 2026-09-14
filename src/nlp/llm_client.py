import json
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """אתה אנליסט OSINT מומחה למודיעין תקשורת. 
נתח את הכתבה הבאה:

כותרת מקורית: {title}
תוכן מקורי: {content}

החזר אך ורק אובייקט JSON תקין (ללא markdown וללא תגיות קוד) במבנה הבא:
{{
  "title_hebrew": "כותרת קולעת ומתורגמת לעברית",
  "summary_hebrew": "2-3 נקודות תמצית בעברית על עיקרי הכתבה והקשרה לישראל",
  "sentiment": "חיובי / נייטרלי / עוין-ביקורתי",
  "sentiment_score": מספר בין 1.0- (עוין קיצוני) ל-1.0 (אוהד קיצוני), כאשר 0.0 הוא נייטרלי
}}
"""

def analyze_article(title: str, content: str, max_retries: int = 3) -> dict:
    prompt = PROMPT_TEMPLATE.format(title=title, content=content)
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait_time = 15 * (attempt + 1)
                print(f"[Rate Limit] ממתין {wait_time} שניות עקב מגבלת קצב של גוגל...")
                time.sleep(wait_time)
            else:
                print(f"LLM Error: {e}")
                break

    return {
        "title_hebrew": title,
        "summary_hebrew": content[:150] if content else "ללא תקציר זמין",
        "sentiment": "נייטרלי",
        "sentiment_score": 0.0
    }