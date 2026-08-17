"""
내 악보 — 직접 적기 · 사진 찍기 · 파일 올리기.

왜 필요한가:
  교본 악보를 그대로 불러다 쓰면 저작권이 걸립니다.
  **내가 적거나 · 내가 가진 악보를 내가 찍어** 개인적으로 쓰는 길을 둡니다.
  그래서 사진은 어디에도 저장하지 않고, 읽고 나면 버립니다.

세 갈래가 전부 **같은 텍스트 한 줄**로 모입니다.

      직접 적기 ─┐
      사진      ─┼→  "라 시 도♯ 레 …"  →  parse  →  build  →  음 목록
      파일      ─┘                                            (화면 세 개가 쓰는 그것)

이렇게 모아 두면, 어느 길로 들어왔든 사용자가 손으로 고칠 수 있습니다.
사진 인식은 반드시 틀립니다 — 고칠 수 있어야 쓸 수 있습니다.
"""

import io
import json
import math
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

import music

#| 흐름  적은 글 · 사진 · 파일 → 음 목록 (화면 세 개가 그대로 쓰는 그것)

# ══════════════════════════════════════════════════════════════
#  1. 적는 법
# ══════════════════════════════════════════════════════════════
HELP = """\
**한 칸에 한 음**, 띄어쓰기·줄바꿈·쉼표 아무거나로 나눕니다.

| 적는 것 | 뜻 |
|---|---|
| `도 레 미 파 솔 라 시` | 계이름 (도 = C, 고정도) |
| `A B C D E F G` | 영문 음이름도 됩니다 |
| `도#` `레b` | 올림·내림 (`♯` `♭` 도 됩니다) |
| `라4` `도#5` | 옥타브 (가운데 도 = C4) |
| `라` | 옥타브를 안 적으면 **앞 음에서 가장 가까운 쪽**으로 잇습니다 |
| `라*2` | 두 박 |
| `라/2` | 반 박 |
"""

SAMPLE = "라 시 도#5 레 미 파# 솔# 라*2"

_KO = {"도": "C", "레": "D", "미": "E", "파": "F", "솔": "G", "라": "A", "시": "B"}
_ALTER = {"#": 1, "♯": 1, "b": -1, "♭": -1, "n": 0, "♮": 0}

# 라4 · 도#5*2 · A/2 …
_TOKEN = re.compile(
    r"^([A-Ga-g]|[도레미파솔라시])"      # 음이름
    r"([#♯b♭n♮]?)"                       # 올림·내림
    r"(-?\d)?"                           # 옥타브
    r"(?:([*/])(\d+(?:\.\d+)?))?$"       # 길이  *2  /2
)


def parse(text: str, octave0: int = 4):
    """적은 글 → [(음이름, 올림내림, 옥타브, 박수), …]

    옥타브를 안 적으면 **앞 음에서 가장 가까운 쪽**으로 잇습니다.
    (도 다음에 시라고 적으면 위가 아니라 아래 시입니다 — 노래하듯이)
    """
    #| 흐름  적은 글을 음 하나씩 뜯는다
    #| 입력  적은 글 · 첫 음의 옥타브
    #| 반복  칸마다
    #| 갈래     읽히나 ? 음 하나로 담는다 : 어디가 틀렸는지 알린다
    #| 갈래     옥타브를 적었나 ? 그대로 : 앞 음에서 6반음 안으로 붙인다
    #| 출력  음 목록 · 못 읽은 칸 목록
    out, bad = [], []
    prev = None                                   # 앞 음의 절대 반음
    for raw in re.split(r"[\s,|]+", text.strip()):
        if not raw:
            continue
        m = _TOKEN.match(raw)
        if not m:
            bad.append(raw)
            continue
        head, sym, octs, mul, num = m.groups()
        letter = _KO.get(head, head.upper())
        alter = _ALTER.get(sym, 0)

        if octs is not None:
            octave = int(octs)
        elif prev is None:
            octave = octave0
        else:
            #| 갈래  앞 음보다 6반음 넘게 벌어지나 ? 옥타브를 옮겨 붙인다 : 그대로
            octave = prev // 12 - 1
            base = music.LETTER_SEMI[letter] + alter
            best, bestd = octave, 99
            for o in (octave - 1, octave, octave + 1):
                d = abs((base + 12 * (o + 1)) - prev)
                if d < bestd:
                    best, bestd = o, d
            octave = best

        beats = 1.0
        if mul == "*":
            beats = float(num)
        elif mul == "/":
            beats = 1.0 / float(num)

        prev = music.LETTER_SEMI[letter] + alter + 12 * (octave + 1)
        out.append((letter, alter, octave, beats))
    return out, bad


def to_text(parsed) -> str:
    """음 목록 → 다시 적은 글. (사진·파일로 들어온 것을 고칠 수 있게)"""
    #| 흐름  음 목록을 사람이 고칠 수 있는 글로 되돌린다
    #| 반복  음마다 계이름·올림내림·옥타브·길이를 붙인다
    ko = {v: k for k, v in _KO.items()}
    p = []
    for letter, alter, octave, beats in parsed:
        s = ko[letter] + ("♯" if alter > 0 else "♭" if alter < 0 else "") + str(octave)
        if abs(beats - 1.0) > 1e-6:
            s += (f"*{beats:g}" if beats > 1 else f"/{1/beats:g}")
        p.append(s)
    return " ".join(p)


# ══════════════════════════════════════════════════════════════
#  2. 어느 줄로 켤지
# ══════════════════════════════════════════════════════════════
MAX_SEMI = 12                 # 한 줄에서 올라갈 수 있는 데까지 (한 옥타브)


def _semi_on(freq: float, string) -> float:
    return 12 * math.log2(freq / string["freq"])


def names_fallback(f):
    """어느 포지션으로도 안 닿을 때 — 그냥 닿는 줄 아무거나."""
    #| 갈래  닿는 줄이 있나 ? 그 줄 : 가장 낮은 줄
    ok = [s for s in music.STRINGS if -0.3 <= _semi_on(f, s) <= MAX_SEMI + 0.3]
    return (ok[0] if ok else music.STRINGS[-1])["name"]


def pick_strings(freqs, forced=None):
    """음마다 어느 줄로 켤지.

    바이올린은 같은 음을 여러 줄에서 낼 수 있습니다.
    연습 악보는 **한 줄 안에서 끝나는 것이 제일 좋으므로**, 먼저 그걸 찾습니다.
    안 되면 음마다 가장 낮은 자리(=높은 줄)를 골라 손을 덜 올립니다.
    """
    #| 흐름  한 줄로 다 되면 그 줄, 안 되면 음마다 가장 편한 줄
    #| 입력  음들의 주파수 · (사용자가 줄을 못박았으면 그 줄)
    #| 갈래  사용자가 골랐나 ? 그 줄로 통일 : 계속 찾는다
    #| 반복  E · A · D · G 를 낮은 줄부터
    #| 갈래     이 줄 하나로 다 되나 ? 그 줄로 끝 : 다음 줄
    #| 반복  (한 줄로 안 되면) 음마다
    #| 단계     닿는 줄 중 가장 높은 줄 = 가장 낮은 자리
    #| 출력  음마다 줄 이름
    if forced:
        return [forced] * len(freqs)

    #| 반복  낮은 줄부터 — 낮은 줄이 소리가 두껍고 손이 편합니다
    for s in reversed(music.STRINGS):
        if all(-0.3 <= _semi_on(f, s) <= MAX_SEMI + 0.3 for f in freqs):
            return [s["name"]] * len(freqs)

    out = []
    for f in freqs:
        ok = [s for s in music.STRINGS if -0.3 <= _semi_on(f, s) <= MAX_SEMI + 0.3]
        out.append((ok[0] if ok else music.STRINGS[-1])["name"])
    return out


# ══════════════════════════════════════════════════════════════
#  3. 음 목록 만들기  ← music._build 와 같은 모양을 돌려줍니다
# ══════════════════════════════════════════════════════════════
def build(parsed, key: int = 0, bpm: int = 60, slur: int = 1,
          forced_string=None, position: str = "1포지션"):
    """적은 음들 → 화면 세 개가 그대로 쓰는 음 목록.

    music.build_notes 와 **같은 열쇠(key)** 를 담습니다.
    그래야 가이드·악보·리포트·분석이 하나도 안 바뀌고 돌아갑니다.
    """
    #| 흐름  적은 음들을 지판자리·손가락·활까지 붙은 음 목록으로
    #| 입력  뜯어 놓은 음들 · 조표 · BPM · 슬러 · (못박은 줄) · 포지션
    #| 단계  음마다 주파수를 낸다
    #| 호출  pick_strings → 음마다 어느 줄
    #| 반복  같은 줄이 이어지는 덩어리마다
    #| 호출     music.assign_positions → 포지션·손가락 (손은 덩어리 안에서만 옮깁니다)
    #| 반복  음마다
    #| 갈래     조표에 이미 있는 올림내림인가 ? 악보에 안 쓴다 : ♯/♭/♮ 를 붙인다
    #| 호출     music.mm_from_freq → 너트에서 몇 mm
    #| 반복  다시 음마다 — 슬러 하나 = 활 한 번
    #| 출력  음 목록
    if not parsed:
        return []

    freqs = [music.A4_HZ * 2 ** ((music.LETTER_SEMI[l] + a + 12 * (o + 1) - 69) / 12)
             for l, a, o, _ in parsed]
    force = {"1포지션": 1, "3포지션": 3}.get(position)
    #| 갈래  포지션을 못박았나 ? 그 포지션에서 닿는 줄로 (손은 그대로, 활만 옮김) : 편한 줄로
    if force and not forced_string:
        reach = music.CROSS_REACH[force]
        base = next((s["name"] for s in music.STRINGS
                     if reach[0] - 0.3 <= music.semi_on(freqs[0], s) <= reach[1] + 0.3),
                    names_fallback(freqs[0]))
        names = music.pick_strings(freqs, base, reach, open_ok=(force == 1))
    else:
        names = pick_strings(freqs, forced_string)

    # 같은 줄이 이어지는 덩어리 안에서만 포지션을 정합니다
    place = [None] * len(parsed)
    i = 0
    while i < len(parsed):
        j = i
        while j < len(parsed) and names[j] == names[i]:
            j += 1
        st = music.STRING_BY_NAME[names[i]]
        semis = [max(0, int(round(_semi_on(freqs[k], st)))) for k in range(i, j)]
        for k, pf in zip(range(i, j), music.assign_positions(semis, force)):
            place[k] = pf
        i = j

    sig, sig_notes = key_of(key)
    beat = 60.0 / bpm

    notes, t = [], 0.0
    for idx, (letter, alter, octave, beats) in enumerate(parsed):
        in_key = letter in sig_notes
        key_alter = (1 if sig == "♯" else -1) if in_key else 0
        acc = "" if alter == key_alter else ("♯" if alter > 0 else
                                             ("♭" if alter < 0 else "♮"))
        st = music.STRING_BY_NAME[names[idx]]
        pos, finger = place[idx]
        freq = freqs[idx]
        notes.append({
            "letter": letter, "octave": octave, "acc": acc,
            "name": letter + ("#" if alter > 0 else "b" if alter < 0 else "")
                    + str(octave),
            "ko": music.KO_NAME[letter] + ("♯" if alter > 0 else
                                           "♭" if alter < 0 else ""),
            "semi": max(0, int(round(_semi_on(freq, st)))), "freq": freq,
            "mm": music.mm_from_freq(freq, st["freq"]),
            "position": pos, "finger": finger,
            "string": st["name"],
            "t": t, "dur": beats * beat, "beat": idx,
        })
        t += beats * beat

    #| 반복  음마다 — 슬러 하나 = 활 한 번, 그룹마다 다운↔업
    for i, n in enumerate(notes):
        g = i // slur
        n["slur"] = g
        n["slur_size"] = slur
        n["slur_head"] = (i % slur == 0)
        n["bow"] = "down" if g % 2 == 0 else "up"
    return notes


# ── 조표 고르기 ──────────────────────────────────────────────
KEYS = [("조표 없음 (다장조 · 가단조)", 0),
        ("♯ 1개 (사장조 · 마단조)", 1),
        ("♯ 2개 (라장조 · 나단조)", 2),
        ("♯ 3개 (가장조 · 올림바단조)", 3),
        ("♯ 4개 (마장조 · 올림다단조)", 4),
        ("♭ 1개 (바장조 · 라단조)", -1),
        ("♭ 2개 (내림나장조 · 사단조)", -2),
        ("♭ 3개 (내림마장조 · 다단조)", -3)]


def key_of(n: int):
    """조표 개수 → (기호, 붙는 음들).  music.key_signature 와 같은 모양."""
    #| 갈래  ♯쪽인가 ? F C G D A E B 순으로 자른다 : B E A D G C F 순으로
    if n >= 0:
        return "♯", music.SHARP_ORDER[:n]
    return "♭", music.FLAT_ORDER[:-n]


def guess_key(parsed) -> int:
    """적은 음들만 보고 조표를 짐작합니다 (사진·파일로 들어올 때 편하게)."""
    #| 흐름  올림·내림이 붙은 음들을 조표 순서와 맞춰 본다
    #| 갈래  올림·내림이 하나도 없나 ? 조표 없음 : 계속한다
    #| 갈래  올림과 내림이 섞였나 ? 조표 없음 (임시표로 다 적습니다) : 계속한다
    #| 반복  적은 것부터 (♯1 → ♯4 / ♭1 → ♭3)
    #| 갈래     적힌 올림내림이 그 조표로 다 설명되나 ? 그 조표 : 다음
    #| 출력  조표 개수 (설명 안 되면 0)
    used = {}
    for letter, alter, _, _ in parsed:
        if alter:
            used[letter] = alter
    if not used:
        return 0
    signs = set(used.values())
    if len(signs) > 1:                       # ♯과 ♭이 섞이면 조표로 못 묶습니다
        return 0
    # 조표는 **가장 적게 붙는 것**이 맞습니다. ♯3으로 되면 ♯4로 적지 않습니다.
    cands = (1, 2, 3, 4) if signs == {1} else (-1, -2, -3)
    for n in cands:
        if set(used) <= set(key_of(n)[1]):
            return n
    return 0


# ══════════════════════════════════════════════════════════════
#  4. 파일에서 — MusicXML
# ══════════════════════════════════════════════════════════════
def from_musicxml(data: bytes):
    """MusicXML(.xml / .musicxml / 압축된 .mxl) → 적은 글.

    MuseScore·Finale·Sibelius 가 전부 내보낼 수 있는 형식입니다.
    **내가 직접 입력해 만든 악보**를 옮겨 오는 길입니다.
    """
    #| 흐름  MusicXML 을 읽어 음 하나씩 뽑는다
    #| 갈래  압축된 mxl 인가 ? 안에서 xml 을 꺼낸다 : 그대로 읽는다
    #| 단계  한 박이 몇 divisions 인지 읽는다 (길이의 기준)
    #| 반복  <note> 마다
    #| 갈래     쉼표인가 ? 건너뛴다 : 음이름·올림내림·옥타브·길이를 담는다
    #| 갈래     화음(chord)인가 ? 건너뛴다 : 담는다 (바이올린 한 줄 연습이라 단선율만)
    #| 출력  음 목록
    if data[:2] == b"PK":                     # .mxl = zip
        import zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name = next((n for n in z.namelist()
                         if n.endswith((".xml", ".musicxml")) and "META-INF" not in n),
                        None)
            if not name:
                raise ValueError("압축 안에 악보 파일이 없습니다.")
            data = z.read(name)

    root = ET.fromstring(data)
    div = 1
    out = []
    for el in root.iter():
        if el.tag == "divisions" and (el.text or "").strip():
            div = float(el.text)
        if el.tag != "note":
            continue
        if el.find("rest") is not None or el.find("chord") is not None:
            continue
        p = el.find("pitch")
        if p is None:
            continue
        letter = (p.findtext("step") or "C").upper()
        alter = int(float(p.findtext("alter") or 0))
        octave = int(p.findtext("octave") or 4)
        dur = float(el.findtext("duration") or div)
        out.append((letter, max(-1, min(1, alter)), octave, max(0.125, dur / div)))
    if not out:
        raise ValueError("음을 하나도 못 찾았습니다.")
    return out


# ══════════════════════════════════════════════════════════════
#  5. 사진에서 — 읽고 바로 버립니다
# ══════════════════════════════════════════════════════════════
# 사진은 **어디에도 저장하지 않습니다.**
#   · 디스크에 쓰지 않고 메모리에서만 다룹니다
#   · 읽고 나면 텍스트만 남기고 사진은 버립니다
#   · 서버 로그에도 남기지 않습니다
# 저작권은 "복제"가 문제이므로, 남는 복제본이 없게 만드는 것이 설계의 핵심입니다.

PROMPT = """이 사진은 바이올린 연습용 악보입니다.
가장 위 성부(단선율)의 음을 처음부터 순서대로 읽어 주세요.

규칙
- 조표와 임시표를 반영한 **실제 소리나는 음**으로 적습니다.
- 옥타브는 가운데 도를 C4 로 하는 국제 표기(C4, A4 …)를 씁니다.
- 길이는 4분음표를 1.0 으로 한 상대값입니다 (2분음표 2.0, 8분음표 0.5).
- 쉼표·화음·반복기호는 무시하고, 단선율만 순서대로 적습니다.
- 설명을 쓰지 말고 JSON 만 출력합니다.

형식
{"notes":[{"step":"A","alter":0,"octave":4,"beats":1.0}, ...]}"""

API = "https://generativelanguage.googleapis.com/v1beta"

# 구글은 모델을 자주 갈아치웁니다. 이름을 하나 박아 두면 몇 달 뒤 404 가 납니다.
# (이 앱도 gemini-2.0-flash 로 굳어 있다가 그렇게 죽었습니다)
#
# 그래서 두 단계로 갑니다.
#   ① 아는 이름부터 차례로 시도한다
#   ② 다 404 면 **API 에게 뭘 쓸 수 있는지 물어본다** (ListModels)
# 이러면 다음에 또 이름이 바뀌어도 앱이 알아서 살아납니다.
# 3.6 Flash 가 악보 사진을 가장 잘 읽었습니다 (직접 써 보고 정했습니다).
# 뒤의 것들은 그것이 막혔을 때를 위한 대비입니다.
PREFERRED = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest",
             "gemini-3.6-flash-lite", "gemini-3.5-flash-lite",
             "gemini-flash-lite-latest"]

_FOUND = {}          # 한 번 찾은 모델은 기억해 둡니다 (키마다)


def _call(url: str, api_key: str, body=None, timeout: int = 60):
    """구글에 한 번 요청.

    키를 주소(?key=)가 아니라 **헤더**로 보냅니다.
    새로 나온 `AQ.` 로 시작하는 키는 주소에 실으면 거절당하는 일이 있습니다.
    """
    #| 흐름  키를 헤더에 싣고 한 번 요청한다
    #| 갈래  보낼 몸통이 있나 ? POST : GET
    #| 출력  받은 JSON
    hdr = {"x-goog-api-key": api_key.strip()}
    data = None
    if body is not None:
        hdr["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def list_models(api_key: str):
    """이 키로 쓸 수 있는 모델 이름들 — 사진을 넣을 수 있는 것만."""
    #| 흐름  이 키가 쓸 수 있는 모델을 물어본다
    #| 호출  _call → 모델 목록
    #| 반복  모델마다 — generateContent 를 지원하나
    #| 출력  이름 목록 (flash·lite 가 앞에 오게)
    got = _call(f"{API}/models", api_key, timeout=20)
    names = [m["name"].split("/")[-1] for m in got.get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]

    def rank(n):
        #| 갈래  악보를 잘 읽는 것부터 — flash → flash-lite → 나머지
        #|       (lite 는 싸지만 흐릿한 악보에서 자주 틀립니다)
        return (0 if ("flash" in n and "lite" not in n) else
                1 if "flash" in n else 2,
                0 if "latest" in n else 1, n)
    return sorted(names, key=rank)


def _models_to_try(api_key: str):
    """시도할 모델 순서 — 기억해 둔 것 → 아는 이름 → 물어본 것."""
    #| 흐름  어떤 모델을 어떤 차례로 시도할지 정한다
    #| 갈래  전에 성공한 것이 있나 ? 그것부터 : 아는 이름부터
    #| 갈래  아는 이름이 다 막혔나 ? API 에 물어본다 : 넘어간다
    #| 출력  모델 이름 목록
    seen, out = set(), []
    for n in [_FOUND.get(api_key)] + PREFERRED:
        if n and n not in seen:
            seen.add(n); out.append(n)
    try:
        for n in list_models(api_key):
            if n not in seen:
                seen.add(n); out.append(n)
    except Exception:
        pass                       # 못 물어봐도 아는 이름으로는 계속 시도합니다
    return out


def _why(code: int) -> str:
    """HTTP 숫자를 사람 말로. 404 를 '키를 확인하라'고 하면 엉뚱한 데를 뒤집니다."""
    #| 갈래  숫자가 무엇인가 ? 그에 맞는 설명 : 일반적인 설명
    return {
        400: "요청이 거절됐습니다 — 키 형식이 맞는지 확인해 주세요.",
        401: "키가 인증되지 않았습니다 — 새 키를 만들어 넣어 주세요.",
        403: "키에 권한이 없습니다 — Google AI Studio 에서 키를 새로 만들어 주세요.",
        404: "쓸 수 있는 모델을 찾지 못했습니다 — 키는 맞는데 모델 이름이 막혔습니다.",
        429: "오늘 쓸 수 있는 양을 다 썼습니다 — 잠시 뒤 다시 해 주세요.",
    }.get(code, f"인식 서비스가 거절했습니다 ({code}).")


def from_image(image_bytes: bytes, api_key: str, mime: str = "image/jpeg",
               timeout: int = 60):
    """악보 사진 → 적은 글.  사진은 읽고 나서 버립니다.

    인식은 **반드시 틀립니다.** 그래서 결과를 곧바로 쓰지 않고
    글로 돌려주어 사용자가 고치게 합니다.
    """
    #| 흐름  사진을 보내 음 목록을 받고, 사진은 버린다
    #| 입력  사진 바이트 · API 키
    #| 갈래  키가 없나 ? 어떻게 넣는지 알린다 : 계속한다
    #| 단계  사진을 base64 로 실어 싣는다 (저장하지 않습니다)
    #| 호출  _models_to_try → 시도할 모델 차례
    #| 반복  모델마다
    #| 갈래     404 인가 ? 다음 모델로 (이름이 바뀐 것뿐입니다) : 여기서 멈춘다
    #| 갈래  다 막혔나 ? 무엇이 문제인지 숫자로 구분해 알린다 : 계속한다
    #| 갈래  대답이 JSON 인가 ? 음 목록으로 바꾼다 : 무슨 말이 왔는지 알린다
    #| 출력  음 목록  (실패하면 이유를 담은 예외)
    import base64
    if not api_key:
        raise ValueError("Gemini API 키가 없습니다. 아래에 키를 넣어 주세요.")

    body = {
        "contents": [{"parts": [
            {"text": PROMPT},
            {"inline_data": {"mime_type": mime,
                             "data": base64.b64encode(image_bytes).decode()}},
        ]}],
        "generationConfig": {"temperature": 0, "response_mime_type": "application/json"},
    }
    raw, last, tried = None, None, []
    try:
        for name in _models_to_try(api_key):
            tried.append(name)
            try:
                raw = _call(f"{API}/models/{name}:generateContent",
                            api_key, body, timeout)
                _FOUND[api_key] = name          # 다음부터는 이걸 먼저 씁니다
                break
            except urllib.error.HTTPError as e:
                last = e.code
                #| 갈래  모델이 없는 것뿐인가 ? 다음 이름으로 : 더 해 봐야 소용없다
                if e.code not in (404, 400):
                    break
            except Exception as e:
                last = str(e)
                break
    finally:
        image_bytes = None                      # 여기서 사진을 놓습니다

    if raw is None:
        if isinstance(last, int):
            hint = _why(last)
            if last == 404 and tried:
                hint += f"  (시도한 모델: {', '.join(tried[:4])}…)"
            raise ValueError(hint)
        raise ValueError(f"인식 서비스에 닿지 못했습니다 — {last}")

    try:
        txt = raw["candidates"][0]["content"]["parts"][0]["text"]
        got = json.loads(txt)["notes"]
    except Exception:
        raise ValueError("악보를 읽지 못했습니다. 사진을 더 밝고 반듯하게 찍어 주세요.")

    out = []
    for n in got:
        letter = str(n.get("step", "C")).upper()[:1]
        if letter not in music.LETTER_SEMI:
            continue
        out.append((letter, max(-1, min(1, int(n.get("alter", 0) or 0))),
                    int(n.get("octave", 4)), max(0.125, float(n.get("beats", 1)))))
    if not out:
        raise ValueError("음을 하나도 못 찾았습니다.")
    return out


# ══════════════════════════════════════════════════════════════
#  6. 내 악보용 교정 드릴
# ══════════════════════════════════════════════════════════════
# 음계 연습의 드릴(music.drill_*)은 '음계'를 전제로 합니다.
# 내 악보는 음계가 아니므로, **적은 음들을 잘라 쓰는** 방식으로 만듭니다.
OPEN_OF = {"E": ("E", 0, 5), "A": ("A", 0, 4), "D": ("D", 0, 4), "G": ("G", 0, 3)}


def drill_note(parsed, notes, idx):
    """문제 음 하나를 **그 음이 쓰는 줄의 개방현**과 번갈아 짚습니다."""
    #| 흐름  개방현 ↔ 문제 음 을 네 번 번갈아 (개방현은 늘 맞는 기준음)
    #| 출력  (음 목록, 못박을 줄)
    s = notes[idx]["string"]
    o = OPEN_OF[s]
    n = parsed[idx]
    return [(o[0], o[1], o[2], 1.0), (n[0], n[1], n[2], 1.0)] * 4, s


def drill_shift(parsed, notes):
    """손을 옮기는 자리 앞뒤 두 음씩만 잘라 두 번 반복합니다."""
    #| 흐름  이동 직전 2음 + 직후 2음을 두 번
    #| 갈래  옮기는 자리가 있나 ? 그 앞뒤를 자른다 : 없다고 알린다
    sh = music.shift_index(notes)
    if sh is None:
        return None
    return parsed[max(0, sh - 2):sh + 2] * 2


def drill_longtone(notes):
    """가장 많이 쓴 줄의 개방현을 여덟 번 — 활이 흔들리는지 봅니다."""
    #| 흐름  이 악보에서 가장 많이 쓰는 줄을 찾아 개방현만 여덟 음
    cnt = {}
    for n in notes:
        cnt[n["string"]] = cnt.get(n["string"], 0) + 1
    s = max(cnt, key=cnt.get) if cnt else "A"
    o = OPEN_OF[s]
    return [(o[0], o[1], o[2], 1.0)] * 8, s
