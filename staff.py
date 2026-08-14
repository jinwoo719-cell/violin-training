"""
악보 한 줄 그리기 — 연습 화면과 결과 리포트가 같이 씁니다.

같은 악보를 두 군데서 따로 그리면 반드시 어긋납니다.
음표의 가로 좌표는 note_x() **한 곳에서만** 정하고,
아래에 붙는 그래프들이 전부 그 좌표를 받아 씁니다.
"""

import music

INK = "#e8e6e0"
AXIS = "#5a5a56"
MUT = "#8a8a86"
DOWN_COLOR = "#3987e5"     # 다운보우 ⊓
UP_COLOR = "#d95926"       # 업보우   ∨
POS_COLOR = {1: "#199e70", 3: "#c98500"}

GAP = 11                   # 오선 간격 (줄과 줄 사이)

# 조표에서 ♯/♭이 놓이는 오선 위치 (아래 첫 줄 E4 = 0)
SHARP_POS = {"F": 8, "C": 5, "G": 9, "D": 6, "A": 3, "E": 7, "B": 4}
FLAT_POS = {"B": 4, "E": 7, "A": 3, "D": 6, "G": 2, "C": 5, "F": 1}


def note_x(i: int, x0: float, step: float) -> float:
    """i번째 음의 가로 좌표. 아래 그래프들도 반드시 이 식을 씁니다."""
    return x0 + step * (i + 0.5)


def staff_pos(letter: str, octave: int) -> int:
    """음이름 → 오선 위치 번호. 아래 첫 줄(E4)이 0, 반칸마다 +1."""
    return (music.LETTERS.index(letter) - 2) + 7 * (octave - 4)


def layout(notes):
    """이 악보를 그리는 데 위아래로 얼마나 필요한지 미리 잽니다.

    G현처럼 낮은 음은 덧줄이 아래로 많이 내려가서
    자리를 미리 잡아 두지 않으면 잘립니다.
    """
    ps = [staff_pos(n["letter"], n["octave"]) for n in notes]
    hi, lo = max(ps), min(ps)
    top = 30 + max(0, (hi - 8)) * (GAP / 2) + 50      # 배지·활·슬러 자리
    bottom = 26 + max(0, (0 - lo)) * (GAP / 2) + 30   # 계이름·포지션 띠 자리
    return top, bottom


def sy(pos: float, top: float) -> float:
    """오선 위치 번호 → y좌표 (top = 맨 위 줄 F5 의 y)"""
    return top + (8 - pos) * (GAP / 2)


def _clef(top, left):
    """높은음자리표 — 나선 중심이 G4(아래에서 둘째 줄)에 오게."""
    ccx, ccy = left + GAP * 1.7, sy(2, top)

    def U(dx, dy):
        return f"{ccx + dx * GAP:.2f} {ccy + dy * GAP:.2f}"

    return (f'<path d="M {U(0,0)} C {U(-0.45,-0.35)} {U(-1.05,0.15)} {U(-1.05,0.78)} '
            f'C {U(-1.05,1.48)} {U(-0.32,1.90)} {U(0.34,1.62)} '
            f'C {U(1.10,1.30)} {U(1.34,0.32)} {U(1.05,-0.58)} '
            f'C {U(0.80,-1.48)} {U(0.05,-2.12)} {U(-0.30,-2.88)} '
            f'C {U(-0.62,-3.55)} {U(0.28,-4.00)} {U(0.64,-3.32)} '
            f'C {U(0.98,-2.72)} {U(0.55,-2.02)} {U(0.20,-1.52)} '
            f'C {U(-0.28,-0.78)} {U(0.30,1.30)} {U(0.42,2.32)} '
            f'C {U(0.54,3.20)} {U(-0.16,3.66)} {U(-0.64,3.24)} '
            f'C {U(-0.98,2.94)} {U(-0.86,2.46)} {U(-0.50,2.42)}" '
            f'fill="none" stroke="{INK}" stroke-width="{GAP*0.19:.2f}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def line(notes, x0, step, top, right, *, sig=("♯", []), left=14,
         badges=None, click=None, show_name=True, show_position=True):
    """악보 한 줄을 SVG 조각 리스트로 만듭니다.

    badges : i → (색, 글자).  결과 리포트에서 음마다 판정을 붙일 때.
    click  : JS 함수 이름.  주면 음표를 눌러 그 부분만 다시 들을 수 있게.
    """
    p = []
    n = len(notes)
    poss = [staff_pos(nt["letter"], nt["octave"]) for nt in notes]

    # ── 오선 다섯 줄 ──
    for i in range(5):
        y = top + i * GAP
        p.append(f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" '
                 f'stroke="{AXIS}" stroke-width="1"/>')
    p.append(_clef(top, left))

    # ── 조표 ──
    mark, keys = sig
    table = SHARP_POS if mark == "♯" else FLAT_POS
    kx = left + GAP * 3.5
    for k in keys:
        p.append(f'<text x="{kx:.1f}" y="{sy(table[k], top)+5:.1f}" '
                 f'text-anchor="middle" font-size="{GAP*1.7:.1f}" fill="{INK}">{mark}</text>')
        kx += GAP * 0.95

    # 활·슬러·배지가 놓이는 높이 — 가장 높은 음표보다 위로 통일합니다
    hi_y = min(sy(pp, top) for pp in poss)
    slur_y = min(hi_y, top) - 11
    bow_y = slur_y - 21          # 슬러 곡선 위로 확실히 띄웁니다
    badge_y = bow_y - 18

    # ── 슬러 — 한 활로 잇는 음들을 묶는 곡선 ──
    groups = {}
    for i, nt in enumerate(notes):
        groups.setdefault(nt["slur"], []).append(i)
    for g, idxs in groups.items():
        col = DOWN_COLOR if notes[idxs[0]]["bow"] == "down" else UP_COLOR
        if len(idxs) > 1:
            xa, xb = note_x(idxs[0], x0, step), note_x(idxs[-1], x0, step)
            p.append(f'<path d="M {xa:.1f} {slur_y+4:.1f} Q {(xa+xb)/2:.1f} '
                     f'{slur_y-9:.1f} {xb:.1f} {slur_y+4:.1f}" fill="none" '
                     f'stroke="{col}" stroke-width="1.8" opacity="0.9"/>')
        # 활 기호는 슬러 하나에 딱 하나 (한 활이니까)
        bx = (note_x(idxs[0], x0, step) + note_x(idxs[-1], x0, step)) / 2
        if notes[idxs[0]]["bow"] == "down":       # ⊓
            p.append(f'<path d="M {bx-5.5:.1f} {bow_y+8} L {bx-5.5:.1f} {bow_y} '
                     f'L {bx+5.5:.1f} {bow_y} L {bx+5.5:.1f} {bow_y+8}" fill="none" '
                     f'stroke="{col}" stroke-width="2.4" stroke-linecap="square"/>')
        else:                                      # ∨
            p.append(f'<path d="M {bx-5.5:.1f} {bow_y} L {bx:.1f} {bow_y+9} '
                     f'L {bx+5.5:.1f} {bow_y}" fill="none" stroke="{col}" '
                     f'stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>')

    # ── 음표 ──
    name_y = top + GAP * 4 + max(0, -min(poss)) * (GAP / 2) + 20
    for i, nt in enumerate(notes):
        x = note_x(i, x0, step)
        pos = poss[i]
        y = sy(pos, top)

        # 덧줄 — 오선 위로도, 아래로도
        for lp in range(10, pos + 1, 2):
            p.append(f'<line x1="{x-11.5:.1f}" y1="{sy(lp,top):.1f}" x2="{x+11.5:.1f}" '
                     f'y2="{sy(lp,top):.1f}" stroke="{INK}" stroke-width="1.4"/>')
        for lp in range(-2, pos - 1, -2):
            p.append(f'<line x1="{x-11.5:.1f}" y1="{sy(lp,top):.1f}" x2="{x+11.5:.1f}" '
                     f'y2="{sy(lp,top):.1f}" stroke="{INK}" stroke-width="1.4"/>')

        if nt["acc"]:
            p.append(f'<text x="{x-13:.1f}" y="{y+5:.1f}" text-anchor="middle" '
                     f'font-size="{GAP*1.6:.1f}" fill="{INK}">{nt["acc"]}</text>')

        p.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="6.2" ry="4.6" '
                 f'transform="rotate(-20 {x:.1f} {y:.1f})" fill="{INK}"/>')
        if pos >= 4:                       # 가운데 줄보다 높으면 기둥은 아래로
            p.append(f'<line x1="{x-5.6:.1f}" y1="{y+1:.1f}" x2="{x-5.6:.1f}" '
                     f'y2="{y+28:.1f}" stroke="{INK}" stroke-width="1.6"/>')
        else:
            p.append(f'<line x1="{x+5.6:.1f}" y1="{y-1:.1f}" x2="{x+5.6:.1f}" '
                     f'y2="{y-28:.1f}" stroke="{INK}" stroke-width="1.6"/>')

        if badges:
            col, txt = badges(i)
            if col:
                p.append(f'<circle cx="{x:.1f}" cy="{badge_y:.1f}" r="9" fill="{col}"/>')
                p.append(f'<text x="{x:.1f}" y="{badge_y+4:.1f}" text-anchor="middle" '
                         f'font-size="10.5" font-weight="700" fill="#fff">{txt}</text>')

        if show_name:
            p.append(f'<text x="{x:.1f}" y="{name_y:.1f}" text-anchor="middle" '
                     f'font-size="12" fill="{MUT}">{nt["ko"]}</text>')
            p.append(f'<text x="{x:.1f}" y="{name_y+14:.1f}" text-anchor="middle" '
                     f'font-size="10.5" fill="{POS_COLOR[nt["position"]]}">'
                     f'{"개방" if nt["finger"] == 0 else str(nt["finger"]) + "번"}</text>')

        if click:
            p.append(f'<rect x="{x-step/2:.1f}" y="{badge_y-12:.1f}" width="{step:.1f}" '
                     f'height="{name_y+18-(badge_y-12):.1f}" fill="transparent" '
                     f'style="cursor:pointer" onclick="{click}({i})"/>')

    # ── 마디선 ──
    for b in range(1, (n + 3) // 4 + 1):
        bx = x0 + step * 4 * b
        last = b * 4 >= n
        if last:
            bx = min(bx, x0 + step * n)
        p.append(f'<line x1="{bx:.1f}" y1="{top}" x2="{bx:.1f}" y2="{top+GAP*4}" '
                 f'stroke="{INK if last else AXIS}" stroke-width="{2.4 if last else 1}"/>')

    # ── 포지션 띠 — 어디서 손을 옮기는지 ──
    pos_y = name_y + 30
    if show_position:
        runs, cur = [], 0
        for i in range(1, n + 1):
            if i == n or notes[i]["position"] != notes[cur]["position"]:
                runs.append((cur, i - 1, notes[cur]["position"]))
                cur = i
        for a, b, ps in runs:
            xa = note_x(a, x0, step) - step * 0.42
            xb = note_x(b, x0, step) + step * 0.42
            col = POS_COLOR[ps]
            p.append(f'<line x1="{xa:.1f}" y1="{pos_y}" x2="{xb:.1f}" y2="{pos_y}" '
                     f'stroke="{col}" stroke-width="3" stroke-linecap="round"/>')
            p.append(f'<text x="{(xa+xb)/2:.1f}" y="{pos_y+16}" text-anchor="middle" '
                     f'font-size="11" font-weight="700" fill="{col}">{ps}포지션</text>')
        for a, b, ps in runs[1:]:
            xs = note_x(a, x0, step) - step * 0.5
            p.append(f'<line x1="{xs:.1f}" y1="{top-10}" x2="{xs:.1f}" y2="{pos_y-6}" '
                     f'stroke="#c3c2b7" stroke-width="1" stroke-dasharray="4 4" '
                     f'opacity="0.5"/>')
            p.append(f'<text x="{xs:.1f}" y="{pos_y-11}" text-anchor="middle" '
                     f'font-size="9.5" fill="#c3c2b7">손 이동</text>')

    return p, pos_y + 22
