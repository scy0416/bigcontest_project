import streamlit as st
from components import *
import pandas as pd
from uuid import uuid4
import xml.parsers.expat as expat
from pydantic import Field, BaseModel

from typing import List, TypedDict, Dict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Command, interrupt

@st.cache_resource
def load_data():
    df1 = pd.read_csv("dataset/big_data_set1_f.csv", encoding="cp949")
    df2 = pd.read_csv("dataset/big_data_set2_f.csv", encoding="cp949")
    df3 = pd.read_csv("dataset/big_data_set3_f.csv", encoding="cp949")
    return df1, df2, df3

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid4())

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=st.secrets["GOOGLE_API_KEY"],
    temperature=0.1,
)

persona = {
    "Data Scientist": """당신은 마케팅 데이터 분석가입니다. 제공되는 데이터를 기반으로 현재 가맹점의 장점, 단점, 인사이트 등을 명확한 근거와 함께 제공해주세요.
각 주장을 할 때마다 명확한 데이터를 근거로 제시해야 하며, 근거는 마크다운 표로 작성해주세요.""",
    "CRM Marketer": """당신은 CRM마케터입니다. 주어진 데이터를 활용하여 고객 세그먼트별로 맞춤 캠페인을 설계하고 추가적인 정보가 필요한 경우에는 사용자에게 추가 정보를 요구하세요.""",
    "Performance Marketer": """당신은 퍼포먼스 마케터입니다. 사용자 요청에 따른 광고를 기획해주세요. 충분한 정보가 주어지지 않았다면 사용자에게 추가 정보를 요구하세요."""
}

class State(TypedDict):
    history: List
    brand_info: Dict
    monthly_usage_info: str
    monthly_usage_consumer_info: str
    same_work_brands_monthly_usage_info: str
    same_work_brands_monthly_usage_consumer_info: str
    speaker: str

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

# def init_analyze(state: State):
#     state["speaker"] = "Data Scientist"
#     prompt = ChatPromptTemplate.from_messages([
#         SystemMessagePromptTemplate.from_template(prompt_template),
#         MessagesPlaceholder("history")
#     ])
#
#     prompt = prompt.invoke({
#         "persona": persona["Data Scientist"],
#         "brand_name": state["brand_info"]["이름"],
#         "brand_work": state["brand_info"]["업종"],
#         "brand_area": state["brand_info"]["지역"],
#         "brand_open": state["brand_info"]["개설일"],
#         "monthly_usage_info": state["monthly_usage_info"],
#         "monthly_usage_consumer_info": state["monthly_usage_consumer_info"],
#         "same_work_brands_monthly_usage_info": state["same_work_brands_monthly_usage_info"],
#         "same_work_brands_monthly_usage_consumer_info": state["same_work_brands_monthly_usage_consumer_info"],
#         "speaker": state["speaker"],
#         "history": state["history"]
#     })
#
#     response = llm.invoke(prompt)
#
#     state["history"].append(AIMessage(content=response.content))
#     return state

def user_input(state: State):
    payload = interrupt({})
    user_text = payload["text"]
    state["history"].append(HumanMessage(content=user_text))
    return state

class SpeakerSelect(BaseModel):
    speaker: Literal["Data Scientist", "CRM Marketer", "Performance Marketer"]

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
    response = llm.with_structured_output(SpeakerSelect).invoke(prompt)
    state["speaker"] = response.speaker
    return state

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

    # response = llm.invoke(prompt)
    buffer = ""
    for chunk in llm.stream(prompt):
        #print('"', chunk.content, '"')
        buffer += chunk.content
        if "</DIALOGUE>" in buffer:
            break
    response = buffer

    #state["history"].append(AIMessage(content=response.content))
    state["history"].append(AIMessage(content=response))
    return state

graph_builder = StateGraph(State)
#graph_builder.add_node("초기 분석", init_analyze)
graph_builder.add_node("사용자 입력", user_input)
graph_builder.add_node("전문가 선정", speaker_select)
graph_builder.add_node("답변 생성", make_response)

#graph_builder.add_edge(START, "초기 분석")
#graph_builder.add_edge("초기 분석", "사용자 입력")
graph_builder.add_edge(START, "사용자 입력")
graph_builder.add_edge("사용자 입력", "전문가 선정")
graph_builder.add_edge("전문가 선정", "답변 생성")
graph_builder.add_edge("답변 생성", "사용자 입력")

#saver = MemorySaver()
saver = None
if "saver" not in st.session_state:
    st.session_state["saver"] = MemorySaver()
    saver = st.session_state["saver"]
else:
    saver = st.session_state["saver"]
graph = graph_builder.compile(checkpointer=saver)

init_sidebar()

if 'selected_brand' not in st.session_state:
    st.switch_page("title.py")

st.set_page_config(layout="centered")

st.header("마케팅 챗봇")
st.badge(f"세션id: {st.session_state['session_id']}")

df1, df2, df3 = load_data()
monthly_usage_info = df2[df2["ENCODED_MCT"]==st.session_state["selected_brand"]["식별코드"]]
monthly_usage_consumer_info = df3[df3["ENCODED_MCT"]==st.session_state["selected_brand"]["식별코드"]]

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

st.subheader("준비된 전문가 페르소나")
col1, col2, col3 = st.columns(3, border=True)
with col1:
    st.write("**데이터 분석가**")
    st.write("역할: 데이터 분석/인사이트 제공")
with col2:
    st.write("**CRM 마케터**")
    st.write("역할: 고객 세분화/재방문 유도")
with col3:
    st.write("**퍼포먼스 마케터**")
    st.write("역할: 광고 전략 추천/최적화")

#st.write("가맹점의 월별 이용 정보")
#st.write(monthly_usage_info)
#st.write("가맹점의 월별 소비자 이용 정보")
#st.write(monthly_usage_consumer_info)
#st.write("가맹점의 동종업계 가맹점들")
same_work_brands = df1[(df1["HPSN_MCT_ZCD_NM"]==st.session_state["selected_brand"]["업종"]) & (df1["ENCODED_MCT"]!=st.session_state["selected_brand"]["식별코드"])]
#st.write(same_work_brands)
same_work_brands_code = same_work_brands["ENCODED_MCT"].tolist()
#st.write(same_work_brands_code)
#st.write("가맹점의 동종업계 이용 정보")
same_work_brands_monthly_usage_info = df2[df2["ENCODED_MCT"].isin(same_work_brands_code)]
#st.write(same_work_brands_monthly_usage_info)
#st.write("가맹점의 동종업계 소비자 이용 정보")
same_work_brands_monthly_usage_consumer_info = df3[df3["ENCODED_MCT"].isin(same_work_brands_code)]
#st.write(same_work_brands_monthly_usage_consumer_info)

config = {"configurable": {"thread_id": st.session_state["session_id"]}}

tup = saver.get_tuple(config)
exists_latest = (tup is not None)

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

config, checkpoint, metadata, parent_config, pending_writes = saver.get_tuple(config)

chat_container = st.container(border=True)

buffer = ""
placeholder = None

def on_start(name, attrs):
    if name != 'DIALOGUE':
        return
    global placeholder, buffer
    placeholder = chat_container.chat_message(attrs["speaker"]).empty()
    buffer += f'{attrs["speaker"]}: '

def on_end(name):
    if name != 'DIALOGUE':
        return
    global buffer, placeholder
    buffer = ""
    placeholder = None

def on_text(data):
    global buffer, placeholder
    buffer += data
    placeholder.markdown(buffer)

for message in checkpoint["channel_values"]["history"]:
    parser = expat.ParserCreate("utf-8")
    parser.StartElementHandler = on_start
    parser.CharacterDataHandler = on_text
    parser.EndElementHandler = on_end
    if isinstance(message, HumanMessage):
        chat_container.chat_message("user").markdown(message.content)
    else:
        parser.Parse(message.content)

if pending_writes and any("__interrupt__" in w for w in pending_writes):
    node_name = checkpoint["updated_channels"][0][10:]
    if node_name == "사용자 입력":
        prompt = st.chat_input()
        if prompt:
            parser = expat.ParserCreate("utf-8")
            parser.StartElementHandler = on_start
            parser.CharacterDataHandler = on_text
            parser.EndElementHandler = on_end

            parser.Parse("<ROOT>", False)

            chat_container.chat_message("user").markdown(prompt)
            cmd = Command(resume={"text": prompt})

            for event in graph.stream(cmd, config, stream_mode="messages"):
                node_name = event[1].get("langgraph_node")
                if node_name == "답변 생성":
                    if not isinstance(event[0], AIMessageChunk):
                        continue
                    chunk = event[0].content or ""
                    #print(chunk)
                    if not chunk:
                        continue

                    parser.Parse(chunk, False)
            parser.Parse("</ROOT>", True)
            #st.rerun()
else:
    st.chat_input(disabled=True)
    graph.invoke(None, config)
    st.rerun()