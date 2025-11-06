import re
import urllib.parse
from urllib.parse import urlparse, parse_qs
import pandas as pd
import streamlit as st

st.set_page_config(page_title="배재중학교 동아리 발표회", layout="wide")
st.title("배재중학교 동아리 발표회")

# ────────────────────────────────────────────────────────────────────────────────
# 전역 CSS: 균일 카드 + 호버 풍선 + 클릭 고정 Popover
# ────────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 카드 전체 */
a.booth {
  position: relative;
  display: block;
  width: 100%;
  height: 130px;                 /* 박스 높이 */
  border: 1px solid #e6e6e6;
  border-radius: 12px;
  text-decoration: none;
  background: #ffffff;
  box-sizing: border-box;
  overflow: hidden;
}
a.booth:hover { border-color: #bdbdbd; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

/* 장소(상단 중앙) */
a.booth .loc {
  position: absolute;
  top: 8px; left: 50%; transform: translateX(-50%);
  font-weight: 700; font-size: 0.95rem; color: #333; text-align: center;
  padding: 0 6px; max-width: 90%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
/* 동아리(정중앙 살짝 위) */
a.booth .club {
  position: absolute;
  top: 50%; left: 50%; transform: translate(-50%, -40%);
  font-size: 1.0rem; font-weight: 500; color: #111; text-align: center;
  padding: 0 8px; max-width: 92%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* 호버 풍선 미리보기 */
a.booth .hover-pop {
  position: absolute;
  left: 50%;
  bottom: 6px;                   /* 카드 하단에서 살짝 위 */
  transform: translateX(-50%) translateY(8px);
  background: #1f2937;           /* 진회색 */
  color: #fff;
  padding: 8px 10px;
  font-size: 0.85rem;
  border-radius: 10px;
  line-height: 1.25;
  max-width: 92%;
  text-align: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity .12s ease, transform .12s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
a.booth .hover-pop::after {
  content: "";
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 6px 6px 0 6px;
  border-style: solid;
  border-color: #1f2937 transparent transparent transparent;
}
a.booth:hover .hover-pop {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* 클릭 고정 Popover(카드 아래에 렌더) */
div.fixed-pop {
  background:#fff; border:1px solid #e5e7eb; border-radius:12px;
  padding: 12px 14px; margin-top: 8px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.08);
}
div.fixed-pop h4 { margin:0 0 6px 0; }
div.fixed-pop .meta { color:#6b7280; font-size:0.9rem; margin-bottom:8px; }

@media (max-width: 640px) {
  a.booth { height: 110px; }
  a.booth .loc { font-size: 0.9rem; }
  a.booth .club { font-size: 0.95rem; }
}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# 시트 URL(내부) : ?sheet=... → st.secrets["SHEET_URL"] → 기본값
# ────────────────────────────────────────────────────────────────────────────────
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1dJr5dVJ50-FPD1WD2_TDwuQOK-wFjPrSBs6PYmQlEAU/edit?usp=sharing"

def get_sheet_url() -> str:
    q = st.experimental_get_query_params()
    if "sheet" in q and q["sheet"] and q["sheet"][0].strip():
        return q["sheet"][0].strip()
    try:
        sec = st.secrets.get("SHEET_URL", "").strip()
        if sec:
            return sec
    except Exception:
        pass
    return DEFAULT_SHEET_URL

SHEET_URL = get_sheet_url()

# ────────────────────────────────────────────────────────────────────────────────
# 구글시트 로드(CSV export)
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
        frag_gid = re.search(r"gid=(\\d+)", parsed.fragment)
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

# ────────────────────────────────────────────────────────────────────────────────
# 5층 1-7반(교실) 제외 규칙
# ────────────────────────────────────────────────────────────────────────────────
_pos_17_re = re.compile(r"^1[\\-\\s]?7(?:\\s*반|\\s*교실)?$", re.IGNORECASE)
def is_excluded_booth(floor_label: str, pos: str) -> bool:
    if not floor_label or not pos: return False
    m = re.search(r"(\\d+)", str(floor_label))
    floor_num = int(m.group(1)) if m else None
    if floor_num == 5 and _pos_17_re.match(str(pos)):
        return True
    return False

# ────────────────────────────────────────────────────────────────────────────────
# 시트 파싱(홀수행=장소, 짝수행=동아리)
# ────────────────────────────────────────────────────────────────────────────────
def parse_layout(df: pd.DataFrame):
    rows_by_floor = {}
    n_rows, n_cols = df.shape
    for r in range(0, n_rows, 2):
        row_pos = df.iloc[r] if r < n_rows else None
        row_club = df.iloc[r+1] if (r+1) < n_rows else None
        if row_pos is None: continue

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
            if not pos: continue
            if is_excluded_booth(floor_label, pos):  # ★ 5층 1-7 제외
                continue
            row_items.append({
                "floor": floor_label or "미지정",
                "pos": pos,
                "club": club or "미정",
                "col_index": c
            })
        if row_items:
            rows_by_floor.setdefault(floor_label or "미지정", []).append(row_items)

    def floor_key(x: str):
        m = re.search(r"(\\d+)", x)
        return (-int(m.group(1)), x) if m else (0, x)
    floors = sorted(rows_by_floor.keys(), key=floor_key)
    return floors, rows_by_floor

# 데이터 로드 & 파싱
error_box = st.empty()
try:
    raw_df = load_sheet(SHEET_URL)
    floors, rows_by_floor = parse_layout(raw_df)
except Exception as e:
    error_box.error(f"스프레드시트를 불러오는 중 오류가 발생했습니다.\\n\\n{e}")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 메뉴바: 층 선택 + 동아리 선택(ㄱㄴㄷ 정렬)
# ────────────────────────────────────────────────────────────────────────────────
club_set = set()
for _f, rows in rows_by_floor.items():
    for row in rows:
        for it in row:
            c = (it["club"] or "").strip()
            if c and c != "미정":
                club_set.add(c)
clubs_sorted = sorted(club_set)

left, right = st.columns([2, 3])
with left:
    sel_floor = st.selectbox("층 선택", options=["전체"] + floors, index=0)
with right:
    sel_club = st.selectbox("동아리 선택", options=["전체"] + clubs_sorted, index=0, help="스크롤해서 동아리명을 선택하세요.")

st.caption("• 카드 위에 마우스를 올리면 미리보기 풍선이 뜨고, 클릭하면 카드 아래에 Popover가 열립니다.")

# ────────────────────────────────────────────────────────────────────────────────
# 선택 상태: ?sel=... (클릭 시) → 해당 카드 아래에 고정 Popover 렌더
# ────────────────────────────────────────────────────────────────────────────────
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

qparams = st.experimental_get_query_params()
sel_param = qparams.get("sel", [None])[0]
current_sel = decode_sel(sel_param) if sel_param else None

def same_item(a, b) -> bool:
    if not a or not b: return False
    return (a["floor"] == b["floor"] and a["col_index"] == b["col_index"]
            and a["pos"] == b["pos"] and a["club"] == b["club"])

# ────────────────────────────────────────────────────────────────────────────────
# 카드 HTML (호버 풍선 포함)
# ────────────────────────────────────────────────────────────────────────────────
def booth_card_html(item: dict) -> str:
    sel = encode_sel(item)
    href = f"?sel={sel}"
    loc = (item["pos"] or "").replace("<", "&lt;").replace(">", "&gt;")
    club = (item["club"] or "미정").replace("<", "&lt;").replace(">", "&gt;")
    hover_text = f"{loc} · {club}"
    return f'''
    <a class="booth" href="{href}">
      <span class="loc">{loc}</span>
      <span class="club">{club}</span>
      <span class="hover-pop">{hover_text}</span>
    </a>
    '''

# ────────────────────────────────────────────────────────────────────────────────
# 고정 Popover 렌더(카드 바로 아래)
# ────────────────────────────────────────────────────────────────────────────────
def render_fixed_popover(item: dict):
    st.markdown('<div class="fixed-pop">', unsafe_allow_html=True)
    st.markdown(f"<h4>🔎 {item['pos']} | {item['club']}</h4>", unsafe_allow_html=True)
    st.markdown(f'<div class="meta">층: <b>{item["floor"]}</b> · 교실/위치: <b>{item["pos"]}</b></div>', unsafe_allow_html=True)
    st.write("팝업 예시입니다. 스프레드시트에 **소개/담당교사/활동시간/비고** 등을 추가해 연결할 수 있어요.")
    col1, col2 = st.columns([1,5])
    with col1:
        if st.button("닫기", key=f"close-{item['floor']}-{item['col_index']}-{item['pos']}", use_container_width=True):
            new_qp = dict(st.experimental_get_query_params())
            new_qp.pop("sel", None)
            st.experimental_set_query_params(**new_qp)
    st.markdown("</div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# 배치도 렌더(필터: 층/동아리) + 선택된 카드 아래 Popover
# ────────────────────────────────────────────────────────────────────────────────
def match_filters(item):
    if sel_club != "전체" and str(item["club"]) != sel_club:
        return False
    return True

def render_floor(floor_label, rows):
    st.subheader(f"🧭 {floor_label}")
    for row_items in rows:
        visible = [x for x in row_items if match_filters(x)]
        if not visible: continue
        visible.sort(key=lambda x: x["col_index"])
        cols = st.columns(len(visible))
        for i, item in enumerate(visible):
            with cols[i]:
                st.markdown(booth_card_html(item), unsafe_allow_html=True)
                if same_item(item, current_sel):
                    render_fixed_popover(item)

if sel_floor == "전체":
    for f in floors:
        render_floor(f, rows_by_floor[f])
else:
    render_floor(sel_floor, rows_by_floor.get(sel_floor, []))

st.write("")
st.caption("데이터 원본: 구글 스프레드시트 → 5분 캐시")
