import streamlit as st
from components import *
# from google.cloud import firestore
# from google.oauth2 import service_account

# @st.cache_resource
# def get_db():
#     creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
#     return firestore.Client(project=st.secrets["gcp_project_id"], credentials=creds)
# db = get_db()

init_sidebar()

st.title("신한카드와 함께하는 소상공인 비밀상담소")
st.subheader("#우리동네 #숨은맛집 #소상공인 #마케팅 #전략")
st.caption("🌀 머리아픈 마케팅 📊 어떻게 하면 좋을까?")

with st.container(border=True):
    st.caption("브랜드 식별 페이지에서 가맹점을 선택해보세요!")
    #st.button("브랜드 식별 페이지로 이동", use_container_width=True)
    if st.button("브랜드 식별 페이지로 이동", use_container_width=True):
        st.switch_page("brand_recognize.py")