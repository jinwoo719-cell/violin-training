"""
소스의 흐름 주석만 읽어 순서도를 만드는 도구.

    python3 flow.py            → 화면에 텍스트 순서도
    python3 flow.py 순서도.md   → 파일로 (텍스트 + Mermaid 플로우차트)

이 파일 자체도 같은 규약으로 주석이 달려 있습니다.

════════════════════════════════════════════════════════════════
 흐름 주석 규약  —  모든 파일에 공통
════════════════════════════════════════════════════════════════

  #| 흐름  <한 줄 요약>          모듈/함수 전체를 한 줄로.  제목이 됩니다
  #| 구역  <구역 이름>            한 파일 안을 여러 덩어리로 나눌 때
  #| 입력  <들어오는 것>          ▱ 평행사변형
  #| 단계  <하는 일>              ▭ 사각형
  #| 갈래  <질문> ? <예> : <아니오>   ◇ 마름모
  #| 반복  <무엇마다>             ▭ 반복 상자 (더 깊이 들여쓴 것이 안쪽)
  #| 호출  <함수> → <받는 것>     ▭ 다른 함수로 (화살표로 연결)
  #| 출력  <나가는 것>            ▱ 평행사변형

규칙 네 가지.

  1. **들여쓰기가 곧 계층이다.** 주석의 들여쓰기 칸 수로 안팎이 정해집니다.
  2. **`def` 안에 있으면 그 함수의 흐름이 된다.** 밖에 있으면 모듈 흐름.
  3. **`#|` 가 아닌 주석은 무시된다.** 설명용 주석은 평소처럼 `#` 로 씁니다.
  4. **설명글(따옴표 세 개) 안은 읽지 않는다.** `#| 흐름` 은 설명글 바로 **아랫줄**에 둡니다.
  5. **갈래의 두 결과는 화살표 이름표가 된다.** 흐름은 그대로 다음 단계로 이어집니다.
     정말 거기서 끝나는 길이면 `#| 출력` 을 따로 한 줄 적어 주세요.

그래서 순서도가 코드와 따로 놀 수 없습니다. 코드를 고치면 주석도 같이 고치게 되고,
`python3 flow.py` 를 다시 돌리면 문서가 갱신됩니다.
"""

import glob
import os
import re
import sys

#| 흐름  소스 읽기 → 주석 뽑기 → 계층 세우기 → 텍스트·Mermaid 로 그리기

KINDS = {                       # 종류: (텍스트 기호, Mermaid 도형 괄호)
    "입력": ("▱", "[/", "/]"),
    "단계": ("▭", "[", "]"),
    "갈래": ("◇", "{", "}"),
    "반복": ("↻", "[[", "]]"),
    "호출": ("→", "([", "])"),
    "출력": ("▱", "[\\", "\\]"),
    "구역": ("┈", "", ""),      # 한 파일 안의 구역 나누기
    "흐름": ("»", "", ""),
}

TAG = re.compile(r"^(\s*)#\|\s*(입력|단계|갈래|반복|호출|출력|구역|흐름)\s+(.*?)\s*$")
DEF = re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)")


def scan(path):
    """파일 하나 → [{함수, 종류, 글, 깊이}]"""
    #| 흐름  한 줄씩 읽으며 지금 어느 함수 안인지 기억한다
    #| 단계  파일을 줄 단위로 읽는다
    out, func, func_indent, quote = [], None, -1, None
    marks = ('"' * 3, "'" * 3)
    for raw in open(path, encoding="utf-8").read().splitlines():
        #| 갈래  설명글 안인가 ? 통째로 건너뛴다 : 계속 읽는다
        # 규약을 적어 둔 설명글까지 순서도로 뽑히면 안 됩니다
        if quote:
            if quote in raw:
                quote = None
            continue
        opened = next((q for q in marks if raw.count(q) == 1), None)
        if opened:
            quote = opened
            continue
        #| 갈래  def 줄인가 ? 지금 함수를 바꾼다 : 그대로 둔다
        d = DEF.match(raw)
        if d:
            func, func_indent = d.group(2), len(d.group(1))
            continue
        #| 갈래  #| 주석인가 ? 뽑아 담는다 : 넘어간다
        m = TAG.match(raw)
        if not m:
            # 함수가 끝났는지 확인 — 들여쓰기가 def 보다 얕은 실제 코드가 나오면 끝
            if raw.strip() and not raw.lstrip().startswith("#") \
                    and func is not None and len(raw) - len(raw.lstrip()) <= func_indent:
                func = None
            continue
        indent, kind, text = len(m.group(1)), m.group(2), m.group(3)
        out.append({"func": func, "kind": kind, "text": text,
                    "depth": indent // 4})
    #| 출력  이 파일에서 찾은 흐름 조각들
    return out


def group(items):
    """조각들을 함수별로 묶습니다. 모듈 흐름(함수 밖)은 맨 앞에."""
    #| 흐름  함수 이름을 열쇠로 삼아 순서를 지키며 모은다
    #| 단계  함수 이름별로 순서를 지켜 모은다
    order, box = [], {}
    for it in items:
        key = it["func"] or "(모듈)"
        if key not in box:
            box[key] = []
            order.append(key)
        box[key].append(it)
    return [(k, box[k]) for k in order]


def as_text(files):
    """텍스트 순서도."""
    #| 흐름  파일 → 함수 → 단계 순으로 들여써 내려간다
    out = []
    #| 반복  파일마다
    for path, items in files:
        if not items:
            continue
        out.append(f"\n📄 {os.path.basename(path)}")
        #| 반복  그 파일의 함수마다
        for name, steps in group(items):
            head = next((s for s in steps if s["kind"] == "흐름"), None)
            title = f"  ├─ {name}()" if name != "(모듈)" else "  ├─ (파일 전체)"
            out.append(title + (f"   « {head['text']}" if head else ""))
            #| 반복  그 함수의 단계마다
            for s in steps:
                if s["kind"] == "흐름":
                    continue
                #| 갈래  구역 표시인가 ? 한 줄 띄우고 제목처럼 쓴다 : 그냥 한 단계로 쓴다
                if s["kind"] == "구역":
                    out.append("  │")
                    out.append(f"  │  ┈┈ {s['text']} ┈┈")
                    continue
                sym = KINDS[s["kind"]][0]
                out.append("  │  " + "   " * s["depth"] + f"{sym} {s['text']}")
    #| 출력  사람이 바로 읽는 순서도
    return "\n".join(out)


def _esc(t):
    """Mermaid 가 못 먹는 글자를 바꿉니다."""
    return (t.replace('"', "'").replace("[", "(").replace("]", ")")
             .replace("{", "(").replace("}", ")").replace("|", "·"))


def as_mermaid(name, steps):
    """함수 하나 → Mermaid 플로우차트."""
    #| 흐름  단계를 노드로, 이어짐을 화살표로 바꾼다
    body = [s for s in steps if s["kind"] != "흐름"]
    if not body:
        return ""
    lines = ["```mermaid", "flowchart TD"]
    prev, labels = None, None
    #| 반복  단계마다 노드 하나
    for i, s in enumerate(body):
        nid = f"n{i}"
        _, lb, rb = KINDS[s["kind"]]
        #| 갈래  갈래인가 ? 두 결과를 화살표 이름표로 단다 : 상자 하나로 그린다
        # 예·아니오를 각각 상자로 만들면 '멈춘다' 에서 다음 단계로 이어지는
        # 잘못된 화살표가 생깁니다. 결과는 화살표에 적고 흐름은 하나로 둡니다.
        if s["kind"] == "갈래" and "?" in s["text"]:
            q, rest = s["text"].split("?", 1)
            yes, no = (rest.split(":", 1) + [""])[:2]
            lines.append(f'  {nid}{{"{_esc(q.strip())}"}}')
            if prev:
                lines.append(f"  {prev} --> {nid}")
            pending = (f'예: {_esc(yes.strip())}', f'아니오: {_esc(no.strip())}')
            prev, labels = nid, pending
            continue
        if s["kind"] == "구역":
            lines.append(f'  {nid}(("{_esc(s["text"])}"))')
        else:
            lines.append(f'  {nid}{lb}"{_esc(s["text"])}"{rb}')
        #| 갈래  앞이 갈래였나 ? 두 갈래를 이름표와 함께 잇는다 : 그냥 잇는다
        if prev and labels:
            for lab in labels:
                lines.append(f'  {prev} -- "{lab}" --> {nid}')
            labels = None
        elif prev:
            lines.append(f"  {prev} --> {nid}")
        prev = nid

    #| 갈래  마지막이 갈래로 끝났나 ? 두 결과를 잎으로 붙인다 : 그대로 둔다
    if labels:
        for k, lab in enumerate(labels):
            lines.append(f'  end{k}["{lab}"]')
            lines.append(f'  {prev} --> end{k}')
    lines.append("```")
    #| 출력  Mermaid 코드 블록
    return "\n".join(lines)


def build(root="."):
    """폴더 전체를 읽어 (경로, 조각들) 목록을 만듭니다."""
    #| 반복  .py 파일마다
    return [(p, scan(p)) for p in sorted(glob.glob(os.path.join(root, "*.py")))]


def main():
    #| 흐름  파일들을 읽어 텍스트를 만들고, 인자가 있으면 파일로 저장한다
    #| 입력  같은 폴더의 .py 파일들
    files = build(os.path.dirname(os.path.abspath(__file__)))
    text = as_text(files)

    #| 갈래  저장할 파일 이름을 받았나 ? 마크다운으로 쓴다 : 화면에 보여준다
    if len(sys.argv) > 1:
        md = ["# 순서도 (자동 생성)",
              "",
              "`python3 flow.py 순서도.md` 로 소스의 `#|` 주석만 읽어 만들었습니다.",
              "코드를 고치면 다시 돌려 주세요.",
              "", "---", "", "## 텍스트 순서도", "", "```text", text, "```", ""]
        #| 반복  파일마다 · 함수마다 Mermaid 플로우차트
        for path, items in files:
            if not items:
                continue
            md += ["", "---", "", f"## {os.path.basename(path)}"]
            for name, steps in group(items):
                head = next((s for s in steps if s["kind"] == "흐름"), None)
                md += ["", f"### {name}()" if name != "(모듈)" else "### 파일 전체"]
                if head:
                    md.append(f"> {head['text']}")
                md += ["", as_mermaid(name, steps)]
        open(sys.argv[1], "w", encoding="utf-8").write("\n".join(md))
        print(f"{sys.argv[1]} 에 썼습니다.")
    else:
        print(text)
    #| 출력  텍스트 순서도 또는 마크다운 파일


if __name__ == "__main__":
    main()
