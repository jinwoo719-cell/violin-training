"""
🎻 Violin Coach — 바이올린 연습 도우미

  연습하기    악보를 보며 지판 어디를 짚을지 · 녹음
  분석 리포트  내 연주를 악보 위에 겹쳐 보기 · 다시 듣기

실행:  streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components

import analyze
import music
import report
import screens
import sheet
import staff
from theme import C, MONO

#| 흐름  왼쪽에서 화면 고르기 → 연습·녹음 → 분석 → 결과 리포트 → 다시 연습

st.set_page_config(page_title="Violin Coach", page_icon="🎻", layout="wide",
                   initial_sidebar_state="collapsed")   # 폰 가로에서 화면을 다 쓰게


# ══════════════════════════════════════════════════════════════
#  겉모습 — 목업에 맞춘 어두운 테마와 왼쪽 메뉴
# ══════════════════════════════════════════════════════════════
st.markdown(f"""<style>
 .stApp {{ background:{C['bg']}; }}
 .block-container {{ padding-top:3.2rem; padding-bottom:2rem; max-width:1400px; }}
 /* 가로로 든 휴대폰 — 위아래 여백을 줄여 가이드가 한 화면에 들어가게 */
 @media (max-height: 560px), (max-width: 900px) {{
   .block-container {{ padding-top:0.6rem !important; padding-bottom:0.6rem !important;
     padding-left:0.7rem !important; padding-right:0.7rem !important; }}
   header[data-testid="stHeader"] {{ height:0; min-height:0; }}
   .ph1, .ph2 {{ display:none !important; }}   /* 가이드 아래 줄에 이미 있음 */
   h4 {{ font-size:14px !important; }}
 }}
 section[data-testid="stSidebar"] {{
   background:{C['panel']}; border-right:1px solid {C['line']}; }}
 section[data-testid="stSidebar"] .stButton button {{
   width:100%; background:transparent; border:1px solid transparent;
   color:{C['ink2']}; border-radius:9px; padding:8px 12px; }}
 /* 스트림릿 버튼은 글자가 안쪽 div/p 에 있어서 거기까지 왼쪽으로 붙여야 합니다 */
 section[data-testid="stSidebar"] .stButton button > div,
 section[data-testid="stSidebar"] .stButton button > div > div {{
   width:100%; justify-content:flex-start; text-align:left; }}
 section[data-testid="stSidebar"] .stButton button p {{
   width:100%; text-align:left; font-size:13.5px; font-weight:500; margin:0; }}
 section[data-testid="stSidebar"] .stButton button:hover {{
   background:{C['panel2']}; color:{C['ink']}; }}
 section[data-testid="stSidebar"] .stButton button[kind="primary"] {{
   background:{C['accent']}; color:#fff; font-weight:600; }}
 .brand {{ display:flex; align-items:center; gap:9px; padding:2px 4px 14px;
   font-size:16.5px; font-weight:700; color:{C['ink']}; }}
 .brand span {{ color:{C['accent']}; font-size:19px; }}
 .sbox {{ background:{C['panel2']}; border:1px solid {C['line']};
   border-radius:11px; padding:11px 13px; margin-top:6px; }}
 .sbox .t {{ font-size:11.5px; color:{C['muted']}; margin-bottom:7px; }}
 .sbox .r {{ display:flex; justify-content:space-between; font-size:12px;
   line-height:1.9; color:{C['ink2']}; }}
 .sbox .r b {{ color:{C['ink']}; font-weight:600; font-family:{MONO};
   font-size:11.5px; }}
 .ph1 {{ font-size:20px; font-weight:700; margin:0 0 3px; color:{C['ink']}; }}
 .ph2 {{ font-size:12.5px; color:{C['muted']}; margin-bottom:14px; }}
 .soon {{ background:{C['panel']}; border:1px dashed {C['line']};
   border-radius:14px; padding:34px; text-align:center; color:{C['muted']};
   font-size:13.5px; line-height:2; }}
 div[data-testid="stMetricValue"] {{ font-family:{MONO}; }}
 hr {{ border-color:{C['line']}; }}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  상태 — 새로고침해도 유지되는 값들
# ══════════════════════════════════════════════════════════════
S = st.session_state
S.setdefault("screen", "practice")   # 지금 보고 있는 화면
S.setdefault("result", None)         # 분석 결과
S.setdefault("wav", None)            # 그때 쓴 녹음
S.setdefault("meta", None)           # 그때의 연습 이름
S.setdefault("when", "")             # 그때의 시각
S.setdefault("take", 0)              # 녹음 회차 — 위젯을 새로 만들 때 씁니다
S.setdefault("practice", 0)          # 고른 음계
S.setdefault("pos", music.POSITIONS[0])   # 포지션 (1 / 3 / 1→3)
S.setdefault("slur", "한 음씩 (데타셰)")
S.setdefault("bpm", 60)
S.setdefault("tol_cent", 12)
S.setdefault("tol_ms", 40)
S.setdefault("drill", None)          # 교정 연습 (없으면 원래 음계)
S.setdefault("my", None)             # 내가 넣은 악보 (없으면 음계 연습)
S.setdefault("my_text", sheet.SAMPLE)   # 「내 악보」 화면에서 적고 있는 글
S.setdefault("my_key", 3)
S.setdefault("my_name", "내 악보")
S.setdefault("my_string", "자동")
S.setdefault("gem_key", "")          # 사진 인식용 키 (기억만 하고 저장하지 않음)
S.setdefault("my_demo", None)        # 「내 악보」 시범 연주
S.setdefault("ref_wav", None)        # 「연습하기」 시범 연주

#| 입력  고른 연습 — 음계 · 범위 · 슬러 · BPM · 허용 범위

# ══════════════════════════════════════════════════════════════
#  왼쪽 — 메뉴와 현재 설정
# ══════════════════════════════════════════════════════════════
MENU = [("연습하기", "practice"), ("내 악보", "sheet"), ("연습 기록", "history"),
        ("곡 목록", "songs"), ("분석 리포트", "report"), ("설정", "settings")]

with st.sidebar:
    st.markdown('<div class="brand"><span>✳</span> Violin Coach</div>',
                unsafe_allow_html=True)
    #| 반복  메뉴 항목마다
    for label, key in MENU:
        #| 갈래     눌렸나 ? 그 화면으로 옮긴다 : 그대로 둔다
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if S.screen == key else "secondary"):
            S.screen = key
            st.rerun()

    st.markdown("---")
    st.markdown("##### 연습 고르기")
    #| 갈래  내 악보를 쓰는 중인가 ? 그 이름을 보이고 되돌리는 버튼 : 음계를 고르게 한다
    if S.my:
        st.info(f'**{S.my["name"]}** 로 연습 중')
        if st.button("음계 연습으로 돌아가기", use_container_width=True):
            S.my = None
            S.drill = None
            st.rerun()
    else:
        S.practice = st.selectbox("음계", range(len(music.PRACTICES)),
                                  index=S.practice,
                                  format_func=lambda i: music.PRACTICES[i][0])
    #| 입력  포지션 — 손을 어디에 두고 연주할지 (음계·내 악보 둘 다에 걸립니다)
    S.pos = st.selectbox(
        "포지션", music.POSITIONS, index=music.POSITIONS.index(S.pos),
        help="1포지션·3포지션을 고르면 손을 옮기지 않습니다. "
             "그 자리에서 안 닿는 음은 옆 줄로 넘어가고, "
             "그래도 안 닿으면 음계가 짧아집니다.")
    S.slur = st.selectbox("활 나누기", list(music.SLURS.keys()),
                          index=list(music.SLURS).index(S.slur))
    S.bpm = st.slider("BPM", 40, 120, S.bpm, step=5)


_, string_name, mode = music.PRACTICES[S.practice]

#| 갈래  내 악보인가 ? 적은 글에서 음 목록을 만든다 : 고른 음계로 만든다
if S.my:
    #| 호출  sheet.build → 내가 적은 악보의 음 목록
    base_notes = sheet.build(S.my["parsed"], S.my["key"], S.bpm,
                             music.SLURS[S.slur],
                             None if S.my["string"] == "자동" else S.my["string"],
                             position=S.pos)
    sig = sheet.key_of(S.my["key"])
    base_title = S.my["name"]
else:
    base_notes = music.build_notes(string_name, mode, slur=music.SLURS[S.slur],
                                   bpm=S.bpm, position=S.pos)
    #| 호출  music.build_notes → 이 연습의 음 목록 (모든 화면이 이걸 씀)
    sig = music.key_signature(music.STRING_BY_NAME[string_name]["letter"], mode)
    #| 호출  music.key_signature → 조표
    base_title = f'{music.PRACTICES[S.practice][0]} · {S.slur}'


with st.sidebar:
    st.markdown("---")
    _used = " · ".join(sorted({n["string"] for n in base_notes},
                              key=lambda s: "EADG".index(s)))
    _pos = " → ".join(str(p) for p in sorted({n["position"] for n in base_notes}))
    st.markdown(
        f'<div class="sbox"><div class="t">현재 설정</div>'
        f'<div class="r"><span>악보</span><b>{base_title[:14]}</b></div>'
        f'<div class="r"><span>음</span><b>{len(base_notes)}음</b></div>'
        f'<div class="r"><span>현</span><b>{_used}현</b></div>'
        f'<div class="r"><span>포지션</span><b>{_pos}포지션</b></div>'
        f'<div class="r"><span>템포</span><b>{S.bpm} BPM</b></div>'
        f'<div class="r"><span>기준음</span><b>A = 440Hz</b></div></div>',
        unsafe_allow_html=True)


def make_drill(spec):
    """리포트에서 넘어온 교정 연습을 음 목록으로."""
    #| 흐름  드릴 종류에 맞는 음 목록과 이름을 만든다
    #| 갈래  내 악보인가 ? 적은 음들을 잘라 쓴다 : 음계에서 만든다
    #| 갈래  음 반복인가 ? 개방현↔문제음 : 다음을 본다
    #| 갈래  시프팅인가 ? 이동 앞뒤만 : 다음을 본다
    #| 갈래  롱톤인가 ? 개방현 한 활 네 음 : 같은 악보를 느리게
    #| 출력  (음 목록, 이름, BPM)
    k = spec["kind"]
    slow = max(40, S.bpm - 20)

    if S.my:                                       # ── 내 악보 ──
        p = S.my["parsed"]
        if k == "note":
            seg, st_ = sheet.drill_note(p, base_notes, spec["idx"])
            bpm = max(40, S.bpm - 10)
            return (sheet.build(seg, S.my["key"], bpm, 1, st_),
                    f'{base_notes[spec["idx"]]["ko"]} 집중 연습 · 개방현과 번갈아', bpm)
        if k == "shift":
            seg = sheet.drill_shift(p, base_notes)
            if seg:
                return sheet.build(seg, S.my["key"], slow, 1), "시프팅 구간 연습", slow
        if k == "longtone":
            seg, st_ = sheet.drill_longtone(base_notes)
            return (sheet.build(seg, S.my["key"], 30, 4, st_),
                    "활 롱톤 · 한 활에 네 음", 30)
        return (sheet.build(p, S.my["key"], slow, music.SLURS[S.slur],
                            None if S.my["string"] == "자동" else S.my["string"],
                            position=S.pos),
                f'{S.my["name"]} · 느리게', slow)

    if k == "note":                                # ── 음계 연습 ──
        bpm = max(40, S.bpm - 10)
        return (music.drill_note(base_notes, spec["idx"], mode, bpm),
                f'{base_notes[spec["idx"]]["ko"]} 집중 연습 · 개방현과 번갈아', bpm)
    if k == "shift":
        return music.drill_shift(base_notes, mode, slow), "시프팅 구간 연습", slow
    if k == "longtone":
        return music.drill_longtone(string_name, mode, 30), "활 롱톤 · 한 활에 네 음", 30
    return (music.build_notes(string_name, mode, slur=music.SLURS[S.slur],
                              bpm=slow, position=S.pos),
            f'{music.PRACTICES[S.practice][0]} · 느리게', slow)


if S.drill:
    notes, title, play_bpm = make_drill(S.drill)
else:
    notes, play_bpm, title = base_notes, S.bpm, base_title


def head(t1, t2):
    st.markdown(f'<div class="ph1">{t1}</div><div class="ph2">{t2}</div>',
                unsafe_allow_html=True)


def run_analysis(wav: bytes):
    #| 흐름  녹음 → 분석 → 결과 화면으로 넘어간다
    #| 입력  녹음 WAV
    #| 호출  analyze.analyze → 음별 결과
    #| 갈래  분석이 실패했나 ? 이유를 보여주고 멈춘다 : 계속한다
    #| 갈래  음을 하나도 못 찾았나 ? 마이크를 확인하라고 한다 : 계속한다
    #| 단계  결과와 녹음을 기억해 둔다 (새로고침해도 남게)
    #| 출력  분석 리포트 화면으로 전환
    from datetime import datetime
    try:
        res = analyze.analyze(wav, notes, play_bpm, S.tol_cent, S.tol_ms)
    except Exception as e:                       # 형식·길이·무음 등
        st.error(f"분석하지 못했습니다 — {e}")
        return
    if len(res["missing"]) == len(notes):
        st.error("음을 하나도 못 찾았습니다. 마이크 볼륨과 녹음 길이를 확인해 주세요.")
        return
    S.result, S.wav, S.meta = res, wav, title
    S.when = datetime.now().strftime("%Y-%m-%d %H:%M")
    S.screen = "report"
    st.rerun()


# ══════════════════════════════════════════════════════════════
#  연습하기
# ══════════════════════════════════════════════════════════════
if S.screen == "practice":
    #| 구역  연습하기 — 가이드를 보며 연주하고 녹음한다
    #| 단계  무엇을 연습할지 고르는 줄 (음계 · 범위 · 활 · BPM)
    #| 호출  screens.guide → 움직이는 가이드 HTML
    #| 단계  마이크 녹음 위젯을 놓는다
    #| 갈래  [분석하기] 를 눌렀나 ? run_analysis(녹음) : 계속 기다린다
    #| 갈래  [데모로 보기] 를 눌렀나 ? run_analysis(합성 연주) : 계속 기다린다
    #| 갈래  [다시 녹음] 을 눌렀나 ? 위젯을 새로 만들어 이전 녹음을 지운다 : 그대로 둔다
    #| 단계  오른쪽에 악보를 바꾸는 길과 손 옮기는 자리 안내를 둔다
    head(title, f'{len(notes)}음 · {play_bpm} BPM · 개방현 A 440Hz 기준')

    #| 갈래  교정 연습 중인가 ? 원래 음계로 돌아가는 버튼을 둔다 : 넘어간다
    if S.drill:
        if st.button("← 원래 음계로 돌아가기"):
            S.drill = None
            st.rerun()

    components.html(screens.guide(notes, sig, play_bpm),
                    height=screens.guide_height(), scrolling=False)

    st.markdown("")
    left, right = st.columns([1.15, 1])

    with left:
        st.markdown("#### 녹음하기")
        st.caption(
            "① 마이크 버튼으로 녹음을 시작하고 ② 가이드의 **[▶ 시작]** 을 누르세요. "
            "가이드는 저절로 시작하지 않습니다 — 녹음과 박자를 맞추기 위해서입니다. "
            "준비 시간이 지난 뒤 **똑 · 똑 · 똑 · 똑** 네 박을 세고 시작합니다 "
            "(준비 시간은 가이드 아래 **[준비]** 에서 바꿉니다). "
            "메트로놈 '똑' 소리는 분석에서 걸러내므로 섞여도 괜찮습니다 — "
            "다만 크게 섞이면 음정이 흐려지니 **이어폰**을 권합니다."
        )
        #| 갈래  시범 연주를 청했나 ? 기준 소리를 만들어 붙인다 : 넘어간다
        with st.expander("🔊 먼저 들어보기 — 이 악보의 기준 연주"):
            st.caption("정확한 음정·박자로 만든 소리입니다. "
                       "가이드 바의 **[🔊 시범 듣기]** 를 켜면 "
                       "떨어지는 노드와 **함께** 들을 수도 있습니다.")
            if st.button("시범 연주 만들기", key="mkref"):
                S.ref_wav = analyze.reference_wav(notes, play_bpm)
            if S.get("ref_wav"):
                st.audio(S.ref_wav, format="audio/wav")

        rec = st.audio_input("마이크", key=f"rec{S.take}", label_visibility="collapsed")

        b1, b2, b3 = st.columns(3)
        if b1.button("분석하기", type="primary", use_container_width=True,
                     disabled=rec is None):
            with st.spinner("음정을 찾는 중…"):
                run_analysis(rec.getvalue())
        if b2.button("데모로 보기", use_container_width=True,
                     help="마이크 없이 전체 흐름을 확인합니다"):
            with st.spinner("데모 연주를 만드는 중…"):
                run_analysis(analyze.demo_wav(notes, play_bpm))
        if b3.button("다시 녹음", use_container_width=True):
            S.take += 1                 # 위젯을 새로 만들어 이전 녹음을 지웁니다
            st.rerun()

    with right:
        #| 단계  악보를 바꾸는 길을 눈에 띄게 — 메뉴 안에만 두면 못 찾습니다
        st.markdown("#### 악보 바꾸기")
        st.caption("음계 말고 **내 악보**로도 연습할 수 있습니다. "
                   "직접 적거나 · 가지고 있는 악보를 찍거나 · MusicXML 을 올리세요. "
                   "사진은 저장하지 않습니다.")
        if st.button("📄 내 악보 만들기 (적기 · 사진 · 파일)", type="primary",
                     use_container_width=True):
            S.screen = "sheet"
            st.rerun()
        st.caption("음계·포지션·활·템포는 **왼쪽 사이드바(≫)** 에서 바꿉니다.")

        sh = music.shift_index(notes)
        #| 갈래  손을 옮기는 자리가 있나 ? 어디서 어떻게 옮기는지 : 안 옮긴다고 알린다
        if sh is not None:
            st.info(f'**{notes[sh]["ko"]}**에서 {notes[sh-1]["position"]}→'
                    f'{notes[sh]["position"]}포지션으로 손을 옮깁니다. '
                    f'직전 음 **{notes[sh-1]["ko"]}**를 짚어 소리로 확인한 뒤 '
                    f'올라가면 자리를 잡기 쉽습니다.')
        else:
            _p = sorted({n["position"] for n in notes})
            st.info(f'손을 옮기지 않습니다 — **{_p[0]}포지션**에서 끝납니다.')


# ══════════════════════════════════════════════════════════════
#  분석 리포트
# ══════════════════════════════════════════════════════════════
elif S.screen == "report":
    #| 구역  분석 리포트 — 결과를 악보 위에 겹쳐 보고 다시 듣는다
    #| 갈래  분석한 결과가 있나 ? 리포트를 그린다 : 먼저 연습하라고 안내한다
    #| 갈래  못 찾은 음이 있나 ? 어떤 음인지 알린다 : 넘어간다
    #| 호출  report.build → 리포트 HTML (녹음이 안에 들어 있음)
    #| 단계  HTML 로 저장할 수 있게 내려받기 버튼을 놓는다
    if S.result is None:
        head("분석 리포트", "아직 분석한 연습이 없습니다")
        st.markdown('<div class="soon">먼저 <b>연습하기</b>에서 녹음하고 '
                    '[분석하기]를 눌러 주세요.<br>'
                    '마이크가 없으면 [데모로 보기]로 전체 흐름을 볼 수 있습니다.</div>',
                    unsafe_allow_html=True)
        if st.button("연습하러 가기", type="primary"):
            S.screen = "practice"
            st.rerun()
    else:
        res = S.result
        top = st.columns([5, 1.2])
        if top[1].button("↻ 다시 연습하기", type="primary", use_container_width=True):
            S.screen = "practice"
            S.take += 1
            st.rerun()
        if res["missing"]:
            st.warning(f'소리를 못 찾은 음: {" · ".join(res["missing"])} '
                       f'— 그 자리는 결과에서 비워 둡니다.')

        html = report.build(res, notes, sig, play_bpm, S.wav, S.meta or title,
                            S.when, tol_cent=S.tol_cent, tol_ms=S.tol_ms)
        components.html(html, height=report.height(notes), scrolling=True)

        #| 단계  분석 코멘트의 처방을 바로 눌러 갈 수 있게
        drills, seen = [], set()
        for t in report.comments(res, notes, S.tol_cent, S.tol_ms):
            d = t.get("drill")
            if d and d["label"] not in seen:
                seen.add(d["label"])
                drills.append(d)
        if drills:
            st.markdown("##### 교정 연습 — 코멘트의 처방을 바로 해 보기")
            cols = st.columns(len(drills) + 1)
            #| 반복  처방마다 버튼 하나
            for c, d in zip(cols, drills):
                #| 갈래     눌렸나 ? 그 드릴로 연습 화면을 연다 : 그대로 둔다
                if c.button(d["label"], use_container_width=True, key="dr_" + d["label"]):
                    S.drill = d
                    S.screen = "practice"
                    S.take += 1
                    st.rerun()
            cols[-1].download_button("리포트 저장 (HTML)", html,
                                     file_name="연습리포트.html", mime="text/html",
                                     use_container_width=True)
        else:
            st.download_button("리포트 저장 (HTML)", html,
                               file_name="연습리포트.html", mime="text/html")


# ══════════════════════════════════════════════════════════════
#  내 악보 — 직접 적기 · 사진 · 파일
# ══════════════════════════════════════════════════════════════
elif S.screen == "sheet":
    #| 구역  내 악보 — 세 갈래로 넣고, 하나의 글로 모아 고친 뒤 연습으로
    #| 단계  세 갈래(직접·사진·파일)가 전부 같은 글칸을 채운다
    #| 갈래  사진을 올렸나 ? 한 번 읽고 바로 버린다 : 넘어간다
    #| 갈래  파일을 올렸나 ? MusicXML 을 읽는다 : 넘어간다
    #| 단계  적은 글을 악보로 그려 눈으로 확인시킨다
    #| 갈래  [이 악보로 연습하기] 를 눌렀나 ? 연습 화면으로 : 그대로 둔다
    head("내 악보", "직접 적거나 · 사진을 찍거나 · 파일을 올려서 내 악보를 만듭니다")

    st.caption("교본 악보를 그대로 불러오는 기능은 넣지 않았습니다. "
               "**내가 적은 것**과 **내가 가진 악보를 내가 찍은 것**만 다룹니다. "
               "사진은 저장하지 않고, 읽고 나면 바로 버립니다.")

    t1, t2, t3 = st.tabs(["✍️ 직접 적기", "📷 사진에서", "📄 파일에서"])

    with t1:
        st.markdown(sheet.HELP)
        if st.button("보기 채우기 (A장조 한 옥타브)"):
            S.my_text = sheet.SAMPLE
            st.rerun()

    with t2:
        #| 갈래  사진에서 — 키가 있어야 인식이 됩니다
        st.markdown("가지고 있는 악보를 **밝은 곳에서 반듯하게** 한 줄씩 찍으세요.")
        st.caption("사진은 인식할 때 한 번만 쓰고 곧바로 버립니다 — "
                   "서버에도, 이 앱에도 남기지 않습니다. "
                   "인식은 반드시 틀리는 곳이 있으니, 아래 글에서 고쳐 쓰세요.")
        shot = st.file_uploader("악보 사진", type=["jpg", "jpeg", "png", "webp"],
                                key=f"shot{S.take}")
        S.gem_key = st.text_input("Gemini API 키", S.gem_key, type="password",
                                  help="키는 이 브라우저 세션에만 있고 저장하지 않습니다. "
                                       "aistudio.google.com 에서 무료로 발급됩니다.")
        if st.button("사진에서 읽기", type="primary", disabled=shot is None):
            with st.spinner("악보를 읽는 중…"):
                try:
                    got = sheet.from_image(shot.getvalue(), S.gem_key.strip(),
                                           mime=shot.type or "image/jpeg")
                    S.my_text = sheet.to_text(got)
                    S.my_key = sheet.guess_key(got)
                    S.my_name = "사진에서 읽은 악보"
                    S.take += 1                    # 사진 위젯을 비워 사진을 놓습니다
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    with t3:
        st.markdown("MuseScore 등에서 내보낸 **MusicXML**(.musicxml / .xml / .mxl) "
                    "을 올리면 음을 뽑아 옵니다.")
        up = st.file_uploader("MusicXML", type=["musicxml", "xml", "mxl"],
                              key=f"mxl{S.take}")
        if st.button("파일에서 읽기", type="primary", disabled=up is None):
            try:
                got = sheet.from_musicxml(up.getvalue())
                S.my_text = sheet.to_text(got)
                S.my_key = sheet.guess_key(got)
                S.my_name = up.name.rsplit(".", 1)[0][:24]
                st.rerun()
            except Exception as e:
                st.error(f"읽지 못했습니다 — {e}")

    st.markdown("---")
    st.markdown("#### 악보 고치기")
    S.my_text = st.text_area("음", S.my_text, height=100, label_visibility="collapsed")

    c1, c2, c3 = st.columns([2, 1.4, 1])
    S.my_name = c1.text_input("이름", S.my_name)
    parsed, bad = sheet.parse(S.my_text)
    #| 갈래  조표를 아직 안 골랐나 ? 적은 음들로 짐작해 둔다 : 고른 것을 쓴다
    keys = [k for _, k in sheet.KEYS]
    S.my_key = c2.selectbox("조표", keys,
                            index=keys.index(S.my_key) if S.my_key in keys else 0,
                            format_func=lambda k: dict((v, n) for n, v in sheet.KEYS)[k])
    S.my_string = c3.selectbox("줄", ["자동", "E", "A", "D", "G"],
                               index=["자동", "E", "A", "D", "G"].index(S.my_string))

    if bad:
        st.warning("못 읽은 칸: " + " · ".join(f"`{b}`" for b in bad))

    if not parsed:
        st.info("위에 음을 적으면 여기에 악보가 그려집니다.")
    else:
        try:
            my_notes = sheet.build(parsed, S.my_key, S.bpm, music.SLURS[S.slur],
                                   None if S.my_string == "자동" else S.my_string)
        except Exception as e:
            my_notes = []
            st.error(f"악보를 만들지 못했습니다 — {e}")
        if my_notes:
            #| 호출  staff.preview → 적은 대로 나오는지 눈으로 확인
            st.markdown(
                f'<div style="background:{C["panel"]};border:1px solid {C["line"]};'
                f'border-radius:12px;padding:10px 6px;overflow-x:auto">'
                f'{staff.preview(my_notes, sheet.key_of(S.my_key), 940)}</div>',
                unsafe_allow_html=True)
            used = " · ".join(sorted({n["string"] for n in my_notes},
                                     key=lambda s: "EADG".index(s)))
            st.caption(f'{len(my_notes)}음 · {used}현 · '
                       f'{" → ".join(str(p) for p in sorted({n["position"] for n in my_notes}))}포지션')

            #| 갈래  [들어보기] 를 눌렀나 ? 기준 연주를 만들어 들려준다 : 그대로 둔다
            #| 호출  analyze.reference_wav → 정확한 음정·박자의 기준 연주
            if st.button("🔊 들어보기 (시범 연주)"):
                S.my_demo = analyze.reference_wav(my_notes, S.bpm)
            if S.get("my_demo"):
                st.audio(S.my_demo, format="audio/wav")
                st.caption("정확한 음정·박자로 만든 **기준 소리**입니다. "
                           "적은 대로 나오는지 귀로도 확인해 보세요 "
                           "(악보가 틀리면 여기서 바로 들립니다).")

            if st.button("이 악보로 연습하기", type="primary"):
                S.my = {"parsed": parsed, "key": S.my_key,
                        "name": S.my_name or "내 악보", "string": S.my_string}
                S.drill = None
                S.screen = "practice"
                S.take += 1
                st.rerun()


# ══════════════════════════════════════════════════════════════
#  설정
# ══════════════════════════════════════════════════════════════
elif S.screen == "settings":
    #| 구역  설정 — 판정 기준과 조율 기준
    #| 단계  음정·박자 허용 범위를 정한다
    #| 단계  개방현이 어떻게 계산되는지 보여준다
    head("설정", "판정 기준과 조율 기준")
    a, b = st.columns(2)
    with a:
        st.markdown("##### 판정 기준")
        S.tol_cent = st.slider("음정 허용 (cent)", 5, 30, S.tol_cent,
                               help="초보일수록 넓게. 튜닝 때 잰 활 흔들림으로 "
                                    "자동 설정하는 것이 다음 단계입니다.")
        S.tol_ms = st.slider("박자 허용 (ms)", 20, 120, S.tol_ms, step=5)
        st.caption("이 값이 리포트의 초록/빨강을 가르고, 종합 점수에도 그대로 들어갑니다.")
    with b:
        st.markdown("##### 조율 기준")
        st.markdown(
            f"진동현 **{music.STRING_LENGTH_MM:.0f}mm** (4/4 바이올린) 기준입니다.\n\n"
            f"개방현은 **순정 5도**로 조율된 것으로 계산합니다 — "
            f"실제로 바이올린을 맞추는 방식(두 줄을 같이 켜서 맥놀이가 없어질 때까지)입니다."
        )
        st.dataframe(
            [{"줄": s["name"], "계이름": s["ko"], "주파수": f'{s["freq"]:.2f} Hz'}
             for s in music.STRINGS],
            hide_index=True, use_container_width=True)
        st.caption("악기 크기는 소리로 알 수 없습니다 — 어떤 크기든 A현은 440Hz로 "
                   "맞추니까요. 크기는 mm 표시에만 영향을 줍니다.")


# ══════════════════════════════════════════════════════════════
#  아직 없는 화면
# ══════════════════════════════════════════════════════════════
else:
    #| 구역  준비 중인 화면 — 연습 기록 · 곡 목록
    name = dict(MENU)[S.screen] if S.screen in dict(MENU).values() else ""
    name = next((l for l, k in MENU if k == S.screen), "준비 중")
    head(name, "다음 단계에서 만들 화면입니다")
    todo = {
        "history": "연습할 때마다 결과가 쌓여, 음정이 나아지는지 날짜별로 보여줍니다.<br>"
                   "선생님께 보여드릴 기간별 리포트도 여기서 나옵니다.",
        "songs": "호만·볼파르트 같은 교본 곡을 골라 연습합니다.<br>"
                 "지금은 음계만 있고, 다음에 MusicXML 업로드를 붙일 예정입니다.",
    }
    st.markdown(f'<div class="soon">{todo.get(S.screen, "")}</div>',
                unsafe_allow_html=True)
