import re
import urllib.parse
from urllib.parse import urlparse, parse_qs
import pandas as pd
import streamlit as st

st.set_page_config(page_title="배재중학교 동아리 발표회", layout="wide")
st.title("배재중학교 동아리 발표회")

# ────────────────────────────────────────────────────────────────────────────────
# 전역 CSS: 균일 카드 + 호버 풍선 + 클릭 Popover(같은 탭 유지; form+button)
# ────────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.booth-form { margin: 0; }
.booth-form input[type="hidden"] { display:none; }

/* 카드 버튼 */
button.booth {
  position: relative;
  display: block;
  width: 100%;
  height: 130px;
  border: 1px solid #e6e6e6;
  border-radius: 12px;
  background: #ffffff;
  box-sizing: border-box;
  overflow: hidden;
  cursor: pointer;
  padding: 0;
}
button.booth:hover { border-color: #bdbdbd; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

/* 장소(상단 중앙) */
button.booth .loc {
  position: absolute;
  top: 8px; left: 50%; transform: translateX(-50%);
  font-weight: 700; font-size: 0.95rem; color: #333; text-align: center;
  padding: 0 6px; max-width: 90%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
/* 동아리(정중앙 살짝 위) */
button.booth .club {
  position: absolute;
  top: 50%; left: 50%; transform: translate(-50%, -40%);
  font-size: 1.0rem; font-weight: 500; color: #111; text-align: center;
  padding: 0 8px; max-width: 92%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* 호버 풍선 */
button.booth .hover-pop {
  position: absolute;
  left: 50%;
  bottom: 6px;
  transform: translateX(-50%) translateY(8px);
  background: #1f2937; color: #fff;
  padding: 8px 10px; font-size: 0.85rem; border-radius: 10px; line-height: 1.25;
  max-width: 92%; text-align: center; opacity: 0; pointer-events: none;
  transition: opacity .12s ease, transform .12s ease;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
button.booth .hover-pop::after {
  content: ""; position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%);
  border-width: 6px 6px 0 6px; border-style: solid;
  border-color: #1f2937 transparent transparent transparent;
}
button.booth:hover .hover-pop { opacity: 1; transform: translateX(-50%) translateY(0); }

/* 클릭 Popover(카드 아래) */
div.fixed-pop {
  background:#fff; border:1px solid #e5e7eb; border-radius:12px;
  padding: 12px 14px; margin-top: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.08);
}
div.fixed-pop h4 { margin:0 0 6px 0; }
div.fixed-pop .meta { color:#6b7280; font-size:0.9rem; margin-bottom:8px; }

@media (max-width: 640px) {
  button.booth { height: 110px; }
  button.booth .loc { font-size: 0.9rem; }
  button.booth .club { font-size: 0.95rem; }
}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# 시트 URL (내부): ?sheet=... → st.secrets["SHEET_URL"] → 기본값(공유 URL)
# 상세 시트: 같은 문서의 '시트명' 지정 우선순위
#   1) ?details_sheet=세부시트명
#   2) st.secrets["DETAILS_SHEET_NAME"]
#   3) 후보 자동 탐색 ["동아리정보","동아리상세","세부내용","Details","details"]
# ────────────────────────────────────────────────────────────────────────────────
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1dJr5dVJ50-FPD1WD2_TDwuQOK-wFjPrSBs6PYmQlEAU/edit?usp=sharing"
DETAIL_SHEET_CANDIDATES = ["동아리정보","동아리상세","세부내용","Details","details"]

def get_qp() -> dict:
    return st.experimental_get_query_params()

def pick_url(qp_key: str, secret_key: str, default: str = "") -> str:
    qp = get_qp()
    if qp_key in qp and qp[qp_key] and qp[qp_key][0].strip():
        return qp[qp_key][0].strip()
    try:
        sec = st.secrets.get(secret_key, "").strip()
        if sec:
            return sec
    except Exception:
        pass
    return default

SHEET_URL = pick_url("sheet", "SHEET_URL", DEFAULT_SHEET_URL)

def pick_details_sheet_name() -> str | None:
    qp = get_qp()
    if "details_sheet" in qp and qp["details_sheet"] and qp["details_sheet"][0].strip():
        return qp["details_sheet"][0].strip()
    try:
        sec = st.secrets.get("DETAILS_SHEET_NAME", "").strip()
        if sec:
            return sec
    except Exception:
        pass
    return None  # 없으면 후보 자동탐색

DETAILS_SHEET_NAME = pick_details_sheet_name()

# ────────────────────────────────────────────────────────────────────────────────
# Google Sheets → CSV
#  - 본문(배치): export?format=csv (첫 번째 시트)
#  - 상세: gviz/tq?tqx=out:csv&sheet=<시트이름> (시트명을 이용해 안전하게 접근)
# ────────────────────────────────────────────────────────────────────────────────
def extract_sheet_id(google_sheet_url: str) -> str | None:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheet_url)
    return m.group(1) if m else None

def to_main_csv_url(google_sheet_url: str) -> str:
    sheet_id = extract_sheet_id(google_sheet_url)
    if not sheet_id:
        return google_sheet_url
    # 첫 번째 시트 CSV
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

def to_details_csv_url(google_sheet_url: str, sheet_name: str) -> str:
    sheet_id = extract_sheet_id(google_sheet_url)
    if not sheet_id:
        return google_sheet_url
    # gviz API: 시트명을 직접 지정
    quoted = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quoted}"

@st.cache_data(ttl=300)
def load_csv(url: str, header=None) -> pd.DataFrame:
    df = pd.read_csv(url, header=header, dtype=str)
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.where(pd.notnull(df), None)
    return df

# ────────────────────────────────────────────────────────────────────────────────
# 5층 1-7반(교실) 제외 규칙
# ────────────────────────────────────────────────────────────────────────────────
_pos_17_re = re.compile(r"^1[\-\s]?7(?:\s*반|\s*교실)?$", re.IGNORECASE)
def is_excluded_booth(floor_label: str, pos: str) -> bool:
    if not floor_label or not pos: return False
    m = re.search(r"(\d+)", str(floor_label))
    floor_num = int(m.group(1)) if m else None
    if floor_num == 5 and _pos_17_re.match(str(pos)):
        return True
    return False

# ────────────────────────────────────────────────────────────────────────────────
# 이름 보정(별칭/오타)
# ────────────────────────────────────────────────────────────────────────────────
def normalize_club_name(name: str | None) -> str:
    if not name: return ""
    s = name.strip()
    # 시트 오타 교정: '음-세-듣' → '음-세-들'
    if s == "음-세-듣":
        s = "음-세-들"
    return s

ALIAS_TO_CANON = {
    "음-하나": "음악으로 하나되기반",
    "음-세-들": "음악으로 세상 들여다 보기반",
}

# ────────────────────────────────────────────────────────────────────────────────
# 메인 배치 시트 파싱 (홀수행=장소, 짝수행=동아리) + 5→…→1층 내림차순
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
            club = normalize_club_name(club.strip()) if isinstance(club, str) else club
            if not pos:
                continue
            if is_excluded_booth(floor_label, pos):
                continue
            row_items.append({
                "floor": floor_label or "미지정",
                "pos": pos,
                "club": club or "미정",
                "col_index": c
            })
        if row_items:
            rows_by_floor.setdefault(floor_label or "미지정", []).append(row_items)

    def floor_num(label: str):
        m = re.search(r"(\d+)", str(label))
        return int(m.group(1)) if m else -999999
    floors = sorted(rows_by_floor.keys(), key=lambda x: (-floor_num(x), str(x)))
    return floors, rows_by_floor

# ────────────────────────────────────────────────────────────────────────────────
# 데이터 로드
# ────────────────────────────────────────────────────────────────────────────────
error_box = st.empty()
try:
    main_df = load_csv(to_main_csv_url(SHEET_URL), header=None)  # 1번째 시트
    floors, rows_by_floor = parse_layout(main_df)
except Exception as e:
    error_box.error(f"스프레드시트를 불러오는 중 오류가 발생했습니다.\n\n{e}")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 상세 시트 로드(동일 문서의 '시트명'으로 접근)
# ────────────────────────────────────────────────────────────────────────────────
details_by_club = {}
def try_load_details(sheet_name: str) -> bool:
    try:
        det_df = load_csv(to_details_csv_url(SHEET_URL, sheet_name), header=0)
        # 기대 헤더: 동아리명 / 장소 / 체험유형 / 세부내용
        col_map = { (c.strip() if isinstance(c,str) else c): c for c in det_df.columns }
        # 필수 열 체크
        if not any(k in col_map for k in ["동아리명","동아리","클럽명","club","Club","name","Name"]):
            return False
        # row 매핑
        name_key = next(k for k in ["동아리명","동아리","클럽명","club","Club","name","Name"] if k in col_map)
        for _, row in det_df.iterrows():
            raw = row.get(col_map[name_key])
            club_name = normalize_club_name(raw.strip() if isinstance(raw,str) else raw)
            if not club_name:
                continue
            # 별칭 → 표준명
            canon = ALIAS_TO_CANON.get(club_name, club_name)
            details_by_club[canon] = {
                "장소": row.get(col_map.get("장소", ""), ""),
                "체험유형": row.get(col_map.get("체험유형", ""), ""),
                "세부내용": row.get(col_map.get("세부내용", ""), ""),
            }
        return True
    except Exception:
        return False

loaded = False
if DETAILS_SHEET_NAME:
    loaded = try_load_details(DETAILS_SHEET_NAME)
if not loaded:
    # 후보 이름 자동 탐색
    for cand in DETAIL_SHEET_CANDIDATES:
        if try_load_details(cand):
            loaded = True
            break
if not loaded:
    st.warning("동아리 상세 시트를 찾지 못했습니다. URL 뒤에 `&details_sheet=세부시트명`을 붙이거나, Secrets에 `DETAILS_SHEET_NAME`을 설정해주세요.")

# ────────────────────────────────────────────────────────────────────────────────
# 상단 메뉴: 층 선택 + 동아리 선택(ㄱㄴㄷ 정렬)
# ────────────────────────────────────────────────────────────────────────────────
club_set = set()
for _f, rows in rows_by_floor.items():
    for row in rows:
        for it in row:
            c = (it["club"] or "").strip()
            if c and c != "미정":
                # 별칭 표준화
                club_set.add(ALIAS_TO_CANON.get(c, c))
clubs_sorted = sorted(club_set)

left, right = st.columns([2, 3])
with left:
    sel_floor = st.selectbox("층 선택", options=["전체"] + floors, index=0)
with right:
    sel_club = st.selectbox("동아리 선택", options=["전체"] + clubs_sorted, index=0,
                            help="스크롤해서 동아리명을 선택하세요.")

st.caption("• 호버=풍선 미리보기 / 클릭=같은 탭에서 카드 아래 Popover (상세: 2번째 시트 매칭)")

# ────────────────────────────────────────────────────────────────────────────────
# 선택 상태: ?sel=... (클릭 시)
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

qparams = get_qp()
sel_param = qparams.get("sel", [None])[0]
current_sel = decode_sel(sel_param) if sel_param else None

def same_item(a, b) -> bool:
    if not a or not b: return False
    return (a["floor"] == b["floor"] and a["col_index"] == b["col_index"]
            and a["pos"] == b["pos"] and a["club"] == b["club"])

# ────────────────────────────────────────────────────────────────────────────────
# 카드/Popover
# ────────────────────────────────────────────────────────────────────────────────
def booth_card_html(item: dict) -> str:
    # 팝업 매칭을 위해 별칭 → 표준명으로 hover에 표시(시각 통일)
    club_display = ALIAS_TO_CANON.get(item["club"], item["club"])
    sel = encode_sel({**item, "club": club_display})
    loc = (item["pos"] or "").replace("<", "&lt;").replace(">", "&gt;")
    club = (club_display or "미정").replace("<", "&lt;").replace(">", "&gt;")
    hover_text = f"{loc} · {club}"
    return f'''
    <form class="booth-form" method="get">
      <input type="hidden" name="sel" value="{sel}">
      <button class="booth" type="submit">
        <span class="loc">{loc}</span>
        <span class="club">{club}</span>
        <span class="hover-pop">{hover_text}</span>
      </button>
    </form>
    '''

def render_fixed_popover(item: dict):
    # 선택된 아이템의 동아리명도 별칭 정규화 → 표준명으로 상세를 찾음
    canon_name = ALIAS_TO_CANON.get(item["club"], item["club"])
    detail = details_by_club.get(canon_name, {}) if details_by_club else {}

    st.markdown('<div class="fixed-pop">', unsafe_allow_html=True)
    st.markdown(f"<h4>🔎 {item['pos']} | {canon_name}</h4>", unsafe_allow_html=True)
    st.markdown(f'<div class="meta">층: <b>{item["floor"]}</b> · 교실/위치: <b>{item["pos"]}</b></div>', unsafe_allow_html=True)

    # 상세 표시 (없으면 안내)
    if detail:
        if detail.get("체험유형"):
            st.markdown(f"**체험유형**: {detail.get('체험유형')}")
        if detail.get("세부내용"):
            st.markdown(f"**세부내용**: {detail.get('세부내용')}")
        if detail.get("장소"):
            st.caption(f"참고 장소: {detail.get('장소')}")
    else:
        st.info("세부 내용이 아직 연결되지 않았습니다. 2번째 시트(동아리명/장소/체험유형/세부내용)를 확인해주세요.")

    col1, col2 = st.columns([1,5])
    with col1:
        if st.button("닫기", key=f"close-{item['floor']}-{item['col_index']}-{item['pos']}", use_container_width=True):
            new_qp = dict(get_qp())
            new_qp.pop("sel", None)
            st.experimental_set_query_params(**new_qp)
    st.markdown("</div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# 필터/렌더
# ────────────────────────────────────────────────────────────────────────────────
def match_filters(item, sel_club_val):
    display_name = ALIAS_TO_CANON.get(item["club"], item["club"])
    if sel_club_val != "전체" and display_name != sel_club_val:
        return False
    return True

def render_floor(floor_label, rows, sel_club_val):
    st.subheader(f"🧭 {floor_label}")
    for row_items in rows:
        visible = [x for x in row_items if match_filters(x, sel_club_val)]
        if not visible: continue
        visible.sort(key=lambda x: x["col_index"])
        cols = st.columns(len(visible))
        for i, item in enumerate(visible):
            with cols[i]:
                st.markdown(booth_card_html(item), unsafe_allow_html=True)
                # current_sel은 이미 별칭→표준화된 이름이 들어올 수 있어 동일성 비교 시 표준화 반영
                normalized_current = None
                if current_sel:
                    normalized_current = {**current_sel, "club": ALIAS_TO_CANON.get(current_sel["club"], current_sel["club"])}
                normalized_item = {**item, "club": ALIAS_TO_CANON.get(item["club"], item["club"])}
                if same_item(normalized_item, normalized_current):
                    render_fixed_popover(normalized_item)

# 렌더 (floors는 5→…→1 내림차순)
if sel_floor == "전체":
    for f in floors:
        render_floor(f, rows_by_floor[f], sel_club)
else:
    render_floor(sel_floor, rows_by_floor.get(sel_floor, []), sel_club)

st.write("")
st.caption("데이터 원본: 1번째 시트=배치 / 2번째 시트=동아리 상세 (5층 1-7반 제외, 5→…→1 내림차순)")
