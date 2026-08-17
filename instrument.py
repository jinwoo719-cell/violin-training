"""
악기 — 줄·길이·그림을 한곳에.

지금은 바이올린만 있지만, 여기에 비올라·첼로를 **더하기만 하면** 됩니다.
그림은 0~1 로 정규화한 경로로 두어서, 화면 크기가 달라져도 같은 모양이 나옵니다.

    지판 왼쪽 ─ scroll   스크롤 · 페그박스 · 줄감개
    지판      ─ board    실제로 짚는 곳
    지판 오른쪽 ─ body    몸통 · 브리지 · f홀

손 그림도 여기 있습니다 — 악기가 바뀌면 손 모양도 바뀌니까요.
그림은 두 가지를 씁니다.
  · 사진 (assets/*.png)  — 스크롤·손처럼 그려서는 예쁘게 안 나오는 것
  · 경로 (아래 리스트)   — 몸통처럼 화면 크기에 맞춰 늘어나야 하는 것
"""

import base64
import os

#| 흐름  악기 하나 = 줄 목록 + 지판 길이 + 좌우 그림 + 손 그림

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def data_url(name: str) -> str:
    """PNG 파일 → HTML 에 바로 넣는 data URL."""
    #| 흐름  파일을 읽어 base64 로 바꾼다 (파일 없으면 빈 문자열)
    #| 갈래  파일이 있나 ? base64 로 바꾼다 : 빈 문자열을 돌려준다
    p = os.path.join(ASSETS, name)
    if not os.path.exists(p):
        return ""
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

# ══════════════════════════════════════════════════════════════
#  그림 — 0~1 정규화 좌표.  JS 가 크기만 맞춰 그립니다.
# ══════════════════════════════════════════════════════════════
# 조각 하나는 다음 중 하나입니다.
#   {"d": 경로, "fill": 색이름}                단색으로 칠하기
#   {"d": 경로, "grad": [위색, 아래색]}         세로 그라데이션으로 칠하기
#   {"d": 경로, "stroke": 색이름, "w": 굵기}    선 긋기 (굵기는 높이 대비 비율)
#
# 실제 바이올린은 옻칠이 깊은 호박색이라 채도가 낮습니다.
# 밝은 주황으로 칠하면 장난감처럼 보입니다.

# ── 왼쪽: 스크롤 · 페그박스.  x=0 이 스크롤 끝, x=1 이 너트 ──
# 실제 비율: 페그박스가 길고, 소용돌이는 생각보다 작습니다.
# 소용돌이를 크게 그리면 달팽이처럼 보입니다.
VIOLIN_SCROLL = [
    # 페그박스 — 길고 얇게
    {"d": "M 0.26 0.26 C 0.40 0.20 0.70 0.16 1.00 0.15 "
          "L 1.00 0.85 C 0.70 0.84 0.40 0.80 0.26 0.74 Z",
     "grad": ["#4a2f1c", "#22140c"]},
    # 페그박스 안쪽 홈
    {"d": "M 0.36 0.36 C 0.50 0.33 0.76 0.31 0.99 0.30 "
          "L 0.99 0.70 C 0.76 0.69 0.50 0.67 0.36 0.64 Z",
     "fill": "hole"},
    # 스크롤 머리 — 작고 둥글게
    {"d": "M 0.27 0.24 C 0.22 0.10 0.10 0.07 0.05 0.18 "
          "C 0.00 0.30 0.04 0.48 0.13 0.56 "
          "C 0.19 0.61 0.24 0.66 0.27 0.72 Z",
     "grad": ["#573721", "#2a190e"]},
    # 소용돌이 — 안으로 감기는 선
    {"d": "M 0.24 0.20 C 0.13 0.13 0.05 0.22 0.07 0.33 "
          "C 0.09 0.43 0.18 0.48 0.23 0.43 "
          "C 0.27 0.39 0.24 0.32 0.19 0.33",
     "stroke": "shade", "w": 0.05},
    # 턱 아래 그늘
    {"d": "M 0.27 0.70 C 0.19 0.64 0.12 0.55 0.10 0.44",
     "stroke": "dark", "w": 0.05},
    # 위쪽 빛 — 얇은 한 줄이 입체를 만듭니다
    {"d": "M 0.30 0.23 C 0.46 0.18 0.72 0.155 0.99 0.15",
     "stroke": "sheen", "w": 0.022},
]
VIOLIN_PEGS = [(0.50, 0.20, True), (0.78, 0.165, True),
               (0.58, 0.80, False), (0.86, 0.835, False)]

# ── 오른쪽: 몸통 · 브리지.  x=0 이 지판 끝, x=1 이 화면 오른쪽 끝 ──
VIOLIN_BODY = [
    # 몸통 어깨 — 위아래로 완만히 벌어집니다
    {"d": "M 0.00 0.10 C 0.24 -0.02 0.50 -0.13 0.76 -0.15 "
          "C 0.92 -0.16 1.00 -0.08 1.00 0.04 L 1.00 0.96 "
          "C 1.00 1.08 0.92 1.16 0.76 1.15 "
          "C 0.50 1.13 0.24 1.02 0.00 0.90 Z",
     "grad": ["#5a3a21", "#281709"]},
    # 가장자리 — 위는 빛, 아래는 그늘
    {"d": "M 0.04 0.075 C 0.27 -0.04 0.52 -0.125 0.76 -0.125",
     "stroke": "sheen", "w": 0.02},
    {"d": "M 0.04 0.925 C 0.27 1.04 0.52 1.125 0.76 1.125",
     "stroke": "dark", "w": 0.02},
    # 지판이 몸통에 얹힌 그림자
    {"d": "M 0.00 0.11 C 0.05 0.08 0.09 0.06 0.13 0.05 "
          "L 0.13 0.95 C 0.09 0.94 0.05 0.92 0.00 0.89 Z",
     "fill": "dark"},
]
VIOLIN_BRIDGE_X = 0.42          # 브리지가 놓이는 자리 (몸통 상자 안에서)

# 손 그림에서 손끝 자리 (그림 크기 대비 0~1)
#
# ⚠ 번호가 왼쪽부터 1이 아닙니다.
# 이 사진은 **너트(스크롤)가 오른쪽**에 있는 방향으로 찍혀 있습니다.
# 1포지션에서 검지(1번)가 너트에 제일 가까우므로,
#
#        왼쪽 ← 4(새끼) · 3(약지) · 2(중지) · 1(검지) → 오른쪽 (너트 쪽)
#
# 이 됩니다. 왼쪽부터 1,2,3,4 로 매기면 실제와 정반대가 됩니다.
VIOLIN_HAND_TIPS = {4: (0.178, 0.020), 3: (0.352, -0.012),
                    2: (0.585, 0.050), 1: (0.835, 0.185)}

VIOLIN = {
    "key": "violin",
    "label": "바이올린",
    "length_mm": 328.0,          # 진동현 길이 (너트~브리지)
    "view_mm": 190.0,            # 지판에서 화면에 보여줄 범위
    "strings": ["E", "A", "D", "G"],   # 위에서부터 (연주자가 내려다보는 방향)
    "scroll_w": 136,             # 지판 왼쪽 그림의 폭 (픽셀)
    "body_w": 149,               # 지판 오른쪽 그림의 폭
    # 옻칠한 나무 — 채도를 낮춰야 장난감처럼 안 보입니다
    # 옻칠한 나무 — 채도를 낮추고 어둡게. 밝은 주황은 장난감처럼 보입니다.
    "wood": {"dark": "#150c06", "shade": "#26170d", "mid": "#432a18",
             "light": "#5f3d22", "sheen": "#8a6038", "edge": "#a8814f",
             "hole": "#0d0704"},
    "board": {"top": "#241b14", "bot": "#100a07"},
    # 사진 — 스크롤은 그려서는 장난감처럼 보여 사진을 씁니다
    "scroll_img": data_url("violin_scroll.png"),
    "scroll_nut": 0.985,          # 사진에서 너트가 있는 가로 자리 (0~1)
    "scroll_aspect": 184 / 182,   # 사진의 세로/가로
    # 사진 속 E현·G현이 있는 세로 자리 (0~1). 지판의 줄 간격에 맞춰 크기를 정합니다.
    "scroll_str": (52 / 184, 120 / 184),
    # 몸통도 사진. 지판이 끝나는 자리부터 브리지까지 — f홀·브리지·줄이 다 들어 있습니다.
    # (코드로 그리면 아무리 다듬어도 장난감처럼 보입니다)
    "body_img": data_url("violin_body.png"),
    "body_aspect": 210 / 99,       # 사진의 세로/가로
    "body_str": (89.5 / 210, 123.5 / 210),   # 사진 속 E현·G현의 세로 자리
    # 네 줄 각각의 세로 자리 (E·A·D·G) — 브리지 그림의 점을 여기에 찍습니다
    "body_str4": (89.5 / 210, 100 / 210, 112 / 210, 123.5 / 210),
    "body_bridge": 54 / 99,        # 사진 속 브리지의 가로 자리 (0~1)
    "hand_img": data_url("hand.png"),
    "hand_tips": VIOLIN_HAND_TIPS,
    "scroll": VIOLIN_SCROLL,
    "pegs": VIOLIN_PEGS,
    "body": VIOLIN_BODY,
    "bridge_x": VIOLIN_BRIDGE_X,
}

INSTRUMENTS = {"violin": VIOLIN}


def get(key: str = "violin"):
    """악기 하나 꺼내기. 없으면 바이올린."""
    #| 흐름  이름으로 악기를 찾는다. 없으면 바이올린으로.
    return INSTRUMENTS.get(key, VIOLIN)


# ══════════════════════════════════════════════════════════════
#  손 그림 — 짚어야 하는 손끝을 빨갛게
# ══════════════════════════════════════════════════════════════
# 왼손을 손등 쪽에서 본 그림. 1~4번 손가락이 위로 섭니다.
# (x중심, 손끝 y, 손가락 길이)
FINGERS = {
    1: (44, 34, 58),    # 검지
    2: (61, 22, 70),    # 중지
    3: (78, 28, 64),    # 약지
    4: (94, 46, 46),    # 새끼
}
THUMB = "M 40 96 C 26 100 16 112 14 124 C 13 131 20 136 26 132 "\
        "C 34 126 44 118 50 112 Z"
PALM = "M 34 84 L 104 84 C 110 84 113 88 113 94 L 113 118 "\
       "C 113 130 104 138 92 138 L 50 138 C 38 138 30 130 30 118 "\
       "L 30 94 C 30 88 30 84 34 84 Z"


def hand_html(inst, size: int = 108, mark="#d96868", dim="#2f3644",
              ink="#ffffff") -> str:
    """손 사진 + 내가 그리는 손끝 배지.

    사진에 배지가 박혀 있으면 어느 손가락을 짚을지 바꿀 수 없습니다.
    그래서 배지는 사진 위에 따로 얹고, JS 가 색만 바꿉니다.
    """
    #| 흐름  손 사진을 깔고 그 위에 손끝 배지 넷을 얹는다
    #| 입력  악기 · 그림 크기
    #| 갈래  손 사진이 있나 ? 사진을 쓴다 : 배지만 얹는다
    #| 반복  1~4번 손가락마다
    #| 단계     손끝 자리에 배지를 하나씩 (색은 JS 가 바꿉니다)
    #| 출력  HTML 한 조각
    img = inst.get("hand_img", "")
    tips = inst.get("hand_tips", VIOLIN_HAND_TIPS)
    h = int(size * 154 / 129)
    pad = max(11, int(size * 0.15))   # 손끝 배지가 위로 삐져나갈 자리
    r = size * 0.105                  # 배지도 그림 크기를 따라갑니다
    fs = size * 0.115
    p = [f'<div style="position:relative;width:{size}px;height:{h + pad}px">']
    if img:
        p.append(f'<img src="{img}" width="{size}" height="{h}" '
                 f'style="position:absolute;left:0;top:{pad}px;'
                 f'filter:saturate(0.9) brightness(0.95)">')
    p.append(f'<svg width="{size}" height="{h + pad}" '
             f'style="position:absolute;left:0;top:0">')
    for f, (fx, fy) in tips.items():
        cx, cy = fx * size, fy * h + pad
        p.append(f'<g id="ft{f}"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                 f'fill="{dim}" stroke="#0d1117" stroke-width="1.4"/>'
                 f'<text x="{cx:.1f}" y="{cy + fs*0.34:.1f}" text-anchor="middle" '
                 f'font-size="{fs:.1f}" font-weight="700" fill="{ink}" '
                 f'font-family="system-ui">{f}</text></g>')
    p.append(f'<g id="ft0" style="display:none">'
             f'<circle cx="{size*0.5:.0f}" cy="{h*0.62 + pad:.0f}" r="{r*1.6:.0f}" '
             f'fill="none" stroke="{mark}" stroke-width="2.4"/>'
             f'<text x="{size*0.5:.0f}" y="{h*0.62 + pad + fs*0.35:.0f}" '
             f'text-anchor="middle" font-size="{fs:.1f}" font-weight="700" '
             f'fill="{mark}" font-family="system-ui">개방</text></g>')
    p.append("</svg></div>")
    return "".join(p)


# ══════════════════════════════════════════════════════════════
#  브리지 — 어느 줄을 켤지
# ══════════════════════════════════════════════════════════════
def bridge_html(inst, w: int = 206, h: int = 58, colors=None,
                ink="#0d1117") -> str:
    """브리지 사진 + 「이 줄을 켭니다」 표시.

    지판은 **어디를 짚나**, 브리지는 **어느 줄을 켜나** 를 말합니다.
    둘은 다른 정보라서, 지판 옆이 아니라 안내 패널에 따로 둡니다.
    (지판 옆에 두면 정작 짚을 자리가 좁아집니다)
    """
    #| 흐름  브리지 사진을 줄 자리에 맞춰 놓고, 줄마다 점을 하나씩 얹는다
    #| 입력  악기 · 상자 크기
    #| 단계  사진 속 E현~G현이 상자 안에 꽉 차도록 배율을 정한다
    #| 단계  상자 폭을 사진 폭에 맞춘다 — 옆에 검은 띠가 남지 않게
    #| 반복  네 줄마다
    #| 단계     브리지 위 그 줄 자리에 줄 이름을 단 점 하나 (색은 JS 가 바꿈)
    #| 출력  HTML 한 조각
    img = inst.get("body_img", "")
    s0, s1 = inst.get("body_str", (0.0, 1.0))
    rows = inst.get("body_str4", (s0, s0, s1, s1))
    aspect = inst.get("body_aspect", 1.0)
    names = inst.get("strings", ["E", "A", "D", "G"])
    colors = colors or {n: "#c9c9c4" for n in names}

    ih = (h - 21) / (s1 - s0)              # 네 줄이 상자에 꽉 차게
    iw = ih / aspect
    box = min(w, int(iw))                  # 사진 폭에 상자를 맞춥니다
    left = (box - iw) / 2
    top = 10.5 - s0 * ih
    bx = left + iw * inst.get("body_bridge", 0.55)

    p = [f'<div style="width:{box}px;height:{h}px;margin:0 auto;'
         f'position:relative;overflow:hidden;border-radius:8px;'
         f'background:#0d1117">']
    if img:
        p.append(f'<img src="{img}" style="position:absolute;'
                 f'left:{left:.1f}px;top:{top:.1f}px;'
                 f'width:{iw:.1f}px;height:{ih:.1f}px">')
    p.append(f'<svg width="{box}" height="{h}" '
             f'style="position:absolute;left:0;top:0">')
    #| 반복  줄마다 — 사진 속 그 줄의 세로 자리에
    for n, fr in zip(names, rows):
        y = top + fr * ih
        p.append(f'<g id="bs{n}">'
                 f'<circle cx="{bx:.1f}" cy="{y:.1f}" r="7.2" '
                 f'fill="#0d1117" fill-opacity="0.62" stroke="{colors[n]}" '
                 f'stroke-opacity="0.5" stroke-width="1.4"/>'
                 f'<text x="{bx:.1f}" y="{y + 3.1:.1f}" text-anchor="middle" '
                 f'font-size="9" font-weight="700" fill="{colors[n]}" '
                 f'fill-opacity="0.6" font-family="system-ui">{n}</text></g>')
    p.append("</svg></div>")
    return "".join(p)
