import streamlit as st
from components import *
import pandas as pd
from uuid import uuid4
import xml.parsers.expat as expat
from pydantic import BaseModel
import random

from typing import List, TypedDict, Dict, Literal
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Command, interrupt

# 선택된 가맹점이 없는 경우 타이틀로 이동
if 'selected_brand' not in st.session_state:
    st.switch_page("title.py")

# 데이터들 전부 로드
@st.cache_resource
def load_data():
    df1 = pd.read_csv("dataset/big_data_set1_f.csv", encoding="cp949")
    df2 = pd.read_csv("dataset/big_data_set2_f.csv", encoding="cp949")
    df3 = pd.read_csv("dataset/big_data_set3_f.csv", encoding="cp949")
    return df1, df2, df3

# 세션id초기화
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid4())

# 제미나이 생성
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=st.secrets["GOOGLE_API_KEY"],
    temperature=0.1,
)

# 각종 페르소나 정의
persona = {
    "Data Scientist": """당신은 마케팅 데이터 분석가입니다. 제공되는 데이터를 기반으로 현재 가맹점의 장점, 단점, 인사이트 등을 명확한 근거와 함께 제공해주세요.
각 주장을 할 때마다 명확한 데이터를 근거로 제시해야 하며, 근거는 마크다운 표로 작성해주세요.""",
    "CRM Marketer": """당신은 CRM마케터입니다. 주어진 데이터를 활용하여 고객 세그먼트별로 맞춤 캠페인을 설계하고 추가적인 정보가 필요한 경우에는 사용자에게 추가 정보를 요구하세요.""",
    "Performance Marketer": """당신은 퍼포먼스 마케터입니다. 사용자 요청에 따른 광고를 기획해주세요. 충분한 정보가 주어지지 않았다면 사용자에게 추가 정보를 요구하세요."""
}

# 상태그래프의 상태
class State(TypedDict):
    history: List                                       # 대화내역
    brand_info: Dict                                    # 가맹점 정보
    monthly_usage_info: str                             # 타겟 가맹점 월별 이용 정보
    monthly_usage_consumer_info: str                    # 타겟 가맹점 월별 이용 고객정보
    same_work_brands_monthly_usage_info: str            # 동종 업계 월별 이용 정보
    same_work_brands_monthly_usage_consumer_info: str   # 동종 업계 월별 이용 고객정보
    speaker: str                                        # 말하는 페르소나

# 프롬프트 템플릿
prompt_template = """{persona}
### 주의점
주장에는 자료에 기반한 명확한 근거를 제시해야합니다.
### 타겟 가맹점 기본 정보
가맹점명: {brand_name}
가맹점 업종: {brand_work}
가맹점 지역: {brand_area}
가맹점 개설일: {brand_open}
### 타겟 가맹점 월별 이용 정보
{monthly_usage_info}
### 타겟 가맹점 월별 이용 고객정보
{monthly_usage_consumer_info}
### 동종 업계 월별 이용 정보
{same_work_brands_monthly_usage_info}
### 동종 업계 월별 이용 고객정보
{same_work_brands_monthly_usage_consumer_info}"""

# 사용자 입력 노드(인터럽트 발생)
def user_input(state: State):
    payload = interrupt({})
    user_text = payload["text"]
    state["history"].append(HumanMessage(content=user_text))
    return state

# 전문가 페르소나 구조
class SpeakerSelect(BaseModel):
    speaker: Literal["Data Scientist", "CRM Marketer", "Performance Marketer"]

# 발화자 선정 노드
def speaker_select(state: State):
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("""당신은 대화대역을 보고서 발화를 할 전문가를 선택하는 중재자입니다.
선택할 수 있는 전문가는 "Data Scientist", "CRM Marketer", "Performance Marketer"가 있습니다.
Data Scientist의 역할은 데이터 분석/인사이트 제공,
CRM Marketer의 역할은 고객 세분화/재방문 유도,
Performance Marketer의 역할은 광고 전략 추천/최적화입니다.
사용자의 역할에 알맞는 전문가를 선택하세요."""),
        MessagesPlaceholder("history")
    ])
    prompt = prompt.invoke({"history": state["history"]})
    # SpeakerSelect구조대로 출력
    response = llm.with_structured_output(SpeakerSelect).invoke(prompt)
    # 발화자 설정
    state["speaker"] = response.speaker
    return state

# 답변 생성
def make_response(state: State):
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(prompt_template),
        MessagesPlaceholder("history"),
        SystemMessagePromptTemplate.from_template("""### 답변 생성 규칙
답변은 XML형식을 가져야 하며, DIALOGUE태그로 감싸져야만 합니다. 태그 밖에는 아무것도 생성하지 마세요. 태그를 닫은 후에는 공백, 개행 등 아무런 출력을 절대 하지 마세요.
### 답변 생성 예시
<DIALOGUE speaker='{speaker}'><![CDATA[답변]]></DIALOGUE>""")
    ])

    prompt = prompt.invoke({
        "persona": persona[state["speaker"]],
        "brand_name": state["brand_info"]["이름"],
        "brand_work": state["brand_info"]["업종"],
        "brand_area": state["brand_info"]["지역"],
        "brand_open": state["brand_info"]["개설일"],
        "monthly_usage_info": state["monthly_usage_info"],
        "monthly_usage_consumer_info": state["monthly_usage_consumer_info"],
        "same_work_brands_monthly_usage_info": state["same_work_brands_monthly_usage_info"],
        "same_work_brands_monthly_usage_consumer_info": state["same_work_brands_monthly_usage_consumer_info"],
        "speaker": state["speaker"],
        "history": state["history"]
    })

    # 태그가 제대로 닫히도록 처리
    buffer = ""
    for chunk in llm.stream(prompt):
        buffer += chunk.content
        if "</DIALOGUE>" in buffer:
            break
    response = buffer

    # 답변 대화내역에 추가
    state["history"].append(AIMessage(content=response))
    return state

# 그래프 생성자 생성
graph_builder = StateGraph(State)

# 그래프 노드 추가
graph_builder.add_node("사용자 입력", user_input)
graph_builder.add_node("전문가 선정", speaker_select)
graph_builder.add_node("답변 생성", make_response)

# 그래프 에지 설정
graph_builder.add_edge(START, "사용자 입력")
graph_builder.add_edge("사용자 입력", "전문가 선정")
graph_builder.add_edge("전문가 선정", "답변 생성")
graph_builder.add_edge("답변 생성", "사용자 입력")

# 메모리 세이버 초기화(rerun할 때마다 초기화 방지)
saver = None
if "saver" not in st.session_state:
    st.session_state["saver"] = MemorySaver()
    saver = st.session_state["saver"]
else:
    saver = st.session_state["saver"]

# 그래프 컨파일
graph = graph_builder.compile(checkpointer=saver)

# 사이드바 초기화
init_sidebar()

st.set_page_config(layout="wide")

st.header("마케팅 챗봇")
st.warning("새로고침을 하면 대화내역이 유지되지 않습니다! 유의해주세요!")
st.badge(f"세션id: {st.session_state['session_id']}")

# 데이터 로드
df1, df2, df3 = load_data()

# 가맹점 월별 이용 정보 추출
monthly_usage_info = df2[df2["ENCODED_MCT"]==st.session_state["selected_brand"]["식별코드"]]
# 가맹점 월별 이용 고객정보 추출
monthly_usage_consumer_info = df3[df3["ENCODED_MCT"]==st.session_state["selected_brand"]["식별코드"]]

# 선택된 가맹점 출력
with st.expander("선택된 가맹점 정보"):
    st.subheader("가맹점명")
    st.write(st.session_state['selected_brand']['이름'])
    st.subheader("업종")
    st.write(st.session_state['selected_brand']['업종'])
    st.subheader("지역")
    st.write(st.session_state['selected_brand']['지역'])
    st.subheader("개설일")
    date = str(st.session_state['selected_brand']['개설일'])
    st.write(f"{date[:4]}년 {date[4:6]}월 {date[6:]}일")

# 페르소나 설명 파트
st.subheader("준비된 전문가 페르소나")
col1, col2, col3 = st.columns(3, border=True)
with col1:
    st.write("**데이터 분석가**")
    st.write("역할: 데이터 분석/인사이트 제공")
    st.info("분석할 때 시간이 오래걸릴 수 있습니다! 주의하세요!")
with col2:
    st.write("**CRM 마케터**")
    st.write("역할: 고객 세분화/재방문 유도")
with col3:
    st.write("**퍼포먼스 마케터**")
    st.write("역할: 광고 전략 추천/최적화")

# 동종업계 브랜드 리스트업
same_work_brands = df1[(df1["HPSN_MCT_ZCD_NM"]==st.session_state["selected_brand"]["업종"]) & (df1["ENCODED_MCT"]!=st.session_state["selected_brand"]["식별코드"])]
same_work_brands_code = same_work_brands["ENCODED_MCT"].tolist()
if "selected_work_brands" not in st.session_state:
    if len(same_work_brands_code) >= 20:
        st.session_state["selected_work_brands"] = random.sample(same_work_brands_code, 20)
    else:
        st.session_state["selected_work_brands"] = same_work_brands_code

# 동종업계의 월별 이용 정보 추출
same_work_brands_monthly_usage_info = df2[df2["ENCODED_MCT"].isin(st.session_state["selected_work_brands"])]
# 동종업계의 월별 이용 고객정보 추출
same_work_brands_monthly_usage_consumer_info = df3[df3["ENCODED_MCT"].isin(st.session_state["selected_work_brands"])]

# config정보
config = {"configurable": {"thread_id": st.session_state["session_id"]}}

# 체크포인트 유뮤 확인
tup = saver.get_tuple(config)
exists_latest = (tup is not None)

# 체크포인트 정보 없으면 초기화
if not exists_latest:
    graph.invoke(State(
        history=[],
        brand_info=st.session_state["selected_brand"],
        monthly_usage_info=monthly_usage_info.to_json(orient="records", force_ascii=False),
        monthly_usage_consumer_info=monthly_usage_consumer_info.to_json(orient="records", force_ascii=False),
        same_work_brands_monthly_usage_info=same_work_brands_monthly_usage_info.to_json(orient="records", force_ascii=False),
        same_work_brands_monthly_usage_consumer_info=same_work_brands_monthly_usage_consumer_info.to_json(orient="records", force_ascii=False),
        speaker=""
    ), config)

# 체크포인트 정보 추출
config, checkpoint, metadata, parent_config, pending_writes = saver.get_tuple(config)

# 채팅 내역이 출력되는 컨테이너
chat_container = st.container(border=True)

# 버퍼와 플레이스 홀더
buffer = ""
placeholder = None

# 태그 시작 콜백 함수
def on_start(name, attrs):
    if name != 'DIALOGUE':
        return
    global placeholder, buffer
    # 발화자 이름으로 chat_message 열고 버퍼에 화자 정보 추가
    placeholder = chat_container.chat_message(attrs["speaker"]).empty()
    buffer += f'{attrs["speaker"]}: '

# 태그 종료 콜백 함수
def on_end(name):
    if name != 'DIALOGUE':
        return
    global buffer, placeholder
    # 버퍼 및 플레이스홀더 초기화
    buffer = ""
    placeholder = None

# 텍스트 처리 콜백 함수
def on_text(data):
    global buffer, placeholder
    # 버퍼에 추가 후 플레이스홀더에 출력
    buffer += data
    placeholder.markdown(buffer)

# 이전 대화 내역 출력
for message in checkpoint["channel_values"]["history"]:
    # 파서 생성
    parser = expat.ParserCreate("utf-8")
    # 파서의 콜백 함수 설정
    parser.StartElementHandler = on_start
    parser.CharacterDataHandler = on_text
    parser.EndElementHandler = on_end

    # 유저의 메시지면 직접 출력
    if isinstance(message, HumanMessage):
        chat_container.chat_message("user").markdown(message.content)
    else:   # AI의 메시지면 파서로 처리
        parser.Parse(message.content)

# 인터럽트 중인 경우
if pending_writes and any("__interrupt__" in w for w in pending_writes):
    # 인터럽트 중인 노드 이름 추출
    node_name = checkpoint["updated_channels"][0][10:]
    # 인터럽트 중인 노드가 사용자 입력 노드인 경우
    if node_name == "사용자 입력":
        # 입력 처리
        prompt = st.chat_input()
        if prompt:
            # 파서 생성
            parser = expat.ParserCreate("utf-8")
            # 파서 콜백 함수 설정
            parser.StartElementHandler = on_start
            parser.CharacterDataHandler = on_text
            parser.EndElementHandler = on_end

            # 루트 파싱 시작(없으면 문제 발생)
            parser.Parse("<ROOT>", False)

            # 사용자의 메시지 출력
            chat_container.chat_message("user").markdown(prompt)
            # 사용자 입력 인터럽트 재개 커맨드
            cmd = Command(resume={"text": prompt})

            # 스트리밍으로 챗봇 재개
            for event in graph.stream(cmd, config, stream_mode="messages"):
                node_name = event[1].get("langgraph_node")
                # 답변 생성의 청크만 처리
                if node_name == "답변 생성":
                    # AIMessageChunk만 처리하고 AIMessage는 무시
                    if not isinstance(event[0], AIMessageChunk):
                        continue
                    # 청크 추출
                    chunk = event[0].content or ""

                    # 청크가 없는 경우
                    if not chunk:
                        continue

                    # 파서로 파싱
                    parser.Parse(chunk, False)

            # 파싱 종료
            parser.Parse("</ROOT>", True)
# 꼬여서 인터럽트 중이 아닌 경우
else:
    st.chat_input(disabled=True)
    # 인터럼트 발생시점까지 진행
    graph.invoke(None, config)
    st.rerun()