import re
import urllib.parse
from urllib.parse import urlparse, parse_qs
import pandas as pd
import streamlit as st

st.set_page_config(page_title="배재중학교 동아리 발표회", layout="wide")
st.title("배재중학교 동아리 발표회")

# ===================== 스타일 =====================
st.markdown("""
<style>
.booth-form { margin: 0; }
.booth-form input[type="hidden"] { display:none; }

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

button.booth .loc {
  position: absolute;
  top: 8px; left: 50%; transform: translateX(-50%);
  font-weight: 700; font-size: 0.95rem; color: #333; text-align: center;
  padding: 0 6px; max-width: 90%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
button.booth .club {
  position: absolute;
  top: 50%; left: 50%; transform: translate(-50%, -40%);
  font-size: 1.0rem; font-weight: 500; color: #111; text-align: center;
  padding: 0 8px; max-width: 92%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

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

# ===================== 기본 설정 =====================
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1dJr5dVJ50-FPD1WD2_TDwuQOK-wFjPrSBs6PYmQlEAU/edit?usp=sharing"
DEFAULT_MAIN_SHEET_NAME = "실내 부스 배치도"
DEFAULT_DETAILS_SHEET_NAME = "동아리 활동 설명"

def qp(): return st.experimental_get_query_params()

def pick(key, secret, default):
    q = qp()
    if key in q and q[key] and q[key][0].strip():
        return q[key][0].strip()
    try:
        v = st.secrets.get(secret, "").strip()
        if v: return v
    except Exception:
        pass
    return default

SHEET_URL = pick("sheet", "SHEET_URL", DEFAULT_SHEET_URL)
MAIN_SHEET_NAME = pick("main_sheet", "MAIN_SHEET_NAME", DEFAULT_MAIN_SHEET_NAME)
DETAILS_SHEET_NAME = pick("details_sheet", "DETAILS_SHEET_NAME", DEFAULT_DETAILS_SHEET_NAME)

# ===================== 유틸 =====================
BLANK_TOKENS = {"-", "—", "–"}  # 하이픈류도 빈 값 취급

def s(x):
    """안전 문자열 변환"""
    if x is None:
        return ""
    try:
        if isinstance(x, float) and pd.isna(x):
            return ""
    except Exception:
        pass
    return x if isinstance(x, str) else str(x)

def normalize_spaces(text: str) -> str:
    """
    눈에 안 보이는 공백 제거 + 줄바꿈/탭 정리:
    NBSP(\u00A0), 전각스페이스(\u3000), 제로폭(\u200B-\u200D), BOM(\ufeff) 제거
    """
    t = s(text)
    # 제거할 특수 공백/컨트롤
    t = t.replace("\ufeff", "")  # BOM
    t = t.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")  # zero-width
    t = t.replace("\u00a0", " ")  # NBSP -> space
    t = t.replace("\u3000", " ")  # 전각스페이스 -> space
    # 줄바꿈/탭을 공백으로 통일
    t = t.replace("\r\n", " ").replace("\n", " ").replace("\t", " ")
    # 다중 공백 압축
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def is_blank(x: str) -> bool:
    """보이는 텍스트가 사실상 비었는지 판단"""
    t = normalize_spaces(x)
    return (t == "" or t in BLANK_TOKENS)

def html_escape(t): 
    return normalize_spaces(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def extract_sheet_id(url):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else None

def to_named_sheet_csv_url(url, sheet_name):
    sid = extract_sheet_id(url)
    if not sid: return url
    return f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"

@st.cache_data(ttl=300)
def load_csv(url, header=None):
    df = pd.read_csv(url, header=header, dtype=str)
    # 문자열 정리(기본 trim까지만; 본 처리는 normalize_spaces에서 수행)
    df = df.where(pd.notnull(df), None)
    return df

# 캐시 강제 새로고침
refresh_q = qp().get("refresh", ["0"])[0] == "1"
col_refresh, _ = st.columns([1, 8])
with col_refresh:
    if st.button("🔄 데이터 새로고침", use_container_width=True) or refresh_q:
        st.cache_data.clear()

# 5층 1-7 제외
_pos_17_re = re.compile(r"^1[\-\s]?7(?:\s*반|\s*교실)?$", re.IGNORECASE)
def is_excluded_booth(floor_label, pos):
    if is_blank(floor_label) or is_blank(pos):
        return False
    m = re.search(r"(\d+)", str(floor_label))
    floor_num = int(m.group(1)) if m else None
    return bool(floor_num == 5 and _pos_17_re.match(str(pos)))

# 이름 보정
def normalize_club_name(name):
    name = normalize_spaces(name)
    if name == "": return ""
    if name == "음-세-듣": name = "음-세-들"  # 오타 교정
    return name

ALIAS_TO_CANON = {
    "음-하나": "음악으로 하나되기반",
    "음-세-들": "음악으로 세상 들여다 보기반",
}

# ===================== 배치 파서 (A열=층, B열~ / 홀수=위치, 짝수=동아리) =====================
def parse_layout(df: pd.DataFrame):
    """
    사람 기준 행 번호:
      1,3,5,...(홀수행)  = 위치행
      2,4,6,...(짝수행)  = 동아리행
    파이썬 인덱스(0부터):
      r(0,2,4,...) = 위치행, r+1 = 동아리행
    A열(0번)은 '층', B열(1번)부터 데이터.
    """
    rows_by_floor = {}
    n_rows, n_cols = df.shape
    data_start_col = 1  # B열부터

    for r in range(0, n_rows, 2):
        row_pos = df.iloc[r] if r < n_rows else None           # 위치행
        row_club = df.iloc[r+1] if (r+1) < n_rows else None     # 동아리행
        if row_pos is None or row_club is None:
            continue

        floor_label = normalize_spaces(row_pos.iloc[0] if 0 < len(row_pos) else "")
        if is_blank(floor_label) and row_club is not None:
            floor_label = normalize_spaces(row_club.iloc[0] if 0 < len(row_club) else "")
        if is_blank(floor_label):
            floor_label = "미지정"

        row_items = []
        for c in range(data_start_col, n_cols):
            pos_raw  = row_pos.iloc[c] if c < len(row_pos) else None
            club_raw = row_club.iloc[c] if c < len(row_club) else None

            pos  = normalize_spaces(pos_raw)
            club = normalize_club_name(club_raw)

            # 공백/하이픈만 있으면 렌더하지 않음
            if is_blank(pos) or is_blank(club):
                continue

            if is_excluded_booth(floor_label, pos):
                continue

            row_items.append({
                "floor": floor_label,
                "pos": pos,
                "club": club,
                "col_index": c
            })

        if row_items:
            rows_by_floor.setdefault(floor_label, []).append(row_items)

    # 층 내림차순(5→…→1)
    def floor_num(label):
        m = re.search(r"(\d+)", str(label))
        return int(m.group(1)) if m else -999999
    floors = sorted(rows_by_floor.keys(), key=lambda x: (-floor_num(x), str(x)))
    return floors, rows_by_floor

# ===================== 데이터 로드 =====================
error_box = st.empty()
try:
    main_df = load_csv(to_named_sheet_csv_url(SHEET_URL, MAIN_SHEET_NAME), header=None)
    floors, rows_by_floor = parse_layout(main_df)
except Exception as e:
    error_box.error(f"배치 시트를 불러오는 중 오류가 발생했습니다.\n\n{e}")
    st.stop()

# ===================== 상세 시트 로드 (동아리 활동 설명) =====================
details_by_club = {}
try:
    det_df = load_csv(to_named_sheet_csv_url(SHEET_URL, DETAILS_SHEET_NAME), header=0)
    col_map = {(normalize_spaces(c) if isinstance(c, str) else c): c for c in det_df.columns}
    name_key = next((k for k in ["동아리명","동아리","클럽명","club","Club","name","Name"] if k in col_map), None)
    if not name_key:
        st.warning("상세 시트에 '동아리명' 헤더가 없습니다. 헤더를 확인해주세요.")
    else:
        for _, row in det_df.iterrows():
            raw = row.get(col_map[name_key])
            club_name = normalize_club_name(raw)
            if is_blank(club_name):
                continue
            canon = ALIAS_TO_CANON.get(club_name, club_name)
            details_by_club[canon] = {
                "장소": normalize_spaces(row.get(col_map.get("장소",""), "")),
                "체험유형": normalize_spaces(row.get(col_map.get("체험유형",""), "")),
                "세부내용": normalize_spaces(row.get(col_map.get("세부내용",""), "")),
            }
except Exception as e:
    st.warning(f"상세 시트를 불러오지 못했습니다. 시트명 '{DETAILS_SHEET_NAME}'를 확인해주세요. 오류: {e}")

# ===================== 상단 메뉴 =====================
club_set = set()
for _f, rows in rows_by_floor.items():
    for row in rows:
        for it in row:
            c = normalize_spaces(it.get("club"))
            if not is_blank(c):
                club_set.add(ALIAS_TO_CANON.get(c, c))
clubs_sorted = sorted(club_set)

left, right = st.columns([2, 3])
with left:
    sel_floor = st.selectbox("층 선택", options=["전체"] + floors, index=0)
with right:
    sel_club = st.selectbox("동아리 선택", options=["전체"] + clubs_sorted, index=0,
                            help="스크롤해서 동아리명을 선택하세요.")

st.caption(f"• 데이터: '{MAIN_SHEET_NAME}' / 상세: '{DETAILS_SHEET_NAME}'  • 호버=풍선 / 클릭=같은 탭 Popover  • 공백/보이지 않는 공백 제거 적용")

# ===================== 선택 상태 (?sel=...) =====================
def encode_sel(item):
    payload = f"{item['floor']}|{item['col_index']}|{item['pos']}|{ALIAS_TO_CANON.get(item['club'], item['club'])}"
    return urllib.parse.quote(payload, safe='')

def decode_sel(sparam):
    try:
        sparam = urllib.parse.unquote(sparam or "")
        floor, col, pos, club = sparam.split("|", 3)
        return {"floor": floor, "col_index": int(col), "pos": pos, "club": club}
    except Exception:
        return None

qparams = qp()
sel_param = qparams.get("sel", [None])[0]
current_sel = decode_sel(sel_param) if sel_param else None

def same_item(a, b):
    if not a or not b: return False
    return (a["floor"] == b["floor"] and a["col_index"] == b["col_index"]
            and a["pos"] == b["pos"] and a["club"] == b["club"])

# ===================== 렌더 =====================
def booth_card_html(item):
    disp = {**item, "club": ALIAS_TO_CANON.get(item["club"], item["club"])}
    sel = encode_sel(disp)
    loc = html_escape(item["pos"])
    club = html_escape(disp["club"])
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

def render_fixed_popover(item):
    canon_name = ALIAS_TO_CANON.get(item["club"], item["club"])
    detail = details_by_club.get(canon_name, {}) if details_by_club else {}

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

    col1, col2 = st.columns([1,5])
    with col1:
        if st.button("닫기", key=f"close-{item['floor']}-{item['col_index']}-{item['pos']}", use_container_width=True):
            new_qp = dict(qp())
            new_qp.pop("sel", None)
            st.experimental_set_query_params(**new_qp)
    st.markdown("</div>", unsafe_allow_html=True)

def match_filters(item, sel_club_val):
    disp_name = ALIAS_TO_CANON.get(item["club"], item["club"])
    if sel_club_val != "전체" and disp_name != sel_club_val:
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
                normalized_current = None
                if current_sel:
                    normalized_current = {**current_sel, "club": ALIAS_TO_CANON.get(current_sel["club"], current_sel["club"])}
                normalized_item = {**item, "club": ALIAS_TO_CANON.get(item["club"], item["club"])}
                if same_item(normalized_item, normalized_current):
                    render_fixed_popover(normalized_item)

if sel_floor == "전체":
    for f in floors:  # 5→…→1
        render_floor(f, rows_by_floor[f], sel_club)
else:
    render_floor(sel_floor, rows_by_floor.get(sel_floor, []), sel_club)

st.write("")
st.caption(f"데이터 원본: '{MAIN_SHEET_NAME}' / 상세: '{DETAILS_SHEET_NAME}' · 보이지 않는 공백 제거 · 5층 1-7 제외 · 층 내림차순  • 강제 새로고침: 버튼 또는 URL에 ?refresh=1")
