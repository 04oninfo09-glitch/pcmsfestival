import re
from urllib.parse import urlparse, parse_qs
import pandas as pd
import streamlit as st

st.set_page_config(page_title="배재중학교 동아리 발표회", layout="wide")

# ── 전역 스타일: 모든 버튼을 동일한 '카드' 크기로 보이게 ─────────────────────────
st.markdown("""
<style>
/* 모든 버튼을 카드처럼 동일한 크기/정렬로 */
div[data-testid="stButton"] > button {
    height: 120px;                 /* ← 고정 높이 (원하면 조절) */
    width: 100%;
    border: 1px solid #e6e6e6;
    border-radius: 12px;
    padding: 10px 12px;
    text-align: center;
    line-height: 1.2;
    white-space: pre-line;          /* \\n 줄바꿈 유지 */
    display: flex;
    flex-direction: column;
    justify-content: space-between; /* 위/아래 줄 간격 균등 */
}
/* 호버/포커스 가시성 */
div[data-testid="stButton"] > button:hover {
    border-color: #bbb;
}
div[data-testid="stButton"] > button:focus {
    outline: 2px solid #A3C4F3;
}
/* 팝업 닫기 버튼은 작게 유지(전역 카드 스타일의 영향 줄이기) */
button[kind="secondary"]#close_popup {
    height: auto !important;
    padding: 6px 10px !important;
}
</style>
""", unsafe_allow_html=True)

TITLE = "배재중학교 동아리 발표회"
st.title(TITLE)

# ────────────────────────────────────────────────────────────────────────────────
# 1) 구글시트 불러오기
# ────────────────────────────────────────────────────────────────────────────────
def to_csv_url(google_sheet_url: str) -> str:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheet_url)
    if not m:
        return google_sheet_url
    sheet_id = m.group(1)
    parsed = urlparse(google_sheet_url)
    q = parse_qs(parsed.query)
    gid = None
    if "gid" in q:
        gid = q["gid"][0]
    elif parsed.fragment:
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
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.where(pd.notnull(df), None)
    return df

sheet_url = st.sidebar.text_input(
    "구글 스프레드시트 URL",
    value="https://docs.google.com/spreadsheets/d/1dJr5dVJ50-FPD1WD2_TDwuQOK-wFjPrSBs6PYmQlEAU/edit?usp=sharing",
    help="A열=층, 홀수행=장소(교실/위치), 짝수행=동아리명 형식으로 작성해 주세요."
)

# ────────────────────────────────────────────────────────────────────────────────
# 2) 시트 파싱 (홀수행: 장소 / 짝수행: 동아리명)
# ────────────────────────────────────────────────────────────────────────────────
def parse_layout(df: pd.DataFrame):
    rows_by_floor = {}
    n_rows, n_cols = df.shape

    for r in range(0, n_rows, 2):
        row_pos = df.iloc[r] if r < n_rows else None
        row_club = df.iloc[r+1] if (r+1) < n_rows else None
        if row_pos is None:
            continue

        floor_label = (row_pos.iloc[0] or "")
        if not floor_label and row_club is not None:
            floor_label = (row_club.iloc[0] or "")
        floor_label = str(floor_label).strip() if floor_label is not None else ""

        row_items = []
        for c in range(1, n_cols):
            pos = row_pos.iloc[c] if row_pos is not None else None
            club = row_club.iloc[c] if row_club is not None else None
            pos = pos.strip() if isinstance(pos, str) else pos
            club = club.strip() if isinstance(club, str) else club
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

    def floor_key(x: str):
        m = re.search(r"(\d+)", x)
        if m:
            return (-int(m.group(1)), x)  # 높은 층이 먼저
        return (0, x)

    floors = sorted(rows_by_floor.keys(), key=floor_key)
    return floors, rows_by_floor

# 데이터 로드
error_box = st.empty()
try:
    raw_df = load_sheet(sheet_url)
    floors, rows_by_floor = parse_layout(raw_df)
except Exception as e:
    error_box.error(f"스프레드시트를 불러오는 중 오류가 발생했습니다.\n\n{e}")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 3) 필터/검색
# ────────────────────────────────────────────────────────────────────────────────
left, right = st.columns([2, 3])
with left:
    sel_floor = st.selectbox("층 선택", options=["전체"] + floors, index=0)
with right:
    q = st.text_input("동아리/장소 검색", value="", placeholder="예: 과학동아리, 3-2반, 체육관...")

st.caption("• 각 네모박스(카드)를 클릭하면 상단에 팝업이 열립니다. (상단=장소, 하단=동아리)")

# 팝업 상태
if "modal_payload" not in st.session_state:
    st.session_state["modal_payload"] = None

def match_query(item, q):
    if not q:
        return True
    ql = q.lower()
    return (ql in str(item["pos"]).lower()) or (ql in str(item["club"]).lower()) or (ql in str(item["floor"]).lower())

# ────────────────────────────────────────────────────────────────────────────────
# 4) 팝업(모달 대체) ─ 상단 카드
# ────────────────────────────────────────────────────────────────────────────────
def render_popup():
    item = st.session_state.get("modal_payload")
    if not item:
        return
    with st.container(border=True):
        st.markdown(f"### 🔎 {item['pos']} | {item['club']}")
        st.markdown(f"- **층**: {item['floor']}")
        st.markdown(f"- **장소(교실/위치)**: {item['pos']}")
        st.markdown(f"- **동아리명**: {item['club']}")
        st.divider()
        st.info("필요하면 스프레드시트에 소개/담당/비고 열을 추가해 이 팝업에 표시할 수 있어요.")
        cols = st.columns([1,6])
        with cols[0]:
            if st.button("닫기", key="close_popup", use_container_width=True):
                st.session_state["modal_payload"] = None

# 현재 선택된 팝업 먼저 그리기
render_popup()

# ────────────────────────────────────────────────────────────────────────────────
# 5) 배치도 렌더링 (균일 박스 + 2행 라벨)
# ────────────────────────────────────────────────────────────────────────────────
def label_two_lines(pos: str, club: str) -> str:
    """
    버튼 라벨을 두 줄로: 1행=장소, 2행=동아리.
    bold/크기 조절은 버튼 내부에서 제한적이라 줄바꿈으로 명확히 구분.
    """
    top = f"{pos}"              # 장소
    bottom = f"{club}"          # 동아리
    return f"{top}\n{bottom}"

def render_floor(floor_label, rows):
    st.subheader(f"🧭 {floor_label}")
    for row_items in rows:
        visible = [x for x in row_items if match_query(x, q)]
        if not visible:
            continue
        visible.sort(key=lambda x: x["col_index"])
        cols = st.columns(len(visible))
        for i, item in enumerate(visible):
            with cols[i]:
                label = label_two_lines(item["pos"], item["club"])
                if st.button(label, key=f"{floor_label}-{item['pos']}-{item['col_index']}", use_container_width=True):
                    st.session_state["modal_payload"] = item
                    render_popup()

if sel_floor == "전체":
    for f in floors:
        render_floor(f, rows_by_floor[f])
else:
    render_floor(sel_floor, rows_by_floor.get(sel_floor, []))

st.write("")
st.caption("데이터 원본: 구글 스프레드시트 → 5분 캐시")
