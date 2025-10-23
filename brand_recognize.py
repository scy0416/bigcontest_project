import streamlit as st
import pandas as pd
from components import *
from uuid import uuid4

# 브랜드와 업계 졍보 초기화
st.session_state['brand'] = None
st.session_state['works'] = None

# 가맹점 정보 로드
@st.cache_resource
def load_brand_data():
    df = pd.read_csv("dataset/big_data_set1_f.csv", encoding="cp949")

    tmp_list = []

    # 지역, 이름, 업종, 식별코드, 개설일만을 추출
    for idx, row in df.iterrows():
        tmp = {'지역': row['MCT_SIGUNGU_NM'], '이름': row['MCT_NM'], '업종': row['HPSN_MCT_ZCD_NM'], '식별코드': row['ENCODED_MCT'], '개설일': row['ARE_D']}
        tmp_list.append(tmp)

    return tmp_list

# 업종 정보만 추출
@st.cache_resource
def load_works():
    works = set()
    df = pd.read_csv("dataset/big_data_set1_f.csv", encoding="cp949")
    for idx, row in df.iterrows():
        works.add(row['HPSN_MCT_ZCD_NM'])
    return list(works)

# 이름 문자열을 처리하는 메소드
def process_name(name):
    if name == "":
        return ""
    if len(name) == 1:
        return '*'
    if len(name) == 2:
        return f"{name[0]}*"
    return f"{name[:2]}{'*'*len(name[2:])}"

# 브랜드 정보 설정 처리
def set_brand_info(brand):
    st.session_state['selected_brand'] = brand

# 사이드바 초기화
init_sidebar()

# 브랜드 정보들 로드
with st.spinner("브랜드 정보 로드 중..."):
    st.session_state['brand'] = load_brand_data()
    st.session_state['works'] = load_works()

st.set_page_config(layout="wide")

select, selected = st.columns(2, border=True)

# 브랜드 검색 칼럼
with select:
    col1, col2 = st.columns(2)

    # 가맹점 검색
    with col1:
        st.subheader("가맹점명")
        st.text_input(label="a", label_visibility="collapsed", key="name")

    # 업종 검색
    with col2:
        st.subheader("업종")
        st.selectbox(label='a', label_visibility="collapsed", key="work", options=st.session_state['works'])

    # 가맹점과 업종을 통해서 가맹점 검색
    if st.button("검색", use_container_width=True):
        name = st.session_state["name"]
        # 원래 이름
        original_name = name
        # 처리된 이름
        processed_name = process_name(name)
        work = st.session_state["work"]

        st.subheader("검색 결과")
        search_result = []
        for brand in st.session_state["brand"]:
            # 원래 이름이나 처리된 이름이 포함되지 않는 경우
            if not (original_name == "" or (original_name in brand['이름'] or processed_name in brand['이름'])):
                continue
            # 업종이 틀린 경우
            if brand['업종'] != work:
                continue
            # 가맹점 추가
            search_result.append(brand)

        with st.container(border=True):
            for brand in search_result:
                # 이름, 지역, 업종, 개설일
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.write(brand["이름"])
                with col2:
                    st.write(brand["지역"])
                with col3:
                    st.write(brand["업종"])
                with col4:
                    st.write(brand["개설일"])
                with col5:
                    st.button("선택", key=f"select_{brand['식별코드']}", on_click=set_brand_info, args=[brand])
                st.divider()

# 선택한 가맹점 정보 출력되는 칼럶
with selected:
    st.header("선택된 가맹점 정보")
    if 'selected_brand' not in st.session_state:
        st.info("아직 가맹점이 선택되지 않았습니다")
    else:
        with st.container(border=True):
            st.subheader("가맹점명")
            st.write(st.session_state['selected_brand']['이름'])
            st.subheader("업종")
            st.write(st.session_state['selected_brand']['업종'])
            st.subheader("지역")
            st.write(st.session_state['selected_brand']['지역'])
            st.subheader("개설일")
            date = str(st.session_state['selected_brand']['개설일'])
            st.write(f"{date[:4]}년 {date[4:6]}월 {date[6:]}일")
            if st.button("마케팅 상담 시작", use_container_width=True):
                st.session_state["session_id"] = str(uuid4())
                st.switch_page("marketing_chatbot.py")