"""
아키텍처를 **주석과 import 에서** 뽑아내는 도구.

    python3 arch.py                          → 화면에 텍스트 아키텍처
    python3 arch.py 아키텍처.md               → 마크다운 (텍스트 + Mermaid)
    python3 arch.py 아키텍처.md 아키텍처.html  → + 그림으로 구운 HTML

flow.py · features.py 와 **같은 원본**을 읽습니다.

    소스의 #| 주석 ──┬─→ flow.py     → 순서도 · 플로우차트   (한 함수 안에서 무슨 순서로)
                     ├─→ features.py → 기능 목록 (엑셀)      (무엇을 할 수 있나)
                     └─→ arch.py     → 아키텍처              (누가 누구를 쓰나)

셋이 보는 층이 다릅니다.

    순서도    함수 **안**   — 단계 · 갈래 · 반복
    기능목록  함수 **하나** — 이름 · 입출력 · 분기 수
    아키텍처  모듈 **사이** — 의존 · 호출 · 계층 · 바깥 경계

아키텍처는 두 군데서 읽습니다.

  ① `import` 문        — 진짜 의존입니다. 거짓말을 할 수 없습니다.
  ② `#| 호출 f → r` 태그 — **의도된** 호출입니다. 사람이 적은 것이라
                          "왜 부르는지(→ 받는 것)"까지 담깁니다.

①만 보면 관계는 맞지만 뜻을 모르고, ②만 보면 뜻은 알지만 빠뜨린 것을
못 잡습니다. 그래서 둘을 겹쳐 보고 **어긋나면 알려 줍니다.**
"""

import ast
import os
import re
import sys
from collections import defaultdict

import features
import flow

#| 흐름  소스 읽기 → 의존·호출 모으기 → 계층 세우기 → 텍스트·Mermaid 로 그리기

# ══════════════════════════════════════════════════════════════
#  1. 바깥과 닿는 곳 — 여기만 손으로 적습니다
# ══════════════════════════════════════════════════════════════
# 아키텍처에서 가장 중요한 건 "어디가 바깥과 닿나"입니다.
# 바깥에 닿는 곳이 곧 **느려지는 곳 · 실패하는 곳 · 시험하기 어려운 곳**입니다.
BOUNDARY = {
    "streamlit":            ("화면",   "사용자에게 보이는 것 · 위젯"),
    "streamlit.components": ("화면",   "iframe 으로 넣는 우리 HTML"),
    "urllib":               ("네트워크", "Gemini 악보 인식 (바깥 서비스)"),
    "wave":                 ("파일",   "녹음 WAV 읽고 쓰기"),
    "base64":               ("파일",   "사진·소리를 글자로 실어 나르기"),
    "numpy":                ("계산",   "음정 검출 (무거운 계산)"),
    "xml.etree":            ("파일",   "MusicXML 읽기"),
}

# 계층 — 낮은 층은 높은 층을 몰라야 합니다. 어기면 아래에서 잡아냅니다.
LAYER_NAME = {
    0: "바탕 (아무것도 안 씀)",
    1: "재료",
    2: "그리기",
    3: "화면",
    4: "앱",
}

# 앱과 **개발 도구**는 따로 세웁니다.
# 한 사다리에 같이 올리면 flow.py 가 app.py 보다 위에 오는 이상한 그림이 됩니다.
# 둘은 층이 아니라 **다른 세계**입니다 — 도구는 앱을 안 쓰고, 앱은 도구를 안 씁니다.
def side(mod, roles):
    """이 모듈이 앱 쪽인가 도구 쪽인가."""
    #| 갈래  「개발 도구」로 적혀 있나 ? 도구 : 앱
    return "도구" if roles.get(mod + ".py", ("", ""))[0] == "개발 도구" else "앱"


# ══════════════════════════════════════════════════════════════
#  2. 소스에서 읽기
# ══════════════════════════════════════════════════════════════
CALL = re.compile(r"^([\w.]+)\s*(?:→|->)\s*(.*)$")


def modules(root):
    """이 폴더의 .py 파일 이름들 (확장자 뺀 것)."""
    #| 흐름  폴더의 파이썬 파일 이름을 모은다
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p, _ in flow.build(root))


def read(root=None):
    """소스 전체 → 모듈마다 {의존, 호출, 함수, 바깥, 흐름 한 줄}.

    import 는 ast 로, 호출은 `#| 호출` 태그로 읽습니다.
    """
    #| 흐름  파일마다 import 와 #| 호출 을 모아 모듈 정보를 만든다
    #| 입력  소스 폴더
    #| 반복  .py 파일마다
    #| 호출     ast.parse → import 문과 함수 이름
    #| 호출     flow.scan → 그 파일의 #| 주석들
    #| 단계     import 중 우리 모듈인 것만 남긴다 (표준 라이브러리는 「바깥」으로)
    #| 반복     #| 호출 태그마다 — 어느 모듈의 함수인지 찾는다
    #| 출력  {모듈: 정보} · 함수가 어느 모듈에 있는지 표
    root = root or os.path.dirname(os.path.abspath(__file__))
    ours = set(modules(root))
    files = flow.build(root)

    # ① 함수가 어느 모듈에 있는지 먼저 만들어 둡니다 (호출을 풀어야 하니까)
    owner = {}
    for path, _ in files:
        mod = os.path.splitext(os.path.basename(path))[0]
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                owner.setdefault(n.name, mod)

    info = {}
    for path, items in files:
        mod = os.path.splitext(os.path.basename(path))[0]
        src = open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        deps, outside = set(), set()
        #| 반복  import 문마다
        for n in ast.walk(tree):
            names = []
            if isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                names = [n.module]
            for name in names:
                head = name.split(".")[0]
                #| 갈래  우리 모듈인가 ? 의존으로 : 바깥으로
                if head in ours and head != mod:
                    deps.add(head)
                elif head not in ours:
                    hit = next((k for k in BOUNDARY if name.startswith(k)), None)
                    if hit:
                        outside.add(hit)

        # ② #| 호출 태그 — 누구를, 무엇을 받으려고
        calls = []
        for it in items:
            if it["kind"] != "호출":
                continue
            m = CALL.match(it["text"])
            if not m:
                continue
            target, gets = m.group(1), m.group(2).strip()
            #| 갈래  모듈 이름이 붙어 있나 ? 그대로 : 함수 이름으로 찾아본다
            if "." in target:
                to_mod, fn = target.split(".", 1)
            else:
                fn, to_mod = target, owner.get(target, mod)
            calls.append({"to": to_mod if to_mod in ours else "(바깥)",
                          "fn": fn, "gets": gets, "at": it["func"]})

        head = next((i["text"] for i in items
                     if i["kind"] == "흐름" and i["func"] == "(모듈)"), "")
        funcs = [n.name for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        info[mod] = {"deps": deps, "outside": outside, "calls": calls,
                     "funcs": funcs, "head": head,
                     "branches": sum(1 for i in items if i["kind"] == "갈래"),
                     "lines": len(src.splitlines())}
    return info, owner


# ══════════════════════════════════════════════════════════════
#  3. 계층 세우기
# ══════════════════════════════════════════════════════════════
def layers(info, only=None):
    """의존 그래프 → 모듈마다 층 번호.

    아무것도 안 쓰는 모듈이 0층, 그 위를 쓰는 것이 1층… 이렇게 쌓습니다.
    **층은 사람이 정하는 게 아니라 import 가 정합니다.**
    """
    #| 흐름  아무것도 안 쓰는 것부터 층을 매긴다
    #| 입력  모듈 정보 · (볼 모듈만 추린 것)
    #| 반복  더 이상 층이 안 바뀔 때까지
    #| 갈래     이 모듈이 쓰는 것들의 층을 다 아나 ? 그 최댓값+1 : 다음 바퀴로
    #| 갈래  끝까지 못 정한 게 있나 ? 사이클이다 — 맨 위층으로 몰아 둔다 : 넘어간다
    #| 출력  {모듈: 층 번호}
    pool = set(only) if only else set(info)
    lv, left = {}, set(pool)
    for _ in range(len(pool) + 2):
        for m in sorted(left):
            d = info[m]["deps"] & pool
            if all(x in lv for x in d):
                lv[m] = max((lv[x] for x in d), default=-1) + 1
        left -= set(lv)
        if not left:
            break
    for m in left:                      # 사이클에 걸린 것들
        lv[m] = max(lv.values(), default=0) + 1
    return lv


def split(info, roles):
    """앱 쪽 · 도구 쪽으로 나누고 각각 층을 세웁니다."""
    #| 흐름  앱과 도구를 갈라 각각 사다리를 세운다
    #| 호출  side → 이 모듈이 어느 쪽인지
    #| 호출  layers → 그 쪽 안에서의 층 번호
    #| 출력  {"앱": {모듈: 층}, "도구": {모듈: 층}}
    g = {"앱": [], "도구": []}
    for m in info:
        g[side(m, roles)].append(m)
    return {k: layers(info, v) for k, v in g.items() if v}


def cycles(info):
    """서로 물고 있는 의존 — 아키텍처에서 가장 먼저 잡아야 할 냄새."""
    #| 흐름  A 가 B 를 쓰고 B 가 A 를 쓰는 짝을 찾는다
    #| 반복  모듈 쌍마다
    #| 출력  (A, B) 목록
    out = []
    for a in sorted(info):
        for b in sorted(info[a]["deps"]):
            if b in info and a in info[b]["deps"] and (b, a) not in out:
                out.append((a, b))
    return out


def violations(info, lv):
    """계층 위반 — 아래층이 위층을 쓰는 곳."""
    #| 흐름  자기보다 높은 층을 쓰는 곳을 찾는다
    #| 반복  모듈마다 · 그 모듈이 쓰는 것마다
    #| 갈래     쓰는 쪽이 더 낮은 층인가 ? 정상 : 위반으로 담는다
    #| 출력  (쓰는 쪽, 쓰이는 쪽) 목록
    return [(a, b) for a in sorted(info) for b in sorted(info[a]["deps"])
            if b in lv and lv[b] >= lv[a]]


def call_edges(info):
    """모듈 → 모듈 호출 횟수와, 무엇을 받으려고 부르는지."""
    #| 흐름  #| 호출 태그를 모듈 단위로 접는다
    #| 반복  모듈마다 · 그 안의 호출마다
    #| 출력  {(부르는 쪽, 불리는 쪽): [받는 것들]}
    edge = defaultdict(list)
    for m, d in info.items():
        for c in d["calls"]:
            if c["to"] != m and c["gets"]:
                edge[(m, c["to"])].append(c["gets"])
    return edge


# ══════════════════════════════════════════════════════════════
#  4. 그리기 — 텍스트
# ══════════════════════════════════════════════════════════════
def as_text(info, groups, roles):
    """화면에 그대로 뿌릴 수 있는 텍스트 아키텍처."""
    #| 흐름  앱·도구를 나누고, 층별로 모듈을 늘어놓는다
    #| 반복  쪽(앱·도구)마다 · 층마다 · 그 층의 모듈마다
    #| 단계     쓰는 것 · 쓰이는 곳 · 바깥 · 크기를 한 줄씩
    #| 호출  cycles · violations → 냄새나는 곳
    #| 출력  여러 줄 문자열
    used_by = defaultdict(set)
    for m, d in info.items():
        for x in d["deps"]:
            used_by[x].add(m)

    out = ["═" * 68, " 아키텍처 — import 와 #| 호출 에서 뽑았습니다", "═" * 68]
    for gname, lv in groups.items():
        out += ["", f"▣ {gname}" + ("  (앱은 도구를 모릅니다)" if gname == "앱"
                                    else "  (도구는 앱을 안 씁니다 — 주석만 읽습니다)"), ""]
        for L in sorted(set(lv.values())):
            name = LAYER_NAME.get(L, f"{L}층")
            out.append(f"┌─ {L}층 · {name} " + "─" * max(0, 46 - len(name)))
            for m in sorted(k for k, v in lv.items() if v == L):
                d = info[m]
                area, role = roles.get(m + ".py", ("", ""))
                out.append(f"│  ■ {m}.py   {area}")
                if role:
                    out.append(f"│      {role}")
                if d["deps"]:
                    out.append(f"│      쓰는 것    {' · '.join(sorted(d['deps']))}")
                if used_by[m]:
                    out.append(f"│      쓰이는 곳  {' · '.join(sorted(used_by[m]))}")
                if d["outside"]:
                    tags = " · ".join(f"{BOUNDARY[o][0]}({o})"
                                      for o in sorted(d["outside"]))
                    out.append(f"│      바깥       {tags}")
                out.append(f"│      함수 {len(d['funcs'])}개 · 분기 {d['branches']}개 "
                           f"· {d['lines']}줄")
            out.append("└" + "─" * 60)

    lv_all = {m: L for g in groups.values() for m, L in g.items()}
    cyc, vio = cycles(info), violations(info, lv_all)
    out.append("")
    out.append("─" * 68)
    out.append(f" 서로 물고 있는 의존 : {len(cyc)}개" +
               ("" if not cyc else "  → " + ", ".join(f"{a}↔{b}" for a, b in cyc)))
    out.append(f" 계층 위반           : {len(vio)}개" +
               ("" if not vio else "  → " + ", ".join(f"{a}→{b}" for a, b in vio)))
    out.append("─" * 68)
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════
#  5. 그리기 — Mermaid
# ══════════════════════════════════════════════════════════════
def _id(m):
    return m.replace(".", "_")


def mermaid_layers(info, lv, roles, title=""):
    """계층도 — 층마다 상자, 화살표는 import 방향."""
    #| 흐름  층을 subgraph 로 묶고 import 를 화살표로 잇는다
    #| 입력  모듈 정보 · 층 번호 · 역할표
    #| 반복  층마다 (위층부터) · 그 층의 모듈마다
    #| 반복  모듈마다 — 쓰는 것으로 화살표
    #| 출력  Mermaid 코드
    out = ["```mermaid", "graph TD"]
    for L in sorted(set(lv.values()), reverse=True):
        out.append(f'  subgraph L{L}["{L}층 · {LAYER_NAME.get(L, str(L) + "층")}"]')
        for m in sorted(k for k, v in lv.items() if v == L):
            area = roles.get(m + ".py", ("", ""))[0]
            label = f"{m}.py<br/>{area}" if area else f"{m}.py"
            out.append(f'    {_id(m)}["{label}"]')
        out.append("  end")
    for m in sorted(lv):
        for d in sorted(info[m]["deps"]):
            if d in lv:
                out.append(f"  {_id(m)} --> {_id(d)}")
    out.append("```")
    return "\n".join(out)


def mermaid_calls(info):
    """호출 지도 — 화살표에 **무엇을 받으려고** 부르는지 적습니다."""
    #| 흐름  #| 호출 태그를 모듈 사이 화살표로 그린다
    #| 반복  화살표마다 — 받는 것 두 개까지 이름표로
    #| 출력  Mermaid 코드
    edge = call_edges(info)
    out = ["```mermaid", "graph LR"]
    seen = set()
    for (a, b), gets in sorted(edge.items()):
        if b == "(바깥)" or b not in info:
            continue
        for m in (a, b):
            if m not in seen:
                out.append(f'  {_id(m)}["{m}.py"]')
                seen.add(m)
        lab = " · ".join(dict.fromkeys(gets))[:38]
        n = len(gets)
        out.append(f'  {_id(a)} -- "{lab}{"…" if n > 2 else ""} ({n})" --> {_id(b)}')
    out.append("```")
    return "\n".join(out)


def mermaid_boundary(info):
    """바깥과 닿는 곳 — 느려지고 실패하는 자리."""
    #| 흐름  바깥에 닿는 모듈만 골라 무엇에 닿는지 잇는다
    #| 반복  모듈마다 · 닿는 바깥마다
    #| 출력  Mermaid 코드
    out = ["```mermaid", "graph LR"]
    kinds = {}
    for m, d in sorted(info.items()):
        for o in sorted(d["outside"]):
            kind, why = BOUNDARY[o]
            kid = "K_" + _id(kind)
            if kind not in kinds:
                out.append(f'  {kid}(["{kind}"])')
                kinds[kind] = True
            out.append(f'  {_id(m)}["{m}.py"] -- "{o}" --> {kid}')
    out.append("```")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════
#  6. 내보내기
# ══════════════════════════════════════════════════════════════
def as_markdown(info, groups, roles):
    """텍스트 + 그림 셋 + 모듈 표를 한 문서로."""
    #| 흐름  텍스트 아키텍처 · 계층도 · 호출 지도 · 경계도 · 모듈 표를 잇는다
    #| 호출  as_text → 텍스트 아키텍처
    #| 호출  mermaid_layers · mermaid_calls · mermaid_boundary → 그림 셋
    #| 반복  모듈마다 표 한 줄
    #| 출력  마크다운 문자열
    used_by = defaultdict(set)
    for m, d in info.items():
        for x in d["deps"]:
            used_by[x].add(m)
    lv = {m: L for g in groups.values() for m, L in g.items()}
    cyc, vio = cycles(info), violations(info, lv)
    app = groups.get("앱", {})

    md = [
        "# 아키텍처 (자동 생성)", "",
        "`python3 arch.py 아키텍처.md` 로 만들었습니다. "
        "**소스의 `import` 문과 `#| 호출` 주석만** 읽었습니다 — 손으로 그린 그림이 아닙니다.",
        "코드를 고치면 다시 돌려 주세요.", "",
        "| | 보는 층 | 도구 |", "|---|---|---|",
        "| 순서도 | 함수 **안** — 단계·갈래·반복 | `flow.py` |",
        "| 기능목록 | 함수 **하나** — 이름·입출력·분기 수 | `features.py` |",
        "| **아키텍처** | 모듈 **사이** — 의존·호출·계층·경계 | `arch.py` |",
        "", "---", "",
        "## 한눈에", "",
        f"- 모듈 **{len(info)}개** · 층 **{len(set(lv.values()))}겹**",
        f"- 함수 **{sum(len(d['funcs']) for d in info.values())}개** · "
        f"분기 **{sum(d['branches'] for d in info.values())}개**",
        f"- 서로 물고 있는 의존 **{len(cyc)}개**" +
        ("" if not cyc else " — " + ", ".join(f"`{a}`↔`{b}`" for a, b in cyc)),
        f"- 계층 위반 **{len(vio)}개**" +
        ("" if not vio else " — " + ", ".join(f"`{a}`→`{b}`" for a, b in vio)),
        "", "---", "",
        "## ① 계층도 — 누가 누구 위에 서 있나", "",
        "화살표는 **쓰는 쪽 → 쓰이는 쪽**입니다. 아래층은 위층을 모릅니다.",
        "그래서 `music.py` 만 따로 떼어 다른 앱에 붙일 수 있고, "
        "`app.py` 는 아무도 안 씁니다 — 맨 위라서요.",
        "",
        "**층은 사람이 정한 게 아니라 `import` 가 정합니다.** 이 그림은 매번 "
        "소스에서 다시 계산됩니다.", "",
        mermaid_layers(info, app, roles), "",
        "### 개발 도구는 따로 섭니다", "",
        "도구는 앱을 **안 씁니다** — `#|` 주석만 읽습니다. 그래서 앱을 통째로 "
        "지워도 도구는 돌고, 도구를 지워도 앱은 돕니다. 한 사다리에 같이 올리면 "
        "`flow.py` 가 `app.py` 보다 위에 오는 이상한 그림이 됩니다.", "",
        mermaid_layers(info, groups.get("도구", {}), roles), "",
        "---", "",
        "## ② 호출 지도 — 무엇을 받으려고 부르나", "",
        "`#| 호출 f → r` 주석에서 뽑았습니다. 화살표 이름표가 **받는 것**이고, "
        "괄호 안 숫자는 그렇게 부르는 자리의 개수입니다.",
        "import 은 \"쓸 수 있다\"는 뜻이고, 이 그림은 \"실제로 무엇을 얻으려고 "
        "부르는가\"입니다.", "",
        mermaid_calls(info), "",
        "---", "",
        "## ③ 바깥과 닿는 곳 — 느려지고 실패하는 자리", "",
        "아키텍처에서 제일 중요한 그림입니다. 여기 있는 곳만이 "
        "**네트워크·파일·사용자** 때문에 실패합니다. 나머지는 전부 계산이라 "
        "같은 입력에 같은 답이 나옵니다 — 그래서 시험하기 쉽습니다.", "",
        mermaid_boundary(info), "",
        "---", "",
        "## ④ 모듈 표", "",
        "| 모듈 | 층 | 하는 일 | 쓰는 것 | 쓰이는 곳 | 함수 | 분기 | 줄 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in sorted(info, key=lambda x: (lv[x], x)):
        d = info[m]
        area, role = roles.get(m + ".py", ("", ""))
        md.append(
            f"| `{m}.py` | {lv[m]} | {area}{' — ' + role if role else ''} | "
            f"{' · '.join(sorted(d['deps'])) or '—'} | "
            f"{' · '.join(sorted(used_by[m])) or '—'} | "
            f"{len(d['funcs'])} | {d['branches']} | {d['lines']} |")

    #| 갈래  냄새나는 곳이 있나 ? 무엇을 어떻게 고칠지 적는다 : 깨끗하다고 적는다
    md += ["", "---", "", "## ⑤ 손봐야 할 곳", ""]
    if not cyc and not vio:
        md.append("없습니다. 순환 의존도 계층 위반도 0개입니다.")
    for a, b in cyc:
        md += [f"### 🔁 `{a}` ↔ `{b}` — 서로 물고 있습니다", "",
               "둘이 서로를 부르면 **하나만 떼어 낼 수 없습니다.** 지금은 한쪽이 "
               "함수 안에서 늦게 `import` 해서 겨우 돌아가는데, 이런 건 언젠가 "
               "터집니다. 공통으로 쓰는 것을 제3의 모듈로 빼거나, 한쪽이 다른 쪽에 "
               "값을 **넘겨주는** 방향으로 바꿔야 합니다.", ""]
    for a, b in vio:
        md += [f"### ⬆ `{a}` → `{b}` — 아래층이 위층을 씁니다", "",
               "계층은 한 방향이어야 합니다. 이 화살표를 뒤집거나, 둘이 같이 쓰는 "
               "것을 더 아래로 내려야 합니다.", ""]

    md += ["", "---", "", "## ⑥ 텍스트 아키텍처", "", "```text",
           as_text(info, groups, roles), "```", ""]
    return "\n".join(md)


def bake(path, info, groups, roles):
    """Mermaid 를 그림으로 구워 자립 HTML 로. (make_flowchart 를 빌려 씁니다)"""
    #| 흐름  그림 넷을 SVG 로 굽고 한 장짜리 HTML 로 묶는다
    #| 입력  저장 경로 · 모듈 정보 · 층 · 역할표
    #| 호출  make_flowchart.render → SVG 들
    #| 호출  make_flowchart.build_html → 자립 HTML
    #| 갈래  mermaid 를 못 찾았나 ? 그냥 알리고 넘어간다 : 굽는다
    #| 출력  HTML 파일
    import make_flowchart as mf
    plain = lambda c: c.replace("```mermaid\n", "").replace("\n```", "")
    items = [
        ("① 계층도 · 앱", "누가 누구 위에 서 있나 — 화살표는 쓰는 쪽 → 쓰이는 쪽",
         plain(mermaid_layers(info, groups.get("앱", {}), roles))),
        ("② 계층도 · 개발 도구", "도구는 앱을 안 씁니다 — #| 주석만 읽습니다",
         plain(mermaid_layers(info, groups.get("도구", {}), roles))),
        ("③ 호출 지도", "무엇을 받으려고 부르나 — #| 호출 주석에서",
         plain(mermaid_calls(info))),
        ("④ 바깥과 닿는 곳", "느려지고 실패하는 자리 — 나머지는 전부 계산입니다",
         plain(mermaid_boundary(info))),
    ]
    svgs = mf.render([c for _, _, c in items])
    head = {
        "title": "바이올린 연습 도우미 — 아키텍처",
        "nav": "🏛 아키텍처",
        "sub": "소스의 <code>import</code> 문과 <code>#| 호출</code> 주석에서 "
               "자동으로 만들었습니다.<br>"
               "다시 만들기: <code>python3 arch.py 아키텍처.md 아키텍처.html</code>",
        "lead": "<b>손으로 그린 그림이 아닙니다.</b> 계층은 사람이 정한 것이 아니라 "
                "<code>import</code> 가 정합니다 — 코드를 고치면 그림이 따라 "
                "바뀝니다.<br>"
                "<code>import</code> 은 거짓말을 못 하는 <b>진짜 의존</b>이고, "
                "<code>#| 호출 f → r</code> 주석은 <b>왜 부르는지</b>까지 담은 "
                "의도입니다. 둘을 겹쳐 봅니다.<br>"
                "같은 주석에서 순서도(<code>순서도.md</code>)와 "
                "기능 목록(<code>기능리스트.xlsx</code>)도 나옵니다.",
    }
    open(path, "w", encoding="utf-8").write(
        mf.build_html(items, svgs, head=head, group=False))
    print(f"{path} 에 썼습니다. (그림 {sum(1 for x in svgs if x)}/{len(svgs)}장)")


def main():
    #| 흐름  소스를 읽어 아키텍처를 만들고, 인자가 있으면 파일로 저장한다
    #| 호출  read → 모듈 정보
    #| 호출  split → 앱·도구로 나눈 층 번호
    #| 갈래  저장할 이름을 받았나 ? 마크다운으로 쓴다 : 화면에 보여준다
    #| 출력  텍스트 아키텍처 또는 마크다운 파일
    root = os.path.dirname(os.path.abspath(__file__))
    info, _ = read(root)
    roles = features.MODULES
    groups = split(info, roles)

    #| 반복  받은 파일 이름마다
    #| 갈래     .html 인가 ? 그림으로 구워 낸다 : 마크다운으로 쓴다
    if len(sys.argv) > 1:
        for out in sys.argv[1:]:
            if out.endswith(".html"):
                bake(out, info, groups, roles)
            else:
                open(out, "w", encoding="utf-8").write(
                    as_markdown(info, groups, roles))
                n = len(groups.get("앱", {}))
                print(f"{out} 에 썼습니다. "
                      f"(앱 {n}개 · 도구 {len(info) - n}개 · "
                      f"순환 {len(cycles(info))}개 · 위반 "
                      f"{len(violations(info, {m: L for g in groups.values() for m, L in g.items()}))}개)")
    else:
        print(as_text(info, groups, roles))


if __name__ == "__main__":
    main()
