import re
from urllib.parse import urlparse, parse_qs
import pandas as pd
import streamlit as st

st.set_page_config(page_title="배재중학교 동아리 발표회", layout="wide")

TITLE = "배재중학교 동아리 발표회"
st.title(TITLE)

# ────────────────────────────────────────────────────────────────────────────────
# 1) 구글시트 불러오기 (공유: 링크가 있는 모든 사용자가 보기 권장)
#    - 스프레드시트 URL을 CSV export URL로 변환해 pandas로 읽습니다.
# ────────────────────────────────────────────────────────────────────────────────
def to_csv_url(google_sheet_url: str) -> str:
    """
    다양한 형태의 구글스프레드시트 URL을 CSV export URL로 안전 변환
    예) https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit?usp=sharing
        -> https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv
    gid가 지정되면 그 시트 탭만 가져옵니다.
    """
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheet_url)
    if not m:
        return google_sheet_url
    sheet_id = m.group(1)

    # gid 추출
    parsed = urlparse(google_sheet_url)
    q = parse_qs(parsed.query)
    gid = None
    # 일반 edit URL의 경우 fragment나 query에 gid가 있을 수 있음
    if "gid" in q:
        gid = q["gid"][0]
    elif parsed.fragment:
        # ex) .../edit#gid=123456
        frag_gid = re.search(r"gid=(\d+)", parsed.fragment)
        if frag_gid:
            gid = frag_gid.group(1)

    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid:
        base += f"&gid={gid}"
    return base

@st.cache_data(ttl=300)
def load_sheet(url: str) -> pd.DataFrame:
    csv_url = to_csv_url(url)
    df = pd.read_csv(csv_url, header=None, dtype=str)
    # 공백 제거 및 NaN 정리
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.where(pd.notnull(df), None)
    return df

# 사용자가 바꿀 수 있게 사이드바에 URL 입력
sheet_url = st.sidebar.text_input(
    "구글 스프레드시트 URL",
    value="https://docs.google.com/spreadsheets/d/1dJr5dVJ50-FPD1WD2_TDwuQOK-wFjPrSBs6PYmQlEAU/edit?usp=sharing",
    help="A열=층, 홀수행=장소(교실/위치), 짝수행=동아리명 형식으로 작성해 주세요."
)

# ────────────────────────────────────────────────────────────────────────────────
# 2) 시트 파싱 규칙
#    - A열: 층(예: 3F, 2층 등) — 홀수행/짝수행 모두 같은 층 표기 권장
#    - 홀수행(1,3,5...): B열부터 위치명(교실/공간)
#    - 짝수행(2,4,6...): B열부터 동아리명 (위치명과 같은 열에 매칭)
# ────────────────────────────────────────────────────────────────────────────────
def parse_layout(df: pd.DataFrame):
    """
    df: 헤더 없는 표 전체
    return:
      floors: 정렬된 층 목록
      rows_by_floor: { floor_label: [ [ {pos, club, col_index}, ... ] , ... ] }
                     같은 floor 안에서 '한 줄(홀수행+짝수행)' 단위로 끊어서 표시
    """
    rows_by_floor = {}
    n_rows, n_cols = df.shape

    # 두 줄(홀수/짝수) 단위로 읽음
    for r in range(0, n_rows, 2):
        row_pos = df.iloc[r] if r < n_rows else None
        row_club = df.iloc[r+1] if (r+1) < n_rows else None

        if row_pos is None:
            continue

        floor_label = (row_pos.iloc[0] or "").strip() if isinstance(row_pos.iloc[0], str) else (row_pos.iloc[0] or "")
        # 짝수행(동아리명)에도 A열에 층 정보가 들어있다면 우선 홀수행 기준 사용
        if not floor_label and row_club is not None:
            floor_label = (row_club.iloc[0] or "")

        # 최소 한 글자라도 있어야 층으로 봄
        floor_label = str(floor_label).strip() if floor_label is not None else ""

        # B열부터 각 칸(열)마다 위치/클럽 매칭
        row_items = []
        for c in range(1, n_cols):
            pos = None
            club = None
            if row_pos is not None:
                pos = row_pos.iloc[c]
            if row_club is not None:
                club = row_club.iloc[c]
            pos = pos.strip() if isinstance(pos, str) else pos
            club = club.strip() if isinstance(club, str) else club

            # 위치명(교실 등)이 비어 있으면 스킵
            if not pos:
                continue

            row_items.append({
                "floor": floor_label or "미지정",
                "pos": pos,
                "club": club or "미정",
                "col_index": c
            })

        if not row_items:
            continue

        rows_by_floor.setdefault(floor_label or "미지정", []).append(row_items)

    # 층 정렬: 숫자/한글/영문 혼합 가능 → 숫자 우선 추출하여 역정렬(3층→2층→1층)
    def floor_key(x: str):
        m = re.search(r"(\d+)", x)
        if m:
            # 큰 숫자가 위쪽(상층)이라고 가정하여 내림차순용 -int
            return (-int(m.group(1)), x)
        return (0, x)

    floors = sorted(rows_by_floor.keys(), key=floor_key)
    return floors, rows_by_floor

# 데이터 로드 & 파싱
error_box = st.empty()
try:
    raw_df = load_sheet(sheet_url)
    floors, rows_by_floor = parse_layout(raw_df)
except Exception as e:
    error_box.error(f"스프레드시트를 불러오는 중 오류가 발생했습니다.\n\n{e}")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 3) 필터/검색 UI
# ────────────────────────────────────────────────────────────────────────────────
left, right = st.columns([2, 3])
with left:
    sel_floor = st.selectbox("층 선택", options=["전체"] + floors, index=0)
with right:
    q = st.text_input("동아리/장소 검색", value="", placeholder="예: 과학동아리, 3-2반, 체육관...")

st.caption("• 각 사각형 버튼을 클릭하면 해당 동아리 정보가 팝업으로 열립니다.")

# 모달 상태 저장
if "modal_payload" not in st.session_state:
    st.session_state["modal_payload"] = None

# ────────────────────────────────────────────────────────────────────────────────
# 4) 배치도 렌더링
#    - 한 층(floor) 안에서 '한 줄(홀수행+짝수행)'씩 가로로 columns를 만들어 버튼 표시
#    - 검색어가 있으면 해당 줄에서 매칭되는 칸만 남김(없으면 줄 숨김)
# ────────────────────────────────────────────────────────────────────────────────
def match_query(item, q):
    if not q:
        return True
    ql = q.lower()
    return (ql in str(item["pos"]).lower()) or (ql in str(item["club"]).lower()) or (ql in str(item["floor"]).lower())

def render_floor(floor_label, rows):
    st.subheader(f"🧭 {floor_label}")
    for row_items in rows:
        # 검색 필터
        visible = [x for x in row_items if match_query(x, q)]
        if not visible:
            continue

        # 원래 열 순서 유지
        visible.sort(key=lambda x: x["col_index"])

        cols = st.columns(len(visible))
        for i, item in enumerate(visible):
            with cols[i]:
                label = f"**{item['pos']}**\n\n{item['club']}"
                if st.button(label, key=f"{floor_label}-{item['pos']}-{item['col_index']}", use_container_width=True):
                    st.session_state["modal_payload"] = item

# 전체/특정 층 렌더링
if sel_floor == "전체":
    for f in floors:
        render_floor(f, rows_by_floor[f])
else:
    render_floor(sel_floor, rows_by_floor.get(sel_floor, []))

# ────────────────────────────────────────────────────────────────────────────────
# 5) 모달 팝업
# ────────────────────────────────────────────────────────────────────────────────
if st.session_state["modal_payload"] is not None:
    item = st.session_state["modal_payload"]
    with st.modal(f"🔎 {item['pos']} | {item['club']}"):
        st.markdown(f"### {item['club']}")
        st.markdown(f"- **층**: {item['floor']}")
        st.markdown(f"- **장소(교실/위치)**: {item['pos']}")
        st.divider()
        st.info("필요하면 이 공간에 동아리 소개글, 담당교사, 활동 사진 링크 등을 추가할 수 있어요.\n\n스프레드시트에 소개/담당/비고 같은 열을 추가하고 파서에서 읽어오도록 확장 가능합니다.")
        if st.button("닫기", use_container_width=True):
            st.session_state["modal_payload"] = None
else:
    # 아무것도 선택되지 않은 경우 깔끔히 유지
    pass

st.write("")
st.caption("데이터 원본: 구글 스프레드시트 → 5분 캐시")
