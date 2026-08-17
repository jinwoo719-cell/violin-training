"""
주석 → 플로우차트 HTML (그림으로 구워서).

    python3 make_flowchart.py 플로우차트.html

flow.py 가 만든 Mermaid 코드를 **미리 그림(SVG)으로 구워** HTML 안에 넣습니다.
그래서 결과 파일은

  · 인터넷 없이 열립니다 (Mermaid 라이브러리를 같이 넣지 않아도 됩니다)
  · 그대로 인쇄·PDF 저장이 됩니다
  · 용량이 작습니다 (그림만 남고 라이브러리는 안 남습니다)

굽는 데에만 노드(mermaid)와 크로미움(playwright)이 필요합니다.
그 둘이 없는 컴퓨터에서는 `python3 flow.py 순서도.md` 를 쓰세요 —
같은 내용이 마크다운(텍스트 + Mermaid 코드)으로 나옵니다.
"""

import glob
import html
import json
import os
import sys
import tempfile

import flow

#| 흐름  주석 → Mermaid 코드 → (브라우저에서 그림으로) → 자립 HTML

# 화면·모듈이 어떻게 이어지는지 한 장으로. 이건 손으로 적습니다 —
# 파일 하나를 보고는 알 수 없는, 전체 그림이기 때문입니다.
SYSTEM = """flowchart LR
  U(("사용자")) --> A["app.py — 화면 전환 · 상태"]
  A --> S1["화면① 연습 가이드<br/>screens.py"]
  A --> S3["화면③ 내 악보<br/>sheet.py"]
  A --> S2["화면② 분석 리포트<br/>report.py"]
  S3 -- "음 목록" --> S1
  S1 -- "녹음 WAV" --> AN(["analyze.py — YIN 음정 검출"])
  AN -- "음별 결과" --> S2
  S2 -- "교정 드릴" --> S1
  M["music.py<br/>음계·조표·포지션"] --> S1
  M --> S2
  M --> S3
  ST["staff.py<br/>악보 한 줄"] --> S1
  ST --> S2
  ST --> S3
  IN["instrument.py<br/>줄·사진·손·브리지"] --> S1
  GL["glyphs.py<br/>𝄞 ♯ ♭ ♮"] --> ST
  TH["theme.py<br/>색·글꼴"] --> A
"""

DATA_FLOW = """flowchart TD
  I1[/"음계 고르기"/] --> B
  I2[/"내가 적은 글"/] --> B
  I3[/"악보 사진"/] --> B
  I4[/"MusicXML"/] --> B
  B["음 목록 만들기<br/>music.build_notes · sheet.build"]
  B --> N["음 하나에 다 들어 있음<br/>높이·mm·포지션·손가락·활·시각"]
  N --> G["화면① 가이드"]
  N --> R["화면② 리포트"]
  N --> AZ["분석"]
  G -- "연주" --> W[/"녹음 WAV"/]
  W --> AZ
  AZ --> RES["음별 (평균 · 편차 · 박자)"]
  RES --> R
  R --> D{"고칠 곳이 있나"}
  D -- "예" --> DR["교정 드릴 음 목록"]
  DR --> G
  D -- "아니오" --> E["다음 연습"]
"""


# 문서에 실릴 순서. 알파벳순이 아니라 **읽는 순서**입니다.
ORDER = ["app.py", "screens.py", "sheet.py", "report.py", "analyze.py",
         "music.py", "staff.py", "instrument.py", "glyphs.py", "theme.py",
         "flow.py", "features.py", "excel_out.py", "make_flowchart.py"]


def split_sections(steps):
    """긴 흐름은 `#| 구역` 으로 나눕니다.

    app.py 처럼 화면이 여럿인 파일은 한 장으로 그리면 세로 7000px 짜리
    괴물이 나옵니다. 구역이 있으면 구역마다 한 장으로 나눠 그립니다.
    """
    #| 흐름  구역 표시를 경계로 삼아 단계들을 덩어리로 나눈다
    #| 반복  단계마다
    #| 갈래     구역 표시인가 ? 지금까지를 한 덩어리로 끊는다 : 지금 덩어리에 담는다
    #| 출력  [(구역 이름, 단계들)]
    chunks, cur, name = [], [], None
    for s in steps:
        if s["kind"] == "구역":
            if cur:
                chunks.append((name, cur))
            cur, name = [], s["text"]
            continue
        if s["kind"] == "흐름":
            continue
        cur.append(s)
    if cur:
        chunks.append((name, cur))
    return chunks


SPLIT_OVER = 14        # 이보다 길고 구역이 있으면 나눕니다


def diagrams(root=None):
    """(제목, 부제, Mermaid 코드) 목록."""
    #| 흐름  전체 그림 두 장 + 파일마다 · 함수마다 한 장씩
    #| 입력  소스 폴더
    #| 단계  손으로 적은 전체 그림 두 장을 맨 앞에 둔다
    #| 반복  .py 파일마다
        #| 반복     함수마다
        #| 호출        flow.as_mermaid → Mermaid 코드
    #| 출력  그림 목록
    root = root or os.path.dirname(os.path.abspath(__file__))
    out = [("시스템 전체", "화면과 모듈이 어떻게 이어지는가", SYSTEM),
           ("데이터 흐름", "무엇이 들어와서 무엇으로 나가는가", DATA_FLOW)]

    files = flow.build(root)
    files.sort(key=lambda f: (ORDER.index(os.path.basename(f[0]))
                              if os.path.basename(f[0]) in ORDER else 99,
                              os.path.basename(f[0])))
    for path, items in files:
        if not items:
            continue
        name = os.path.basename(path)
        for fn, steps in flow.group(items):
            head = next((s for s in steps if s["kind"] == "흐름"), None)
            why = head["text"] if head else ""
            label = ("파일 전체" if fn == "(모듈)"
                     else fn if fn.endswith(")") else fn + "()")
            chunks = split_sections(steps)

            #| 갈래  길고 구역이 있나 ? 구역마다 한 장씩 : 통째로 한 장
            if len(steps) > SPLIT_OVER and len([c for c in chunks if c[0]]) > 1:
                for sec, part in chunks:
                    code = flow.as_mermaid(fn, part)
                    if not code:
                        continue
                    code = code.replace("```mermaid\n", "").replace("\n```", "")
                    tail = f" · {sec}" if sec else " · 시작"
                    out.append((f"{name} · {label}{tail}", why, code))
                continue

            code = flow.as_mermaid(fn, steps)
            if not code:
                continue
            code = code.replace("```mermaid\n", "").replace("\n```", "")
            out.append((f"{name} · {label}", why, code))
    return out


def render(codes):
    """Mermaid 코드 → SVG 문자열들 (브라우저에서 굽습니다)."""
    #| 흐름  로컬 크로미움에 mermaid 를 물려 한 장씩 SVG 로 굽는다
    #| 입력  Mermaid 코드 목록
    #| 갈래  mermaid.min.js 를 찾았나 ? 굽는다 : 어디에 두라고 알린다
    #| 출력  SVG 문자열 목록 (실패한 것은 빈 문자열)
    lib = next((p for p in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "node_modules/mermaid/dist/mermaid.min.js"),
        "/tmp/node_modules/mermaid/dist/mermaid.min.js",
    ) + tuple(glob.glob(os.path.expanduser(
        "~/**/node_modules/mermaid/dist/mermaid.min.js"), recursive=True))
        if os.path.exists(p)), None)
    if not lib:
        raise SystemExit(
            "mermaid 를 못 찾았습니다.  npm install mermaid  를 먼저 하세요.\n"
            "(굽지 않고 텍스트로만 보려면  python3 flow.py 순서도.md)")

    from playwright.sync_api import sync_playwright

    page_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script>{open(lib, encoding='utf-8').read()}</script></head>
<body><div id="out"></div><script>
window.CODES = {json.dumps(codes, ensure_ascii=False)};
mermaid.initialize({{startOnLoad:false, theme:'dark', securityLevel:'loose',
  htmlLabels:false,
  fontFamily:"'Malgun Gothic',system-ui,sans-serif",
  themeVariables:{{darkMode:true, background:'#0d1117',
    primaryColor:'#1c2230', primaryTextColor:'#e6e9ef',
    primaryBorderColor:'#d6a85f', lineColor:'#9ba4b0',
    secondaryColor:'#161b26', tertiaryColor:'#161b26'}},
  flowchart:{{curve:'basis', nodeSpacing:34, rankSpacing:44,
    htmlLabels:false, useMaxWidth:true}}}});
window.SVGS = [];
window.done = (async () => {{
  for (let i = 0; i < CODES.length; i++) {{
    try {{
      const r = await mermaid.render('m' + i, CODES[i]);
      SVGS.push(r.svg);
    }} catch (e) {{ SVGS.push(''); }}
  }}
  return true;
}})();
</script></body></html>"""

    tmp = os.path.join(tempfile.gettempdir(), "_mermaid_build.html")
    open(tmp, "w", encoding="utf-8").write(page_html)

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        pg.goto("file://" + tmp, wait_until="load")
        pg.wait_for_function("window.SVGS && window.SVGS.length === window.CODES.length",
                             timeout=180000)
        svgs = pg.evaluate("window.SVGS")
        b.close()
    return svgs


CSS = """
:root{--bg:#0d1117;--panel:#161b26;--line:#252c3b;--ink:#e6e9ef;
  --ink2:#b3b8bf;--muted:#9ba4b0;--accent:#d6a85f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:'Malgun Gothic',system-ui,-apple-system,sans-serif;
  display:flex}
#nav{width:270px;flex:none;height:100vh;overflow:auto;position:sticky;top:0;
  background:var(--panel);border-right:1px solid var(--line);padding:16px 10px}
#nav h1{font-size:15px;margin:0 6px 4px;color:var(--ink)}
#nav .sub{font-size:11px;color:var(--muted);margin:0 6px 14px;line-height:1.6}
#nav a{display:block;padding:5px 8px;border-radius:7px;color:var(--ink2);
  text-decoration:none;font-size:12px;line-height:1.35}
#nav a:hover{background:#1c2230;color:var(--ink)}
#nav a.big{font-weight:700;color:var(--ink);margin-top:10px}
#nav .grp{font-size:10.5px;color:var(--muted);margin:14px 8px 4px;
  text-transform:none;letter-spacing:.02em}
main{flex:1;padding:26px 30px 80px;max-width:1180px}
section{margin-bottom:34px;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:16px 18px 10px}
h2{font-size:15.5px;margin:0 0 3px}
.why{font-size:12px;color:var(--muted);margin:0 0 12px}
.box{overflow:auto;background:#0d1117;border-radius:10px;padding:10px}
svg{max-width:100%;height:auto}
.top{font-size:22px;margin:0 0 4px}
.lead{color:var(--ink2);font-size:13px;line-height:1.9;margin:0 0 22px}
code{background:#1c2230;padding:1px 5px;border-radius:4px;font-size:12px}
@media print{
  body{display:block;background:#fff;color:#111}
  #nav{display:none}
  section{break-inside:avoid;page-break-inside:avoid;background:#fff;
    border:1px solid #ccc}
  .box{background:#fff}
}
"""


def _hoist_styles(svgs):
    """그림마다 든 <style> 을 문서 위로 한 번만 모읍니다.

    Mermaid 의 선택자는 `#m12 .node` 처럼 그림 id 로 갈려 있어서,
    한곳에 모아도 서로 섞이지 않습니다. 파일이 눈에 띄게 가벼워집니다.
    """
    #| 흐름  SVG 안의 <style> 을 떼어 모으고, 군더더기 속성도 지운다
    #| 반복  그림마다
    #| 단계     Mermaid 가 붙여 둔 data-points(base64) 같은 내부용 속성을 뺀다
    #| 출력  (스타일 한 덩어리, 가벼워진 SVG 목록)
    import re
    pat = re.compile(r"<style>(.*?)</style>", re.S)
    # Mermaid 는 선마다 좌표 배열을 base64 로 붙여 둡니다.
    # 그리는 데는 안 쓰이는데 파일의 대부분을 차지합니다.
    junk = re.compile(r'\s(?:data-(?:points|id|et|edge|look|node)|role|'
                      r'aria-roledescription|aria-labelledby)="[^"]*"')
    # 곡선 좌표가 소수점 15자리까지 적혀 있습니다. 화면에서는 1자리면 충분합니다.
    dpat = re.compile(r'(\sd=")([^"]*)(")')
    num = re.compile(r"-?\d+\.\d+")

    def _round(m):
        body = num.sub(lambda k: f"{float(k.group()):.1f}", m.group(2))
        return m.group(1) + body + m.group(3)

    css, out = [], []
    for s in svgs:
        css += pat.findall(s)
        s = junk.sub("", pat.sub("", s))
        out.append(dpat.sub(_round, s))
    return "\n".join(css), out


def build_html(items, svgs):
    """제목 + 그림 → 자립 HTML."""
    #| 흐름  왼쪽 목차 + 오른쪽 그림들로 한 장짜리 문서를 만든다
    #| 반복  그림마다 목차 항목과 본문 한 칸
    #| 출력  HTML 문자열
    css, svgs = _hoist_styles(svgs)
    nav, body, last = [], [], None
    for i, ((title, why, _), svg) in enumerate(zip(items, svgs)):
        anchor = f"d{i}"
        mod = title.split(" · ")[0]
        #| 갈래  파일이 바뀌었나 ? 목차에 파일 이름을 끼운다 : 넘어간다
        if i >= 2 and mod != last:
            nav.append(f'<div class="grp">📄 {html.escape(mod)}</div>')
            last = mod
        label = title if i < 2 else title.split(" · ", 1)[-1]
        cls = ' class="big"' if i < 2 else ""
        nav.append(f'<a href="#{anchor}"{cls}>{html.escape(label)}</a>')
        body.append(
            f'<section id="{anchor}"><h2>{html.escape(title)}</h2>'
            f'<p class="why">{html.escape(why)}</p>'
            f'<div class="box">{svg or "<i>그리지 못했습니다</i>"}</div></section>')

    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>바이올린 연습 도우미 — 플로우차트</title>
<style>{CSS}</style>
<style>{css}</style></head><body>
<nav id="nav"><h1>🎻 플로우차트</h1>
<p class="sub">소스의 <code>#|</code> 흐름 주석에서 자동으로 만들었습니다.<br>
다시 만들기: <code>python3 make_flowchart.py 플로우차트.html</code></p>
{''.join(nav)}</nav>
<main>
<h1 class="top">바이올린 연습 도우미 — 플로우차트</h1>
<p class="lead">
파이썬의 <code>#|</code> 주석과 화면 스크립트의 <code>//|</code> 주석만 읽어
자동으로 만든 그림입니다. 그림을 따로 그리지 않으므로
<b>코드와 문서가 어긋날 수 없습니다.</b><br>
같은 주석에서 기능 목록(<code>기능리스트.xlsx</code>)도 나옵니다.
</p>
{''.join(body)}</main></body></html>"""


def main():
    #| 흐름  그림 목록을 모아 굽고, 한 장짜리 HTML 로 저장한다
    #| 입력  저장할 파일 이름
    #| 호출  diagrams → (제목, 부제, Mermaid 코드) 목록
    #| 호출  render → SVG 목록
    #| 호출  build_html → 자립 HTML
    #| 출력  플로우차트 HTML 파일
    out = sys.argv[1] if len(sys.argv) > 1 else "플로우차트.html"
    items = diagrams()
    print(f"그림 {len(items)}장 굽는 중…")
    svgs = render([c for _, _, c in items])
    open(out, "w", encoding="utf-8").write(build_html(items, svgs))
    ok = sum(1 for s in svgs if s)
    print(f"{out} 에 썼습니다. ({ok}/{len(svgs)}장)")


if __name__ == "__main__":
    main()
