import re
import urllib.parse
from urllib.parse import urlparse, parse_qs
import pandas as pd
import streamlit as st

st.set_page_config(page_title="배재중학교 동아리 발표회", layout="wide")

TITLE = "배재중학교 동아리 발표회"
st.title(TITLE)

# ────────────────────────────────────────────────────────────────────────────────
# 전역 스타일: 균일 크기의 '클릭 카드' (상단=장소, 중앙=동아리)
# ────────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 카드 컨테이너 그리드에 넣기 전에 a.booth 자체가 카드 형태 */
a.booth {
  position: relative;
  display: block;
  width: 100%;
  height: 130px;                 /* ← 박스 높이(원하면 조절) */
  border: 1px solid #e6e6e6;
  border-radius: 12px;
  text-decoration: none;
  background: #ffffff;
  box-sizing: border-box;
  overflow: hidden;
}

/* 호버 효과 */
a.booth:hover { border-color: #bdbdbd; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

/* 장소(상단, 가운데 정렬) */
a.booth .loc {
  position: absolute;
  top: 8px;                      /* 상단 여백 */
  left: 50%;
  transform: translateX(-50%);
  font-weight: 700;
  font-size: 0.95rem;
  color: #333;
  text-align: center;
  line-height: 1.1;
  padding: 0 6px;
  max-width: 90%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 동아리명(박스 정가운데) */
a.booth .club {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -40%);  /* -40%로 살짝 위로 올려 시각 균형 */
  font-size: 1.0rem;
  font-weight: 500;
  color: #111;
  text-align: center;
  padding: 0 8px;
  max-width: 92%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 모바일/좁은 화면에서 폰트 조금 줄이기 */
@media (max-width: 640px) {
  a.booth { height: 110px; }
  a.booth .loc { font-size: 0.9rem; }
  a.booth .club { font-size: 0.95rem; }
}

/* 상단 팝업 카드 여백 정리 */
div.popup-card { background:#fff; border:1px solid #eee; border-radius:12px; padding:14px 16px; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# 1) 구글시트 불러오기 (CSV export)
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
# 2) 시트 파싱 규칙 (홀수행: 장소 / 짝수행: 동아리)
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
            return (-int(m.group(1)), x)  # 높은 층 먼저
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

st.caption("• 카드(네모박스)를 클릭하면 상단에 상세 팝업이 열립니다. (상단=장소, 한가운데=동아리)")

# ────────────────────────────────────────────────────────────────────────────────
# 4) 선택 상태: 쿼리스트링 sel=... 으로 전달/해석
# ────────────────────────────────────────────────────────────────────────────────
# sel payload를 "floor|col|pos|club" 형태로 인코딩
def encode_sel(item: dict) -> str:
    payload = f"{item['floor']}|{item['col_index']}|{item['pos']}|{item['club']}"
    return urllib.parse.quote(payload, safe='')

def decode_sel(s: str):
    try:
        s = urllib.parse.unquote(s or "")
        floor, col, pos, club = s.split("|", 3)
        return {"floor": floor, "col_index": int(col), "pos": pos, "club": club}
    except Exception:
        return None

# 현재 선택 읽기
sel_param = st.query_params.get("sel", [None])
sel_param = sel_param[0] if isinstance(sel_param, list) else sel_param
current_sel = decode_sel(sel_param) if sel_param else None

# ────────────────────────────────────────────────────────────────────────────────
# 5) 팝업(모달 대체) - 상단 카드
# ────────────────────────────────────────────────────────────────────────────────
def render_popup(selected):
    if not selected:
        return
    with st.container():
        st.markdown('<div class="popup-card">', unsafe_allow_html=True)
        st.markdown(f"### 🔎 {selected['pos']} | {selected['club']}")
        st.markdown(f"- **층**: {selected['floor']}")
        st.markdown(f"- **장소(교실/위치)**: {selected['pos']}")
        st.markdown(f"- **동아리명**: {selected['club']}")
        st.divider()
        st.info("스프레드시트에 소개/담당/비고 열을 추가하면 이 팝업에 더 자세히 표시할 수 있어요.")
        col1, col2 = st.columns([1,5])
        with col1:
            if st.button("닫기", use_container_width=True):
                # sel 파라미터 제거(=팝업 닫기)
                qp = dict(st.query_params)
                qp.pop("sel", None)
                st.query_params.clear()
                st.query_params.update(qp)
        st.markdown("</div>", unsafe_allow_html=True)

render_popup(current_sel)

# ────────────────────────────────────────────────────────────────────────────────
# 6) 배치도 렌더링 (균일 카드 + 위치/동아리 배치)
# ────────────────────────────────────────────────────────────────────────────────
def match_query(item, q):
    if not q:
        return True
    ql = q.lower()
    return (ql in str(item["pos"]).lower()) or (ql in str(item["club"]).lower()) or (ql in str(item["floor"]).lower())

def booth_card_html(item: dict) -> str:
    """
    HTML 카드(링크). 클릭하면 ?sel=... 로 이동해 선택 상태를 만든다.
    카드 내부:
      - .loc : 상단 가운데(굵게)
      - .club: 카드 정가운데(약간 위로)
    """
    sel = encode_sel(item)
    href = f"?sel={sel}"
    loc = (item["pos"] or "").replace("<", "&lt;").replace(">", "&gt;")
    club = (item["club"] or "미정").replace("<", "&lt;").replace(">", "&gt;")
    return f'''
    <a class="booth" href="{href}">
      <span class="loc">{loc}</span>
      <span class="club">{club}</span>
    </a>
    '''

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
                st.markdown(booth_card_html(item), unsafe_allow_html=True)

# 전체/선택 층 렌더링
if sel_floor == "전체":
    for f in floors:
        render_floor(f, rows_by_floor[f])
else:
    render_floor(sel_floor, rows_by_floor.get(sel_floor, []))

st.write("")
st.caption("데이터 원본: 구글 스프레드시트 → 5분 캐시")
