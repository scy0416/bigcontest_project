import streamlit as st
from components import *

init_sidebar()

st.title(":blue[신한카드]와 함께하는 소상공인 비밀상담소")
st.subheader("#우리동네 #숨은맛집 #소상공인 #마케팅 #전략")
st.caption("🌀 머리아픈 마케팅 📊 어떻게 하면 좋을까?")

with st.container(border=True):
    st.subheader("서비스 목표")
    st.container(border=True).write("""사용자가 선택한 가맹점에 대한 정보를 바탕으로 도움을 줄 수 있는 전문가가 여러분의 마케팅 전략을 제안해드립니다!""")
    st.subheader("서비스 이용 순서")
    st.container(border=True).markdown("""1. 가맹점 선택
    
2. 전문가 챗봇들과 상담 진행""")
    st.subheader("이걸 만든 팀: 동그란 네모")
    st.container(border=True).write("""- 김믿음(프롬프트 엔지니어링)

- 옥승현(데이터 처리)

- 송찬영(streamlit 어플리케이션 및 챗봇 구성)""")
    st.caption("브랜드 식별 페이지에서 가맹점을 선택해보세요!")
    if st.button("브랜드 선택 페이지로 이동", use_container_width=True):
        st.switch_page("brand_recognize.py")