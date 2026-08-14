"""
음악 데이터 — 음계 · 손가락 · 포지션 · 활 · 슬러 · 지판 위치.

여기서 만든 '음 목록' 하나를 화면 세 개(가이드·악보·리포트)가 같이 씁니다.
음 하나에 필요한 정보를 전부 담아 두면 뒤에서 다시 계산할 일이 없습니다.
"""

import math

# ══════════════════════════════════════════════════════════════
#  1. 악기
# ══════════════════════════════════════════════════════════════
STRING_LENGTH_MM = 328.0     # 4/4 바이올린의 진동현 길이 (너트~브리지)
VIEW_MM = 190.0              # 지판에서 화면에 보여줄 범위

A4_HZ = 440.0

# 개방현은 **순정 5도**로 조율합니다 (실제로 바이올린을 맞추는 방식).
# 두 줄을 같이 켜서 맥놀이가 없어질 때까지 = 정확히 3:2.
FIFTH = 1.5

# 위에서부터 E · A · D · G  (연주자가 내려다보는 방향)
STRINGS = [
    {"name": "E", "ko": "미", "freq": A4_HZ * FIFTH,      "letter": "E", "octave": 5},
    {"name": "A", "ko": "라", "freq": A4_HZ,              "letter": "A", "octave": 4},
    {"name": "D", "ko": "레", "freq": A4_HZ / FIFTH,      "letter": "D", "octave": 4},
    {"name": "G", "ko": "솔", "freq": A4_HZ / FIFTH ** 2, "letter": "G", "octave": 3},
]
STRING_BY_NAME = {s["name"]: s for s in STRINGS}

LETTERS = "CDEFGAB"
LETTER_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
KO_NAME = {"C": "도", "D": "레", "E": "미", "F": "파", "G": "솔", "A": "라", "B": "시"}


def mm_from_freq(freq: float, f_open: float, length: float = STRING_LENGTH_MM) -> float:
    """주파수 → 너트에서 몇 mm 떨어진 곳을 짚어야 하는지.

    줄의 진동수는 진동 길이에 반비례합니다.  f = f_open x L / (L - d)
    검산: 한 옥타브 위는 정확히 줄의 절반이 나옵니다.
    """
    return length * (1 - f_open / freq)


def cents(f: float, target: float) -> float:
    """두 주파수 차이를 센트로. 100센트 = 반음."""
    return 1200 * math.log2(f / target)


# ══════════════════════════════════════════════════════════════
#  2. 음계 — 으뜸음에서의 반음 거리
# ══════════════════════════════════════════════════════════════
SCALES = {
    "장조":       [0, 2, 4, 5, 7, 9, 11, 12],
    "자연단조":   [0, 2, 3, 5, 7, 8, 10, 12],
    "화성단조":   [0, 2, 3, 5, 7, 8, 11, 12],   # 7음을 반음 올림 → 이국적인 소리
    "가락단조":   [0, 2, 3, 5, 7, 9, 11, 12],   # 올라갈 때만. 6·7음을 올림
}

# 화면에 보여줄 연습 목록  (이름, 줄, 음계)
PRACTICES = [
    ("A장조 · A현",       "A", "장조"),
    ("A자연단조 · A현",   "A", "자연단조"),
    ("A화성단조 · A현",   "A", "화성단조"),
    ("A가락단조 · A현",   "A", "가락단조"),
    ("D장조 · D현",       "D", "장조"),
    ("D자연단조 · D현",   "D", "자연단조"),
    ("D화성단조 · D현",   "D", "화성단조"),
    ("G자연단조 · G현",   "G", "자연단조"),
    ("G화성단조 · G현",   "G", "화성단조"),
    ("E자연단조 · E현",   "E", "자연단조"),
    ("E화성단조 · E현",   "E", "화성단조"),
]

SLURS = {
    "한 음씩 (데타셰)": 1,
    "2음 슬러": 2,
    "4음 슬러": 4,
}


# ══════════════════════════════════════════════════════════════
#  3. 손가락과 포지션
# ══════════════════════════════════════════════════════════════
# 개방현에서 몇 반음 위인지 → 몇 번 손가락인지.
# 1포지션은 손이 너트 가까이, 3포지션은 손 전체가 5반음 위로 올라간 상태입니다.
FINGER_1ST = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}
FINGER_3RD = {5: 1, 6: 1, 7: 2, 8: 2, 9: 3, 10: 3, 11: 4, 12: 4}


def assign_positions(semis):
    """음계 전체를 보고 **어디서 손을 옮길지** 정합니다.

    한 음씩 따로 보면 안 됩니다. 손은 한 번 옮기면 계속 그 자리에 있으니까요.

    규칙: 1포지션으로 끝까지 닿으면 안 옮깁니다.
          닿지 않으면, **3포지션에서 1번 손가락이 짚는 자리**(개방현+5반음)에서
          옮깁니다. 그 자리가 바로 1포지션 3번 손가락이 짚던 자리라서,
          짚어 보고 소리로 확인한 뒤 올라갈 수 있습니다.
    """
    if max(semis) <= 8:                       # 1포지션으로 충분
        return [(1, FINGER_1ST[s]) for s in semis]

    shift = next((i for i, s in enumerate(semis) if s >= 5), len(semis))
    out = []
    for i, s in enumerate(semis):
        if i < shift:
            out.append((1, FINGER_1ST[s]))
        else:
            out.append((3, FINGER_3RD.get(s, 4)))
    return out


# ══════════════════════════════════════════════════════════════
#  4. 조표 — 몇 개의 ♯ 또는 ♭이 붙는지
# ══════════════════════════════════════════════════════════════
SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]

# 으뜸음 → ♯ 개수(양수) / ♭ 개수(음수)
MAJOR_KEY = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F": -1}
MINOR_KEY = {"A": 0, "E": 1, "B": 2, "D": -1, "G": -2, "C": -3, "F": -4}


def key_signature(root_letter: str, mode: str):
    """(기호, 붙는 음들) — 예: ('♯', ['F','C','G'])

    단조는 **자연단조 기준**으로 조표를 붙입니다.
    화성·가락단조에서 올린 음은 조표가 아니라 그 자리에 임시표로 붙습니다.
    (그래서 A화성단조는 조표가 없고 솔♯에만 ♯이 붙습니다)
    """
    n = MAJOR_KEY.get(root_letter, 0) if mode == "장조" else MINOR_KEY.get(root_letter, 0)
    if n >= 0:
        return "♯", SHARP_ORDER[:n]
    return "♭", FLAT_ORDER[:-n]


# ══════════════════════════════════════════════════════════════
#  5. 음 목록 만들기  ← 화면 세 개가 전부 이 결과를 씁니다
# ══════════════════════════════════════════════════════════════
def build_notes(string_name: str, mode: str, slur: int = 1, bpm: int = 60,
                first_position_only: bool = False):
    """음계 하나를 '연주할 수 있는 음 목록'으로 바꿉니다.

    음 하나에 들어가는 것:
      freq/mm      어디를 짚나          position/finger  몇 포지션 몇 번 손가락
      letter/oct   악보 어디에 그리나    acc              임시표
      bow/slur     활을 어느 쪽으로      t/dur            언제 몇 초
    """
    st = STRING_BY_NAME[string_name]
    pattern = SCALES[mode]
    if first_position_only:
        pattern = [s for s in pattern if s <= 7]      # 1포지션에서 편하게 닿는 데까지
    sig, sig_notes = key_signature(st["letter"], mode)
    beat = 60.0 / bpm

    root_li = LETTERS.index(st["letter"])
    place = assign_positions(pattern)
    notes = []
    for deg, semi in enumerate(pattern):
        letter = LETTERS[(root_li + deg) % 7]
        octave = st["octave"] + (root_li + deg) // 7

        # 음이름이 정해졌으니, 실제 높이와의 차이가 곧 임시표입니다
        natural = LETTER_SEMI[letter] + 12 * octave
        want = LETTER_SEMI[st["letter"]] + 12 * st["octave"] + semi
        delta = want - natural                       # +1 = ♯, -1 = ♭

        # 조표에 이미 들어 있으면 악보에는 안 씁니다
        in_key = (letter in sig_notes)
        key_delta = (1 if sig == "♯" else -1) if in_key else 0
        acc = "" if delta == key_delta else ("♯" if delta > 0 else
                                             ("♭" if delta < 0 else "♮"))

        pos, finger = place[deg]
        freq = st["freq"] * 2 ** (semi / 12)

        notes.append({
            "letter": letter, "octave": octave, "acc": acc,
            "name": letter + ("#" if delta > 0 else "b" if delta < 0 else "") + str(octave),
            "ko": KO_NAME[letter] + ("♯" if delta > 0 else "♭" if delta < 0 else ""),
            "semi": semi, "freq": freq,
            "mm": mm_from_freq(freq, st["freq"]),
            "position": pos, "finger": finger,
            "string": string_name,
            "t": deg * beat, "dur": beat, "beat": deg,
        })

    # ── 활 방향과 슬러 ──
    # 슬러 하나 = 활 한 번. 그룹마다 방향이 바뀝니다.
    for i, n in enumerate(notes):
        g = i // slur
        n["slur"] = g
        n["slur_size"] = slur
        n["slur_head"] = (i % slur == 0)
        n["bow"] = "down" if g % 2 == 0 else "up"

    return notes


def shift_index(notes):
    """포지션이 바뀌는 자리의 인덱스. 없으면 None."""
    for i in range(1, len(notes)):
        if notes[i]["position"] != notes[i - 1]["position"]:
            return i
    return None


def title_of(string_name: str, mode: str) -> str:
    return f'{STRING_BY_NAME[string_name]["name"]}{mode} · {string_name}현'
