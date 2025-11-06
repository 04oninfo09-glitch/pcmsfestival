import io
import re
import urllib.parse
from typing import Dict, List, Tuple

import pandas as pd
import requests
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────────
# 기본 설정
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="배재중학교 동아리 발표회", layout="wide")
st.title("배재중학교 동아리 발표회")

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1dJr5dVJ50-FPD1WD2_TDwuQOK-wFjPrSBs6PYmQlEAU/edit?usp=sharing"
MAIN_SHEET_NAME    = "실내 부스 배치도"     # 1번 시트 이름
DETAILS_SHEET_NAME = "동아리 활동 설명"     # 2번 시트 이름

# ────────────────────────────────────────────────────────────────────────────────
# 유틸
# ────────────────────────────────────────────────────────────────────────────────
def qp() -> Dict[str, List[str]]:
    return st.experimental_get_query_params()

def extract_sheet_id(google_sheet_url: str) -> str | None:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheet_url)
    return m.group(1) if m else None

def csv_url_by_sheet_name(google_sheet_url: str, sheet_name: str) -> str:
    """
    시트명으로 CSV를 뽑는 안정적인 방법 (gviz/tq)
    """
    sid = extract_sheet_id(google_sheet_url)
    qname = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={qname}"

# 보이지 않는 공백/컨트롤 제거 + 공백 압축
def normalize_spaces(text) -> str:
    if text is None:
        return ""
    if isinstance(text, float) and pd.isna(text):
        return ""
    s = str(text)
    s = s.replace("\ufeff", "")  # BOM
    s = s.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")  # zero width
    s = s.replace("\u00a0", " ")  # NBSP -> space
    s = s.replace("\u3000", " ")  # 전각스페이스 -> space
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\t", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

BLANK_TOKENS = {"-", "—", "–"}
def is_blank(x: str) -> bool:
    t = normalize_spaces(x)
    return t == "" or t in BLANK_TOKENS

def html_escape(t: str) -> str:
    t = normalize_spaces(t)
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

# 오타/별칭 보정
def normalize_club_name(name: str) -> str:
    name = normalize_spaces(name)
    if name == "음-세-듣":
        name = "음-세-들"
    return name

ALIAS_TO_CANON = {
    "음-하나": "음악으로 하나되기반",
    "음-세-들": "음악으로 세상 들여다 보기반",
}

# 5층 1-7 제외
_pos_17_re = re.compile(r"^1[\-\s]?7(?:\s*반|\s*교실)?$", re.IGNORECASE)
def is_excluded_booth(floor_label: str, pos: str) -> bool:
    if is_blank(floor_label) or is_blank(pos):
        return False
    m = re.search(r"(\d+)", str(floor_label))
    floor_num = int(m.group(1)) if m else None
    return bool(floor_num == 5 and _pos_17_re.match(str(pos)))

# ────────────────────────────────────────────────────────────────────────────────
# 데이터 로더(완전 신규): requests로 CSV 직접 로드
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_sheet_csv(url: str) -> pd.DataFrame:
    """
    url: gviz/tq?tqx=out:csv&sheet=시트명
    """
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    # UTF-8-SIG도 자동 처리
    content = resp.content
    df = pd.read_csv(io.BytesIO(content), dtype=str, header=None, keep_default_na=False)
    # keep_default_na=False 덕분에 빈칸은 ""로 들어옴 → normalize_spaces에서 처리
    return df

# ────────────────────────────────────────────────────────────────────────────────
# 파서(새로 작성): A열=층, B열~ / 홀수행=위치, 짝수행=동아리
#   - A열에 '층' 텍스트가 있는 행을 위치행으로 간주하고, 그 다음 행을 동아리행으로 매칭
#   - 공백/보이지 않는 공백만 있으면 제외
# ────────────────────────────────────────────────────────────────────────────────
def parse_layout(df: pd.DataFrame) -> Tuple[List[str], Dict[str, List[List[Dict]]]]:
    rows_by_floor: Dict[str, List[List[Dict]]] = {}
    n_rows, n_cols = df.shape
    data_start_col = 1  # B열부터 데이터

    r = 0
    while r < n_rows:
        # 위치행 후보
        row_pos = df.iloc[r] if r < n_rows else None
        if row_pos is None:
            r += 1
            continue

        floor_label = normalize_spaces(row_pos.iloc[0] if 0 < len(row_pos) else "")
        # A열이 텅 빈 줄이면 다음 줄로
        if is_blank(floor_label):
            r += 1
            continue

        # 동아리행은 바로 다음 줄
        if r + 1 >= n_rows:
            break
        row_club = df.iloc[r + 1]

        # 실제 데이터 추출
        row_items: List[Dict] = []
        for c in range(data_start_col, n_cols):
            pos  = normalize_spaces(row_pos.iloc[c] if c < len(row_pos) else "")
            club = normalize_club_name(row_club.iloc[c] if c < len(row_club) else "")

            if is_blank(pos) or is_blank(club):
                continue
            if is_excluded_booth(floor_label, pos):
                continue

            row_items.append({
                "floor": floor_label,
                "pos": pos,
                "club": club,
                "col_index": c,
            })

        if row_items:
            rows_by_floor.setdefault(floor_label, []).append(row_items)

        # 다음 페어로 이동(2줄 점프)
        r += 2

    # 층 내림차순(5→…→1)
    def floor_num(label: str) -> int:
        m = re.search(r"(\d+)", str(label))
        return int(m.group(1)) if m else -999999

    floors = sorted(rows_by_floor.keys(), key=lambda x: (-floor_num(x), str(x)))
    return floors, rows_by_floor

# ────────────────────────────────────────────────────────────────────────────────
# 상세 시트 로드
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_details(google_sheet_url: str, sheet_name: str) -> Dict[str, Dict[str, str]]:
    url = csv_url_by_sheet_name(google_sheet_url, sheet_name)
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    df = pd.read_csv(io.BytesIO(resp.content), dtype=str, header=0, keep_default_na=False)

    # 헤더 정규화
    df.columns = [normalize_spaces(c) for c in df.columns]
    name_key = None
    for k in ["동아리명", "동아리", "클럽명", "club", "Club", "name", "Name"]:
        if k in df.columns:
            name_key = k
            break

    details_map: Dict[str, Dict[str, str]] = {}
    if not name_key:
        return details_map

    for _, row in df.iterrows():
        club_raw = normalize_club_name(row.get(name_key, ""))
        if is_blank(club_raw):
            continue
        canon = ALIAS_TO_CANON.get(club_raw, club_raw)
        details_map[canon] = {
            "장소":     normalize_spaces(row.get("장소", "")),
            "체험유형": normalize_spaces(row.get("체험유형", "")),
            "세부내용": normalize_spaces(row.get("세부내용", "")),
        }
    return details_map

# ────────────────────────────────────────────────────────────────────────────────
# 데이터 로드 & 파싱
# ────────────────────────────────────────────────────────────────────────────────
sheet_url = DEFAULT_SHEET_URL  # 고정
main_csv = csv_url_by_sheet_name(sheet_url, MAIN_SHEET_NAME)
try:
    main_df = load_sheet_csv(main_csv)
    floors, rows_by_floor = parse_layout(main_df)
except Exception as e:
    st.error(f"배치 시트를 불러오는 중 오류가 발생했습니다.\n\n{e}")
    st.stop()

details_by_club = {}
try:
    details_by_club = load_details(sheet_url, DETAILS_SHEET_NAME)
except Exception as e:
    st.warning(f"상세 시트를 불러오지 못했습니다. 시트명 '{DETAILS_SHEET_NAME}'를 확인해주세요. 오류: {e}")

# 디버그 보기(토글)
with st.expander("🔍 디버그 보기(파싱 결과 샘플)"):
    total_items = sum(len(row) for rows in rows_by_floor.values() for row in rows)
    st.write(f"총 층 수: {len(floors)} / 파싱된 부스 열(카드) 묶음 수: {total_items}")
    # 샘플 10개만 표로
    sample = []
    for f in floors:
        for row in rows_by_floor[f]:
            for item in row:
                sample.append({"층": item["floor"], "위치": item["pos"], "동아리": item["club"]})
                if len(sample) >= 10:
                    break
            if len(sample) >= 10: break
        if len(sample) >= 10: break
    if sample:
        st.dataframe(pd.DataFrame(sample))

# ────────────────────────────────────────────────────────────────────────────────
# 상단 필터 (층 / 동아리)
# ────────────────────────────────────────────────────────────────────────────────
club_set = set()
for _f, rows in rows_by_floor.items():
    for row in rows:
        for it in row:
            club_set.add(ALIAS_TO_CANON.get(it["club"], it["club"]))
clubs_sorted = sorted([c for c in club_set if not is_blank(c)])

c1, c2 = st.columns([2, 3])
with c1:
    sel_floor = st.selectbox("층 선택", options=["전체"] + floors, index=0)
with c2:
    sel_club  = st.selectbox("동아리 선택", options=["전체"] + clubs_sorted, index=0)

st.caption(f"• 데이터: '{MAIN_SHEET_NAME}' / 상세: '{DETAILS_SHEET_NAME}'  • 공백/제로폭 문자 정규화 적용  • 5층 1-7 제외  • 5→…→1 정렬")

# ────────────────────────────────────────────────────────────────────────────────
# 렌더(균일 카드 + 호버 풍선 + 같은 탭 팝업)
# ────────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.booth-form { margin: 0; }
.booth-form input[type="hidden"] { display:none; }
button.booth {
  position: relative; display: block; width: 100%; height: 130px;
  border: 1px solid #e6e6e6; border-radius: 12px; background: #fff;
  box-sizing: border-box; overflow: hidden; cursor: pointer; padding: 0;
}
button.booth:hover { border-color: #bdbdbd; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
button.booth .loc {
  position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
  font-weight: 700; font-size: 0.95rem; color: #333; text-align: center;
  padding: 0 6px; max-width: 90%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
button.booth .club {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -40%);
  font-size: 1.0rem; font-weight: 500; color: #111; text-align: center;
  padding: 0 8px; max-width: 92%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
button.booth .hover-pop {
  position: absolute; left: 50%; bottom: 6px; transform: translateX(-50%) translateY(8px);
  background: #1f2937; color: #fff; padding: 8px 10px; font-size: 0.85rem;
  border-radius: 10px; line-height: 1.25; max-width: 92%; text-align: center; opacity: 0;
  pointer-events: none; transition: opacity .12s ease, transform .12s ease;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
button.booth .hover-pop::after {
  content: ""; position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%);
  border-width: 6px 6px 0 6px; border-style: solid; border-color: #1f2937 transparent transparent transparent;
}
button.booth:hover .hover-pop { opacity: 1; transform: translateX(-50%) translateY(0); }
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

def booth_card_html(item: Dict) -> str:
    loc  = html_escape(item["pos"])
    club = html_escape(ALIAS_TO_CANON.get(item["club"], item["club"]))
    hover = f"{loc} · {club}"
    # 같은 탭 팝업을 위해 쿼리파라미터 sel 사용
    payload = urllib.parse.quote(f"{item['floor']}|{item['col_index']}|{item['pos']}|{ALIAS_TO_CANON.get(item['club'], item['club'])}", safe='')
    return f"""
    <form class="booth-form" method="get">
      <input type="hidden" name="sel" value="{payload}">
      <button class="booth" type="submit">
        <span class="loc">{loc}</span>
        <span class="club">{club}</span>
        <span class="hover-pop">{hover}</span>
      </button>
    </form>
    """

def decode_sel(sparam: str) -> Dict | None:
    try:
        sparam = urllib.parse.unquote(sparam or "")
        floor, col, pos, club = sparam.split("|", 4)
        return {"floor": floor, "col_index": int(col), "pos": pos, "club": club}
    except Exception:
        return None

def same_item(a: Dict, b: Dict) -> bool:
    if not a or not b: return False
    return (a["floor"] == b["floor"] and a["col_index"] == b["col_index"]
            and a["pos"] == b["pos"] and a["club"] == b["club"])

qparams = qp()
current_sel = decode_sel(qparams.get("sel", [None])[0])

def render_popover(item: Dict):
    canon_name = ALIAS_TO_CANON.get(item["club"], item["club"])
    detail = details_by_club.get(canon_name, {})

    st.markdown('<div class="fixed-pop">', unsafe_allow_html=True)
    st.markdown(f"<h4>🔎 {html_escape(item['pos'])} | {html_escape(canon_name)}</h4>", unsafe_allow_html=True)
    st.markdown(f'<div class="meta">층: <b>{html_escape(item["floor"])}</b> · 교실/위치: <b>{html_escape(item["pos"])}</b></div>', unsafe_allow_html=True)

    if detail:
        if not is_blank(detail.get("체험유형","")):
            st.markdown(f"**체험유형**: {html_escape(detail.get('체험유형'))}")
        if not is_blank(detail.get("세부내용","")):
            st.markdown(f"**세부내용**: {html_escape(detail.get('세부내용'))}")
        if not is_blank(detail.get("장소","")):
            st.caption(f"참고 장소: {html_escape(detail.get('장소'))}")
    else:
        st.info("세부 내용이 아직 연결되지 않았습니다. '동아리 활동 설명' 시트를 확인해주세요.")

    col1, _ = st.columns([1,5])
    with col1:
        if st.button("닫기", key=f"close-{item['floor']}-{item['col_index']}-{item['pos']}", use_container_width=True):
            new_q = dict(qparams)
            new_q.pop("sel", None)
            st.experimental_set_query_params(**new_q)
    st.markdown("</div>", unsafe_allow_html=True)

def pass_filter(item: Dict) -> bool:
    if sel_club != "전체":
        return ALIAS_TO_CANON.get(item["club"], item["club"]) == sel_club
    return True

def render_floor(floor_label: str, rows: List[List[Dict]]):
    st.subheader(f"🧭 {floor_label}")
    for row in rows:
        visible = [x for x in row if pass_filter(x)]
        if not visible: 
            continue
        visible.sort(key=lambda x: x["col_index"])
        cols = st.columns(len(visible))
        for i, it in enumerate(visible):
            with cols[i]:
                st.markdown(booth_card_html(it), unsafe_allow_html=True)
                # 같은 탭 팝업
                if current_sel:
                    # 비교 시 club은 정규화해 동일 기준으로
                    norm_current = {**current_sel, "club": ALIAS_TO_CANON.get(current_sel["club"], current_sel["club"])}
                    norm_item    = {**it,         "club": ALIAS_TO_CANON.get(it["club"], it["club"])}
                    if same_item(norm_item, norm_current):
                        render_popover(norm_item)

# 렌더
if sel_floor == "전체":
    for f in floors:  # 5→…→1 정렬
        render_floor(f, rows_by_floor.get(f, []))
else:
    render_floor(sel_floor, rows_by_floor.get(sel_floor, []))

st.caption("• 공백/제로폭/개행 정규화 완료 · 공백만 있는 셀 제외 · 5층 1-7 제외 · 같은 탭 팝업")
