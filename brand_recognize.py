import streamlit as st
import pandas as pd

st.session_state['brand'] = None
st.session_state['works'] = None
@st.cache_resource
def load_brand_data():
    df = pd.read_csv("dataset/big_data_set1_f.csv", encoding="cp949")

    tmp_list = []

    for idx, row in df.iterrows():
        tmp = {'지역': row['MCT_SIGUNGU_NM'], '이름': row['MCT_NM'], '업종': row['HPSN_MCT_ZCD_NM'], '식별코드': row['ENCODED_MCT'], '개설일': row['ARE_D']}
        tmp_list.append(tmp)

    return tmp_list

@st.cache_resource
def load_works():
    works = set()
    df = pd.read_csv("dataset/big_data_set1_f.csv", encoding="cp949")
    for idx, row in df.iterrows():
        works.add(row['HPSN_MCT_ZCD_NM'])
    return list(works)

def process_name(name):
    if name == "":
        return ""
    if len(name) == 1:
        return '*'
    if len(name) == 2:
        return f"{name[0]}*"
    return f"{name[:2]}{'*'*len(name[2:])}"

with st.spinner("브랜드 정보 로드 중..."):
    st.session_state['brand'] = load_brand_data()
    st.session_state['works'] = load_works()

#st.write(st.session_state['brand'])

col1, col2 = st.columns(2)

with col1:
    st.subheader("가맹점명")
    st.text_input(label="a", label_visibility="collapsed", key="name")

with col2:
    st.subheader("업종")
    #st.text_input(label="a", label_visibility="collapsed", key="work")
    st.selectbox(label='a', label_visibility="collapsed", key="work", options=st.session_state['works'])

if st.button("검색", use_container_width=True):
    name = st.session_state["name"]
    original_name = name
    processed_name = process_name(name)
    work = st.session_state["work"]

    st.subheader("검색 결과")
    search_result = []
    for brand in st.session_state["brand"]:
        if not (original_name == "" or (original_name in brand['이름'] or processed_name in brand['이름'])):
            continue
        if brand['업종'] != work:
            continue
        search_result.append(brand)
    #st.write(search_result)
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
                st.button("선택", key=brand["식별코드"])