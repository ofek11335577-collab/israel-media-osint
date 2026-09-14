init_db()

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM articles ORDER BY id DESC", conn)
    conn.close()
    return df

def run_auto_ingestion():
    arts = fetch_relevant_articles()
    new_c = 0
    for a in arts:
        if not is_article_exists(a['url']):
            a.update(analyze_article(a['title_original'], a['content_original']))
            save_article(a)
            new_c += 1
            time.sleep(12)
    return new_c

df = load_data()

# סריקה אוטומטית אם המאגר ריק לחלוטין בעליית האתר בענן
if df.empty:
    with st.spinner("🚀 טוען את דסק המודיעין ומבצע איסוף ראשוני ממקורות גלובליים..."):
        run_auto_ingestion()
        df = load_data()

with st.sidebar:
    st.markdown("### ⚙️ פעולות דסק")
    if st.button("🔄 סרוק מקורות ידנית", use_container_width=True):
        with st.status("איסוף וניתוח בתהליך...") as s:
            new_count = run_auto_ingestion()
            s.update(label=f"התווספו {new_count} דיווחים חדשים", state="complete")
            st.rerun()