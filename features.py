"""
기능 목록을 **주석에서** 뽑아내는 도구.

    python3 features.py              → 화면에 표로
    python3 features.py 기능리스트.xlsx → 엑셀로

flow.py 와 같은 `#|` 주석을 읽습니다. 그래서 순서도와 기능 목록이
**같은 원본**에서 나옵니다 — 둘이 어긋날 수가 없습니다.

    소스의 #| 주석 ──┬─→ flow.py     → 순서도 · 플로우차트
                     └─→ features.py → 기능 목록 (엑셀)

기능 하나 = 함수 하나입니다.
  기능명   함수의 설명글 첫 줄
  설명     #| 흐름  (한 줄 요약)
  입력/출력 #| 입력 · #| 출력
  분기 수   #| 갈래 개수 — 테스트해야 할 경우의 수와 같습니다
"""

import ast
import os
import sys

import flow

#| 흐름  소스의 주석·설명글 → 기능 한 줄씩 → 표 또는 엑셀

# ══════════════════════════════════════════════════════════════
#  모듈이 무엇을 맡는가 — 여기만 손으로 적습니다
# ══════════════════════════════════════════════════════════════
# 나머지는 전부 소스에서 뽑습니다. 이 표는 "어느 화면의 무엇인가"를
# 사람이 정해 주는 자리입니다.
MODULES = {
    "app.py":        ("앱 셸",        "화면 전환 · 상태 · 사이드바 · 녹음 흐름"),
    "screens.py":    ("화면① 연습",   "움직이는 가이드 (악보·낙하 노드·지판·안내)"),
    "report.py":     ("화면② 리포트", "분석 결과 · 음별 표 · 코멘트 · 교정 연습"),
    "sheet.py":      ("화면③ 내 악보", "직접 적기 · 사진 · MusicXML → 음 목록"),
    "analyze.py":    ("분석 엔진",     "YIN 음정 검출 · 음별 통계 · 소리 합성"),
    "music.py":      ("음악 데이터",   "음계 · 조표 · 포지션 · 손가락 · 지판 위치"),
    "staff.py":      ("악보 렌더링",   "오선 · 음표 · 조표 · 슬러 (SVG)"),
    "instrument.py": ("악기·손",       "줄 · 스크롤/몸통 사진 · 손 · 브리지"),
    "glyphs.py":     ("악보 기호",     "𝄞 ♯ ♭ ♮ 를 SVG 경로로"),
    "theme.py":      ("디자인 토큰",   "색 · 글꼴 한곳에"),
    "flow.py":       ("개발 도구",     "주석 → 순서도 · 플로우차트"),
    "features.py":   ("개발 도구",     "주석 → 기능 목록 (이 파일)"),
    "excel_out.py":  ("개발 도구",     "기능 목록 → 엑셀 (시트 네 장)"),
    "make_flowchart.py": ("개발 도구", "주석 → 플로우차트 HTML (그림으로 구워서)"),
    "arch.py":       ("개발 도구",   "주석 + import → 아키텍처 (의존·계층·경계)"),
}

# 아직 안 끝난 것 (함수 이름 → 상태·비고)
STATUS = {
    "from_image": ("부분 구현", "Gemini 키가 있어야 동작 · 사진은 저장하지 않음"),
    "from_musicxml": ("부분 구현", "단선율만 · 쉼표/붙임줄 미지원"),
    "drill_shift": ("완료", "포지션 이동이 없는 악보에서는 건너뜀"),
}

# 아직 만들지 않은 화면·기능 (엑셀의 「다음 단계」 시트)
BACKLOG = [
    ("튜닝 · 캘리브레이션", "analyze.py + 새 화면", "높음",
     "개방현 4개를 켜는 동안 ① 내 악기 기준 주파수 ② 내 활 흔들림을 같이 재서 "
     "허용 범위를 사람마다 다르게 (지금은 슬라이더 수동)"),
    ("연습 기록", "새 모듈 + app.py", "높음",
     "연습할 때마다 결과를 쌓아 날짜별로 음정이 나아지는지 보여주기"),
    ("곡 목록", "sheet.py + 새 화면", "중간",
     "퍼블릭 도메인 교본(호만·볼파르트)부터. 저작권 있는 악보는 넣지 않음"),
    ("활 연습", "analyze.py + 새 화면", "중간",
     "개방현 롱톤의 음량 곡선 — 활 속도·압력이 고른지"),
    ("리포트 2종", "report.py", "중간",
     "학생용 한 줄 요약 / 선생님용 상세"),
    ("쉼표 · 붙임줄 · 여러 줄", "sheet.py", "중간",
     "지금은 단선율 한 줄만 읽음"),
    ("두 줄에 걸친 음계", "music.py", "낮음",
     "지금은 한 줄 + 포지션 이동"),
    ("비올라 · 첼로", "instrument.py", "낮음",
     "instrument.py 에 악기 하나를 더하면 화면은 그대로 돌아감"),
]


def collect(root=None):
    """소스 전체 → 기능 한 줄씩.

    설명글(docstring)은 ast 로, 흐름 주석은 flow.py 로 읽어 합칩니다.
    """
    #| 흐름  파일마다 설명글과 #| 주석을 합쳐 기능 한 줄씩 만든다
    #| 입력  소스 폴더
    #| 반복  .py 파일마다
        #| 호출     ast.parse → 함수 이름과 설명글
        #| 호출     flow.scan → 그 파일의 #| 주석들
        #| 반복     함수마다
            #| 단계        흐름·입력·출력·갈래를 모아 한 줄로
            #| 갈래        상태를 손으로 적어 뒀나 ? 그걸 쓴다 : '완료'
    #| 출력  기능 목록 (딕셔너리 리스트)
    root = root or os.path.dirname(os.path.abspath(__file__))
    rows, no = [], 0

    for path, items in flow.build(root):
        name = os.path.basename(path)
        area, role = MODULES.get(name, ("기타", ""))
        src = open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        docs = {n.name: (ast.get_docstring(n) or "").strip()
                for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        lines = {n.name: n.lineno for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

        for fn, steps in flow.group(items):
            #| 갈래  모듈 전체 흐름인가 ? 파일 요약 줄로 : 함수 한 줄로
            def pick(kind):
                return " / ".join(s["text"] for s in steps if s["kind"] == kind)

            summary = pick("흐름")
            if fn == "(모듈)":
                title = f"[모듈] {name}"
                doc = (src.split('"""')[1].strip().splitlines()[0]
                       if '"""' in src else role)
                line = 1
            else:
                title = (docs.get(fn, "").splitlines() or [fn])[0].strip()
                doc = title
                line = lines.get(fn, 0)

            st, note = STATUS.get(fn, ("완료", ""))
            no += 1
            rows.append({
                "번호": no,
                "영역": area,
                "모듈": name,
                "함수": ("" if fn == "(모듈)"
                       else fn if fn.endswith(")") else fn + "()"),
                "기능명": doc or title,
                "설명(흐름)": summary,
                "입력": pick("입력"),
                "출력": pick("출력"),
                "단계": sum(1 for s in steps if s["kind"] == "단계"),
                "분기": sum(1 for s in steps if s["kind"] == "갈래"),
                "반복": sum(1 for s in steps if s["kind"] == "반복"),
                "호출": sum(1 for s in steps if s["kind"] == "호출"),
                "상태": st,
                "줄": line,
                "비고": note,
            })
    return rows


COLS = ["번호", "영역", "모듈", "함수", "기능명", "설명(흐름)", "입력", "출력",
        "단계", "분기", "반복", "호출", "상태", "줄", "비고"]


def as_text(rows):
    """화면에 바로 보는 표."""
    #| 흐름  기능 목록을 글자 표로
    out = [" | ".join(("영역", "모듈", "함수", "기능명"))]
    out.append("-" * 90)
    for r in rows:
        out.append(f'{r["영역"]:<12} | {r["모듈"]:<14} | '
                   f'{r["함수"]:<22} | {r["기능명"]}')
    out.append(f"\n총 {len(rows)}개")
    return "\n".join(out)


def main():
    #| 흐름  기능을 모아 화면에 보이거나 엑셀로 저장한다
    #| 갈래  파일 이름을 받았나 ? 엑셀로 쓴다 : 화면에 표로 보여준다
    rows = collect()
    if len(sys.argv) > 1:
        # 열 이름(COLS)을 **넘겨줍니다.** excel_out 이 features 를 되돌아
        # import 하면 둘이 서로 물려서 하나만 떼어 낼 수 없게 됩니다.
        # (arch.py 가 이 순환을 잡아 줘서 고쳤습니다)
        import excel_out
        excel_out.write(sys.argv[1], rows, MODULES, BACKLOG, COLS)
        print(f"{sys.argv[1]} 에 썼습니다. (기능 {len(rows)}개)")
    else:
        print(as_text(rows))


if __name__ == "__main__":
    main()
