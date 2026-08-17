"""
음악 데이터 — 음계 · 손가락 · 포지션 · 활 · 슬러 · 지판 위치.

여기서 만든 '음 목록' 하나를 화면 세 개(가이드·악보·리포트)가 같이 씁니다.
음 하나에 필요한 정보를 전부 담아 두면 뒤에서 다시 계산할 일이 없습니다.
"""

import math

#| 흐름  음계 하나 → 연주할 수 있는 음 목록 (높이·지판자리·손가락·포지션·활·슬러)

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
    #| 흐름  주파수를 너트에서의 거리(mm)로 바꾼다
    #| 입력  낼 주파수 · 그 줄의 개방현 주파수
    #| 단계  f = f_open x L / (L - d) 를 d 에 대해 푼 식을 적용한다
    #| 출력  너트에서 몇 mm
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


# 기본은 **1포지션**입니다. 손을 옮기는 것(시프팅)은 나중에 배우는 기술이라,
# 처음부터 1→3 을 섞어 주면 배우는 순서가 뒤집힙니다.
POSITIONS = ["1포지션", "3포지션", "1 → 3포지션 (손 옮기기)"]

# 그 포지션에서 짚을 수 있는 범위 (개방현에서 몇 반음 위까지)
REACH = {1: (0, 8), 3: (5, 12)}


def semi_on(freq, string):
    """그 줄에서 개방현으로부터 몇 반음 위인지."""
    return 12 * math.log2(freq / string["freq"])


# 줄을 넘어갈지 정할 때 쓰는 사정거리.  REACH 보다 좁습니다 —
# 4번 손가락으로 두 음을 잇달아 짚게 두느니 옆 줄로 넘어가는 편이 낫기 때문입니다.
CROSS_REACH = {1: (0, 7), 3: (5, 11)}


def pick_strings(freqs, base, reach, open_ok=True):
    """음마다 어느 줄로 켤지 — **손을 옮기지 않고** 닿게.

    1포지션에서 한 옥타브 음계를 하려면 도중에 옆 줄로 넘어가야 합니다
    (A현 1포지션은 레까지, 그 위는 E현으로). 손은 그대로 두고 활만 옮깁니다.
    """
    #| 흐름  줄을 최대한 지키다가, 안 닿으면 옆 줄로 넘어간다
    #| 입력  음들의 주파수 · 시작 줄 · 그 포지션의 사정거리
    #| 반복  음마다
    #| 갈래     지금 줄로 닿나 ? 그대로 : 닿는 줄 중 가장 낮은 자리로 옮긴다
    #| 출력  음마다 줄 이름
    lo, hi = reach

    def ok(f, st):
        #| 갈래  개방현인가 ? 1포지션에서는 쓴다 (3포지션 연습에서는 안 씁니다) : 사정거리 안인지 본다
        v = semi_on(f, st)
        if abs(v) < 0.3:
            return open_ok
        return lo - 0.3 <= v <= hi + 0.3

    cur = STRING_BY_NAME[base]
    out = []
    for f in freqs:
        if not ok(f, cur):
            cur = next((s for s in STRINGS if ok(f, s)), cur)
        out.append(cur["name"])
    return out


def playable(pattern, base, force):
    """고른 포지션에서 **손을 옮기지 않고 닿는 음**만 남깁니다.

    네 줄을 다 봐서, 어느 줄로도 안 닿는 음은 뺍니다.
    E현 1포지션처럼 위로 더 갈 줄이 없으면 음계가 짧아집니다 — 그게 맞습니다.
    (안 닿는 음을 그려 놓고 짚으라고 하면 연습이 안 됩니다)
    """
    #| 흐름  네 줄 중 어디로도 안 닿는 음은 뺀다
    #| 입력  반음 목록 · 시작 줄 · 못박은 포지션
    #| 갈래  포지션을 안 박았나 ? 음계 그대로 : 계속한다
    #| 반복  음마다
    #| 갈래     어느 줄로든 닿나 ? 남긴다 : 뺀다
    #| 갈래  남은 게 없나 ? 원래 음계를 돌려준다 : 남은 것만
    #| 출력  반음 목록
    if force not in (1, 3):
        return list(pattern)
    lo, hi = CROSS_REACH[force]
    f0 = STRING_BY_NAME[base]["freq"]

    def any_ok(sm):
        for st in STRINGS:
            v = semi_on(f0 * 2 ** (sm / 12), st)
            if abs(v) < 0.3:
                if force == 1:
                    return True
                continue
            if lo - 0.3 <= v <= hi + 0.3:
                return True
        return False

    out = [s for s in pattern if any_ok(s)]
    return out or list(pattern)


def assign_positions(semis, force=None):
    """음계 전체를 보고 **어디서 손을 옮길지** 정합니다.

    한 음씩 따로 보면 안 됩니다. 손은 한 번 옮기면 계속 그 자리에 있으니까요.

    규칙: 1포지션으로 끝까지 닿으면 안 옮깁니다.
          닿지 않으면, **3포지션에서 1번 손가락이 짚는 자리**(개방현+5반음)에서
          옮깁니다. 그 자리가 바로 1포지션 3번 손가락이 짚던 자리라서,
          짚어 보고 소리로 확인한 뒤 올라갈 수 있습니다.
    """
    #| 흐름  음계 전체를 보고 손을 옮길 자리를 한 번에 정한다
    #| 입력  개방현에서 몇 반음 위인지의 목록
    #| 갈래  포지션을 못박았나 ? 전부 그 포지션으로 : 어디서 옮길지 정한다
    #| 갈래  1포지션으로 끝까지 닿나 ? 안 옮긴다 : 옮길 자리를 찾는다
    #| 단계  3포지션 1번 손가락 자리(+5반음)를 옮기는 지점으로 잡는다
    #| 반복  음마다
        #| 단계     옮기는 지점 앞이면 1포지션, 뒤면 3포지션 손가락표를 쓴다
    #| 출력  음마다 (포지션, 손가락)
    # 포지션을 못박은 경우 — 개방현은 어느 포지션에서든 개방현입니다
    if force in (1, 3):
        table = FINGER_1ST if force == 1 else FINGER_3RD
        return [(1, 0) if s == 0 else (force, table.get(s, 4)) for s in semis]

    if max(semis) <= 8:                       # 1포지션으로 충분
        return [(1, FINGER_1ST[s]) for s in semis]

    shift = next((i for i, s in enumerate(semis) if s >= 5), len(semis))
    out = []
    for i, s in enumerate(semis):
        #| 갈래  개방현인가 ? 손 위치와 상관없이 개방 : 포지션에 맞는 손가락
        if s == 0:
            out.append((1, 0))
        elif i < shift:
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
    #| 흐름  으뜸음과 조성으로 조표를 정한다
    #| 갈래  장조인가 ? 장조표에서 찾는다 : 단조표에서 찾는다
    #| 갈래  ♯쪽인가 ? F C G D A E B 순으로 자른다 : B E A D G C F 순으로 자른다
    #| 출력  (기호, 붙는 음들)
    n = MAJOR_KEY.get(root_letter, 0) if mode == "장조" else MINOR_KEY.get(root_letter, 0)
    if n >= 0:
        return "♯", SHARP_ORDER[:n]
    return "♭", FLAT_ORDER[:-n]


# ══════════════════════════════════════════════════════════════
#  5. 음 목록 만들기  ← 화면 세 개가 전부 이 결과를 씁니다
# ══════════════════════════════════════════════════════════════
def notes_from(string_name: str, pattern, mode: str, slur: int = 1, bpm: int = 60,
               place=None, force=None):
    """반음 목록 → 연주할 수 있는 음 목록.

    음계든 교정 드릴이든 결국 '반음 목록'입니다.
    같은 함수를 쓰므로 화면·분석이 그대로 돌아갑니다.

    place 를 주면 손가락·포지션을 그대로 씁니다.
    (교정 드릴은 원래 음계에서 짚던 자리를 그대로 연습해야 뜻이 있습니다)
    """
    #| 흐름  반음 목록을 음이름·지판자리·손가락·활이 다 붙은 음 목록으로
    return _build(string_name, list(pattern), mode, slur, bpm, place, force)


def build_notes(string_name: str, mode: str, slur: int = 1, bpm: int = 60,
                position: str = "1 → 3포지션"):
    """음계 하나를 '연주할 수 있는 음 목록'으로 바꿉니다.

    음 하나에 들어가는 것:
      freq/mm      어디를 짚나          position/finger  몇 포지션 몇 번 손가락
      letter/oct   악보 어디에 그리나    acc              임시표
      bow/slur     활을 어느 쪽으로      t/dur            언제 몇 초
    """
    #| 흐름  음계 하나를 화면 세 개가 그대로 쓸 수 있는 음 목록으로 만든다
    #| 입력  줄 · 음계 · 슬러 · BPM · 포지션
    #| 호출  playable → 그 포지션에서 닿는 음만
    #| 호출  key_signature → 조표
    #| 호출  assign_positions → 음마다 (포지션, 손가락)
    #| 반복  음계의 음마다
        #| 단계     으뜸음에서 몇 번째인지로 음이름(A~G)과 옥타브를 정한다
        #| 단계     음이름의 본래 높이와 실제 높이의 차 = 임시표
        #| 갈래     조표에 이미 있나 ? 악보에 안 쓴다 : ♯/♭/♮ 를 붙인다
        #| 호출     mm_from_freq → 지판 위 mm
    #| 반복  다시 음마다 — 활과 슬러
        #| 단계     슬러 하나 = 활 한 번. 그룹마다 다운↔업을 바꾼다
    #| 출력  음 목록 (화면 ①·② 와 분석이 전부 이걸 씀)
    force = {"1포지션": 1, "3포지션": 3}.get(position)
    #| 갈래  포지션을 못박았나 ? 한 옥타브 그대로 두고 줄을 넘나든다 : 한 줄에서 손을 옮긴다
    if force:
        return _build(string_name, playable(SCALES[mode], string_name, force),
                      mode, slur, bpm, force=force, cross=True)
    return _build(string_name, list(SCALES[mode]), mode, slur, bpm)


def _build(string_name, pattern, mode, slur, bpm, place=None, force=None,
           cross=False):
    st = STRING_BY_NAME[string_name]
    sig, sig_notes = key_signature(st["letter"], mode)
    beat = 60.0 / bpm

    root_li = LETTERS.index(st["letter"])
    # 반음은 **시작 줄 기준**입니다. 줄을 넘어가면 그 줄 기준으로 다시 셉니다.
    freqs = [st["freq"] * 2 ** (sm / 12) for sm in pattern]
    #| 갈래  줄을 넘나드나 ? 음마다 닿는 줄을 고른다 : 전부 시작 줄
    if cross:
        names = pick_strings(freqs, string_name, CROSS_REACH[force],
                             open_ok=(force == 1))
    else:
        names = [string_name] * len(pattern)
    own = [int(round(semi_on(f, STRING_BY_NAME[n])))
           for f, n in zip(freqs, names)]
    place = place or assign_positions(own, force)

    # 반음 → 음계에서 몇 번째 음인지.
    # 음계는 0,1,2… 순서지만 교정 드릴은 [0,9,0,9] 처럼 뒤죽박죽입니다.
    # 순서가 아니라 **반음**으로 음이름을 정해야 이름이 안 깨집니다.
    deg_of = {sm: i for i, sm in enumerate(SCALES[mode])}

    notes = []
    for pos_in_list, semi in enumerate(pattern):
        deg = deg_of.get(semi, min(deg_of, key=lambda k: abs(k - semi)) and
                         deg_of[min(deg_of, key=lambda k: abs(k - semi))])
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

        pos, finger = place[pos_in_list]
        freq = freqs[pos_in_list]
        on = STRING_BY_NAME[names[pos_in_list]]

        notes.append({
            "letter": letter, "octave": octave, "acc": acc,
            "name": letter + ("#" if delta > 0 else "b" if delta < 0 else "") + str(octave),
            "ko": KO_NAME[letter] + ("♯" if delta > 0 else "♭" if delta < 0 else ""),
            "semi": own[pos_in_list], "freq": freq,
            "mm": mm_from_freq(freq, on["freq"]),
            "position": pos, "finger": finger,
            "string": on["name"],
            "t": pos_in_list * beat, "dur": beat, "beat": pos_in_list,
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
    #| 흐름  앞 음과 포지션이 달라지는 첫 자리를 찾는다
    for i in range(1, len(notes)):
        if notes[i]["position"] != notes[i - 1]["position"]:
            return i
    return None


def title_of(string_name: str, mode: str) -> str:
    return f'{STRING_BY_NAME[string_name]["name"]}{mode} · {string_name}현'


# ══════════════════════════════════════════════════════════════
#  6. 교정 드릴 — 리포트에서 "이 부분 연습하기" 로 넘어오는 것
# ══════════════════════════════════════════════════════════════
def drill_note(base, idx, mode, bpm):
    """문제 음 하나를 개방현과 번갈아 짚습니다.

    개방현은 늘 맞는 소리라서, 바로 앞뒤에 두면
    귀가 기준을 잃지 않습니다. 음정 교정의 기본형입니다.
    """
    #| 흐름  개방현 ↔ 문제 음 을 네 번 번갈아
    #| 입력  원래 음 목록 · 문제 음의 자리
    #| 출력  음 목록 (개방-대상 x4)
    n = base[idx]
    # 원래 음계에서 짚던 자리를 그대로 — 드릴에서만 손가락이 바뀌면 뜻이 없습니다
    place = [(1, 0), (n["position"], n["finger"])] * 4
    return notes_from(n["string"], [0, n["semi"]] * 4, mode, 1, bpm, place)


def drill_shift(base, mode, bpm):
    """포지션을 옮기는 자리 앞뒤만 잘라 두 번 반복합니다."""
    #| 흐름  이동 직전 2음 + 직후 2음을 두 번
    #| 갈래  옮기는 자리가 있나 ? 그 앞뒤를 자른다 : 원래 음계를 돌려준다
    sh = shift_index(base)
    if sh is None:
        return base
    cut = base[max(0, sh - 2):sh + 2]
    seg = [n["semi"] for n in cut]
    place = [(n["position"], n["finger"]) for n in cut]
    return notes_from(base[0]["string"], seg * 2, mode, 1, bpm, place * 2)


def drill_longtone(string_name, mode, bpm=30):
    """개방현을 한 활에 네 음씩 — 활이 흔들리는지 보는 연습."""
    #| 흐름  개방현만 여덟 번, 4음 슬러 (한 활에 네 음)
    return notes_from(string_name, [0] * 8, mode, 4, bpm)
