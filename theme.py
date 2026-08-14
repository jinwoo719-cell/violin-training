"""
색과 치수를 한곳에 모아 둡니다.

화면마다 색을 따로 적으면 반드시 어긋납니다.
바꿀 일이 생기면 이 파일만 고칩니다.
"""

#| 흐름  모든 화면이 같이 쓰는 색·치수

C = {
    # ── 바탕 ──
    "bg":     "#0d1117",   # 페이지
    "panel":  "#161b26",   # 카드
    "panel2": "#1c2230",   # 카드 안의 칸
    "line":   "#252c3b",   # 테두리
    "grid":   "#20263300",  # (미사용 자리)

    # ── 글자 ──
    "ink":   "#e6e9ef",
    "ink2":  "#aab3c5",
    "muted": "#7c8698",

    # ── 강조 ──
    "accent": "#4f46e5",   # 버튼 · 켜진 메뉴

    # ── 판정 ──
    "good": "#22c55e",     # 허용 범위 안
    "bad":  "#ef4444",     # 낮게 벗어남
    "high": "#3b82f6",     # 높게 벗어남
    "warn": "#f59e0b",     # 박자 · 주의

    # ── 지표별 ──
    "beat":   "#f59e0b",   # 박자
    "steady": "#a855f7",   # 안정도(활 흔들림)

    # ── 활 방향 ──
    "down": "#3b82f6",     # 다운보우 ⊓
    "up":   "#f97316",     # 업보우 ∨

    # ── 그 밖 ──
    "trace": "#f0d98c",    # 내 음정 궤적 (A현 색)
    "pos1":  "#22c55e",    # 1포지션
    "pos3":  "#f59e0b",    # 3포지션
}

FONT = "system-ui,-apple-system,'Malgun Gothic',sans-serif"
MONO = "ui-monospace,Menlo,'D2Coding',monospace"


def score_color(v: float) -> str:
    """점수 → 색.  60 미만 빨강, 80 미만 주황, 그 위 초록"""
    #| 갈래  60점 미만인가 ? 빨강 : 80점 미만이면 주황, 아니면 초록
    return C["bad"] if v < 60 else (C["warn"] if v < 80 else C["good"])
