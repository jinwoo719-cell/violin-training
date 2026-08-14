"""
화면 ② — 결과 리포트.

정보의 순서가 이 화면의 전부입니다.

    ① 얼마나 했나        종합 점수 + 지표 넷
    ② 어디가 문제인가     악보 + 음별 표  (같은 가로 좌표)
    ③ 음 안에서 어땠나    궤적
    ④ 무엇부터 고치나     취약 음 TOP 3 · 코멘트 · 분포
    ⑤ 다시 듣기          그 부분 내 연주

표의 열은 위쪽 악보의 음표와 **같은 가로 좌표**를 씁니다.
악보를 보며 "어느 음"을 알고, 표에서 "얼마나"를 읽습니다.
"""

import base64
import json

import music
import staff
from theme import C, FONT, MONO, score_color

#| 흐름  분석 결과 + 녹음 → 결과 리포트 HTML

# ── 표의 세로 배치 ──
ROW_H = 34
ROWS = [("음정", "cent"), ("박자", "ms"), ("안정도", "cent"), ("활 방향", "")]


def _txt(x, y, s, size=11, fill=None, anchor="middle", weight=400, mono=False):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" font-family="{MONO if mono else FONT}" '
            f'fill="{fill or C["ink"]}">{s}</text>')


# ══════════════════════════════════════════════════════════════
#  ② 악보 + 음별 표  —  한 좌표계 위에
# ══════════════════════════════════════════════════════════════
def _score_table(res, notes, sig, width, x0, step, tol_cent, tol_ms):
    """악보 한 줄 아래에 음별 표를 같은 열로 붙입니다."""
    #| 흐름  악보를 그리고, 그 음표 x 를 그대로 표의 열로 쓴다
    #| 입력  분석 결과 · 음 목록 · 조표 · 가로 배치 · 허용 범위
    #| 호출  staff.line → 악보 (판정 배지 + 누르면 재생)
    #| 단계  악보 아래에 표의 가로줄과 왼쪽 이름표를 그린다
    #| 반복  음마다 = 표의 열 하나
    #| 갈래     소리를 못 찾았나 ? 빈 칸으로 둔다 : 세 지표를 막대로 그린다
    #| 단계     음정·박자·안정도를 각각 작은 막대와 숫자로
    #| 단계     활 방향 기호를 맨 아랫줄에
    #| 갈래     포지션을 옮기는 음인가 ? 열 전체를 강조하고 '손 이동' 을 단다 : 그대로 둔다
    #| 단계  재생 위치를 따라다닐 세로선을 악보와 표에 걸쳐 하나 놓는다
    #| 출력  (SVG, 높이)
    rows = res["rows"]
    n = len(rows)
    W = step * n
    p = []

    def badge(i):
        r = rows[i]
        if not r["detected"]:
            return C["muted"], "?"
        if abs(r["cent"]) <= tol_cent:
            return C["good"], "✓"
        return (C["high"], "↑") if r["cent"] > 0 else (C["bad"], "↓")

    top = staff.layout(notes)[0]
    parts, sc_bottom = staff.line(notes, x0, step, top, right=x0 + W + 8,
                                  sig=sig, badges=badge, click="playNote",
                                  show_name=False, show_position=True)
    p += parts

    # ── 표 ──
    head_y = sc_bottom + 26                 # 음 이름 줄
    t0 = head_y + 14                        # 첫 지표 줄의 위쪽
    shift = music.shift_index(notes)

    # 강조 열 (포지션을 옮기는 음)
    if shift is not None:
        hx = x0 + step * shift
        p.append(f'<rect x="{hx:.1f}" y="{head_y-22:.1f}" width="{step:.1f}" '
                 f'height="{ROW_H*len(ROWS)+34:.1f}" rx="8" fill="{C["warn"]}" '
                 f'opacity="0.10" stroke="{C["warn"]}" stroke-opacity="0.45"/>')
        p.append(_txt(hx + step / 2, t0 + ROW_H * len(ROWS) + 16, "손 이동",
                      10, C["warn"], weight=600))

    # 가로줄 + 왼쪽 이름표
    for k, (label, unit) in enumerate(ROWS):
        y = t0 + ROW_H * k
        p.append(f'<line x1="{x0-96:.1f}" y1="{y:.1f}" x2="{x0+W:.1f}" y2="{y:.1f}" '
                 f'stroke="{C["line"]}" stroke-width="1"/>')
        p.append(_txt(x0 - 12, y + ROW_H / 2 + 4, label, 11, C["ink2"], "end", 600))
        if unit:
            p.append(_txt(x0 - 12, y + ROW_H / 2 + 16, f"({unit})", 9, C["muted"], "end"))
    p.append(f'<line x1="{x0-96:.1f}" y1="{t0+ROW_H*len(ROWS):.1f}" '
             f'x2="{x0+W:.1f}" y2="{t0+ROW_H*len(ROWS):.1f}" '
             f'stroke="{C["line"]}" stroke-width="1"/>')
    p.append(_txt(x0 - 12, head_y, "음", 11, C["ink2"], "end", 600))

    def cell_bar(cx, cy, val, scale, color, cap=13.0):
        """칸 하나 안의 작은 막대. 가운데 선에서 위/아래로 자랍니다."""
        h = max(1.5, min(cap, abs(val) * scale))
        y = cy - h if val > 0 else cy
        return (f'<rect x="{cx-15:.1f}" y="{y:.1f}" width="30" height="{h:.1f}" '
                f'rx="2" fill="{color}" opacity="0.9"/>')

    for i, r in enumerate(rows):
        cx = staff.note_x(i, x0, step)

        # 음 이름 + 손가락
        fing = "개방" if r["finger"] == 0 else f'{r["finger"]}번'
        p.append(_txt(cx, head_y, f'{r["ko"]} ({fing})', 12,
                      C["ink"] if r["detected"] else C["muted"], weight=600))

        if not r["detected"]:
            p.append(_txt(cx, t0 + ROW_H * 1.5, "소리 없음", 9.5, C["muted"]))
            continue

        # ① 음정 — 허용 범위 안이면 초록, 벗어나면 높게=파랑 / 낮게=빨강
        y = t0 + ROW_H / 2
        col = C["good"] if abs(r["cent"]) <= tol_cent else (
            C["high"] if r["cent"] > 0 else C["bad"])
        p.append(f'<line x1="{cx-19:.1f}" y1="{y:.1f}" x2="{cx+19:.1f}" y2="{y:.1f}" '
                 f'stroke="{C["line"]}" stroke-width="1"/>')
        p.append(cell_bar(cx, y, r["cent"], 0.42, col))
        p.append(_txt(cx, y + (16 if r["cent"] > 0 else -6), f'{r["cent"]:+.0f}',
                      10.5, col, weight=700, mono=True))

        # ② 박자 — 허용 안이면 초록, 벗어나면 주황
        y = t0 + ROW_H * 1.5
        col = C["good"] if abs(r["ms"]) <= tol_ms else C["beat"]
        p.append(f'<line x1="{cx-19:.1f}" y1="{y:.1f}" x2="{cx+19:.1f}" y2="{y:.1f}" '
                 f'stroke="{C["line"]}" stroke-width="1"/>')
        p.append(cell_bar(cx, y, r["ms"], 7.0 / tol_ms, col, cap=14))
        p.append(_txt(cx, y + (16 if r["ms"] > 0 else -6), f'{r["ms"]:+.0f}',
                      10.5, col, weight=700, mono=True))

        # ③ 안정도 — 크기만 (아래로 자라게)
        y = t0 + ROW_H * 2.5
        p.append(f'<line x1="{cx-19:.1f}" y1="{y-6:.1f}" x2="{cx+19:.1f}" y2="{y-6:.1f}" '
                 f'stroke="{C["line"]}" stroke-width="1"/>')
        p.append(cell_bar(cx, y - 6, -r["std"], 1.5, C["steady"], cap=15))
        p.append(_txt(cx, y + 14, f'±{r["std"]:.0f}', 10.5, C["steady"],
                      weight=700, mono=True))

        # ④ 활 방향
        y = t0 + ROW_H * 3.5
        bc = C["down"] if r["bow"] == "down" else C["up"]
        if r["bow"] == "down":
            p.append(f'<path d="M {cx-6} {y+5} L {cx-6} {y-4} L {cx+6} {y-4} '
                     f'L {cx+6} {y+5}" fill="none" stroke="{bc}" stroke-width="2.2" '
                     f'stroke-linecap="square"/>')
        else:
            p.append(f'<path d="M {cx-6} {y-4} L {cx} {y+6} L {cx+6} {y-4}" '
                     f'fill="none" stroke="{bc}" stroke-width="2.2" '
                     f'stroke-linecap="round" stroke-linejoin="round"/>')

        # 열 전체를 누르면 그 음이 재생됩니다
        p.append(f'<rect x="{cx-step/2:.1f}" y="{head_y-20:.1f}" width="{step:.1f}" '
                 f'height="{ROW_H*len(ROWS)+30:.1f}" fill="transparent" '
                 f'style="cursor:pointer" onclick="playNote({i})"/>')

    H = t0 + ROW_H * len(ROWS) + 34
    p.append(f'<line id="phead" x1="{x0}" y1="{top-44}" x2="{x0}" y2="{H-6}" '
             f'stroke="{C["trace"]}" stroke-width="1.6" opacity="0" '
             f'style="pointer-events:none"/>')

    return (f'<svg viewBox="0 0 {width} {H}" width="100%" '
            f'style="max-width:100%;height:auto;display:block">{"".join(p)}</svg>'), H


# ══════════════════════════════════════════════════════════════
#  ③ 궤적 — 음 하나 안에서의 움직임
# ══════════════════════════════════════════════════════════════
TR_SPAN = 45.0
TR_PPC = 84 / TR_SPAN


def _trace(res, notes, width, x0, step, tol_cent):
    """음 안에서의 흔들림. 표와 같은 가로 좌표를 씁니다."""
    #| 흐름  음 안에서 음정이 어떻게 움직였는지 그린다
    #| 입력  분석 결과 · 가로 배치 · 허용 범위
    #| 단계  허용 범위 띠와 눈금을 깔고 음 경계마다 세로선을 긋는다
    #| 반복  궤적을 끊어 가며
    #| 갈래     센트가 화면 밖으로 튀나 ? 선을 끊는다 : 이어 그린다
    #| 단계  목표선 위는 파랑, 아래는 빨강으로 채운다
    #| 출력  (SVG, 높이)
    n = len(notes)
    W = step * n
    y0 = 104
    p = []

    def X(u):
        return x0 + step * u

    def Y(c):
        return y0 - max(-TR_SPAN, min(TR_SPAN, c)) * TR_PPC

    p.append(f'<rect x="{x0}" y="{Y(tol_cent):.1f}" width="{W:.1f}" '
             f'height="{Y(-tol_cent)-Y(tol_cent):.1f}" fill="{C["good"]}" opacity="0.12"/>')
    for cv in (-40, -20, 0, 20, 40):
        y, main = Y(cv), cv == 0
        p.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+W:.1f}" y2="{y:.1f}" '
                 f'stroke="{C["line"] if not main else C["ink2"]}" '
                 f'stroke-width="{1.6 if main else 1}" '
                 f'opacity="{0.7 if main else 1}"/>')
        p.append(_txt(x0 - 12, y + 3.5, f'{cv:+d}' if cv else '0', 9.5,
                      C["muted"], "end", mono=True))
    for i in range(1, n):
        p.append(f'<line x1="{X(i):.1f}" y1="{Y(TR_SPAN):.1f}" x2="{X(i):.1f}" '
                 f'y2="{Y(-TR_SPAN):.1f}" stroke="{C["line"]}" stroke-width="1"/>')

    # 음이 바뀌는 순간에는 앞 음이 남아 센트가 수백까지 튑니다 → 선을 끊습니다
    runs, cur = [], []
    for u, v in res["trace"]:
        if abs(v) <= TR_SPAN * 0.97:
            cur.append((u, v))
        else:
            if len(cur) > 2:
                runs.append(cur)
            cur = []
    if len(cur) > 2:
        runs.append(cur)

    for sign, col in ((1, C["high"]), (-1, C["bad"])):
        for run in runs:
            seg = []
            for u, v in run + [(run[-1][0], 0.0)]:
                if v * sign > 0:
                    seg.append((X(u), Y(v)))
                else:
                    if len(seg) > 1:
                        d = (f'M {seg[0][0]:.1f} {y0} '
                             + " ".join(f'L {a:.1f} {b:.1f}' for a, b in seg)
                             + f' L {seg[-1][0]:.1f} {y0} Z')
                        p.append(f'<path d="{d}" fill="{col}" opacity="0.28"/>')
                    seg = []
    for i in range(n):
        p.append(f'<line x1="{X(i)+3:.1f}" y1="{y0}" x2="{X(i+1)-3:.1f}" y2="{y0}" '
                 f'stroke="{C["ink"]}" stroke-width="2.2" opacity="0.8" '
                 f'stroke-linecap="round"/>')
    for run in runs:
        d = "M " + " L ".join(f'{X(u):.1f} {Y(v):.1f}' for u, v in run)
        p.append(f'<path d="{d}" fill="none" stroke="{C["trace"]}" stroke-width="2" '
                 f'stroke-linejoin="round"/>')

    lx = x0 + W + 12
    p.append(_txt(lx, y0 - 38, "높게", 10, C["high"], "start", 600))
    p.append(_txt(lx, y0 + 4, "목표", 10, C["ink"], "start", 600))
    p.append(_txt(lx, y0 + 44, "낮게", 10, C["bad"], "start", 600))
    p.append(_txt(lx, Y(tol_cent) - 5, f"±{tol_cent:.0f} 허용", 9, C["muted"], "start"))

    H = y0 + 96
    p.append(f'<line id="phead2" x1="{x0}" y1="14" x2="{x0}" y2="{H-30}" '
             f'stroke="{C["trace"]}" stroke-width="1.6" opacity="0" '
             f'style="pointer-events:none"/>')
    return (f'<svg viewBox="0 0 {width} {H}" width="100%" '
            f'style="max-width:100%;height:auto;display:block">{"".join(p)}</svg>'), H


# ══════════════════════════════════════════════════════════════
#  ④ 숫자를 말로
# ══════════════════════════════════════════════════════════════
def overall_score(res, tol_cent, tol_ms):
    """종합 점수 — 음정 50 · 박자 30 · 활 20."""
    #| 흐름  세 지표를 정해진 비중으로 섞어 한 숫자로 만든다
    #| 단계  활 안정도는 ±3센트 이하를 100점, ±20센트를 0점으로 환산한다
    #| 출력  (종합 점수, 부분 점수 셋)
    pitch = res["pitch_pct"]
    beat = res["time_pct"]
    bow = max(0.0, min(100.0, 100 - (res["bow_std"] - 3) * 6))
    return round(pitch * 0.5 + beat * 0.3 + bow * 0.2), (pitch, beat, bow)


def weak_notes(res, tol_cent, top=3):
    """가장 먼저 고칠 음 — 오차가 큰 순서."""
    #| 흐름  허용 범위를 벗어난 음을 오차 큰 순서로 셋 고른다
    bad = [(i, r) for i, r in enumerate(res["rows"])
           if r["detected"] and abs(r["cent"]) > tol_cent]
    bad.sort(key=lambda x: -abs(x[1]["cent"]))
    return bad[:top]


def distribution(res, tol_cent):
    """음정 오차 분포 — 다섯 칸."""
    #| 흐름  음정 오차를 다섯 구간으로 나눠 개수를 센다
    #| 단계  구간 경계는 허용 범위(±t)와 그 두 배(±2t)로 잡는다
    t = tol_cent
    bins = [(f"<−{2*t:.0f}", C["bad"], lambda c: c < -2 * t),
            (f"−{2*t:.0f} ~ −{t:.0f}", C["warn"], lambda c: -2 * t <= c < -t),
            (f"−{t:.0f} ~ +{t:.0f}", C["good"], lambda c: -t <= c <= t),
            (f"+{t:.0f} ~ +{2*t:.0f}", "#60a5fa", lambda c: t < c <= 2 * t),
            (f">+{2*t:.0f}", C["high"], lambda c: c > 2 * t)]
    cents = [r["cent"] for r in res["rows"] if r["detected"]]
    return [(lab, col, sum(1 for c in cents if f(c))) for lab, col, f in bins]


def cent_to_mm(note, cent):
    """센트 오차 → 손가락을 몇 mm 옮겨야 하는지.

    "18센트 낮다"는 초보자에게 감이 안 옵니다.
    "2.4mm 브리지 쪽으로"가 바로 실행할 수 있는 지시입니다.
    """
    #| 흐름  틀린 주파수와 목표 주파수의 지판 위치 차이를 잰다
    f_open = music.STRING_BY_NAME[note["string"]]["freq"]
    played = note["freq"] * 2 ** (cent / 1200)
    return (music.mm_from_freq(played, f_open)
            - music.mm_from_freq(note["freq"], f_open))


def comments(res, notes, tol_cent, tol_ms):
    """분석 코멘트 — 진단 한 줄 + 바로 아래 처방 한 줄.

    원인만 적으면 "그래서 뭘 하지?"가 남습니다.
    한 항목은 반드시 (무엇이 문제인가 · 무엇을 하면 되는가) 두 줄입니다.
    """
    #| 흐름  숫자 → (진단 · 처방 · 교정 드릴) 묶음
    #| 입력  분석 결과 · 음 목록 · 허용 범위
    #| 갈래  평균이 한쪽으로 쏠렸나 ? 손 전체를 옮기라고 한다 : 들쭉날쭉하다고 한다
    #| 갈래  유난히 큰 음이 있나 ? 그 음을 mm 로 짚어 준다 : 넘어간다
    #| 갈래  포지션 옮긴 뒤가 더 나쁜가 ? 기준음 짚고 올라가라고 한다 : 넘어간다
    #| 갈래  흔들림이 큰 음이 있나 ? 롱톤을 권한다 : 넘어간다
    #| 갈래  늦게 들어간 음이 있나 ? BPM 을 낮추라고 한다 : 넘어간다
    #| 출력  항목 목록 — 각 항목은 진단·처방·드릴
    rows = [r for r in res["rows"] if r["detected"]]
    if not rows:
        return [{"why": "소리를 찾지 못했습니다.",
                 "fix": "마이크 볼륨과 녹음 길이를 확인한 뒤 다시 녹음해 주세요.",
                 "drill": None}]

    out = []
    st = notes[0]["string"]
    m = res["mean_cent"]

    # ① 전체 치우침
    if abs(m) > tol_cent / 2:
        low = m < 0
        out.append({
            "why": f'{st}현 전체가 평균 <b>{m:+.0f} cent</b>로 '
                   f'{"낮습니다" if low else "높습니다"}.',
            "fix": f'손 전체가 {"너트" if low else "브리지"} 쪽으로 흘렀습니다. '
                   f'개방현을 먼저 울려 기준을 잡고, 손 전체를 '
                   f'{"브리지" if low else "너트"} 쪽으로 조금 옮긴 채 다시 해 보세요.',
            "drill": {"kind": "slow", "label": "느리게 다시"},
        })
    else:
        out.append({
            "why": "치우침은 없지만 음마다 <b>들쭉날쭉</b>합니다.",
            "fix": "자리를 외우기보다 소리로 확인하는 연습이 필요합니다. "
                   "개방현과 번갈아 짚으며 귀로 맞춰 보세요.",
            "drill": {"kind": "slow", "label": "느리게 다시"},
        })

    # ② 가장 큰 음 — mm 로 바꿔서 알려줍니다
    worst_i, worst = max(((i, r) for i, r in enumerate(res["rows"]) if r["detected"]),
                         key=lambda x: abs(x[1]["cent"]))
    if abs(worst["cent"]) > tol_cent:
        mm = cent_to_mm(worst, worst["cent"])
        high = worst["cent"] > 0
        fing = "개방현" if worst["finger"] == 0 else f'{worst["finger"]}번 손가락'
        out.append({
            "why": f'{st}현 {worst["position"]}포지션 {fing} '
                   f'<b>{worst["ko"]}</b>가 {abs(worst["cent"]):.0f} cent '
                   f'{"높습니다" if high else "낮습니다"} — 이번 연습에서 가장 큽니다.',
            "fix": f'그 손가락을 <b>{abs(mm):.1f}mm {"너트" if high else "브리지"} 쪽</b>으로 '
                   f'옮기세요. 개방현과 번갈아 짚으면 귀로 바로 확인됩니다.',
            "drill": {"kind": "note", "idx": worst_i,
                      "label": f'{worst["ko"]} 집중 연습'},
        })

    # ③ 포지션 이동
    sh = music.shift_index(notes)
    if sh is not None and sh < len(res["rows"]):
        before = [abs(r["cent"]) for r in res["rows"][:sh] if r["detected"]]
        after = [abs(r["cent"]) for r in res["rows"][sh:] if r["detected"]]
        if before and after:
            ratio = (sum(after) / len(after)) / max(1e-6, sum(before) / len(before))
            if ratio > 1.3:
                out.append({
                    "why": f'{notes[sh]["position"]}포지션으로 옮긴 뒤 오차가 '
                           f'<b>{ratio:.1f}배</b>로 커집니다.',
                    "fix": f'옮기기 직전 음 <b>{notes[sh-1]["ko"]}</b>를 짚어 소리로 '
                           f'확인한 뒤 올라가세요. 손목만 꺾지 말고 팔 전체로 옮깁니다.',
                    "drill": {"kind": "shift", "label": "시프팅 구간만"},
                })

    # ④ 활 흔들림
    shaky = max(rows, key=lambda r: r["std"])
    if shaky["std"] > 4:
        out.append({
            "why": f'<b>{shaky["ko"]}</b>의 흔들림이 ±{shaky["std"]:.0f} cent로 '
                   f'가장 큽니다 — 손가락이 아니라 <b>활</b> 문제입니다.',
            "fix": "활 속도가 일정하지 않습니다. 개방현을 한 활에 네 박씩 길게 켜며 "
                   "처음부터 끝까지 소리 크기가 같은지 들어 보세요.",
            "drill": {"kind": "longtone", "label": "활 롱톤"},
        })

    # ⑤ 박자
    late = [r for r in rows if abs(r["ms"]) > tol_ms]
    if late:
        out.append({
            "why": f'{"·".join(r["ko"] for r in late)}에서 박자가 '
                   f'<b>{max(late, key=lambda r: abs(r["ms"]))["ms"]:+.0f}ms</b> 밀립니다.',
            "fix": "대개 손을 옮기거나 활을 바꾸는 데 걸리는 시간입니다. "
                   "BPM을 20 낮춰 정확히 맞춘 뒤 다시 올리세요.",
            "drill": {"kind": "slow", "label": "느리게 다시"},
        })

    return out[:5]


# ══════════════════════════════════════════════════════════════
#  한 장으로 합치기
# ══════════════════════════════════════════════════════════════
def height(notes, width: int = 980) -> int:
    """components.html 에 넘길 높이."""
    #| 흐름  표 높이 + 궤적 높이 + 고정 카드 높이를 더한다
    top = staff.layout(notes)[0]
    _, sc_bottom = staff.line(notes, 108, (width - 150 - 108) / len(notes), top,
                              right=width, sig=("♯", []))
    tbl = sc_bottom + 26 + 14 + ROW_H * len(ROWS) + 34
    return int(tbl + 200 + 700)


def build(res, notes, sig, bpm, wav_bytes, title, when, width=980,
          tol_cent=12.0, tol_ms=40.0) -> str:
    """분석 결과 + 녹음 → 결과 리포트 HTML."""
    #| 흐름  분석 결과 + 녹음 → 결과 리포트 한 장
    #| 입력  분석 결과 · 음 목록 · 조표 · BPM · 녹음 WAV
    #| 단계  녹음을 HTML 안에 통째로 넣는다 — 파일 하나로 공유되게
    #| 호출  overall_score → 종합 점수와 부분 점수
    #| 단계  ① 종합 점수 도넛 + 지표 넷을 만든다
    #| 호출  _score_table → ② 악보 + 음별 표
    #| 호출  _trace → ③ 음 안에서의 움직임
    #| 호출  weak_notes → ④ 가장 취약한 음 셋
    #| 호출  comments → ④ 분석 코멘트
    #| 호출  distribution → ④ 음정 분포
    #| 단계  ⑤ 다시 듣기 — 전체·마디별·취약음별 버튼
    #| 단계  화면의 0초는 '첫 소리가 난 자리' 라고 JS 에 알려준다 (T0)
    #| 출력  HTML  (누르면 그 부분 내 연주가 재생됨)
    n = len(notes)
    x0 = max(108, staff.head_width(sig))
    step = (width - 150 - x0) / n
    beat = 60.0 / bpm
    b64 = base64.b64encode(wav_bytes).decode()

    total, (p_pitch, p_beat, p_bow) = overall_score(res, tol_cent, tol_ms)
    ring = score_color(total)
    circ = 2 * 3.14159 * 42

    stats = [
        ("음정 정확도", f'{res["pitch_pct"]:.0f}%',
         f'±{tol_cent:.0f} cent 안',
         C["good"] if res["pitch_pct"] >= 60 else C["bad"]),
        ("평균 음정 오차", f'{res["mean_cent"]:+.0f}',
         "cent · 전체적으로 " + ("낮게" if res["mean_cent"] < 0 else "높게"),
         C["bad"] if res["mean_cent"] < -3 else
         (C["high"] if res["mean_cent"] > 3 else C["good"])),
        ("박자 정확도", f'{res["time_pct"]:.0f}%', f'±{tol_ms:.0f} ms 안',
         C["high"] if res["time_pct"] >= 60 else C["warn"]),
        ("활 안정도", f'±{res["bow_std"]:.0f}', "cent · 음 안에서의 흔들림",
         C["steady"]),
    ]
    stat_html = "".join(
        f'<div class="card stat"><div class="lab">{a}</div>'
        f'<div class="num" style="color:{d}">{b}</div>'
        f'<div class="sub">{c}</div></div>' for a, b, c, d in stats)

    table_svg, _ = _score_table(res, notes, sig, width, x0, step, tol_cent, tol_ms)
    trace_svg, _ = _trace(res, notes, width, x0, step, tol_cent)

    weak = weak_notes(res, tol_cent)
    if weak:
        weak_html = "".join(
            f'<button class="wk" onclick="playNote({i})">'
            f'<span class="rk" style="background:{[C["bad"],C["warn"],"#64748b"][k]}">{k+1}</span>'
            f'<span class="wko">{r["ko"]} '
            f'<i>({"개방" if r["finger"]==0 else str(r["finger"])+"번"})</i></span>'
            f'<span class="wc" style="color:{C["high"] if r["cent"]>0 else C["bad"]}">'
            f'{r["cent"]:+.0f} cent</span></button>'
            for k, (i, r) in enumerate(weak))
    else:
        weak_html = (f'<div style="color:{C["good"]};font-size:13px;padding:10px 2px">'
                     f'허용 범위를 벗어난 음이 없습니다.</div>')

    tips = comments(res, notes, tol_cent, tol_ms)
    cmt_html = "".join(
        f'<li><div class="why">{t["why"]}</div>'
        f'<div class="fix">↳ {t["fix"]}</div></li>' for t in tips)

    dist = distribution(res, tol_cent)
    dmax = max(1, max(c for _, _, c in dist))
    dist_html = "".join(
        f'<div class="db"><div class="dbar" style="height:{6+38*c/dmax:.0f}px;'
        f'background:{col};opacity:{0.95 if c else 0.25}"></div>'
        f'<div class="dnum">{c}개</div>'
        f'<div class="dlab" style="color:{col if c else C["muted"]}">{lab}</div></div>'
        for lab, col, c in dist)

    seg_html = "".join(
        f'<button onclick="playRange({i*4*beat:.3f},{min((i+1)*4,n)*beat:.3f})">'
        f'{i+1}마디</button>' for i in range((n + 3) // 4))

    js = json.dumps([{"ko": r["ko"],
                      "cent": None if not r["detected"] else round(r["cent"], 1)}
                     for r in res["rows"]], ensure_ascii=False)

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 *{{box-sizing:border-box}}
 body{{margin:0;background:{C['bg']};color:{C['ink']};font-family:{FONT}}}
 #w{{width:{width+40}px;margin:0 auto;padding:4px 20px 24px}}
 .head{{display:flex;align-items:flex-start;gap:16px;margin-bottom:14px}}
 .h1{{font-size:20px;font-weight:700;margin:0 0 3px}}
 .h2{{font-size:13.5px;color:{C['ink2']};margin:0 0 3px}}
 .h3{{font-size:12px;color:{C['muted']}}}
 .card{{background:{C['panel']};border:1px solid {C['line']};border-radius:14px;
   padding:14px 16px}}
 .top{{display:grid;grid-template-columns:1.65fr 1fr 1fr 1fr 1fr;gap:11px;
   margin-bottom:12px}}
 .stat{{display:flex;flex-direction:column;justify-content:center}}
 .lab{{font-size:11.5px;color:{C['muted']};margin-bottom:2px}}
 .num{{font-size:29px;font-weight:700;line-height:1.15;font-family:{MONO}}}
 .sub{{font-size:10.5px;color:{C['muted']};line-height:1.4;margin-top:2px}}
 .ring{{display:flex;align-items:center;gap:14px}}
 .rtxt{{font-size:11px;color:{C['muted']};line-height:1.8;white-space:nowrap}}
 .rtxt b{{color:{C['ink2']};font-weight:600}}
 .ct{{font-size:14px;font-weight:600;margin-bottom:2px}}
 .cs{{font-size:11.5px;color:{C['muted']};margin-bottom:10px;line-height:1.6}}
 .mb{{margin-bottom:12px}}
 .bot{{display:grid;grid-template-columns:1fr 1.15fr 1.25fr;gap:11px}}
 .wk{{display:flex;align-items:center;gap:10px;width:100%;text-align:left;
   background:{C['panel2']};border:1px solid {C['line']};border-radius:10px;
   padding:9px 12px;margin-bottom:7px;cursor:pointer;font-family:inherit;
   color:{C['ink']}}}
 .wk:hover{{border-color:{C['accent']}}}
 .rk{{flex:none;width:21px;height:21px;border-radius:50%;color:#fff;font-size:11px;
   font-weight:700;display:flex;align-items:center;justify-content:center}}
 .wko{{font-size:13.5px;font-weight:600}}
 .wko i{{font-size:10.5px;font-style:normal;color:{C['muted']};font-weight:400}}
 .wc{{margin-left:auto;font-family:{MONO};font-size:13px;font-weight:700}}
 ul{{margin:0;padding-left:15px}}
 li{{margin-bottom:9px}}
 li::marker{{color:{C['muted']}}}
 .why{{font-size:12.5px;line-height:1.6;color:{C['ink2']}}}
 .why b{{color:{C['ink']}}}
 .fix{{font-size:12px;line-height:1.6;color:{C['good']};margin-top:2px}}
 .fix b{{color:#7ee89a}}
 .dist{{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;
   align-items:end;height:120px}}
 .db{{display:flex;flex-direction:column;align-items:center;
   justify-content:flex-end;height:100%}}
 .dbar{{width:100%;border-radius:5px 5px 0 0}}
 .dnum{{font-size:11.5px;font-weight:700;font-family:{MONO};margin-top:5px}}
 .dlab{{font-size:9.5px;margin-top:2px;text-align:center;line-height:1.3}}
 .play{{display:flex;gap:7px;align-items:center;flex-wrap:wrap;
   border-top:1px solid {C['line']};margin-top:12px;padding-top:11px}}
 button{{background:{C['panel2']};color:{C['ink']};border:1px solid {C['line']};
   border-radius:8px;padding:6px 12px;font-size:12px;cursor:pointer;
   font-family:inherit}}
 button:hover{{border-color:{C['accent']}}}
 .main{{background:{C['accent']};border-color:{C['accent']};color:#fff;
   font-weight:600}}
 .hint{{font-size:11.5px;color:{C['muted']}}}
 #now{{font-family:{MONO};font-size:12px;color:{C['trace']};min-width:120px}}
 /* 좁은 화면 — 카드를 접어 세로로 */
 @media (max-width: 900px) {{
   #w{{width:100%;padding:4px 10px 18px}}
   .top{{grid-template-columns:1fr 1fr;gap:8px}}
   .bot{{grid-template-columns:1fr;gap:8px}}
   .num{{font-size:24px}}
   .ring svg{{width:82px;height:82px}}
 }}
</style></head><body><div id="w">

 <div class="head">
   <div>
     <div class="h1">연습 결과</div>
     <div class="h2">{title}</div>
     <div class="h3">{n}음 · {bpm} BPM · {when}</div>
   </div>
 </div>

 <div class="top">
   <div class="card ring">
     <svg width="100" height="100" viewBox="0 0 100 100" style="flex:none">
       <circle cx="50" cy="50" r="42" fill="none" stroke="{C['line']}" stroke-width="9"/>
       <circle cx="50" cy="50" r="42" fill="none" stroke="{ring}" stroke-width="9"
         stroke-linecap="round" stroke-dasharray="{circ*total/100:.1f} {circ:.1f}"
         transform="rotate(-90 50 50)"/>
       <text x="50" y="52" text-anchor="middle" font-size="27" font-weight="700"
         font-family="{MONO}" fill="{C['ink']}">{total}</text>
       <text x="50" y="68" text-anchor="middle" font-size="11"
         font-family="{MONO}" fill="{C['muted']}">/100</text>
     </svg>
     <div>
       <div class="lab">종합 점수</div>
       <div class="rtxt">
         음정 <b>{p_pitch:.0f}</b> × 50%<br>박자 <b>{p_beat:.0f}</b> × 30%<br>활 <b>{p_bow:.0f}</b> × 20%
       </div>
     </div>
   </div>
   {stat_html}
 </div>

 <div class="card mb">
   <div class="ct">음별 분석 결과</div>
   <div class="cs">표의 열은 위 악보의 음표와 <b>같은 가로 좌표</b>입니다.
     악보에서 어느 음인지 보고, 표에서 얼마나 벗어났는지 읽습니다 ·
     <b>아무 열이나 누르면 그 부분 내 연주가 다시 들립니다</b></div>
   {table_svg}
   <div class="play">
     <button class="main" onclick="playRange(0,{n*beat:.3f})">▶ 전체 듣기</button>
     {seg_html}
     <button onclick="stopAll()">■ 정지</button>
     <span id="now"></span>
     <span class="hint" style="margin-left:auto">
       음정 ±{tol_cent:.0f} cent · 박자 ±{tol_ms:.0f} ms 를 허용 범위로 봅니다</span>
   </div>
 </div>

 <div class="card mb">
   <div class="ct">음 하나 안에서의 움직임</div>
   <div class="cs">가운데 굵은 선이 목표입니다. 위로 벗어나면 높게, 아래로 벗어나면 낮게 ·
     이 흔들림의 크기가 위 표의 <b>안정도</b>입니다 (활 문제)</div>
   {trace_svg}
 </div>

 <div class="bot">
   <div class="card">
     <div class="ct">가장 취약한 음 TOP 3</div>
     <div class="cs">눌러서 그 음만 다시 듣기</div>
     {weak_html}
   </div>
   <div class="card">
     <div class="ct">분석 코멘트</div>
     <div class="cs">회색 = 무엇이 문제인가 · <b style="color:{C['good']}">초록 = 무엇을
       하면 되는가</b> · 아래 [교정 연습]에서 바로 넘어갈 수 있습니다</div>
     <ul>{cmt_html}</ul>
   </div>
   <div class="card">
     <div class="ct">음정 분포</div>
     <div class="cs">{n}음이 어느 구간에 들어갔는지 (cent)</div>
     <div class="dist">{dist_html}</div>
   </div>
 </div>

 <audio id="rec" src="data:audio/wav;base64,{b64}"></audio>
</div>
<script>
const NOTES = {js};
const X0 = {x0}, STEP = {step}, BEAT = {beat}, T0 = {res["t0"]:.4f};
const rec = document.getElementById('rec');
const ph = document.getElementById('phead'), ph2 = document.getElementById('phead2');
const now = document.getElementById('now');
let stopAt = null, raf = null;

// 화면의 0초는 '첫 소리가 난 자리'. 녹음 파일에서는 T0 만큼 뒤입니다.
function playRange(a, b) {{
  stopAt = T0 + b; rec.currentTime = T0 + a; rec.play();
  if (!raf) raf = requestAnimationFrame(tick);
}}
function playNote(i) {{ playRange(i * BEAT, (i + 1) * BEAT); }}
function stopAll() {{ rec.pause(); stopAt = null; move(null); }}

function move(t) {{
  if (t === null) {{
    ph.style.opacity = ph2.style.opacity = 0; now.textContent = ''; return;
  }}
  const x = (X0 + STEP * (t / BEAT)).toFixed(1);
  for (const e of [ph, ph2]) {{
    e.setAttribute('x1', x); e.setAttribute('x2', x); e.style.opacity = 0.9;
  }}
  const nt = NOTES[Math.min(NOTES.length - 1, Math.max(0, Math.floor(t / BEAT)))];
  now.textContent = nt.cent === null ? nt.ko + '  —'
    : `${{nt.ko}}  ${{nt.cent > 0 ? '+' : ''}}${{nt.cent.toFixed(0)}} cent`;
}}
function tick() {{
  if (rec.paused) {{ raf = null; move(null); return; }}
  if (stopAt !== null && rec.currentTime >= stopAt - 0.01) {{
    rec.pause(); raf = null; move(null); return;
  }}
  move(rec.currentTime - T0);
  raf = requestAnimationFrame(tick);
}}
</script></body></html>"""
