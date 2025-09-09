import streamlit as st

st.set_page_config(page_title="마케팅 챗봇 with 신한카드")

pages = {
    "메뉴": [
        st.Page("title.py", title="타이틀"),
        st.Page("brand_recognize.py", title="브랜드 식별"),
        st.Page("marketing_chatbot.py", title="마케팅 챗봇"),
        st.Page("visualize.py", title="시각화")
    ]
}

pg = st.navigation(pages, position="top")
pg.run()