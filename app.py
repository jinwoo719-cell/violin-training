"""
🎻 바이올린 연습 도우미 — MVP

화면 ①  연습 가이드   악보를 보며 지판 어디를 짚을지 · 녹음
화면 ②  결과 리포트   내 연주를 악보 위에 겹쳐 보기 · 다시 듣기

실행:  streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components

import analyze
import music
import screens

st.set_page_config(page_title="바이올린 연습 도우미", page_icon="🎻", layout="wide")

# ══════════════════════════════════════════════════════════════
#  상태 — 새로고침해도 유지되는 값들
# ══════════════════════════════════════════════════════════════
S = st.session_state
S.setdefault("screen", "practice")   # 지금 보고 있는 화면
S.setdefault("result", None)         # 분석 결과
S.setdefault("wav", None)            # 그때 쓴 녹음
S.setdefault("meta", None)           # 그때의 연습 설정
S.setdefault("take", 0)              # 녹음 회차 — 위젯을 새로 만들 때 씁니다


# ══════════════════════════════════════════════════════════════
#  왼쪽 — 무엇을 연습할지
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 연습 고르기")
    labels = [p[0] for p in music.PRACTICES]
    choice = st.selectbox("음계", labels, index=0)
    _, string_name, mode = music.PRACTICES[labels.index(choice)]

    rng = st.radio("범위", ["한 옥타브 (1→3포지션)", "1포지션만"], index=0)
    first_only = rng.startswith("1포지션")

    slur_label = st.radio("활 나누기", list(music.SLURS.keys()), index=0)
    slur = music.SLURS[slur_label]

    bpm = st.slider("BPM", 40, 120, 60, step=5)

    st.markdown("---")
    st.markdown("### 판정 기준")
    tol_cent = st.slider("음정 허용 (센트)", 5, 30, 12,
                         help="초보일수록 넓게. 튜닝 때 잰 활 흔들림으로 자동 설정하는 것이 다음 단계입니다.")
    tol_ms = st.slider("박자 허용 (ms)", 20, 120, 40, step=5)

    st.markdown("---")
    st.caption(
        f"진동현 **{music.STRING_LENGTH_MM:.0f}mm** (4/4) 기준 · "
        f"개방현은 **순정 5도**로 조율된 것으로 계산합니다 "
        f"(A 440Hz → E {music.STRING_BY_NAME['E']['freq']:.1f} · "
        f"D {music.STRING_BY_NAME['D']['freq']:.1f} · "
        f"G {music.STRING_BY_NAME['G']['freq']:.1f})."
    )

notes = music.build_notes(string_name, mode, slur=slur, bpm=bpm,
                          first_position_only=first_only)
sig = music.key_signature(music.STRING_BY_NAME[string_name]["letter"], mode)
title = f"{choice} · {slur_label}"

# ══════════════════════════════════════════════════════════════
#  위쪽 — 화면 바꾸기
# ══════════════════════════════════════════════════════════════
st.markdown("## 🎻 바이올린 연습 도우미")

c1, c2, c3 = st.columns([1, 1, 4])
if c1.button("① 연습 가이드", use_container_width=True,
             type="primary" if S.screen == "practice" else "secondary"):
    S.screen = "practice"
if c2.button("② 결과 리포트", use_container_width=True, disabled=S.result is None,
             type="primary" if S.screen == "report" else "secondary"):
    S.screen = "report"
if S.result is None:
    c3.caption("녹음하고 분석하면 ② 결과 리포트가 열립니다.")
else:
    c3.caption(f"마지막 분석: {S.meta}")

st.markdown("")


# ══════════════════════════════════════════════════════════════
#  화면 ① — 연습 가이드
# ══════════════════════════════════════════════════════════════
def run_analysis(wav: bytes):
    try:
        res = analyze.analyze(wav, notes, bpm, tol_cent, tol_ms)
    except Exception as e:                       # 형식·길이·무음 등
        st.error(f"분석하지 못했습니다 — {e}")
        return
    if len(res["missing"]) == len(notes):
        st.error("음을 하나도 못 찾았습니다. 마이크 볼륨과 녹음 길이를 확인해 주세요.")
        return
    S.result, S.wav = res, wav
    S.meta = f"{title} · {bpm}BPM"
    S.screen = "report"
    st.rerun()


if S.screen == "practice":
    guide_h = screens.guide_height(notes)
    components.html(screens.guide(notes, sig, bpm), height=guide_h, scrolling=False)

    st.markdown("")
    left, right = st.columns([1.15, 1])

    with left:
        st.markdown("#### 녹음하기")
        st.caption(
            f"가이드의 커서를 보며 **{bpm} BPM**으로 {len(notes)}음을 이어서 연주하세요. "
            "녹음을 언제 시작하든 **첫 소리가 난 자리**를 첫 음으로 맞춥니다. "
            "메트로놈을 쓸 때는 **이어폰**을 끼세요 (소리가 섞이면 분석이 흐려집니다)."
        )
        rec = st.audio_input("마이크", key=f"rec{S.take}", label_visibility="collapsed")

        b1, b2, b3 = st.columns([1, 1, 1])
        if b1.button("분석하기", type="primary", use_container_width=True,
                     disabled=rec is None):
            with st.spinner("음정을 찾는 중…"):
                run_analysis(rec.getvalue())
        if b2.button("데모로 보기", use_container_width=True,
                     help="마이크 없이 전체 흐름을 확인합니다"):
            with st.spinner("데모 연주를 만드는 중…"):
                run_analysis(analyze.demo_wav(notes, bpm))
        if b3.button("다시 녹음", use_container_width=True):
            S.take += 1                 # 위젯을 새로 만들어 이전 녹음을 지웁니다
            st.rerun()

    with right:
        st.markdown("#### 이번 연습")
        rows = []
        for i, n in enumerate(notes):
            rows.append({
                "": i + 1,
                "계이름": n["ko"],
                "포지션": f'{n["position"]}포지션',
                "손가락": "개방" if n["finger"] == 0 else f'{n["finger"]}번',
                "너트에서": f'{n["mm"]:.1f}mm',
                "Hz": f'{n["freq"]:.1f}',
                "활": "⊓ 다운" if n["bow"] == "down" else "∨ 업",
            })
        st.dataframe(rows, hide_index=True, use_container_width=True, height=320)

        sh = music.shift_index(notes)
        if sh is not None:
            st.info(
                f'**{notes[sh]["ko"]}**에서 {notes[sh-1]["position"]}→'
                f'{notes[sh]["position"]}포지션으로 손을 옮깁니다.\n\n'
                f'옮기기 직전 음 **{notes[sh-1]["ko"]}**를 짚어 보고 소리로 확인한 뒤 '
                f'올라가면 자리를 잡기 쉽습니다.'
            )
        else:
            st.info("이 연습은 손을 옮기지 않고 1포지션에서 끝납니다.")


# ══════════════════════════════════════════════════════════════
#  화면 ② — 결과 리포트
# ══════════════════════════════════════════════════════════════
elif S.screen == "report" and S.result is not None:
    res = S.result
    if res["missing"]:
        st.warning(f'소리를 못 찾은 음: {" · ".join(res["missing"])} '
                   f'— 그 자리는 결과에서 비워 둡니다.')

    html = screens.report(res, notes, sig, bpm, S.wav, S.meta or title,
                          tol_cent=tol_cent, tol_ms=tol_ms)
    components.html(html, height=screens.report_height(notes), scrolling=True)

    st.download_button("리포트 저장 (HTML)", html,
                       file_name="연습리포트.html", mime="text/html")

else:
    S.screen = "practice"
    st.rerun()
