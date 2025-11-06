import streamlit as st

# 기본 설정
st.set_page_config(
    page_title="배재중학교 동아리 발표회",
    layout="wide",
)

# ----- 동아리 / 교실 데이터 정의 -----
# row, col 값을 바꾸면 배치도에서 위치가 바뀝니다.
# 실제 학교 배치에 맞게 언제든지 수정하면 돼요.
ROOMS = [
    {
        "id": "3-1",
        "name": "3-1 교실",
        "club": "과학 탐구 동아리",
        "summary": "실험과 탐구를 좋아하는 친구들이 모인 과학 동아리입니다.",
        "detail": """
- 주요 활동: 화학·물리 실험, 과학 키트 만들기, 실험 결과 발표
- 운영 시간: 매주 화요일 7~8교시
- 담당 교사: 김과학 선생님
- 모집 대상: 과학을 좋아하는 1~3학년
        """,
        "row": 1,
        "col": 1,
    },
    {
        "id": "3-2",
        "name": "3-2 교실",
        "club": "밴드 동아리",
        "summary": "보컬, 기타, 드럼 등으로 공연을 준비하는 밴드 동아리입니다.",
        "detail": """
- 주요 활동: 합주 연습, 학교 행사 공연, 자작곡 연주
- 운영 시간: 매주 수요일 7~8교시, 토요일 자율연습
- 담당 교사: 이음악 선생님
- 모집 대상: 악기를 배우고 싶은 학생 누구나
        """,
        "row": 1,
        "col": 2,
    },
    {
        "id": "3-3",
        "name": "3-3 교실",
        "club": "미술 동아리",
        "summary": "그림, 디자인, 공예를 함께 만드는 미술 동아리입니다.",
        "detail": """
- 주요 활동: 수채화, 아크릴화, 캐릭터 디자인, 전시 준비
- 운영 시간: 매주 월요일 7~8교시
- 담당 교사: 박미술 선생님
- 모집 대상: 그림 그리기를 좋아하는 학생
        """,
        "row": 1,
        "col": 3,
    },
    {
        "id": "2-1",
        "name": "2-1 교실",
        "club": "코딩 동아리",
        "summary": "파이썬, 스크래치로 게임과 프로그램을 만드는 코딩 동아리입니다.",
        "detail": """
- 주요 활동: 게임 만들기, 간단한 웹페이지 제작, 알고리즘 기초
- 운영 시간: 매주 목요일 7~8교시
- 담당 교사: 최정보 선생님
- 모집 대상: 코딩에 관심 있는 학생 (기초 무관)
        """,
        "row": 2,
        "col": 1,
    },
    {
        "id": "2-2",
        "name": "2-2 교실",
        "club": "사진·영상 동아리",
        "summary": "사진 촬영과 영상 편집을 배우는 미디어 동아리입니다.",
        "detail": """
- 주요 활동: 학교 행사 촬영, 브이로그 제작, 편집 기초 배우기
- 운영 시간: 매주 금요일 7~8교시
- 담당 교사: 정미디어 선생님
- 모집 대상: 사진·영상에 관심 있는 학생
        """,
        "row": 2,
        "col": 2,
    },
    {
        "id": "2-3",
        "name": "2-3 교실",
        "club": "보드게임 동아리",
        "summary": "전략 보드게임과 협동 게임을 함께 즐기는 동아리입니다.",
        "detail": """
- 주요 활동: 다양한 보드게임 플레이, 학교 대회 개최
- 운영 시간: 매주 수요일 점심시간 + 7교시
- 담당 교사: 한논리 선생님
- 모집 대상: 보드게임 좋아하는 누구나
        """,
        "row": 2,
        "col": 3,
    },
    {
        "id": "1-1",
        "name": "1-1 교실",
        "club": "독서 토론 동아리",
        "summary": "책을 읽고 생각을 나누는 독서 토론 동아리입니다.",
        "detail": """
- 주요 활동: 한 달 한 권 같이 읽기, 독서 토론, 서평 쓰기
- 운영 시간: 매주 화요일 점심시간
- 담당 교사: 오독서 선생님
- 모집 대상: 책 읽는 걸 좋아하는 학생
        """,
        "row": 3,
        "col": 1,
    },
    {
        "id": "1-2",
        "name": "1-2 교실",
        "club": "스포츠 동아리",
        "summary": "농구, 풋살 등 다양한 스포츠를 즐기는 동아리입니다.",
        "detail": """
- 주요 활동: 농구·풋살 경기, 체력 단련, 학급 대항전 준비
- 운영 시간: 매주 월·목방과후
- 담당 교사: 김체육 선생님
- 모집 대상: 운동을 좋아하는 학생
        """,
        "row": 3,
        "col": 2,
    },
    {
        "id": "1-3",
        "name": "1-3 교실",
        "club": "봉사 동아리",
        "summary": "학교 안팎에서 봉사 활동을 기획하고 실천하는 동아리입니다.",
        "detail": """
- 주요 활동: 교내 환경 정리, 지역 봉사, 기부 캠페인
- 운영 시간: 격주 금요일 7~8교시
- 담당 교사: 장나눔 선생님
- 모집 대상: 봉사를 통해 보람을 느끼고 싶은 학생
        """,
        "row": 3,
        "col": 3,
    },
]

# ----- 간단한 스타일(배치도 타일 예쁘게) -----
st.markdown(
    """
    <style>
    .room-box {
        padding: 0.75rem 0.9rem;
        border-radius: 0.8rem;
        border: 1px solid #e0e0e0;
        background-color: #f9fafb;
        text-align: center;
        font-size: 0.9rem;
        height: 100%;
    }
    .room-name {
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .room-club {
        font-size: 0.8rem;
        color: #555;
        margin-bottom: 0.5rem;
        min-height: 2.2em;
    }
    .room-btn button {
        width: 100%;
        border-radius: 999px !important;
    }
    .floor-label {
        font-weight: 600;
        margin: 1.2rem 0 0.4rem 0;
        font-size: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----- 헤더 -----
st.title("배재중학교 동아리 발표회")
st.write(
    "아래 배치도에서 **교실(부스)**를 클릭하면, 해당 동아리 소개가 팝업으로 나타납니다. 😊"
)

st.divider()

# ----- 배치도(그리드) 생성 -----
max_row = max(r["row"] for r in ROOMS)
max_col = max(r["col"] for r in ROOMS)

# 층 이름 예시 (원하면 수정 가능)
floor_names = {
    1: "3층",
    2: "2층",
    3: "1층",
}

for row in range(1, max_row + 1):
    # 층 라벨
    floor_label = floor_names.get(row, f"{row}층")
    st.markdown(f'<div class="floor-label">🏫 {floor_label}</div>', unsafe_allow_html=True)

    cols = st.columns(max_col, gap="small")
    for col in range(1, max_col + 1):
        with cols[col - 1]:
            room = next(
                (rm for rm in ROOMS if rm["row"] == row and rm["col"] == col),
                None,
            )
            if room:
                with st.container():
                    st.markdown('<div class="room-box">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="room-name">{room["name"]}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="room-club">{room["club"]}</div>',
                        unsafe_allow_html=True,
                    )
                    # 버튼(클릭 시 모달 오픈)
                    btn_key = f"btn_{room['id']}"
                    clicked = st.button(
                        "자세히 보기",
                        key=btn_key,
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

                    if clicked:
                        st.session_state["modal_room_id"] = room["id"]
            else:
                st.empty()

st.divider()

st.caption("※ 실제 배치와 다를 수 있으며, 동아리·교실 정보는 예시입니다. 필요한 대로 코드를 수정해서 사용하세요.")

# ----- 모달(팝업) -----
if "modal_room_id" in st.session_state:
    selected_id = st.session_state["modal_room_id"]
    selected_room = next((rm for rm in ROOMS if rm["id"] == selected_id), None)

    if selected_room:
        with st.modal(f"{selected_room['name']} · {selected_room['club']}"):
            st.subheader(selected_room["club"])
            st.write(f"**위치:** {selected_room['name']}")
            st.write(selected_room["summary"])
            st.markdown("---")
            st.markdown(selected_room["detail"])

            st.info("※ 이 영역에 활동 사진, 시간표, 행사 일정 등을 더 넣어도 좋아요!")

            if st.button("닫기", use_container_width=True):
                st.session_state.pop("modal_room_id", None)
                st.rerun()
