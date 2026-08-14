"""
화면 두 개.

  화면 ①  guide()   움직이는 가이드 — 악보 + 지판으로 떨어지는 노드
  화면 ②  report()  결과 리포트 — 악보 위에 음정·박자·궤적을 겹쳐 보기

둘 다 악보의 가로 좌표를 staff.note_x() 에서 가져옵니다.
따로 계산하면 반드시 어긋납니다.
"""

import base64
import json

import music
import staff

C = {
    "bg": "#0d0d0c", "panel": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7",
    "muted": "#8a8a86", "grid": "#2c2c2a", "axis": "#3a3a37", "line": "#2e2e2b",
    "sharp": "#3987e5",    # 높게
    "flat": "#e66767",     # 낮게
    "good": "#0ca30c",     # 허용 범위 안
    "trace": "#f0d98c",    # 내 음정
}

# 지판 가로 배치 — 파이썬과 JS가 같은 식을 써야 잇는 선이 맞습니다
BOARD_X0 = 78.0
BOARD_PAD = 130.0

# 줄 색 — 굵은 줄일수록 어둡게
STRING_COLOR = {"E": "#f6e9b8", "A": "#f0d98c", "D": "#cbb06a", "G": "#a98c4e"}


def board_x(mm: float, width: int) -> float:
    return BOARD_X0 + (width - BOARD_PAD) * (mm / music.VIEW_MM)


def _txt(x, y, s, size=11, fill=None, anchor="middle", weight=400, mono=False):
    fam = ("ui-monospace,Menlo,monospace" if mono
           else "system-ui,-apple-system,'Malgun Gothic',sans-serif")
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" font-family="{fam}" '
            f'fill="{fill or C["ink"]}">{s}</text>')


# ══════════════════════════════════════════════════════════════
#  화면 ① — 움직이는 가이드
# ══════════════════════════════════════════════════════════════
LANE_H = 232          # 노드가 떨어지는 구간 높이
BOARD_H = 142         # 판정선 아래 지판 구간 높이
CANVAS_H = LANE_H + BOARD_H


def _score_bottom(notes, width):
    top = staff.layout(notes)[0]
    _, bottom = staff.line(notes, 78, (width - 46 - 78) / len(notes), top,
                           right=width, sig=("♯", []))
    return bottom


def guide_height(notes, width: int = 900) -> int:
    """components.html 에 넘길 전체 높이"""
    return int(_score_bottom(notes, width) + CANVAS_H + 46)


def guide(notes, sig, bpm: int, width: int = 900) -> str:
    """악보 → 낙하 노드 → 판정선 → 지판, 하나의 세로 흐름.

    **악보의 음표 x와 낙하 노드 x를 똑같이 둡니다.**
    악보에서 음표를 짚어 아래로 눈을 내리면 그 노드가 바로 거기 있어야
    "무엇을 / 언제"가 한 번에 읽힙니다.

    그럼 '지판 어디를 짚나'는? 판정선 **아래**에서 답합니다.
    노드가 닿는 순간 지판의 실제 mm 자리로 선이 이어지고 손가락이 찍힙니다.
    (지판의 가로는 거리라서 악보의 가로와 같을 수가 없습니다)
    """
    x0, x1 = 78, width - 46
    step = (x1 - x0) / len(notes)
    top = staff.layout(notes)[0]

    parts, bottom = staff.line(notes, x0, step, top, right=x0 + step * len(notes) + 10,
                               sig=sig)

    # 음표 아래로 내려가는 옅은 세로선 — 캔버스의 레인과 이어집니다
    for i in range(len(notes)):
        sx = staff.note_x(i, x0, step)
        parts.append(f'<line x1="{sx:.1f}" y1="{top + staff.GAP*4 + 6:.1f}" '
                     f'x2="{sx:.1f}" y2="{bottom:.1f}" stroke="#ffffff" '
                     f'stroke-width="1" opacity="0.09"/>')

    parts.append(f'<rect id="cursor" x="{x0:.1f}" y="{top-8}" width="{step:.1f}" '
                 f'height="{staff.GAP*4+16}" fill="{C["trace"]}" opacity="0.16" rx="4"/>')

    score = (f'<svg id="score" viewBox="0 0 {width} {bottom}" width="{width}" '
             f'height="{bottom}" style="display:block">{"".join(parts)}</svg>')

    active = notes[0]["string"]
    data = [{"i": i, "ko": n["ko"], "finger": n["finger"], "bow": n["bow"],
             "mm": n["mm"], "t": n["t"], "dur": n["dur"], "pos": n["position"],
             "color": staff.DOWN_COLOR if n["bow"] == "down" else staff.UP_COLOR,
             "slurHead": n["slur_head"]}
            for i, n in enumerate(notes)]
    strings = [{"name": s["name"], "color": STRING_COLOR[s["name"]],
                "w": 1.5 + 0.45 * i} for i, s in enumerate(music.STRINGS)]
    marks = {s["name"]: [music.mm_from_freq(s["freq"] * 2 ** (k / 12), s["freq"])
                         for k in (2, 4, 5, 7)] for s in music.STRINGS}

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0;background:{C['bg']}}}
 #wrap{{width:{width}px;margin:0 auto;
   font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif}}
 canvas{{display:block;border-radius:0 0 14px 14px}}
 #bar{{display:flex;gap:10px;align-items:center;padding:9px 4px 0;
   color:{C['ink2']};font-size:12.5px;flex-wrap:wrap}}
 button{{background:#262624;color:#fff;border:1px solid {C['axis']};
   border-radius:8px;padding:6px 13px;font-size:12.5px;cursor:pointer;
   font-family:inherit}}
 button:hover{{background:#333330}}
 .k{{display:inline-flex;align-items:center;gap:5px;margin-left:10px}}
 .sw{{width:11px;height:11px;border-radius:3px;display:inline-block}}
 .dim{{color:{C['muted']};font-size:11.5px}}
</style></head><body><div id="wrap">
 <div style="background:{C['bg']};border-radius:14px 14px 0 0">{score}</div>
 <canvas id="cv" width="{width}" height="{CANVAS_H}"></canvas>
 <div id="bar">
   <button id="go">▶ 처음부터</button>
   <span>{bpm} BPM · <b style="color:{STRING_COLOR[active]}">{active}현</b></span>
   <span class="k"><i class="sw" style="background:{staff.DOWN_COLOR}"></i>⊓ 다운보우</span>
   <span class="k"><i class="sw" style="background:{staff.UP_COLOR}"></i>∨ 업보우</span>
   <span class="dim" style="margin-left:auto">
     악보 = 무엇을 · 노드 = 언제 · 판정선 = 지금 · 지판 = 어디를</span>
 </div>
</div>
<script>
const NOTES = {json.dumps(data, ensure_ascii=False)};
const STRINGS = {json.dumps(strings, ensure_ascii=False)};
const MARKS = {json.dumps(marks)};
const ACTIVE = "{active}";
const VIEW_MM = {music.VIEW_MM}, W = {width}, H = {CANVAS_H};
const X0 = {x0}, STEP = {step}, BEAT = {60.0 / bpm};
const TOTAL = {len(notes) * 60.0 / bpm};
const HIT_Y = {LANE_H};                       // 판정선
const BOARD_TOP = HIT_Y + 16, BOARD_BOT = H - 22;
const ROW = {{}};
STRINGS.forEach((s, i) => ROW[s.name] = BOARD_TOP + 18 + i * 22);
const LEAD = {LANE_H} / 116, PPS = 116;       // 초당 내려오는 픽셀

const cv = document.getElementById('cv'), g = cv.getContext('2d');
const cursor = document.getElementById('cursor');

// 낙하 레인의 x = 악보 음표의 x.  둘은 **같은 식**을 씁니다.
const laneX = i => X0 + STEP * (i + 0.5);
// 지판의 x = 너트에서의 실제 거리. 파이썬 board_x() 와 같은 식.
const boardX = mm => {BOARD_X0} + (W - {BOARD_PAD}) * (mm / VIEW_MM);

let t0 = performance.now();
document.getElementById('go').onclick = () => {{ t0 = performance.now(); }};

function lanes() {{
  // 악보에서 내려온 세로선이 그대로 이어집니다
  NOTES.forEach(n => {{
    const x = laneX(n.i);
    g.strokeStyle = 'rgba(255,255,255,0.07)'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, 0); g.lineTo(x, HIT_Y); g.stroke();
  }});
}}

function board() {{
  g.beginPath();
  g.moveTo(56, BOARD_TOP + 6); g.lineTo(W - 18, BOARD_TOP);
  g.lineTo(W - 18, BOARD_BOT); g.lineTo(56, BOARD_BOT - 6); g.closePath();
  const gr = g.createLinearGradient(0, BOARD_TOP, 0, BOARD_BOT);
  gr.addColorStop(0, '#3a2f28'); gr.addColorStop(1, '#241c17');
  g.fillStyle = gr; g.fill();
  g.fillStyle = '#e8e2d6'; g.fillRect(48, BOARD_TOP + 2, 8, BOARD_BOT - BOARD_TOP - 3);

  STRINGS.forEach(s => {{
    const y = ROW[s.name], on = s.name === ACTIVE;
    g.globalAlpha = on ? 1 : 0.28;
    g.strokeStyle = s.color; g.lineWidth = on ? s.w + 1.3 : s.w;
    g.beginPath(); g.moveTo(56, y); g.lineTo(W - 18, y); g.stroke();
    MARKS[s.name].forEach(mm => {{
      g.fillStyle = s.color; g.globalAlpha = on ? 0.45 : 0.14;
      g.beginPath(); g.arc(boardX(mm), y, on ? 2.8 : 2.1, 0, 6.284); g.fill();
    }});
    g.globalAlpha = 1;
    g.fillStyle = on ? s.color : '#6b6b67';
    g.font = (on ? '700 ' : '') + '11px system-ui'; g.textAlign = 'right';
    g.fillText(s.name, 42, y + 4);
  }});
  g.globalAlpha = 1;

  // 이번 연습에 쓰는 음의 지판 자리
  g.textAlign = 'center';
  NOTES.forEach(n => {{
    const x = boardX(n.mm);
    g.strokeStyle = 'rgba(255,255,255,0.09)'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, BOARD_TOP + 4); g.lineTo(x, BOARD_BOT - 4); g.stroke();
    g.fillStyle = '#7c7c78'; g.font = '10.5px system-ui';
    g.fillText(n.ko, x, BOARD_BOT + 15);
  }});

  // 판정선 — 악보보다 앞서면 안 되므로 얇고 차분하게
  g.strokeStyle = 'rgba(227,73,72,0.55)'; g.lineWidth = 1.4;
  g.beginPath(); g.moveTo(40, HIT_Y); g.lineTo(W - 18, HIT_Y); g.stroke();
  g.fillStyle = 'rgba(227,73,72,0.65)'; g.font = '10px system-ui';
  g.textAlign = 'left'; g.fillText('지금', 14, HIT_Y + 4);
}}

function draw() {{
  let t = (performance.now() - t0) / 1000;
  if (t > TOTAL + 1.0) {{ t0 = performance.now(); t = 0; }}
  g.fillStyle = '{C['bg']}'; g.fillRect(0, 0, W, H);
  lanes();

  const idx = Math.max(0, Math.min(NOTES.length - 1, Math.floor(t / BEAT)));
  cursor.setAttribute('x', (X0 + STEP * idx).toFixed(1));

  // ── 떨어지는 노드 — 악보 음표 바로 아래 레인에서 ──
  NOTES.forEach(n => {{
    const yB = HIT_Y - (n.t - t) * PPS;
    const h = Math.max(n.dur * PPS - 6, 10), yT = yB - h;
    if (yB < -16 || yT > HIT_Y + 8) return;
    const x = laneX(n.i), w = Math.min(34, STEP - 10);
    const live = yB >= HIT_Y - 4 && yT <= HIT_Y + 4;

    g.save(); g.beginPath(); g.rect(0, 0, W, HIT_Y); g.clip();
    if (live) {{ g.shadowColor = n.color; g.shadowBlur = 20; }}
    g.fillStyle = n.color; g.globalAlpha = live ? 1 : 0.88;
    g.beginPath(); g.roundRect(x - w/2, yT, w, h, 7); g.fill();
    g.restore();
    g.globalAlpha = 1; g.shadowBlur = 0;

    if (h > 34) {{
      if (n.slurHead) {{        // 슬러로 묶인 음은 첫 음에만 (한 활이니까)
        g.strokeStyle = 'rgba(255,255,255,0.92)'; g.lineWidth = 2;
        const by = yT + 12; g.beginPath();
        if (n.bow === 'down') {{
          g.moveTo(x-6, by+6); g.lineTo(x-6, by); g.lineTo(x+6, by); g.lineTo(x+6, by+6);
        }} else {{
          g.moveTo(x-6, by); g.lineTo(x, by+7); g.lineTo(x+6, by);
        }}
        g.stroke();
      }}
      g.fillStyle = '#fff'; g.font = '700 16px system-ui'; g.textAlign = 'center';
      g.fillText(n.finger === 0 ? '○' : n.finger, x, yT + h/2 + 7);
    }}
  }});

  board();

  // ── 판정선에 닿은 음 → 지판의 실제 자리로 이어 줍니다 ──
  const y = ROW[ACTIVE];
  NOTES.forEach(n => {{
    if (t < n.t - 0.1 || t > n.t + n.dur) return;
    const lx = laneX(n.i), bx = boardX(n.mm);
    const fresh = Math.max(0, 1 - Math.abs(t - n.t) / 0.35);

    // 레인 → 지판 자리 (가로가 다른 두 축을 잇는 선)
    g.strokeStyle = n.color; g.globalAlpha = 0.55; g.lineWidth = 1.4;
    g.beginPath(); g.moveTo(lx, HIT_Y); g.lineTo(bx, y); g.stroke();
    g.globalAlpha = 1;

    g.save(); g.shadowColor = n.color; g.shadowBlur = 16 + 20 * fresh;
    g.fillStyle = n.color;
    g.beginPath(); g.arc(bx, y, 10 + 5 * fresh, 0, 6.284); g.fill();
    g.restore();
    g.fillStyle = '#fff'; g.font = '700 13px system-ui'; g.textAlign = 'center';
    g.fillText(n.finger === 0 ? '○' : n.finger, bx, y + 4.5);

    // 너트에서 여기까지
    g.strokeStyle = n.color; g.globalAlpha = 0.35; g.lineWidth = 1.4;
    g.beginPath(); g.moveTo(56, y); g.lineTo(bx - 13, y); g.stroke();
    g.globalAlpha = 1;
    g.fillStyle = n.color; g.font = '600 11.5px ui-monospace,Menlo,monospace';
    g.textAlign = 'left'; g.fillText(n.mm.toFixed(1) + 'mm', bx + 15, y - 7);

    g.font = '700 12px system-ui';
    g.fillStyle = n.pos === 1 ? '#199e70' : '#c98500';
    g.fillText(n.pos + '포지션', 14, HIT_Y - 8);
    g.textAlign = 'center';
  }});

  requestAnimationFrame(draw);
}}
draw();
</script></body></html>"""


# ══════════════════════════════════════════════════════════════
#  화면 ② — 결과 리포트
# ══════════════════════════════════════════════════════════════
BAR_PPC = 1.55
BAR_CLAMP = 42
TR_SPAN = 45.0
TR_PPC = 88 / TR_SPAN


def _sec(x0, top, title, note=""):
    y = top - 14
    return [f'<line x1="{x0}" y1="{y-4:.1f}" x2="{x0+8:.1f}" y2="{y-4:.1f}" '
            f'stroke="{C["axis"]}" stroke-width="2"/>',
            _txt(x0 + 14, y, title, 11, C["ink2"], "start", 600),
            _txt(x0 + 16 + len(title) * 12, y, note, 10.5, C["muted"], "start")]


def _stack(res, notes, sig, width, x0, step, tol_cent, tol_ms):
    """악보 · 음정 · 박자 · 궤적을 **한 좌표계 위에** 쌓습니다."""
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
        return (C["sharp"], "↑") if r["cent"] > 0 else (C["flat"], "↓")

    top = staff.layout(notes)[0]
    parts, sc_bottom = staff.line(notes, x0, step, top, right=x0 + W + 10,
                                  sig=sig, badges=badge, click="playNote")
    p += parts

    BAR_Y = sc_bottom + 88
    p += _sec(x0, BAR_Y - 65, "음정", "· 음마다의 평균 — 손가락 자리")
    p.append(f'<rect x="{x0}" y="{BAR_Y-tol_cent*BAR_PPC:.1f}" width="{W:.1f}" '
             f'height="{2*tol_cent*BAR_PPC:.1f}" fill="{C["good"]}" opacity="0.15"/>')
    for cv in (-40, -20, 20, 40):
        y = BAR_Y - cv * BAR_PPC
        p.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+W:.1f}" y2="{y:.1f}" '
                 f'stroke="{C["grid"]}" stroke-width="1"/>')
        p.append(_txt(x0 - 9, y + 3.5, f'{cv:+d}', 9.5, C["muted"], "end", mono=True))
    p.append(f'<line x1="{x0}" y1="{BAR_Y}" x2="{x0+W:.1f}" y2="{BAR_Y}" '
             f'stroke="{C["axis"]}" stroke-width="1.5"/>')
    p.append(_txt(x0 - 9, BAR_Y + 3.5, "0", 9.5, C["muted"], "end", mono=True))
    p.append(_txt(x0 - 9, BAR_Y - 77, "센트", 9.5, C["muted"], "end"))

    for i, r in enumerate(rows):
        x = staff.note_x(i, x0, step)
        if not r["detected"]:
            p.append(_txt(x, BAR_Y - 4, "소리 없음", 9.5, C["muted"]))
            continue
        c = max(-BAR_CLAMP, min(BAR_CLAMP, r["cent"]))
        h = abs(c) * BAR_PPC
        col = C["good"] if abs(r["cent"]) <= tol_cent else (
            C["sharp"] if r["cent"] > 0 else C["flat"])
        y = BAR_Y - h if c > 0 else BAR_Y
        p.append(f'<rect x="{x-15:.1f}" y="{y:.1f}" width="30" '
                 f'height="{max(h,2.5):.1f}" fill="{col}" rx="3" opacity="0.92"/>')
        ly = (y - 6) if c > 0 else (y + h + 13)
        p.append(_txt(x, ly, f'{r["cent"]:+.0f}', 10.5, col, weight=700, mono=True))

    T_Y = BAR_Y + 118
    p += _sec(x0, T_Y - 14, "박자", "· 첫 음 기준 · 초록 구간이 허용 범위")
    MS_PX = 0.42
    for i, r in enumerate(rows):
        x = staff.note_x(i, x0, step)
        tw = tol_ms * MS_PX
        p.append(f'<rect x="{x-tw:.1f}" y="{T_Y-9}" width="{2*tw:.1f}" height="18" '
                 f'fill="{C["good"]}" opacity="0.15" rx="4"/>')
        p.append(f'<line x1="{x:.1f}" y1="{T_Y-13}" x2="{x:.1f}" y2="{T_Y+13}" '
                 f'stroke="{C["axis"]}" stroke-width="1"/>')
        if not r["detected"]:
            continue
        dx = max(-46, min(46, r["ms"] * MS_PX))
        ok = abs(r["ms"]) <= tol_ms
        col = C["good"] if ok else (C["sharp"] if r["ms"] > 0 else C["flat"])
        if abs(dx) > 1.5:
            p.append(f'<line x1="{x:.1f}" y1="{T_Y}" x2="{x+dx:.1f}" y2="{T_Y}" '
                     f'stroke="{col}" stroke-width="2.5" stroke-linecap="round" '
                     f'opacity="0.8"/>')
        p.append(f'<circle cx="{x+dx:.1f}" cy="{T_Y}" r="5.5" fill="{col}"/>')
        if not ok:
            p.append(_txt(x + dx, T_Y + 22, f'{r["ms"]:+.0f}ms', 9.5, col, mono=True))
    p.append(_txt(x0 + W + 10, T_Y - 4, "◀ 빨리", 9.5, C["flat"], "start"))
    p.append(_txt(x0 + W + 10, T_Y + 10, "늦게 ▶", 9.5, C["sharp"], "start"))

    TR_Y0 = T_Y + 146
    p += _sec(x0, TR_Y0 - 88, "궤적", "· 음 안에서의 흔들림 — 활")

    def X(u):
        return x0 + step * u

    def Y(c):
        return TR_Y0 - max(-TR_SPAN, min(TR_SPAN, c)) * TR_PPC

    p.append(f'<rect x="{x0}" y="{Y(tol_cent):.1f}" width="{W:.1f}" '
             f'height="{Y(-tol_cent)-Y(tol_cent):.1f}" fill="{C["good"]}" opacity="0.13"/>')
    for cv in (-40, -20, 0, 20, 40):
        y, main = Y(cv), cv == 0
        p.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+W:.1f}" y2="{y:.1f}" '
                 f'stroke="{C["axis"] if main else C["grid"]}" '
                 f'stroke-width="{2 if main else 1}"/>')
        p.append(_txt(x0 - 9, y + 3.5, f'{cv:+d}' if cv else '0', 9.5,
                      C["muted"], "end", mono=True))
    for i in range(1, n):
        p.append(f'<line x1="{X(i):.1f}" y1="{Y(TR_SPAN):.1f}" x2="{X(i):.1f}" '
                 f'y2="{Y(-TR_SPAN):.1f}" stroke="{C["grid"]}" stroke-width="1"/>')

    # 음이 바뀌는 순간에는 아직 앞 음의 소리가 남아 있어 센트가 수백까지 튑니다.
    # 그 구간은 이어 그리지 않고 **끊습니다**. 안 끊으면 그래프가 스파이크 투성이가 됩니다.
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

    for sign, col in ((1, C["sharp"]), (-1, C["flat"])):
        for run in runs:
            seg = []
            for u, v in run + [(run[-1][0], 0.0)]:
                if v * sign > 0:
                    seg.append((X(u), Y(v)))
                else:
                    if len(seg) > 1:
                        d = (f'M {seg[0][0]:.1f} {TR_Y0} '
                             + " ".join(f'L {a:.1f} {b:.1f}' for a, b in seg)
                             + f' L {seg[-1][0]:.1f} {TR_Y0} Z')
                        p.append(f'<path d="{d}" fill="{col}" opacity="0.30"/>')
                    seg = []

    for i in range(n):
        p.append(f'<line x1="{X(i)+3:.1f}" y1="{TR_Y0}" x2="{X(i+1)-3:.1f}" '
                 f'y2="{TR_Y0}" stroke="{C["ink"]}" stroke-width="2.5" '
                 f'opacity="0.85" stroke-linecap="round"/>')

    for run in runs:
        d = "M " + " L ".join(f'{X(u):.1f} {Y(v):.1f}' for u, v in run)
        p.append(f'<path d="{d}" fill="none" stroke="{C["trace"]}" stroke-width="2" '
                 f'stroke-linejoin="round"/>')

    lx = x0 + W + 10
    p.append(_txt(lx, TR_Y0 - 40, "높게", 10, C["sharp"], "start", 600))
    p.append(_txt(lx, TR_Y0 + 4, "목표", 10, C["ink"], "start", 600))
    p.append(_txt(lx, TR_Y0 + 46, "낮게", 10, C["flat"], "start", 600))
    p.append(_txt(lx, Y(tol_cent) - 5, f"±{tol_cent:.0f} 허용", 9, C["muted"], "start"))

    H = TR_Y0 + 100
    p.append(f'<line id="phead" x1="{x0}" y1="{top-42}" x2="{x0}" y2="{H-14}" '
             f'stroke="{C["trace"]}" stroke-width="1.6" opacity="0" '
             f'style="pointer-events:none"/>')

    return (f'<svg viewBox="0 0 {width} {H}" width="100%" '
            f'style="max-width:100%;height:auto;display:block">{"".join(p)}</svg>'), H


def stack_height(notes, width: int = 900) -> int:
    """리포트 가운데 그림의 높이 — 앱이 창 크기를 잡는 데 씁니다."""
    top = staff.layout(notes)[0]
    _, sc_bottom = staff.line(notes, 80, (width - 116 - 80) / len(notes), top,
                              right=width, sig=("♯", []))
    return int(sc_bottom + 88 + 118 + 146 + 100)


def report_height(notes, width: int = 900) -> int:
    return stack_height(notes, width) + 750


def weak_notes(res, tol_cent, top=3):
    """가장 먼저 고칠 음 — 오차가 큰 순서대로.

    결과를 본 사람이 바로 답을 얻어야 하는 질문은 하나입니다.
    "그래서 나는 어느 음을 다시 연습해야 하지?"
    """
    bad = [(i, r) for i, r in enumerate(res["rows"])
           if r["detected"] and abs(r["cent"]) > tol_cent]
    bad.sort(key=lambda x: -abs(x[1]["cent"]))
    return bad[:top]


def headline(res, tol_cent):
    """한 줄 진단 — 무엇이 문제인지."""
    det = [r for r in res["rows"] if r["detected"]]
    if not det:
        return "소리를 찾지 못했습니다."
    bad = [r for r in det if abs(r["cent"]) > tol_cent]
    if not bad:
        return f"{len(det)}음 모두 ±{tol_cent:.0f}센트 안입니다. 다음 단계로 넘어가도 좋습니다."
    m = res["mean_cent"]
    if m < -6:
        return "전체적으로 음이 <b>낮게</b> 연주됐습니다. 손 전체가 너트 쪽으로 치우쳐 있습니다."
    if m > 6:
        return "전체적으로 음이 <b>높게</b> 연주됐습니다. 손 전체가 브리지 쪽으로 치우쳐 있습니다."
    return "치우침은 없지만 <b>음마다 들쭉날쭉</b>합니다. 자리를 외우기보다 소리로 확인하는 연습이 필요합니다."


def coach(res, notes, tol_cent, tol_ms):
    """숫자를 사람 말로 바꿉니다. 지적은 많아야 넷."""
    rows = [r for r in res["rows"] if r["detected"]]
    tips = []
    if not rows:
        return [("확인", "소리를 못 찾았습니다. 마이크와 녹음 길이를 확인해 주세요.")]

    low = [r for r in rows if r["cent"] < -tol_cent]
    high = [r for r in rows if r["cent"] > tol_cent]
    if len(low) >= 2:
        w = min(rows, key=lambda r: r["cent"])
        tips.append(("음정", f'{len(low)}개 음이 낮습니다. 특히 <b>{w["ko"]}</b>가 '
                             f'{abs(w["cent"]):.0f}센트 낮습니다 '
                             f'({w["position"]}포지션 {w["finger"]}번). '
                             f'손 전체가 너트 쪽으로 치우쳐 있습니다.'))
    elif len(high) >= 2:
        w = max(rows, key=lambda r: r["cent"])
        tips.append(("음정", f'{len(high)}개 음이 높습니다. 특히 <b>{w["ko"]}</b>가 '
                             f'{w["cent"]:.0f}센트 높습니다.'))
    else:
        tips.append(("음정", f'{len(rows)}개 중 {sum(1 for r in rows if r["ok"])}개가 '
                             f'±{tol_cent:.0f}센트 안입니다. 좋습니다.'))

    sh = music.shift_index(notes)
    if sh is not None and sh < len(res["rows"]) and res["rows"][sh]["detected"]:
        r = res["rows"][sh]
        tips.append(("포지션", f'{notes[sh-1]["position"]}→{r["position"]}포지션으로 '
                               f'옮기는 <b>{r["ko"]}</b>: {r["cent"]:+.0f}센트, '
                               f'{r["ms"]:+.0f}ms. '
                               f'<b>{notes[sh-1]["ko"]}</b>를 짚어 소리로 확인한 뒤 '
                               f'올라가면 자리를 잡기 쉽습니다.'))

    shaky = max(rows, key=lambda r: r["std"])
    tips.append(("활", f'<b>{shaky["ko"]}</b>의 흔들림이 ±{shaky["std"]:.0f}센트로 '
                       f'가장 큽니다. 같은 음을 활만 길게 쓰는 연습이 도움이 됩니다.'))

    late = [r for r in rows if r["ms"] > tol_ms]
    if late:
        tips.append(("박자", f'{"·".join(r["ko"] for r in late)}에서 늦게 들어갑니다. '
                             f'대개 손을 옮기거나 활을 바꾸는 데 걸리는 시간입니다.'))
    return tips


def report(res, notes, sig, bpm, wav_bytes, title, width=900,
           tol_cent=12.0, tol_ms=40.0) -> str:
    n = len(notes)
    x0 = 80
    step = (width - 116 - x0) / n
    beat = 60.0 / bpm
    b64 = base64.b64encode(wav_bytes).decode()

    stats = [
        ("음정 정확도", f'{res["pitch_pct"]:.0f}%',
         f'{n}음 중 {round(res["pitch_pct"]*n/100)}개가 ±{tol_cent:.0f}센트 안',
         C["flat"] if res["pitch_pct"] < 60 else C["good"]),
        ("평균 치우침", f'{res["mean_cent"]:+.0f}', "센트 · +면 높은 쪽, −면 낮은 쪽",
         C["flat"] if res["mean_cent"] < -5 else
         (C["sharp"] if res["mean_cent"] > 5 else C["good"])),
        ("박자 정확도", f'{res["time_pct"]:.0f}%', f'±{tol_ms:.0f}ms 안',
         C["good"] if res["time_pct"] >= 75 else C["sharp"]),
        ("활 안정도", f'±{res["bow_std"]:.0f}', "센트 · 음 하나 안에서의 흔들림", C["ink2"]),
    ]
    stat_html = "".join(
        f'<div class="stat"><div class="lab">{a}</div>'
        f'<div class="num" style="color:{d}">{b}</div>'
        f'<div class="sub">{c}</div></div>' for a, b, c, d in stats)

    tip_html = "".join(f'<div class="tip"><span class="tag">{t}</span>'
                       f'<span>{s}</span></div>' for t, s in coach(res, notes, tol_cent, tol_ms))

    seg_html = "".join(
        f'<button onclick="playRange({i*4*beat:.3f},{min((i+1)*4,n)*beat:.3f})">'
        f'{i+1}마디</button>' for i in range((n + 3) // 4))

    det = [i for i, r in enumerate(res["rows"]) if r["detected"]]
    worst = sorted(det, key=lambda i: -abs(res["rows"][i]["cent"]))[:3]
    worst_html = "".join(
        f'<button class="bad" onclick="playNote({i})">{res["rows"][i]["ko"]} '
        f'{res["rows"][i]["cent"]:+.0f}</button>' for i in sorted(worst))

    js = json.dumps([{"ko": r["ko"], "cent": None if not r["detected"] else round(r["cent"], 1)}
                     for r in res["rows"]], ensure_ascii=False)
    stack_svg, _stack_h = _stack(res, notes, sig, width, x0, step, tol_cent, tol_ms)

    # 가장 먼저 고칠 음 — 결과를 본 직후 답해야 하는 질문
    weak = weak_notes(res, tol_cent)
    if weak:
        rank_html = "".join(
            f'<button class="wk" onclick="playNote({i})">'
            f'<span class="rk">{k+1}</span>'
            f'<span class="wko">{r["ko"]}</span>'
            f'<span class="wcent" style="color:{C["sharp"] if r["cent"]>0 else C["flat"]}">'
            f'{r["cent"]:+.0f}<i>센트</i></span>'
            f'<span class="wsub">{r["position"]}포지션 '
            f'{"개방" if r["finger"]==0 else str(r["finger"])+"번"} · '
            f'{"높게" if r["cent"]>0 else "낮게"}</span>'
            f'<span class="wply">▶ 듣기</span></button>'
            for k, (i, r) in enumerate(weak))
    else:
        rank_html = ('<div style="color:#0ca30c;font-size:13px;padding:6px 0">'
                     '이번엔 허용 범위를 벗어난 음이 없습니다.</div>')

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 *{{box-sizing:border-box}}
 body{{margin:0;background:{C['bg']};color:{C['ink']};
   font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif}}
 #wrap{{width:{width+40}px;margin:0 auto;padding:6px 20px 20px}}
 .cap{{color:{C['muted']};font-size:12.5px;margin:0 0 12px}}
 .card{{background:{C['panel']};border:1px solid {C['line']};border-radius:14px;
   padding:14px 16px;margin-bottom:12px}}
 .ct{{font-size:13px;font-weight:600;color:{C['ink2']};margin-bottom:2px}}
 .cs{{font-size:11.5px;color:{C['muted']};margin-bottom:10px;line-height:1.6}}
 .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}}
 .stat{{background:{C['panel']};border:1px solid {C['line']};border-radius:12px;
   padding:11px 13px}}
 .lab{{font-size:11px;color:{C['muted']}}}
 .num{{font-size:25px;font-weight:700;line-height:1.25;
   font-family:ui-monospace,Menlo,monospace}}
 .sub{{font-size:10.5px;color:{C['muted']};line-height:1.35}}
 .row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
 button{{background:#262624;color:#fff;border:1px solid {C['axis']};border-radius:8px;
   padding:7px 13px;font-size:12.5px;cursor:pointer;font-family:inherit}}
 button:hover{{background:#333330}}
 .main{{background:{C['trace']};color:#20200f;border:none;font-weight:700}}
 .bad{{border-color:{C['flat']};color:{C['flat']};
   font-family:ui-monospace,Menlo,monospace}}
 .hint{{font-size:11.5px;color:{C['muted']};margin-left:4px}}
 .tip{{display:flex;gap:9px;align-items:flex-start;font-size:12.5px;line-height:1.6;
   padding:6px 0;border-top:1px solid {C['line']}}}
 .tip:first-child{{border-top:none}}
 .tag{{flex:none;background:#262624;color:{C['ink2']};border-radius:5px;padding:1px 7px;
   font-size:11px;font-weight:600;margin-top:2px}}
 b{{color:{C['ink']}}}
 #now{{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:{C['trace']};
   min-width:140px}}
 .focus{{border-color:#4a4a44;background:#1f1f1d}}
 .ranks{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
 .wk{{display:grid;grid-template-columns:auto 1fr;grid-template-rows:auto auto auto;
   gap:2px 10px;align-items:center;text-align:left;padding:11px 13px;
   background:#141413;border:1px solid {C['axis']};border-radius:11px}}
 .wk:hover{{background:#232321}}
 .rk{{grid-row:1/3;width:26px;height:26px;border-radius:50%;background:#33322e;
   color:{C['ink2']};font-size:13px;font-weight:700;display:flex;
   align-items:center;justify-content:center}}
 .wko{{font-size:17px;font-weight:700}}
 .wcent{{font-family:ui-monospace,Menlo,monospace;font-size:19px;font-weight:700;
   line-height:1.1}}
 .wcent i{{font-size:10.5px;font-style:normal;margin-left:2px;opacity:.75}}
 .wsub{{grid-column:2;font-size:11px;color:{C['muted']}}}
 .wply{{grid-column:1/3;font-size:11px;color:{C['trace']};margin-top:5px}}
</style></head><body><div id="wrap">
 <div class="cap">{title} · {bpm} BPM · {n}음</div>
 <div class="stats">{stat_html}</div>

 <div class="card focus">
   <div class="ct">가장 먼저 고칠 음</div>
   <div class="cs">{headline(res, tol_cent)}</div>
   <div class="ranks">{rank_html}</div>
 </div>

 <div class="card">
   <div class="ct">음별 상세 분석</div>
   <div class="cs">악보 아래 세 층이 같은 가로 좌표 위에 있습니다 — 위에서 아래로
     <b>어느 음 / 얼마나 높거나 낮았나 / 빨랐나 늦었나 / 음 안에서 어떻게 흔들렸나</b>.
     음표를 누르면 <b>그 부분 내 연주</b>가 다시 들리고, 세로선이 네 층을 함께 지나갑니다.</div>
   {stack_svg}
 </div>

 <div class="card">
   <div class="ct">다시 듣기 · 반복 연습</div>
   <div style="height:8px"></div>
   <div class="row">
     <button class="main" onclick="playRange(0,{n*beat:.3f})">▶ 전체</button>
     {seg_html}
     <span class="hint">오차가 큰 음 →</span>
     {worst_html}
     <button onclick="stopAll()">■ 정지</button>
     <span id="now"></span>
   </div>
 </div>

 <div class="card">
   <div class="ct">오늘의 한마디</div>
   <div style="height:4px"></div>
   {tip_html}
 </div>

 <audio id="rec" src="data:audio/wav;base64,{b64}"></audio>
</div>
<script>
const NOTES = {js};
const X0 = {x0}, STEP = {step}, BEAT = {beat}, T0 = {res["t0"]:.4f};
const rec = document.getElementById('rec');
const ph = document.getElementById('phead'), now = document.getElementById('now');
let stopAt = null, raf = null;

// 화면의 0초는 '첫 소리가 난 자리'입니다. 녹음 파일에서는 T0 만큼 뒤죠.
function playRange(a, b) {{
  stopAt = T0 + b; rec.currentTime = T0 + a; rec.play();
  if (!raf) raf = requestAnimationFrame(tick);
}}
function playNote(i) {{ playRange(i * BEAT, (i + 1) * BEAT); }}
function stopAll() {{ rec.pause(); stopAt = null; move(null); }}

function move(t) {{
  if (t === null) {{ ph.style.opacity = 0; now.textContent = ''; return; }}
  const x = X0 + STEP * (t / BEAT);
  ph.setAttribute('x1', x.toFixed(1)); ph.setAttribute('x2', x.toFixed(1));
  ph.style.opacity = 0.9;
  const n = NOTES[Math.min(NOTES.length - 1, Math.max(0, Math.floor(t / BEAT)))];
  now.textContent = n.cent === null ? n.ko + '  —'
    : `${{n.ko}}  ${{n.cent > 0 ? '+' : ''}}${{n.cent.toFixed(0)}}센트`;
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
