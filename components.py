import streamlit as st

def init_sidebar():
    with st.sidebar:
        st.header("소상공인 비밀상담소")
        st.divider()
        with st.container(border=True):
            st.subheader("페이지")
            if st.button("타이틀", use_container_width=True):
                st.switch_page("title.py")
            if st.button("브랜드 선택", use_container_width=True):
                st.switch_page("brand_recognize.py")
        with st.container(border=True):
            st.subheader("Credit")
            st.write("Made by **동그란네모**")
            st.write("- 김믿음")
            st.write("- 옥승현")
            st.write("- 송찬영")