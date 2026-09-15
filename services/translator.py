# services/translator.py
from deep_translator import GoogleTranslator
import streamlit as st

@st.cache_data(ttl=3600)
def translate_to_hebrew(text: str) -> str:
    """מתרגם טקסט אוטומטית לעברית תקנית"""
    if not text or len(text.strip()) == 0:
        return text
    try:
        translated = GoogleTranslator(source='auto', target='iw').translate(text)
        return translated if translated else text
    except Exception:
        return text