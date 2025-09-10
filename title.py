import streamlit as st
# from google.cloud import firestore
# from google.oauth2 import service_account

# @st.cache_resource
# def get_db():
#     creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
#     return firestore.Client(project=st.secrets["gcp_project_id"], credentials=creds)
# db = get_db()

st.title("신한카드와 함께하는 소상공인 비밀상담소")
st.subheader("#우리동네 #숨은맛집 #소상공인 #마케팅 #전략")
st.caption("🌀 머리아픈 마케팅 📊 어떻게 하면 좋을까?")

with st.container(border=True):
    if not st.user.is_logged_in:
        st.subheader("로그인을 하고 서비스를 이용해보세요!")
        if st.button("구글 로그인", use_container_width=True):
            st.login()
    else:
        st.subheader(f"안녕하세요! {st.user.name}님!")
        st.divider()
        st.write(f"나의 가맹점 정보: 아직 가맹점을 유추하지 않았습니다!")
        st.caption("브랜드 식별 페이지에서 가맹점을 설정해보세요!")
        st.button("브랜드 식별 페이지로 이동", use_container_width=True)
        if st.button("로그아웃", use_container_width=True):
            st.logout()

    # if st.button("데이터 추가 테스트"):
    #     user_ref = db.collection("user").document(st.user.sub)
    #     user_ref.set({"test": "테스트 추가"})