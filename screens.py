"""
화면 ① — 움직이는 가이드.

  악보 → 낙하 노드 → 판정선 → 지판, 하나의 세로 흐름.
  오른쪽에 「다음 음 안내」 — 몇 번 손가락인지 손 그림으로.

**가로로 든 휴대폰**을 기준으로 짰습니다.
논리 크기 880 x 330 으로 그린 뒤, 화면 폭에 맞춰 통째로 줄입니다.
가로 844px 짜리 폰에서 스크롤 없이 한 화면에 들어갑니다.

결과 리포트는 report.py 에 있습니다.
둘 다 악보의 가로 좌표를 staff.note_x() 에서 가져옵니다 — 따로 계산하면 어긋납니다.
"""

import hashlib
import json
import os

import streamlit.components.v1 as components

import instrument
import music
import staff
from theme import C          # 색은 theme.py 한곳에서

#| 흐름  음 목록 → 화면 ①(가이드) HTML

# ── 논리 크기 (가로 폰 기준) ──
W = 880             # 전체 폭
H = 364             # 전체 높이 (가로 폰 한 화면)
PANEL_W = 232       # 오른쪽 「다음 음 안내」 폭
BODY_EDGE = 34      # 지판 오른쪽에 남기는 몸통 가장자리
                    # (브리지는 안내 패널로 옮겼습니다 — 지판을 넓게 쓰려고)
GAPX = 12
LW = W - PANEL_W - GAPX       # 왼쪽(악보+캔버스) 폭
BAR_H = 24          # 맨 아래 설명 줄
LANE_H = 78         # 노드가 떨어지는 구간
LEAD = 1.35         # 몇 초 앞의 음까지 보여줄지
ROW_GAP = 18        # 지판에서 줄 사이 간격 (계이름이 들어갈 자리까지)

STRING_COLOR = {"E": "#f6e9b8", "A": "#f0d98c", "D": "#cbb06a", "G": "#a98c4e"}


_GUIDE_DIR = os.path.join(os.path.dirname(__file__), "guide_component")
if not os.path.isfile(os.path.join(_GUIDE_DIR, "index.html")):
    # 배포할 때 이 폴더를 빠뜨리면 여기서 멈춥니다.
    # 안 그러면 "왜 녹음이 안 되지" 하고 한참 헤매게 됩니다.
    raise FileNotFoundError(
        "guide_component/index.html 이 없습니다. "
        "이 폴더를 통째로 함께 올려야 [● 시작 + 녹음] 이 됩니다. "
        f"(찾은 자리: {_GUIDE_DIR})")

_GUIDE = components.declare_component("violin_guide", path=_GUIDE_DIR)


def guide_component(html: str, height: int, key: str = "guide"):
    """가이드를 띄우고, **녹음한 소리를 되돌려 받습니다.**

    돌려주는 것: {"wav": base64 WAV, "sec": 길이, "id": 녹음 번호} 또는 None.
    같은 녹음이 여러 번 올라오므로, 쓰는 쪽에서 id 로 걸러야 합니다.
    """
    #| 흐름  가이드를 띄우고 녹음을 받아 온다
    #| 입력  가이드 HTML · 높이
    #| 단계  내용이 바뀌었는지 알 수 있게 표식(sig)을 붙인다 — 같으면 다시 안 그립니다
    #| 출력  녹음 {wav, sec, id} 또는 None
    sig = hashlib.md5(html.encode()).hexdigest()[:12]
    return _GUIDE(html=html, height=height, sig=sig, key=key, default=None)


def guide_height(notes=None, sig=None) -> int:
    """components.html 에 넘길 높이. 논리 높이 그대로입니다."""
    #| 흐름  논리 높이에 여백만 조금 더한다
    return H + 8


def _score(notes, sig, x0, step):
    """가이드용 악보 — 배지·손가락줄 없이 얇게."""
    #| 흐름  악보를 얇게 그리고, 음표 아래로 세로선을 내려 캔버스 레인과 잇는다
    #| 입력  음 목록 · 조표 · 가로 배치
    #| 호출  staff.layout → 위 여백 (배지가 없으니 덜 필요)
    #| 호출  staff.line → 악보 조각 (계이름만, 포지션 띠는 얇게)
    #| 반복  음마다
    #| 단계     음표 아래로 옅은 세로선 — 아래 레인과 이어집니다
    #| 단계  지금 어디인지 알려주는 커서를 얹는다
    #| 출력  (SVG, 높이)
    top = staff.layout(notes, with_badges=False)[0]
    parts, bottom = staff.line(notes, x0, step, top,
                               right=x0 + step * len(notes) + 8,
                               sig=sig, show_finger=False, show_position=False,
                               compact=True, mark_ids=True)
    for i in range(len(notes)):
        sx = staff.note_x(i, x0, step)
        parts.append(f'<line x1="{sx:.1f}" y1="{top + staff.GAP*4 + 5:.1f}" '
                     f'x2="{sx:.1f}" y2="{bottom:.1f}" stroke="#ffffff" '
                     f'stroke-width="1" opacity="0.08"/>')
    parts.append(f'<rect id="cursor" x="{x0:.1f}" y="{top-9}" width="{step:.1f}" '
                 f'height="{staff.GAP*4+18}" fill="#ffffff" fill-opacity="0.13" '
                 f'stroke="#ffffff" stroke-opacity="0.5" stroke-width="1.4" rx="6"/>')
    return (f'<svg id="score" viewBox="0 0 {LW} {bottom}" width="{LW}" '
            f'height="{bottom}" style="display:block">{"".join(parts)}</svg>'), bottom


def guide(notes, sig, bpm: int, inst: str = "violin", ready: int = 5) -> str:
    """악보 → 낙하 노드 → 판정선 → 지판, 하나의 세로 흐름."""
    #| 흐름  악보 · 낙하 노드 · 지판 · 다음 음 안내를 한 화면에
    #| 입력  음 목록 · 조표 · BPM · 악기 · 준비 시간
    #| 호출  instrument.get → 줄·길이·좌우 그림
    #| 호출  _score → 악보 SVG (낙하 레인과 같은 x)
    #| 호출  instrument.hand_svg → 손 그림 (손끝 표시를 미리 다 만들어 둠)
    #| 단계  음 정보를 JS 에 넘긴다 (자리·손가락·활·색·시각)
    #| 단계  화면 폭에 맞춰 통째로 줄이는 코드를 붙인다 (가로 폰 대응)
    #| 출력  HTML  (JS 가 매 프레임 다시 그림)
    ins = instrument.get(inst)
    x0 = max(70, staff.head_width(sig))
    x1 = LW - 22
    step = (x1 - x0) / len(notes)

    score_svg, score_h = _score(notes, sig, x0, step)
    cv_h = H - score_h - BAR_H

    # 지판에 **이번 연습이 쓰는 만큼만** 보여줍니다.
    # 늘 190mm 를 그리면, 낮은 자리만 쓰는 악보는 왼쪽 구석에 몰려 붙습니다.
    #| 단계  이번 악보가 쓰는 지판 범위에 맞춰 보여줄 폭을 정한다
    need = max([n["mm"] for n in notes] + [40.0])
    view_mm = min(ins["view_mm"], max(60.0, need * 1.22 + 10))

    #| 호출  instrument.bridge_html → 「어느 줄을 켜나」 (지판 옆이 아니라 패널에)
    bridge_svg = instrument.bridge_html(
        ins, PANEL_W - 26, 58,
        colors={s: STRING_COLOR[s] for s in ins["strings"]})
    # 내 악보는 줄을 넘나들 수 있습니다 — 쓰는 줄을 모두 밝게 합니다
    used = [s for s in ins["strings"] if any(n["string"] == s for n in notes)]
    active = notes[0]["string"]
    used_label = " · ".join(
        f'<b style="color:{STRING_COLOR[s]}">{s}현</b>' for s in used)

    data = [{"i": i, "ko": n["ko"], "finger": n["finger"], "bow": n["bow"],
             "mm": n["mm"], "t": n["t"], "dur": n["dur"], "pos": n["position"],
             "str": n["string"], "f": n["freq"],
             "color": staff.DOWN_COLOR if n["bow"] == "down" else staff.UP_COLOR,
             "slurHead": n["slur_head"]}
            for i, n in enumerate(notes)]
    strings = [{"name": s, "color": STRING_COLOR[s], "w": 1.4 + 0.4 * i}
               for i, s in enumerate(ins["strings"])]
    # 다른 줄에도 1포지션 손가락 자리를 흐리게 — 지판 전체가 보이게
    marks = {s["name"]: [music.mm_from_freq(s["freq"] * 2 ** (k / 12), s["freq"])
                         for k in (2, 4, 5, 7)] for s in music.STRINGS}
    art = {"scroll": ins["scroll"], "body": ins["body"], "pegs": ins["pegs"],
           "wood": ins["wood"], "board": ins["board"], "bridge_x": ins["bridge_x"],
           "scroll_img": ins.get("scroll_img", ""),
           "scroll_nut": ins.get("scroll_nut", 1.0),
           "scroll_aspect": ins.get("scroll_aspect", 1.0),
           "scroll_str": list(ins.get("scroll_str", (0.0, 1.0))),
           "body_img": ins.get("body_img", ""),
           "body_aspect": ins.get("body_aspect", 1.0),
           "body_str": list(ins.get("body_str", (0.0, 1.0)))}

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<style>
 html,body{{margin:0;padding:0;background:{C['bg']};overflow:hidden;
   -webkit-text-size-adjust:100%}}
 #fit{{width:100%;overflow:hidden}}
 #wrap{{width:{W}px;transform-origin:top left;
   font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif}}
 #row{{display:flex;gap:{GAPX}px}}
 #left{{width:{LW}px;flex:none}}
 canvas{{display:block;border-radius:0 0 12px 12px}}
 #panel{{width:{PANEL_W}px;flex:none;background:{C['panel']};
   border:1px solid {C['line']};border-radius:12px;padding:11px 13px;
   height:{cv_h}px;box-sizing:border-box;display:flex;flex-direction:column}}
 .pt{{font-size:11.5px;color:{C['muted']};margin-bottom:6px}}
 .pbody{{display:flex;gap:8px;align-items:center;flex:1}}
 .pinfo{{flex:1;min-width:0}}
 .pko{{font-size:27px;font-weight:700;color:{C['ink']};line-height:1.15}}
 .pfg{{font-size:12.5px;color:{C['ink2']};margin-bottom:8px}}
 .pbow{{display:inline-block;font-size:12px;font-weight:600;border-radius:6px;
   padding:3px 8px;margin-bottom:7px}}
 .ppos{{font-size:11.5px;font-weight:600;margin-top:4px}}
 /* 한 줄로 유지합니다 — 줄바꿈되면 버튼이 세로로 깨져 자리를 잃습니다 */
 #bar{{display:flex;gap:9px;align-items:center;height:{BAR_H}px;
   color:{C['ink2']};font-size:11.5px;white-space:nowrap;overflow:hidden}}
 #bar>*{{flex:none}}
 button{{background:{C['panel2']};color:{C['ink']};border:1px solid {C['line']};
   border-radius:7px;padding:4px 11px;font-size:11.5px;cursor:pointer;
   font-family:inherit;touch-action:manipulation}}
 .k{{display:inline-flex;align-items:center;gap:4px;margin-left:8px}}
 .sw{{width:9px;height:9px;border-radius:2px;display:inline-block}}
 /* 노드 속도 — 연주하면서 바로 만질 수 있게 바 안에 둡니다 */
 #spbox{{gap:6px}}
 #sp{{width:88px;height:18px;accent-color:{C['accent']};cursor:pointer;
   touch-action:manipulation}}
 #spv{{font-family:ui-monospace,Menlo,monospace;font-size:11px;
   color:{C['ink']};min-width:34px}}
 /* 폰에서 손가락으로 잡기 쉽게 */
 #sp::-webkit-slider-thumb{{width:16px;height:16px}}
 select{{background:{C['panel2']};color:{C['ink']};border:1px solid {C['line']};
   border-radius:6px;padding:3px 5px;font-size:11.5px;font-family:inherit;
   cursor:pointer}}
 #rot{{position:fixed;inset:0;background:{C['bg']};color:{C['ink2']};
   display:none;align-items:center;justify-content:center;font-size:15px;
   text-align:center;line-height:2;z-index:9}}
</style></head><body>
<div id="fit"><div id="wrap">
 <div id="row">
  <div id="left">
   {score_svg}
   <canvas id="cv" width="{LW}" height="{cv_h}"></canvas>
  </div>
  <div id="panel">
   <div class="pt">다음 음 안내</div>
   <div class="pbody">
    <div class="pinfo">
      <div class="pko" id="pko">—</div>
      <div class="pfg" id="pfg">&nbsp;</div>
      <div class="pbow" id="pbow">&nbsp;</div>
      <div class="ppos" id="ppos">&nbsp;</div>
    </div>
    <div style="flex:none">{instrument.hand_html(ins, 78)}</div>
   </div>
   <div class="pt" style="margin:2px 0 3px">어느 줄을 켜나</div>
   {bridge_svg}
  </div>
 </div>
 <div id="bar">
   <button id="go">● 시작 + 녹음</button>
   <button id="dm" title="악보를 소리로 먼저 들려줍니다 (녹음 전에)">🔊 시범 듣기</button>
   <span id="rec" class="k"></span>
   <span class="k">준비
     <select id="rd">
       <option value="0">없음</option><option value="3">3초</option>
       <option value="5">5초</option><option value="7">7초</option>
       <option value="10">10초</option><option value="15">15초</option>
     </select></span>
   <span>{bpm} BPM · {used_label}</span>
   <span class="k"><i class="sw" style="background:{staff.DOWN_COLOR}"></i>⊓ 다운</span>
   <span class="k"><i class="sw" style="background:{staff.UP_COLOR}"></i>∨ 업</span>
   <span class="k" id="spbox" style="margin-left:auto">노드 속도
     <input id="sp" type="range" min="0.5" max="3" step="0.1" value="1">
     <b id="spv">1.0배</b></span>
 </div>
</div></div>
<div id="rot"><div>📱 가로로 돌려서 보세요<br>
<span style="font-size:12.5px;opacity:.7">악보와 지판을 한 화면에 놓으려면
가로가 필요합니다</span></div></div>
<script>
const NOTES = {json.dumps(data, ensure_ascii=False)};
const STRINGS = {json.dumps(strings, ensure_ascii=False)};
const MARKS = {json.dumps(marks)};
const ART = {json.dumps(art, ensure_ascii=False)};
const ACTIVE = "{active}", USED = {json.dumps(used)}, VIEW_MM = {view_mm:.1f};
const LW = {LW}, CV = {cv_h};
const X0 = {x0}, STEP = {step}, BEAT = {60.0 / bpm};
const TOTAL = {len(notes) * 60.0 / bpm};
// 지판은 네 줄이 들어갈 만큼만 쓰고, 남는 높이는 전부 **노드 레인**에 줍니다.
// (레인이 길수록 앞의 음이 더 일찍 보입니다)
const ROW_GAP = {ROW_GAP};
const BOARD_BOT = CV - 6;
const BOARD_TOP = BOARD_BOT - (11 + 3 * ROW_GAP + 14);
const HIT_Y = BOARD_TOP - 8;                // 판정선
const SCROLL_W = {ins["scroll_w"]}, BODY_W = {BODY_EDGE};
const BX0 = SCROLL_W, BX1 = LW - BODY_W;    // 지판의 왼쪽·오른쪽 끝
const LEAD_BASE = {LEAD};                   // 1.0배일 때 몇 초 앞까지 보이나
const ROW = {{}};
STRINGS.forEach((s, i) => ROW[s.name] = BOARD_TOP + 11 + i * ROW_GAP);

const cv = document.getElementById('cv'), g = cv.getContext('2d');
const scrollImg = new Image();
scrollImg.src = ART.scroll_img || '';
const bodyImg = new Image();
bodyImg.src = ART.body_img || '';
const cursor = document.getElementById('cursor');
const wrap = document.getElementById('wrap'), fitbox = document.getElementById('fit');
const P = {{ko: pko, fg: pfg, bow: pbow, pos: ppos}};

// 낙하 레인의 x = 악보 음표의 x.  둘은 같은 식을 씁니다.
const laneX = i => X0 + STEP * (i + 0.5);
// 지판의 x = 너트에서의 실제 거리
const boardX = mm => BX0 + (BX1 - BX0) * (mm / VIEW_MM);

// ── 화면 폭에 맞춰 통째로 키우거나 줄이기 ──
//
//  예전에는 상한이 1이라 넓은 화면에서도 880px 에 머물렀습니다.
//  그래서 PC 에서 가이드만 가운데 좁게 놓이고 좌우가 비었습니다.
//  이제 폭에 맞춰 **키웁니다.** 다만 키울 때만 화면 높이를 봅니다 —
//  가이드가 화면을 다 먹으면 아래 [분석하기] 가 밖으로 밀려나기 때문입니다.
//  (폰 가로에서는 s 가 1 을 넘지 않으므로 지금 그대로입니다)
let VP_H = 0;                       // 바깥 창의 높이 (껍데기가 알려줍니다)
addEventListener('message', (e) => {{
  if (e.data && e.data.vpH) {{ VP_H = e.data.vpH; fit(); }}
}});

function fit() {{
  const w = document.documentElement.clientWidth;
  document.getElementById('rot').style.display = (w < 540) ? 'flex' : 'none';
  let s = Math.max(0.5, w / {W});
  //| 갈래  키우는 중인가 ? 화면 높이의 55% 를 넘지 않게 잡는다 : 그대로 (폰은 여기 안 걸립니다)
  if (s > 1 && VP_H) s = Math.max(1, Math.min(s, VP_H * 0.55 / {H}));
  wrap.style.transform = `scale(${{s}})`;
  wrap.style.marginLeft = Math.max(0, (w - {W} * s) / 2) + 'px';
  fitbox.style.height = ({H} * s) + 'px';
  //| 단계  바깥(스트림릿)에도 높이를 알린다 — 안 그러면 아래가 잘립니다
  if (parent !== window) parent.postMessage({{violinHeight: Math.ceil({H} * s) + 10}}, '*');
}}
addEventListener('resize', fit); fit();

// ══════════════════════════════════════════════════════════════
//  시작 전 — 준비 시간 → 메트로놈 카운트인 → 연주  (노래방처럼)
// ══════════════════════════════════════════════════════════════
// 시각 t 는 **첫 음이 울리는 순간이 0** 입니다. 그 앞은 음수입니다.
//     t < -4박          준비 (자세 잡기) — 남은 초를 크게
//     -4박 ≤ t < 0      메트로놈 똑 · 똑 · 똑 · 똑
//     t ≥ 0             연주
// 하나의 시간축이라 노드·악보·소리가 저절로 맞습니다.
//| 흐름  준비 시간 → 4박 카운트인 → 연주.  셋이 한 시간축입니다.
const COUNT = 4;                            // 카운트인 박 수
let READY = {ready};                        // 준비 시간 (초)
const rdIn = document.getElementById('rd');
try {{
  const v = parseFloat(localStorage.getItem('vc_ready'));
  if (v >= 0) READY = v;
}} catch (e) {{}}
rdIn.value = READY;
if (rdIn.selectedIndex < 0) rdIn.value = 5;  // 저장된 값이 목록에 없으면

// t0 가 null 이면 **아직 시작 전**입니다. 저절로 시작하지 않습니다 —
// 녹음 버튼을 먼저 누르고 ▶ 를 눌러야 박자가 녹음과 맞습니다.
let t0 = null, clicked = -1, played = -1;
function start(ready) {{
  //| 흐름  지금부터 (준비 + 카운트인) 뒤에 첫 음이 오도록 시각을 맞춘다
  t0 = performance.now() + (ready + COUNT * BEAT) * 1000;
  clicked = -1;                              // 메트로놈을 처음부터 다시
  played = -1;                               // 시범 연주도 처음부터
  marked = -2; shown = -2;
  goBtn.textContent = '■ 멈춤';
}}

function stop() {{
  //| 흐름  멈춘다. 녹음도 같이 끝내고 위로 올려보냅니다.
  t0 = null;
  marked = -2; shown = -2;
  goBtn.textContent = '● 시작 + 녹음';
  recStop();
}}

// ── 메트로놈 — 짧은 클릭. 첫 박만 높게 (어디가 1박인지 알게) ──
let ac = null;
function audio() {{
  //| 갈래  소리 장치가 있나 ? 그대로 : 하나 만든다 (막혀 있으면 깨운다)
  try {{
    if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
    if (ac.state === 'suspended') ac.resume();
  }} catch (e) {{ ac = null; }}
  return ac;
}}
function tick(accent) {{
  const a = audio();
  if (!a || a.state !== 'running') return;
  const o = a.createOscillator(), gn = a.createGain(), t1 = a.currentTime;
  o.type = 'square';
  o.frequency.value = accent ? 1760 : 1175;
  gn.gain.setValueAtTime(0.0001, t1);
  gn.gain.exponentialRampToValueAtTime(accent ? 0.42 : 0.26, t1 + 0.004);
  gn.gain.exponentialRampToValueAtTime(0.0001, t1 + 0.07);
  o.connect(gn); gn.connect(a.destination);
  o.start(t1); o.stop(t1 + 0.09);
}}
// 브라우저는 손가락이 닿기 전에는 소리를 내주지 않습니다 — 첫 접촉 때 깨웁니다
addEventListener('pointerdown', () => audio(), {{once: true}});

// ── 시범 연주 — 악보를 소리로 먼저 들려줍니다 ──
// 톱니파를 저역통과로 깎으면 활 소리 비슷해집니다 (배음이 많고 위가 부드러움).
// 완벽한 악기 소리가 목적이 아니라, **음정과 박자를 귀로 확인**하는 것이 목적입니다.
//| 흐름  음 하나를 그 높이·길이만큼 소리 낸다
let DEMO = false;
const dmBtn = document.getElementById('dm');
function setDemo(v) {{
  DEMO = v;
  dmBtn.style.background = v ? '{C['accent']}' : '{C['panel2']}';
  dmBtn.style.color = v ? '{C['on_accent']}' : '{C['ink']}';
  dmBtn.style.color = v ? '#fff' : '{C['ink']}';
  dmBtn.textContent = v ? '🔊 시범 켜짐' : '🔊 시범 듣기';
}}
dmBtn.onclick = () => {{ audio(); setDemo(!DEMO); start(READY); }};

function tone(n) {{
  const a = audio();
  if (!a || a.state !== 'running') return;
  const t1 = a.currentTime, d = Math.max(0.14, n.dur * 0.95);
  const o = a.createOscillator(), lp = a.createBiquadFilter(), gn = a.createGain();
  o.type = 'sawtooth'; o.frequency.value = n.f;
  lp.type = 'lowpass'; lp.frequency.value = Math.min(7000, n.f * 6); lp.Q.value = 0.7;
  gn.gain.setValueAtTime(0.0001, t1);
  gn.gain.exponentialRampToValueAtTime(0.20, t1 + 0.055);   // 활이 걸리는 시간
  gn.gain.exponentialRampToValueAtTime(0.13, t1 + d * 0.72);
  gn.gain.exponentialRampToValueAtTime(0.0001, t1 + d);
  o.connect(lp); lp.connect(gn); gn.connect(a.destination);
  o.start(t1); o.stop(t1 + d + 0.03);
}}

// ══════════════════════════════════════════════
//  녹음 — 시작 버튼 하나에 묶습니다
//
//  왜 묶나: 녹음과 가이드가 따로면 사용자가 순서를 지켜야 하고,
//  순서가 틀어지면 박자가 어긋나 분석이 통째로 무의미해집니다.
//  같은 클릭에서 시작하면 어긋날 수가 없습니다.
// ══════════════════════════════════════════════
const goBtn = document.getElementById('go'), recTag = document.getElementById('rec');
let mr = null, chunks = [], recOn = false;

function recMsg(t, color) {{
  recTag.textContent = t;
  recTag.style.color = color || '{C['muted']}';
}}

function toWav(buf) {{
  //| 흐름  브라우저 소리 → WAV (파이썬 쪽을 안 고치려고 여기서 만듭니다)
  //| 입력  디코딩된 소리
  //| 반복  표본마다 16비트 정수로
  //| 출력  base64 WAV
  const n = buf.length, sr = buf.sampleRate, d = buf.getChannelData(0);
  const ab = new ArrayBuffer(44 + n * 2), v = new DataView(ab);
  const w = (o, t) => {{ for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); }};
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVEfmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, 'data'); v.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {{
    let x = Math.max(-1, Math.min(1, d[i]));
    v.setInt16(44 + i * 2, x < 0 ? x * 32768 : x * 32767, true);
  }}
  let b = '', u = new Uint8Array(ab);
  for (let i = 0; i < u.length; i += 8192) {{
    b += String.fromCharCode.apply(null, u.subarray(i, i + 8192));
  }}
  return btoa(b);
}}

function up(msg) {{
  //| 갈래  스트림릿 안인가 ? 위로 올려보낸다 : (혼자 열린 파일이면) 아무것도 안 한다
  if (parent !== window) parent.postMessage(msg, '*');
}}

async function recStart() {{
  //| 흐름  마이크를 잡고 녹음을 건다
  //| 갈래  마이크가 열리나 ? 녹음을 시작한다 : 알리고 녹음 없이 진행한다
  if (recOn) return true;
  try {{
    const stream = await navigator.mediaDevices.getUserMedia({{audio: {{
      echoCancellation: false, noiseSuppression: false, autoGainControl: false
    }}}});
    chunks = []; mr = new MediaRecorder(stream);
    mr.ondataavailable = e => chunks.push(e.data);
    mr.onstop = async () => {{
      stream.getTracks().forEach(t => t.stop());
      recOn = false;
      try {{
        const ac = new (window.AudioContext || window.webkitAudioContext)();
        const buf = await ac.decodeAudioData(await new Blob(chunks).arrayBuffer());
        //| 갈래  너무 짧나 ? 버린다 : 위로 올려보낸다
        if (buf.duration < 0.5) {{ recMsg('너무 짧아 버렸습니다'); return; }}
        recMsg('✓ ' + buf.duration.toFixed(1) + '초', '{C['good']}');
        up({{violin: {{wav: toWav(buf), sec: buf.duration, id: Date.now()}}}});
      }} catch (e) {{ recMsg('소리를 읽지 못했습니다'); }}
    }};
    mr.start(); recOn = true;
    recMsg('● 녹음 중', '{C['bad']}');
    return true;
  }} catch (e) {{
    recMsg('마이크 없이 진행합니다 (' + e.name + ')');
    return false;
  }}
}}

function recStop() {{
  //| 갈래  녹음 중인가 ? 멈추고 내려보낸다 : 그냥 둔다
  if (recOn && mr && mr.state !== 'inactive') mr.stop();
}}

//| 갈래  이미 돌고 있나 ? 멈춘다 : 마이크를 잡고 준비 시간부터 시작한다
goBtn.onclick = async () => {{
  audio();
  if (t0 !== null) {{ stop(); return; }}
  recMsg('마이크 여는 중…');
  await recStart();
  start(READY);
}};
rdIn.onchange = () => {{
  READY = +rdIn.value;
  try {{ localStorage.setItem('vc_ready', READY); }} catch (e) {{}}
}};

// ── 아직 시작 전 ──
// 빈 화면을 두면 "고장났나" 싶습니다. 무엇을 눌러야 하는지 적어 둡니다.
//| 흐름  시작 전에는 무엇을 눌러야 하는지 알려준다
function idle() {{
  g.save(); g.textAlign = 'center';
  g.fillStyle = '{C['ink']}'; g.font = '700 15px system-ui';
  g.fillText('●  시작 + 녹음  을 누르면 녹음과 가이드가 함께 시작됩니다',
             LW / 2, HIT_Y / 2 - 4);
  g.fillStyle = '{C['muted']}'; g.font = '12.5px system-ui';
  g.fillText('준비 시간 뒤 메트로놈 네 박을 세고 시작합니다', LW / 2, HIT_Y / 2 + 18);
  g.restore();
}}

// ── 준비·카운트인 표시 ──
// 지판 왼쪽(스크롤 위쪽)은 노드가 지나가지 않는 자리라 여기에 그립니다.
function countIn(t) {{
  //| 갈래  아직 준비 시간인가 ? 남은 초를 크게 : 메트로놈 네 박을 점으로
  g.save(); g.textAlign = 'center';
  if (t < -COUNT * BEAT) {{
    const s = Math.ceil(-t - COUNT * BEAT);
    g.fillStyle = '{C['ink']}'; g.font = '700 34px system-ui';
    g.fillText(s, LW / 2, 38);
    g.fillStyle = '{C['muted']}'; g.font = '12.5px system-ui';
    g.fillText('자세를 잡으세요 · 곧 메트로놈이 울립니다', LW / 2, 60);
  }} else {{
    const b = Math.floor((t + COUNT * BEAT) / BEAT);        // 지금 몇 박째
    const frac = ((t + COUNT * BEAT) % BEAT) / BEAT;
    const gap = 26, x0c = BX0 / 2 - gap * (COUNT - 1) / 2, cy = HIT_Y / 2 - 6;
    //| 반복  네 박마다 점 하나 — 지난 박은 켜고, 지금 박은 크게
    for (let k = 0; k < COUNT; k++) {{
      const on = k === b;
      g.beginPath();
      g.arc(x0c + gap * k, cy, on ? 11 - 4 * frac : 6, 0, 6.284);
      g.fillStyle = k < b ? 'rgba(255,255,255,0.45)'
                  : (on ? (k === 0 ? '{C['accent']}' : '{C['ink']}')
                        : 'rgba(255,255,255,0.16)');
      g.fill();
    }}
    // 선생님이 세어 주듯 — 마지막 박에 「시작!」
    const say = ['하나', '둘', '셋', '넷 — 시작!'];
    g.fillStyle = b === COUNT - 1 ? '{C['accent']}' : '{C['ink2']}';
    g.font = '700 12.5px system-ui';
    g.fillText(say[b] || '', BX0 / 2, cy + 30);
  }}
  g.restore();
}}

// ── 노드 속도 — 빠를수록 앞이 덜 보이고 노드가 빨리 내려옵니다 ──
// (BPM 은 '음악의 빠르기', 이건 '몇 초 앞까지 보여줄지'라 서로 다릅니다)
let SPEED = 1;
try {{ SPEED = parseFloat(localStorage.getItem('vc_speed')) || 1; }} catch (e) {{}}
const spIn = document.getElementById('sp'), spV = document.getElementById('spv');
function setSpeed(v) {{
  SPEED = Math.max(0.5, Math.min(3, v));
  spIn.value = SPEED; spV.textContent = SPEED.toFixed(1) + '배';
  // 배속이 뭘 바꾸는지 — 몇 초 앞까지 보이는지
  spIn.title = '앞이 보이는 시간 ' + (LEAD_BASE / SPEED).toFixed(2) + '초';
  try {{ localStorage.setItem('vc_speed', SPEED); }} catch (e) {{}}
}}
spIn.oninput = () => setSpeed(+spIn.value);
setSpeed(SPEED);
setDemo(false);

// ── 악기 그림 — 0~1 좌표를 상자에 맞춰 그립니다 ──
function art(list, x, w, y, h) {{
  g.save(); g.beginPath(); g.rect(x - 3, y - 16, w + 6, h + 32); g.clip();
  for (const it of list) {{
    const p = new Path2D();
    p.addPath(new Path2D(it.d), {{a: w, b: 0, c: 0, d: h, e: x, f: y}});
    if (it.grad) {{
      const gr = g.createLinearGradient(0, y, 0, y + h);
      gr.addColorStop(0, it.grad[0]); gr.addColorStop(1, it.grad[1]);
      g.fillStyle = gr; g.fill(p);
    }} else if (it.fill) {{ g.fillStyle = ART.wood[it.fill]; g.fill(p); }}
    else {{ g.strokeStyle = ART.wood[it.stroke]; g.lineWidth = it.w * h;
            g.lineCap = 'round'; g.lineJoin = 'round'; g.stroke(p); }}
  }}
  g.restore();
}}

// 사진 하나를 **줄 간격에 맞춰** 놓습니다.
// 사진 속 E현·G현 자리를 지판의 E·G 줄에 맞추면 크기가 저절로 정해지고,
// 사진의 줄과 화면의 줄이 한 줄로 이어져 보입니다.
//| 흐름  사진 속 두 줄 자리를 지판의 두 줄에 맞춰 크기와 위치를 정한다
function photo(img, str, aspect, anchorX, atFrac) {{
  const r0 = ROW[STRINGS[0].name], r3 = ROW[STRINGS[3].name];
  const ih = (r3 - r0) / (str[1] - str[0]);      // 줄 간격이 맞는 높이
  const iw = ih / aspect;
  g.drawImage(img, anchorX - iw * atFrac, r0 - str[0] * ih, iw, ih);
}}

function board() {{
  const top = BOARD_TOP, bot = BOARD_BOT, h = bot - top;

  // 오른쪽 — 몸통. 사진이 있으면 사진, 없으면 그림.
  //| 갈래  몸통 사진이 있나 ? 지판 끝에 이어 붙인다 : 코드로 그린다
  if (bodyImg.complete && bodyImg.naturalWidth) {{
    // 몸통은 지판보다 훨씬 넓어서, 줄 간격을 맞추면 위아래가 화면 밖으로 나갑니다.
    // 잘린 자리가 네모나게 보이지 않도록 위아래를 바탕색으로 흐리게 덮습니다.
    const y0 = HIT_Y + 2, y1 = CV - 1;         // 판정선 아래 ~ 캔버스 끝
    g.save();
    g.beginPath(); g.rect(BX1 - 1, y0, LW - BX1 + 1, y1 - y0); g.clip();
    photo(bodyImg, ART.body_str, ART.body_aspect, BX1, 0);
    //| 반복  위·아래 잘린 자리마다 — 바탕색으로 서서히 사라지게
    for (const [ya, yb, hh] of [[y0, y0 + 12, 12], [y1, y1 - 20, 20]]) {{
      const fg = g.createLinearGradient(0, ya, 0, yb);
      fg.addColorStop(0, '{C['bg']}'); fg.addColorStop(1, 'rgba(13,17,23,0)');
      g.fillStyle = fg;
      g.fillRect(BX1 - 1, Math.min(ya, yb), LW - BX1 + 1, hh);
    }}
    g.restore();
  }} else {{
    art(ART.body, BX1, BODY_W, top, h);
  }}

  // 왼쪽 — 스크롤·페그박스는 사진.
  // 사진 속 줄 간격을 지판의 줄 간격에 맞춰 크기를 정하고,
  // 너트가 지판 시작점(BX0)에 오도록 놓습니다. 그래야 줄이 이어져 보입니다.
  if (scrollImg.complete && scrollImg.naturalWidth) {{
    photo(scrollImg, ART.scroll_str, ART.scroll_aspect, BX0, ART.scroll_nut);
  }} else {{
    art(ART.scroll, 0, SCROLL_W, top, h);      // 사진이 없으면 그림으로
    for (const pg of ART.pegs) {{
      const x = pg[0] * SCROLL_W, y = top + pg[1] * h;
      g.strokeStyle = ART.wood.dark; g.lineWidth = 2.2;
      g.beginPath(); g.moveTo(x, top + 0.5 * h); g.lineTo(x, y); g.stroke();
      g.fillStyle = ART.wood.sheen;
      g.beginPath(); g.ellipse(x, y, 2.8, 4.6, 0, 0, 6.284); g.fill();
    }}
  }}

  // 지판 (흑단)
  g.beginPath();
  g.moveTo(BX0 - 2, top + 4); g.lineTo(BX1 + 2, top);
  g.lineTo(BX1 + 2, bot); g.lineTo(BX0 - 2, bot - 4); g.closePath();
  const gr = g.createLinearGradient(0, top, 0, bot);
  gr.addColorStop(0, ART.board.top); gr.addColorStop(1, ART.board.bot);
  g.fillStyle = gr; g.fill();
  g.fillStyle = '#d8cfbd'; g.fillRect(BX0 - 4.5, top + 3, 3.6, h - 5);   // 너트

  // 네 줄 — 연주하는 줄만 밝게, 나머지는 자리 참고용
  // 몸통이 사진이면 사진 안에 이미 줄이 있으므로, 내 줄은 지판 끝에서 멈춥니다.
  const photoBody = bodyImg.complete && bodyImg.naturalWidth;
  const bx = photoBody ? BX1 + 5 : BX1 + BODY_W * ART.bridge_x;
  STRINGS.forEach(s => {{
    const y = ROW[s.name], on = USED.indexOf(s.name) >= 0;
    g.globalAlpha = on ? 1 : 0.26;
    g.strokeStyle = s.color; g.lineWidth = on ? s.w + 1.2 : s.w;
    g.beginPath(); g.moveTo(BX0 - 6, y); g.lineTo(bx, y); g.stroke();
    MARKS[s.name].forEach(mm => {{
      g.fillStyle = s.color; g.globalAlpha = on ? 0.4 : 0.12;
      g.beginPath(); g.arc(boardX(mm), y, on ? 2.4 : 1.8, 0, 6.284); g.fill();
    }});
    // 줄 이름(E·A·D·G)은 **너트 왼쪽**에 둡니다.
    // 지판 위에 두면 계이름이 들어갈 자리를 뺏습니다.
    g.globalAlpha = 1;
    g.fillStyle = on ? s.color : '#8a8a86';
    g.font = (on ? '700 ' : '') + '9.5px system-ui'; g.textAlign = 'right';
    g.strokeStyle = 'rgba(0,0,0,0.85)'; g.lineWidth = 2.6;
    g.strokeText(s.name, BX0 - 7, y + 3.4);    // 사진 위라 테두리를 넣어 읽히게
    g.fillText(s.name, BX0 - 7, y + 3.4);
  }});
  g.globalAlpha = 1;

  // 브리지 — 사진에는 이미 있으므로 그림일 때만
  //| 갈래  몸통이 사진인가 ? 사진의 브리지를 쓴다 : 브리지를 그린다
  if (!photoBody) {{
    const bgd = g.createLinearGradient(bx - 6, 0, bx + 6, 0);
    bgd.addColorStop(0, ART.wood.edge); bgd.addColorStop(1, ART.wood.mid);
    g.fillStyle = bgd;
    g.beginPath();
    g.moveTo(bx - 3, top + 4); g.lineTo(bx + 3, top + 4);
    g.lineTo(bx + 5, bot - 4); g.lineTo(bx - 5, bot - 4); g.closePath(); g.fill();
  }}

  // 이번 연습에 쓰는 음의 자리 — 세로 안내선은 지판 전체에
  g.textAlign = 'center';
  SPOTS.forEach(sp => {{
    const x = boardX(sp.mm);
    g.strokeStyle = 'rgba(255,255,255,0.09)'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, top + 2); g.lineTo(x, bot - 2); g.stroke();
  }});

  // 계이름은 **그 음이 쓰는 줄 바로 아래**에, 그 줄 색으로.
  // 아래에 한 줄로 몰아 적으면 줄이 여럿일 때 어느 줄 이름인지 알 수 없습니다.
  // (같은 손가락 자리라도 줄이 다르면 다른 음입니다)
  //| 반복  계이름 라벨마다 — 자기 줄 아래에
  g.textAlign = 'center';
  LABELS.forEach(L => {{
    g.font = '700 8.5px system-ui';
    g.strokeStyle = 'rgba(0,0,0,0.9)'; g.lineWidth = 2.8;
    g.strokeText(L.ko, L.x, ROW[L.s] + 9);
    g.fillStyle = SCOL[L.s] || '#9a9a94';
    g.globalAlpha = USED.indexOf(L.s) >= 0 ? 0.95 : 0.4;
    g.fillText(L.ko, L.x, ROW[L.s] + 9);
    g.globalAlpha = 1;
  }});

  // 판정선 — 여기 닿는 순간 짚습니다. 나무색 위에서도 튀도록 원색으로.
  g.save();
  const hg = g.createLinearGradient(0, HIT_Y - 16, 0, HIT_Y);
  hg.addColorStop(0, 'rgba(255,45,69,0)'); hg.addColorStop(1, 'rgba(255,45,69,0.18)');
  g.fillStyle = hg; g.fillRect(BX0 + 1, HIT_Y - 16, LW, 16);
  // 판정선 — 예전엔 새빨간 형광이라 화면에서 제일 먼저 눈에 띄었습니다.
  // 짚는 **순간**을 알리는 선이지 오류 표시가 아니므로 순하게 낮췄습니다.
  // (금색으로 해 봤더니 줄 색에 묻혀 사라져서 산호색으로 갑니다)
  g.shadowColor = '#e0736e'; g.shadowBlur = 6;
  g.strokeStyle = '#e0736e'; g.lineWidth = 1.9;
  g.beginPath(); g.moveTo(BX0 + 1, HIT_Y); g.lineTo(LW, HIT_Y); g.stroke();
  g.restore();
}}

// 노드는 처음부터 끝까지 **지판 자리**에서 곧게 떨어집니다.
// 악보 자리에서 흘러내리게도 해 봤는데, 어디에 앉을지 예측이 안 돼 헷갈렸습니다.
// 대신 "지금 어느 음인지"는 위 악보에서 그 음표를 켜서 알려줍니다.
const NODE_W = 30, NODE_R = 7;      // 판정 자리(리셉터)와 같은 폭·모서리

function lanes() {{
  // 아래 절반은 지판 자리 그대로 — 노드가 여기로 내려앉습니다
  NOTES.forEach(n => {{
    const x = boardX(n.mm);
    const grd = g.createLinearGradient(0, 0, 0, HIT_Y);
    grd.addColorStop(0, 'rgba(255,255,255,0)');
    grd.addColorStop(0.55, 'rgba(255,255,255,0.05)');
    grd.addColorStop(1, 'rgba(255,255,255,0.11)');
    g.strokeStyle = grd; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, 0); g.lineTo(x, HIT_Y); g.stroke();
  }});
}}

// ── 판정 자리(리셉터) — 리듬게임의 그 자리. 여기에 맞추면 됩니다 ──
// 줄이 달라도 손가락 자리가 같으면 x 가 겹칩니다 (실제로 같은 자리니까요).
// 겹친 것을 여러 번 그리면 꺼진 것이 켜진 것을 덮으므로, 자리별로 묶어 한 번만 그립니다.
const SPOTS = (() => {{
  const m = new Map();
  NOTES.forEach(n => {{
    const k = Math.round(n.mm * 2);
    if (!m.has(k)) m.set(k, {{mm: n.mm, list: []}});
    m.get(k).list.push(n);
  }});
  return [...m.values()];
}})();

// ── 계이름 라벨 — 줄마다 하나씩, 너무 붙으면 앞의 것만 ──
const SCOL = {{}};
STRINGS.forEach(s => SCOL[s.name] = s.color);
const LABELS = (() => {{
  const by = {{}}, out = [];
  NOTES.forEach(n => (by[n.str] = by[n.str] || []).push(n));
  for (const s in by) {{
    let lastX = -999;
    //| 반복  그 줄의 음을 지판 순서로
    //| 갈래     앞 이름과 너무 붙나 ? 건너뛴다 : 라벨 하나를 놓는다
    for (const n of by[s].slice().sort((a, b) => a.mm - b.mm)) {{
      const x = Math.max(boardX(n.mm), BX0 + 10);   // 개방현은 줄 이름과 안 겹치게
      if (x - lastX < 16) continue;
      lastX = x;
      out.push({{x: x, s: s, ko: n.ko}});
    }}
  }}
  return out;
}})();

function receptors(t) {{
  SPOTS.forEach(sp => {{
    const x = boardX(sp.mm);
    const n = sp.list.find(v => t >= v.t - 0.09 && t <= v.t + v.dur) || sp.list[0];
    const live = (t >= n.t - 0.09 && t <= n.t + n.dur);
    g.save();
    if (live) {{ g.shadowColor = n.color; g.shadowBlur = 14; }}
    g.strokeStyle = live ? n.color : 'rgba(255,255,255,0.30)';
    g.fillStyle = live ? n.color + '33' : 'rgba(255,255,255,0.05)';
    g.lineWidth = live ? 2.2 : 1.2;
    g.beginPath(); g.roundRect(x - NODE_W/2, HIT_Y - 8, NODE_W, 16, NODE_R);
    g.fill(); g.stroke();
    g.restore();
  }});
}}

// ── 악보에서 지금 음표 켜기 ──
// 노드는 지판 자리로 떨어지므로, "악보의 어느 음인지"는 여기서 알려줍니다.
const INK = '#e8e5dc';
function markScore(i) {{
  if (i === marked) return;
  for (const j of [marked, i]) {{
    if (j < 0 || j >= NOTES.length) continue;
    const on = (j === i), col = on ? NOTES[j].color : INK;
    const h = document.getElementById('nh' + j),
          st = document.getElementById('ns' + j),
          kn = document.getElementById('nk' + j);
    if (h) h.setAttribute('fill', col);
    if (st) st.setAttribute('stroke', col);
    if (kn) {{      // 계이름도 같이 — 어느 음인지 글자로도 보이게
      kn.setAttribute('fill', on ? col : '{staff.MUT}');
      kn.setAttribute('font-weight', on ? 700 : 400);
      kn.setAttribute('font-size', on ? 13.5 : 12);
    }}
  }}
  if (i >= 0) {{
    cursor.setAttribute('fill', NOTES[i].color);
    cursor.setAttribute('fill-opacity', 0.16);
    cursor.setAttribute('stroke', NOTES[i].color);
    cursor.setAttribute('stroke-opacity', 0.8);
  }}
  marked = i;
}}

// ── 다음 음 안내 — 바뀔 때만 고칩니다 (매 프레임 고치면 느립니다) ──
let shown = -2, marked = -2;
function panel(i) {{
  if (i === shown) return;
  shown = i;
  // 손끝 배지 — 짚는 손가락만 빨갛게, 나머지는 어둡게
  for (const k of [1, 2, 3, 4]) {{
    const e = document.getElementById('ft' + k);
    if (e) e.querySelector('circle').setAttribute('fill', '#2f3644');
  }}
  const open0 = document.getElementById('ft0');
  if (open0) open0.style.display = 'none';
  // 브리지 — 켜야 하는 줄만 밝게
  //| 반복  네 줄마다 — 이번에 켜는 줄인지 표시
  STRINGS.forEach(s => {{
    const e = document.getElementById('bs' + s.name);
    if (!e) return;
    const c = e.querySelector('circle'), tx = e.querySelector('text');
    const on = i >= 0 && NOTES[i].str === s.name;
    c.setAttribute('fill', on ? s.color : '#0d1117');
    c.setAttribute('fill-opacity', on ? 1 : 0.62);
    c.setAttribute('stroke', on ? '#0d1117' : s.color);
    c.setAttribute('stroke-opacity', on ? 0.9 : 0.5);
    tx.setAttribute('fill', on ? '#0d1117' : s.color);
    tx.setAttribute('fill-opacity', on ? 1 : 0.6);
  }});
  if (i < 0) return;
  const n = NOTES[i];
  P.ko.textContent = n.ko;
  //| 갈래  줄을 넘나드는 악보인가 ? 어느 줄인지도 같이 : 손가락만
  P.fg.textContent = (n.finger === 0 ? '개방현' : n.finger + '번 손가락')
                   + (USED.length > 1 ? ' · ' + n.str + '현' : '');
  P.bow.textContent = (n.bow === 'down' ? '⊓ 다운보우' : '∨ 업보우');
  P.bow.style.color = n.color;
  P.bow.style.background = n.color + '22';
  P.pos.textContent = n.pos + '포지션';
  P.pos.style.color = n.pos === 1 ? '#22c55e' : '#f59e0b';
  //| 갈래  개방현인가 ? '개방' 표시를 켠다 : 그 손끝 배지를 빨갛게
  if (n.finger === 0) {{
    if (open0) open0.style.display = '';
  }} else {{
    const ft = document.getElementById('ft' + n.finger);
    if (ft) ft.querySelector('circle').setAttribute('fill', '{C['bad']}');
  }}
}}

function draw() {{
  //| 갈래  아직 시작 전인가 ? 지판만 그리고 안내를 띄운다 : 계속 그린다
  if (t0 === null) {{
    g.fillStyle = '{C['bg']}'; g.fillRect(0, 0, LW, CV);
    lanes(); board(); receptors(-99); idle(); panel(0); markScore(-1);
    requestAnimationFrame(draw);
    return;
  }}
  let t = (performance.now() - t0) / 1000;
  //| 갈래  끝까지 갔나 ? 멈춘다 (다시 ▶ 를 눌러야 시작) : 계속
  if (t > TOTAL + 0.9) {{ stop(); requestAnimationFrame(draw); return; }}
  g.fillStyle = '{C['bg']}'; g.fillRect(0, 0, LW, CV);
  lanes();
  const PPS = HIT_Y * SPEED / LEAD_BASE;      // 배속만큼 빨리 내려옵니다

  //| 갈래  카운트인 구간인가 ? 박이 넘어갈 때마다 똑 소리 : 넘어간다
  if (t < 0 && t >= -COUNT * BEAT) {{
    const b = Math.floor((t + COUNT * BEAT) / BEAT);
    if (b > clicked) {{ clicked = b; tick(b === 0); }}
  }}
  //| 갈래  시범 연주가 켜져 있나 ? 차례가 된 음을 소리 낸다 : 넘어간다
  if (DEMO && t >= 0) {{
    while (played + 1 < NOTES.length && t >= NOTES[played + 1].t - 0.02) {{
      played++; tone(NOTES[played]);
    }}
  }}

  const idx = Math.max(0, Math.min(NOTES.length - 1, Math.floor(t / BEAT)));
  cursor.setAttribute('x', (X0 + STEP * idx).toFixed(1));
  markScore(idx);
  panel(idx);

  // 떨어지는 노드 — 지판 자리에서 곧게. 판정 자리와 같은 폭·모서리입니다.
  NOTES.forEach(n => {{
    const yB = HIT_Y - (n.t - t) * PPS;
    const h = Math.max(n.dur * PPS - 5, 10), yT = yB - h;
    if (yB < -14 || yT > HIT_Y + 8) return;
    const x = boardX(n.mm);
    const live = yB >= HIT_Y - 4 && yT <= HIT_Y + 4;

    g.save(); g.beginPath(); g.rect(0, 0, LW, HIT_Y); g.clip();
    if (live) {{ g.shadowColor = n.color; g.shadowBlur = 16; }}
    g.fillStyle = n.color; g.globalAlpha = live ? 1 : 0.86;
    g.beginPath(); g.roundRect(x - NODE_W/2, yT, NODE_W, h, NODE_R); g.fill();
    g.restore();
    g.globalAlpha = 1; g.shadowBlur = 0;

    if (h > 26) {{
      if (n.slurHead) {{      // 슬러로 묶인 음은 첫 음에만 (한 활이니까)
        g.strokeStyle = 'rgba(255,255,255,0.92)'; g.lineWidth = 1.8;
        const by = yT + 11; g.beginPath();
        if (n.bow === 'down') {{
          g.moveTo(x-5, by+5); g.lineTo(x-5, by); g.lineTo(x+5, by); g.lineTo(x+5, by+5);
        }} else {{
          g.moveTo(x-5, by); g.lineTo(x, by+6); g.lineTo(x+5, by);
        }}
        g.stroke();
      }}
      g.fillStyle = '#fff'; g.font = '700 14px system-ui'; g.textAlign = 'center';
      const yc = yT + h / 2 + (USED.length > 1 ? 2 : 6);
      g.fillText(n.finger === 0 ? '○' : n.finger, x, yc);
      //| 갈래  줄을 넘나드는 악보인가 ? 어느 줄인지 작게 덧붙인다 : 손가락만
      if (USED.length > 1) {{
        g.font = '700 9px system-ui'; g.globalAlpha = 0.85;
        g.fillText(n.str, x, yc + 11); g.globalAlpha = 1;
      }}
    }}
  }});

  board();
  receptors(t);

  // 판정선에 닿은 음 → 지판의 실제 자리로 이어 줍니다 (그 음이 쓰는 줄 위에)
  NOTES.forEach(n => {{
    if (t < n.t - 0.1 || t > n.t + n.dur) return;
    const y = ROW[n.str] || ROW[ACTIVE], bx2 = boardX(n.mm);
    const fresh = Math.max(0, 1 - Math.abs(t - n.t) / 0.3);

    g.save(); g.shadowColor = n.color; g.shadowBlur = 10 + 14 * fresh;
    g.fillStyle = n.color;
    g.beginPath(); g.arc(bx2, y, 8.5 + 4 * fresh, 0, 6.284); g.fill();
    g.restore();
    g.fillStyle = '#fff'; g.font = '700 11px system-ui'; g.textAlign = 'center';
    g.fillText(n.finger === 0 ? '○' : n.finger, bx2, y + 4);
  }});

  //| 갈래  아직 시작 전인가 ? 준비·카운트인을 얹는다 : 넘어간다
  if (t < 0) countIn(t);

  requestAnimationFrame(draw);
}}
stop();          // 저절로 시작하지 않습니다 — ▶ 를 눌러야 시작
draw();
</script></body></html>"""
