import streamlit as st
from dotenv import load_dotenv
import os
import openai
import re
import time
import random

# --- 1. 환경 설정 및 API 키 로드 ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- 2. 이미지 파일 경로 설정 ---
IMAGE_PATHS = {
    'player_normal': 'assets/player_normal_avatar.png',
    'boss_kim': 'assets/boss_kim_avatar.png',
    'manager_park': 'assets/manager_park_avatar.png',
    'intern_lee': 'assets/intern_lee_avatar.png',
    'gm_icon': 'assets/gm_avatar.png'
}

# OpenAI 클라이언트 초기화
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- 3. 마스터 프롬프트 ---
MASTER_PROMPT = """
### 역할 ###
너는 '신입사원 생존기: 1999' 게임의 게임 마스터(GM)다.
너는 플레이어가 흥미를 느낄 만한 사건을 제시하고, 그에 대한 반응을 유도해야 한다.
90년대 PC통신 채팅 느낌의 문체를 사용해라. (예: 안녕하세용 방가방가ㅋ)
NPC의 대사는 항상 "NPC이름: 대사" 형식으로 시작한다.

### 세계관 ###
- 배경: 90년대 말, 벤처 붐이 일던 시기의 IT 기업 '새롬정보기술' 사무실.
- 시간: 오전 9시. 플레이어는 오늘 첫 출근한 신입사원이다.
- 등장인물:
    - 김부장: 아재개그와 잔소리를 좋아함.
    - 박대리: 무뚝뚝하지만 사실 츤데레.
    - 동기 이씨: 의욕 넘치지만 눈치 없음.

### 게임 진행 규칙 ###
1.  **이벤트 제시:** 플레이어에게 구체적인 사건이나 상황을 제시한다.
2.  **선택지 제공:** 플레이어가 무엇을 할지 쉽게 결정할 수 있도록, 괄호 안에 **(1. OOO하기), (2. XXX하기)** 와 같이 두 가지 행동 선택지를 예시로 제공한다. 플레이어는 이 선택지를 따르거나, 다른 창의적인 행동을 할 수 있다.
3.  **결과 묘사:** 플레이어의 행동에 대한 결과를 재치있고 실감나게 묘사한다.
4.  **상태 업데이트:** 너의 모든 답변은 반드시 아래 형식으로 끝나야 한다.
    - 스탯 변화량을 `[스탯명: +/-N]` 형식으로 보여주고, (변화가 없으면 생략 가능)
    - 최종 스탯을 `[멘탈: 현재값] [업무 능력: 현재값] [사회성: 현재값]` 형식으로 표시한다.
5.  **시간 규칙:** 중요한 과제가 끝나면 시간을 1시간 흐르게 하고, 이를 이야기 속에 자연스럽게 묘사한다.

### 게임 시작 ###
이제, 플레이어가 흥미를 느낄만한 첫 번째 이벤트를 제시하며 게임을 시작해라. 반드시 2가지 선택지를 포함해야 한다.
"""

# --- 4. UI 스타일링 (눈이 편안한 'Amber 터미널' 버전) ---
page_style = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic+Coding&display=swap');

#MainMenu {visibility: hidden;}
header {visibility: hidden;}

.stApp {
    background-color: #1a1a1a;
    font-family: 'Nanum Gothic Coding', monospace;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 1rem;
}
.game-title {
    font-size: 2.5em;
    text-align: center;
    padding-bottom: 15px;
    margin-bottom: 15px;
    border-bottom: 3px double #555;
    color: #FFB800;
}
.status-hud {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    background-color: #2a2a2a;
    border: 2px solid #555;
    border-radius: 5px;
    margin-bottom: 20px;
    color: #FAFAFA;
}
.status-item { font-size: 1.1em; font-weight: bold; }
.status-item progress { width: 70px; height: 12px; }
.status-item progress::-webkit-progress-bar { background-color: #444; border-radius: 2px; }
.status-item progress::-webkit-progress-value { background-color: #FFB800; border-radius: 2px; }
div[data-testid="stChatMessageContent"] {
    background-color: #333333;
    border: 1px solid #555;
    border-radius: 5px;
    font-size: 1.1rem;
    color: #FFDDAA;
}
.st-emotion-cache-4oy321 { background-color: #40382D; }
.st-emotion-cache-16txtl3 img {
    border: 2px solid #555;
    border-radius: 5px;
    background-color: #444;
    width: 45px; height: 45px;
    object-fit: contain;
    image-rendering: pixelated;
}
.stChatInput {
    background-color: #1a1a1a;
    border-top: 2px solid #555;
}
.final-report-container {
    background-color: #333333;
    color: #FFDDAA;
    border: 1px solid #555;
    padding: 15px;
    font-family: 'Courier New', monospace;
    white-space: pre-wrap;
    margin-top: 20px;
    max-height: 400px;
    overflow-y: auto;
}
</style>
"""

# --- 5. 핵심 함수 ---
def initialize_game():
    st.session_state.stats = {"멘탈": 100, "업무 능력": 50, "사회성": 50}
    st.session_state.time = "09:00"
    st.session_state.messages = [{"role": "system", "content": MASTER_PROMPT}]
    st.session_state.chat_history = []
    
    # ✨ AI가 직접 첫 이벤트를 생성하도록 변경
    response_content = get_ai_response_content() 
    st.session_state.messages.append({"role": "assistant", "content": response_content})
    st.session_state.chat_history.append({"role": "assistant", "content": response_content})
    update_stats_from_response(response_content)


# 시간 업데이트를 파이썬에서 직접 처리
def update_stats_from_response(response):
    # 키워드 기반 시간 경과
    time_keywords = ['보고서', '회의', '완료', '끝', '심부름', '다녀왔', '점심', '휴식']

    # AI 응답에 키워드가 있고, 마지막 턴 이후로 시간이 흐르지 않았다면
    if any(keyword in response for keyword in time_keywords) and not st.session_state.get('time_passed_this_turn', False):
        hours_passed = random.choice([1, 2]) # 1~2시간 랜덤으로 경과
        current_hour = int(st.session_state.time.split(':')[0])
        new_hour = current_hour + hours_passed
        st.session_state.time = f"{new_hour:02d}:00"
        st.session_state.time_passed_this_turn = True

    stat_changes = re.findall(r"\[(멘탈|업무 능력|사회성):\s*([+\-]\d+)\]", response)
    for stat_name, change in stat_changes:
        st.session_state.stats[stat_name] += int(change)

    final_stats_match = re.search(r"\[멘탈:\s*(\d+)\]\s*\[업무 능력:\s*(\d+)\]\s*\[사회성:\s*(\d+)\]", response)
    if final_stats_match:
        st.session_state.stats['멘탈'] = int(final_stats_match.group(1))
        st.session_state.stats['업무 능력'] = int(final_stats_match.group(2))
        st.session_state.stats['사회성'] = int(final_stats_match.group(3))


def get_ai_response_content():
    # 다음 턴을 위해 시간 경과 플래그 초기화
    st.session_state.time_passed_this_turn = False
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=st.session_state.messages, temperature=0.7)
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"API 호출 중 오류 발생: {e}")
        return "앗, 죄송합니다! 잠시 문제가 발생한 것 같아요. 다른 행동을 입력해보시겠어요?"

def generate_final_report_content():
    report_messages = [{"role": "system", "content": "너는 인사팀장이다. 아래의 대화 기록을 보고 신입사원의 첫날을 평가하는 보고서를 작성해라."}]
    for msg in st.session_state.chat_history:
        report_messages.append(msg)
    
    report_prompt = "위 대화 기록을 바탕으로, 이 신입사원의 첫날 근무에 대한 최종 평가 보고서를 '인사팀장'의 관점에서 작성해줘. 냉철하고 프로페셔널하게 작성하되, 약간의 유머를 섞어줘. 강점, 약점, 그리고 이 신입의 미래에 대한 예측을 포함해서. 보고서는 한 단락으로 요약하지 말고, 여러 항목으로 나눠서 상세하게 작성해줘."
    report_messages.append({"role": "user", "content": report_prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-4", messages=report_messages, temperature=0.5)
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"보고서 생성 중 오류 발생: {e}")
        return "죄송합니다, 최종 평가 보고서를 생성하는 데 실패했습니다. API 상태를 확인해주세요."


# --- 6. Streamlit UI 구성 ---
st.set_page_config(page_title="신입사원 생존기: 1999", layout="centered")

st.markdown(page_style, unsafe_allow_html=True)

if 'stats' not in st.session_state:
    initialize_game()

st.markdown('<h1 class="game-title">신입사원 생존기 \'99</h1>', unsafe_allow_html=True)

mental_val = max(0, min(st.session_state.stats['멘탈'], 200))
work_val = max(0, min(st.session_state.stats['업무 능력'], 200))
social_val = max(0, min(st.session_state.stats['사회성'], 200))

hud_html = f"""
<div class="status-hud">
    <div class="status-item">🧠 M: {st.session_state.stats['멘탈']} <progress value="{mental_val}" max="200"></progress></div>
    <div class="status-item">💼 W: {st.session_state.stats['업무 능력']} <progress value="{work_val}" max="200"></progress></div>
    <div class="status-item">🤝 S: {st.session_state.stats['사회성']} <progress value="{social_val}" max="200"></progress></div>
    <div class="status-item">⏰ {st.session_state.time}</div>
</div>
"""
st.markdown(hud_html, unsafe_allow_html=True)


chat_container = st.container(height=500)
with chat_container:
    for msg_entry in st.session_state.chat_history:
        role, content = msg_entry["role"], msg_entry["content"]
        npc_match = re.match(r"^(김부장|박대리|동기 이씨|GM):\s*(.*)", content, re.DOTALL)
        
        avatar_path = IMAGE_PATHS['player_normal']
        actual_content = content

        if role == "assistant":
            avatar_path = IMAGE_PATHS['gm_icon']
            if npc_match:
                npc_name, actual_content = npc_match.groups()
                if npc_name == "김부장": avatar_path = IMAGE_PATHS['boss_kim']
                elif npc_name == "박대리": avatar_path = IMAGE_PATHS['manager_park']
                elif npc_name == "동기 이씨": avatar_path = IMAGE_PATHS['intern_lee']
            with st.chat_message("assistant", avatar=avatar_path):
                st.write(actual_content.strip())
        elif role == "user":
            with st.chat_message("user", avatar=avatar_path):
                st.write(actual_content.strip())

game_over_flag = False
if st.session_state.stats['멘탈'] <= 0:
    st.error("GAME OVER: 멘탈이 바사삭... 재기불능 상태가 되었다.")
    game_over_flag = True
elif st.session_state.stats['업무 능력'] <= 0:
    st.error("GAME OVER: '내일부터 나오지 말게.' 라는 말을 들었다.")
    game_over_flag = True
elif st.session_state.time >= "18:00":
    st.success("CONGRATULATIONS! 무사히 칼퇴근에 성공했다!")
    st.balloons()
    game_over_flag = True

if game_over_flag:
    if st.button("최종 평가 보고서 보기"):
        with st.spinner("인사팀에서 보고서를 전송받는 중..."):
            report = generate_final_report_content()
            st.subheader("최종 평가 보고서")
            st.info(report)
    st.stop()

user_input = st.chat_input("명령어를 입력하세요...", key="chat_input")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.spinner("..."):
        ai_response_content = get_ai_response_content()
        update_stats_from_response(ai_response_content)
        st.session_state.messages.append({"role": "assistant", "content": ai_response_content})
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response_content})
    st.rerun()