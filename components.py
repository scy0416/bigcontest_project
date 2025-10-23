import streamlit as st

def init_sidebar():
    with st.sidebar:
        st.write("페이지")
        with st.container(border=True):
            if st.button("타이틀", use_container_width=True):
                st.switch_page("title.py")
            if st.button("브랜드 선택", use_container_width=True):
                st.switch_page("brand_recognize.py")