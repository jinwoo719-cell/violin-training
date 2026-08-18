"""
악보 한 줄 그리기 — 연습 화면과 결과 리포트가 같이 씁니다.

같은 악보를 두 군데서 따로 그리면 반드시 어긋납니다.
음표의 가로 좌표는 note_x() **한 곳에서만** 정하고,
아래에 붙는 그래프들이 전부 그 좌표를 받아 씁니다.
"""

import glyphs
import music

#| 흐름  음 목록 → 악보 한 줄 SVG (가로 좌표를 여기서만 정한다)

INK = "#e8e5dc"        # 악보 — 순백이 아니라 아이보리 (나무색과 이어지게)
AXIS = "#5a5a56"
MUT = "#8a8a86"
DOWN_COLOR = "#5da9e9"     # 다운보우 ⊓
UP_COLOR = "#c9814a"         # 업보우   ∨
POS_COLOR = {1: "#4f8f6c", 3: "#a8813a"}

GAP = 11                   # 오선 간격 (줄과 줄 사이)

# 조표에서 ♯/♭이 놓이는 오선 위치 (아래 첫 줄 E4 = 0)
SHARP_POS = {"F": 8, "C": 5, "G": 9, "D": 6, "A": 3, "E": 7, "B": 4}
FLAT_POS = {"B": 4, "E": 7, "A": 3, "D": 6, "G": 2, "C": 5, "F": 1}


def note_x(i: int, x0: float, step: float) -> float:
    """i번째 음의 가로 좌표. 아래 그래프들도 반드시 이 식을 씁니다."""
    #| 흐름  음 번호 → 가로 좌표.  악보·낙하 노드·리포트 세 층이 모두 이 식을 쓴다
    return x0 + step * (i + 0.5)


def staff_pos(letter: str, octave: int) -> int:
    """음이름 → 오선 위치 번호. 아래 첫 줄(E4)이 0, 반칸마다 +1."""
    #| 흐름  음이름(A~G)과 옥타브 → 오선 몇 번째 칸인지
    return (music.LETTERS.index(letter) - 2) + 7 * (octave - 4)


def head_width(sig, left=14) -> float:
    """자리표 + 조표가 차지하는 가로 폭.

    음표는 이 뒤에서 시작해야 조표와 겹치지 않습니다.
    """
    #| 흐름  자리표 폭 + 조표 개수만큼의 폭을 더한다
    mark, keys = sig
    gl = glyphs.SHARP if mark == "♯" else glyphs.FLAT
    gh = GAP * (2.7 if mark == "♯" else 2.4)
    w = left + 2 + glyphs.width_of(glyphs.CLEF_G, GAP * 6.7) + GAP * 0.55
    w += len(keys) * (glyphs.width_of(gl, gh) + GAP * 0.2)
    return w + GAP


# 아래쪽은 **언제나 G현 개방현(G3)** 자리까지 비웁니다.
#
#  왜 고정하나: 아래 여백을 그 악보의 최저음에 맞춰 잡으면, A현 연습에서는
#  계이름이 오선 바로 밑에 붙고 G현 연습에서는 한참 아래로 내려갑니다.
#  그러면 ① 줄을 바꿀 때마다 악보 높이가 출렁이고
#         ② G현처럼 덧줄이 많은 악보에서 음표머리와 계이름이 겹칩니다.
#  G3 는 바이올린이 낼 수 있는 가장 낮은 음이라, 여기 맞춰 두면 어느 줄이든
#  같은 자리에 같은 모양으로 그려집니다.
FLOOR = -5                 # staff_pos("G", 3) — G현 개방현


def layout(notes, with_badges=True):
    """이 악보를 그리는 데 위아래로 얼마나 필요한지 미리 잽니다.

    아래는 **항상 G현 개방현 기준**입니다 (위 FLOOR 설명 참고).
    위는 그 악보의 최고음에 맞춥니다 — 위쪽엔 활 기호와 슬러뿐이라
    겹칠 것이 없고, 낮은 곡에서 위를 비워 두면 자리만 버립니다.
    판정 배지가 없는 화면(연습 가이드)은 위 여백이 덜 필요합니다.
    """
    #| 흐름  이 악보를 그리는 데 위아래로 얼마나 필요한지 미리 잰다
    #| 입력  음 목록 · 판정 배지를 다는지
    #| 단계  가장 높은 음의 오선 위치를 찾는다
    #| 단계  아래는 실제 최저음이 아니라 **G현 개방현** 기준으로 잡는다
    #| 갈래  배지를 다나 ? 위를 더 비운다 : 활·슬러 자리만 비운다
    #| 출력  (위 여백, 아래 여백)
    ps = [staff_pos(n["letter"], n["octave"]) for n in notes]
    hi = max(ps)
    lo = min(min(ps), FLOOR)          # ← 실제보다 낮게 잡아 자리를 미리 비웁니다
    top = (58 if with_badges else 40) + max(0, (hi - 8)) * (GAP / 2)
    bottom = 26 + max(0, (0 - lo)) * (GAP / 2) + 30
    return top, bottom


def sy(pos: float, top: float) -> float:
    """오선 위치 번호 → y좌표 (top = 맨 위 줄 F5 의 y)"""
    return top + (8 - pos) * (GAP / 2)


def _clef(top, left):
    """높은음자리표. 나선 중심이 G4(아래에서 둘째 줄)에 오게 놓습니다."""
    #| 흐름  글리프의 기준선을 G4 줄에 맞춰 놓는다
    #| 단계  자리표 높이는 오선 6.7칸 — 위로 1칸, 아래로 1.7칸쯤 나옵니다
    h = GAP * 6.7
    return glyphs.place(glyphs.CLEF_G, left + 2, sy(2, top), h, INK,
                        anchor="baseline")


def line(notes, x0, step, top, right, *, sig=("♯", []), left=14,
         badges=None, click=None, show_name=True, show_position=True,
         show_finger=True, compact=False, mark_ids=False, id_base=0):
    """악보 한 줄을 SVG 조각 리스트로 만듭니다.

    badges : i → (색, 글자).  결과 리포트에서 음마다 판정을 붙일 때.
    click  : JS 함수 이름.  주면 음표를 눌러 그 부분만 다시 들을 수 있게.
    id_base: 악보를 여러 장으로 나눠 그릴 때, id 가 겹치지 않게 더하는 값.
             (같은 화면에 두 장이 있으면 nh0 이 둘이 되어 JS 가 엉뚱한 걸 칠합니다)
    """
    #| 흐름  음 목록 → 오선·조표·음표·슬러·활·마디선·포지션 띠 SVG 조각들
    #| 입력  음 목록 · 가로 배치 · 조표 · (판정 배지 · 클릭 함수)
    #| 단계  오선 다섯 줄을 긋고 높은음자리표를 그린다
    #| 단계  조표(♯/♭)를 정해진 오선 자리에 놓는다
    #| 단계  가장 높은 음표 위로 슬러·활·배지 높이를 통일해 잡는다
    #| 반복  슬러 그룹마다
        #| 갈래     두 음 이상인가 ? 잇는 곡선을 그린다 : 안 그린다
        #| 단계     활 기호는 그룹 하나에 하나만 (한 활이니까)
    #| 반복  음마다
        #| 호출     note_x → 가로 좌표
        #| 갈래     오선을 벗어났나 ? 덧줄을 위/아래로 긋는다 : 넘어간다
        #| 갈래     임시표가 있나 ? 음표 왼쪽에 붙인다 : 넘어간다
        #| 단계     머리와 기둥을 그린다 (가운데 줄보다 높으면 기둥은 아래로)
        #| 갈래     판정 배지가 있나 ? 음표 위에 동그라미를 놓는다 : 넘어간다
        #| 단계     아래에 계이름과 손가락 번호를 쓴다
        #| 갈래     클릭을 받나 ? 투명한 누름 영역을 덮는다 : 넘어간다
    #| 단계  마디선을 긋는다
    #| 단계  포지션이 같은 구간끼리 묶어 띠를 그리고, 바뀌는 자리에 '손 이동' 점선
    #| 출력  (SVG 조각 목록, 아래쪽 끝 y좌표)
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
    gl = glyphs.SHARP if mark == "♯" else glyphs.FLAT
    gh = GAP * (2.7 if mark == "♯" else 2.4)
    # 자리표가 끝나는 자리부터 조표를 놓습니다
    kx = left + 2 + glyphs.width_of(glyphs.CLEF_G, GAP * 6.7) + GAP * 0.55
    for k in keys:
        p.append(glyphs.place(gl, kx, sy(table[k], top), gh, INK))
        kx += glyphs.width_of(gl, gh) + GAP * 0.2

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
    # 계이름 줄도 **G현 개방현 기준**으로 고정합니다. 실제 최저음에 맞추면
    # A현과 G현에서 자리가 달라져 줄을 바꿀 때 화면이 출렁입니다.
    # 여유(23)는 음표머리 반지름(4.6)과 글자 높이를 더한 것보다 넉넉하게 —
    # 12 로 두었더니 G현에서 음표머리와 계이름이 겹쳤고, 17 도 1px 모자랐습니다.
    name_y = (top + GAP * 4 + max(0, -min(min(poss), FLOOR)) * (GAP / 2)
              + (23 if compact else 30))
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
            gl = {"♯": glyphs.SHARP, "♭": glyphs.FLAT, "♮": glyphs.NATURAL}[nt["acc"]]
            gh = GAP * (2.5 if nt["acc"] == "♭" else 2.7)
            # 음표 머리 왼쪽에 붙입니다 (오른쪽 끝이 머리에서 3px 떨어지게)
            p.append(glyphs.place(gl, x - 9 - glyphs.width_of(gl, gh), y, gh, INK))

        # mark_ids 를 주면 id 가 붙어, 연주 중에 JS 가 그 음만 색을 바꿉니다
        gid = i + id_base
        hid = f' id="nh{gid}"' if mark_ids else ''
        sid = f' id="ns{gid}"' if mark_ids else ''
        p.append(f'<ellipse{hid} cx="{x:.1f}" cy="{y:.1f}" rx="6.2" ry="4.6" '
                 f'transform="rotate(-20 {x:.1f} {y:.1f})" fill="{INK}"/>')
        if pos >= 4:                       # 가운데 줄보다 높으면 기둥은 아래로
            p.append(f'<line{sid} x1="{x-5.6:.1f}" y1="{y+1:.1f}" x2="{x-5.6:.1f}" '
                     f'y2="{y+28:.1f}" stroke="{INK}" stroke-width="1.6"/>')
        else:
            p.append(f'<line{sid} x1="{x+5.6:.1f}" y1="{y-1:.1f}" x2="{x+5.6:.1f}" '
                     f'y2="{y-28:.1f}" stroke="{INK}" stroke-width="1.6"/>')

        if badges:
            col, txt = badges(i)
            if col:
                p.append(f'<circle cx="{x:.1f}" cy="{badge_y:.1f}" r="9" fill="{col}"/>')
                p.append(f'<text x="{x:.1f}" y="{badge_y+4:.1f}" text-anchor="middle" '
                         f'font-size="10.5" font-weight="700" fill="#fff">{txt}</text>')

        if show_name:
            nid = f' id="nk{i + id_base}"' if mark_ids else ''
            p.append(f'<text{nid} x="{x:.1f}" y="{name_y:.1f}" text-anchor="middle" '
                     f'font-size="12" font-weight="400" fill="{MUT}">{nt["ko"]}</text>')
        if show_finger:
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
    pos_y = name_y + (14 if compact else 30)
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

    # 포지션 띠를 안 그리면 그만큼 아래가 짧아집니다
    if not show_position:
        return p, name_y + (8 if compact else 14)
    return p, pos_y + (14 if compact else 22)


def preview(notes, sig, width: int = 900, show_position: bool = True) -> str:
    """악보 한 줄을 그대로 보여주는 SVG 한 덩어리.

    「내 악보」 화면에서 **적은 대로 나오는지 눈으로 확인**하는 데 씁니다.
    적은 글이 틀렸는지는 글자로는 모르고, 악보로 봐야 압니다.
    """
    #| 흐름  음 목록 → 그대로 붙여 쓸 수 있는 SVG 문자열
    #| 입력  음 목록 · 조표 · 폭
    #| 갈래  음이 하나도 없나 ? 빈 문자열 : 그린다
    #| 호출  layout → 위 여백,  line → 악보 조각
    #| 출력  <svg> … </svg>
    if not notes:
        return ""
    x0 = max(70, head_width(sig))
    step = (width - x0 - 24) / len(notes)
    top = layout(notes, with_badges=False)[0]
    parts, bottom = line(notes, x0, step, top, right=width - 16, sig=sig,
                         show_position=show_position, compact=True)
    return (f'<svg viewBox="0 0 {width} {bottom}" width="100%" '
            f'height="{bottom}" style="display:block">{"".join(parts)}</svg>')
