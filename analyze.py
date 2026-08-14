"""
녹음 → 숫자.

  ① 소리에서 음높이 뽑기        YIN 알고리즘 (직접 구현, 라이브러리 없음)
  ② 언제 시작했는지 찾기        첫 소리 = 첫 음
  ③ 음마다 평균·편차·박자 내기

평균은 **손가락 자리**, 표준편차는 **활**입니다.
둘을 나눠야 "위치가 틀린 것"과 "흔들린 것"에 다른 처방을 줄 수 있습니다.
"""

import io
import math
import wave

import numpy as np

#| 흐름  녹음 WAV → 음정 궤적 → 음마다 (평균 · 편차 · 박자)

# ══════════════════════════════════════════════════════════════
#  0. 파일 읽기
# ══════════════════════════════════════════════════════════════
def decode_wav(data: bytes):
    """녹음 파일 → (샘플레이트, -1~1 사이의 모노 배열)

    st.audio_input 은 WAV로 돌려주므로 파이썬 기본 모듈만으로 읽힙니다.
    (라이브러리를 안 쓰면 배포가 훨씬 가볍고 빨라집니다)
    """
    #| 흐름  파일 형식을 가려 읽어 모노 파형으로 만든다
    #| 입력  녹음 파일의 바이트
    #| 갈래  WAV 로 읽히나 ? 바로 쓴다 : soundfile 로 한 번 더 시도한다
    #| 갈래  그것도 안 되나 ? 형식 안내를 띄운다 : 파형을 넘긴다
    #| 출력  (샘플레이트, 모노 파형)
    try:
        return _read_wave(data)
    except wave.Error:
        pass
    try:                                    # 혹시 다른 형식이면
        import soundfile as sf
        x, sr = sf.read(io.BytesIO(data), dtype="float64", always_2d=True)
        return sr, x.mean(axis=1)
    except Exception:
        raise ValueError(
            "WAV가 아닌 형식입니다. 브라우저 마이크로 녹음하면 WAV가 됩니다 "
            "(파일을 올렸다면 WAV로 바꿔 주세요)."
        )


def _read_wave(data: bytes):
    with wave.open(io.BytesIO(data), "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())

    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sw == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    elif sw == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128) / 128.0
    else:
        raise ValueError(f"지원하지 않는 형식입니다 ({sw*8}비트)")

    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)      # 스테레오면 합쳐서 모노로
    return sr, x


# ══════════════════════════════════════════════════════════════
#  1. YIN — 소리에서 음높이 뽑기
# ══════════════════════════════════════════════════════════════
def _yin_frame(frame, sr, tau_min, tau_max, thresh=0.13):
    """한 조각(약 40ms)에서 기본 주파수 하나를 찾습니다.

    원리: 파형을 tau만큼 밀어서 자기 자신과 겹쳐 봅니다.
          한 주기만큼 밀었을 때 가장 잘 맞으므로, 그 tau가 주기입니다.
    자기상관만 쓰면 옥타브를 자주 틀리므로,
    YIN이 제안한 '누적 평균 정규화'를 거쳐 낮은 tau 쪽에 불이익을 줍니다.
    """
    #| 흐름  파형 한 조각(약 46ms)에서 기본 주파수 하나를 찾는다
    #| 입력  파형 한 조각 · 찾을 주기 범위
    #| 단계  파형을 tau 만큼 밀어 자기 자신과 겹쳐 본다 (FFT 자기상관)
    #| 단계  차이 함수 d(tau) 를 만든다
    #| 단계  누적 평균으로 정규화한다 — 낮은 tau 에 불이익을 줘 옥타브 오류를 막는다
    #| 갈래  임계값 아래로 떨어지는 골짜기가 있나 ? 그 바닥을 쓴다 : 가장 낮은 곳을 쓴다
    #| 단계  포물선 보간으로 정수 tau 사이를 메운다 — 센트 정밀도의 핵심
    #| 출력  (주파수, 불안정도)
    W = len(frame)
    x = frame - frame.mean()

    size = 1 << (2 * W - 1).bit_length()
    fx = np.fft.rfft(x, size)
    acf = np.fft.irfft(fx * np.conj(fx), size)[:tau_max]

    cs = np.concatenate(([0.0], np.cumsum(x ** 2)))
    taus = np.arange(tau_max)
    d = cs[W - taus] + (cs[W] - cs[taus]) - 2 * acf      # 차이 함수

    # 누적 평균 정규화
    cmnd = np.ones(tau_max)
    run = np.cumsum(d[1:])
    nz = run > 1e-12
    cmnd[1:][nz] = d[1:][nz] * np.arange(1, tau_max)[nz] / run[nz]

    seg = cmnd[tau_min:tau_max]
    below = np.where(seg < thresh)[0]
    if len(below):
        t = below[0]
        while t + 1 < len(seg) and seg[t + 1] < seg[t]:   # 골짜기 바닥까지
            t += 1
        tau = tau_min + t
    else:
        tau = tau_min + int(np.argmin(seg))

    # 포물선 보간 — 정수 tau만 쓰면 센트 단위 정밀도가 안 나옵니다
    if 0 < tau < tau_max - 1:
        a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
        den = a - 2 * b + c
        if abs(den) > 1e-12:
            tau = tau + 0.5 * (a - c) / den

    return sr / tau, float(cmnd[int(round(tau))])


def track_pitch(x, sr, fmin=180.0, fmax=1500.0, hop_ms=10.0, win_ms=46.0):
    """전체 녹음 → (시각, 주파수, 불안정도, 음량) 네 줄기"""
    #| 흐름  녹음 전체를 10ms 간격으로 훑어 음높이 궤적을 만든다
    #| 입력  파형 · 샘플레이트
    #| 반복  10ms 마다 한 조각씩
        #| 호출     _yin_frame → (주파수, 불안정도)
        #| 단계     그 조각의 음량(RMS)도 같이 잰다
    #| 출력  (시각, 주파수, 불안정도, 음량) 네 줄기
    W = int(sr * win_ms / 1000)
    hop = int(sr * hop_ms / 1000)
    tau_min = max(2, int(sr / fmax))
    tau_max = min(W // 2, int(sr / fmin) + 2)

    t, f, ap, rms = [], [], [], []
    for s in range(0, max(0, len(x) - W), hop):
        fr = x[s:s + W]
        r = float(np.sqrt(np.mean(fr ** 2)))
        freq, a = _yin_frame(fr, sr, tau_min, tau_max)
        t.append((s + W / 2) / sr)
        f.append(freq)
        ap.append(a)
        rms.append(r)
    return (np.array(t), np.array(f), np.array(ap), np.array(rms))


# ══════════════════════════════════════════════════════════════
#  2. 분석
# ══════════════════════════════════════════════════════════════
def _fold(c):
    """옥타브 오류를 접습니다. YIN이 한 옥타브 틀리는 일은 흔합니다."""
    #| 흐름  ±600센트 안으로 접어 옥타브 오류를 없앤다
    while c > 600:
        c -= 1200
    while c < -600:
        c += 1200
    return c


def _onset(t, f, good, notes, beat):
    """첫 음이 시작된 시각.

    가장 이른 소리를 그냥 쓰면, 카운트인 메트로놈이 마이크에 섞였을 때
    그 '똑'을 첫 음으로 잡아 버립니다. 그래서 두 가지를 봅니다.

      ① 충분히 이어지는가   — 똑 소리는 0.1초도 못 갑니다
      ② 첫 음과 비슷한가     — 아니면 다음 덩어리를 봅니다
    """
    #| 흐름  이어지는 소리 덩어리를 모아, 첫 음과 맞는 첫 덩어리를 시작으로 삼는다
    #| 입력  시각 · 주파수 · 소리 여부 · 악보 · 한 박의 길이
    #| 단계  소리가 이어지는 덩어리를 찾는다 (짧은 것은 버린다 — 메트로놈·잡음)
    #| 반복  덩어리마다
    #| 갈래     첫 음과 비슷한 높이인가 ? 여기가 시작이다 : 다음 덩어리를 본다
    #| 갈래  맞는 덩어리가 없나 ? 첫 덩어리를 쓴다 : 찾은 곳을 쓴다
    #| 출력  첫 음이 시작된 시각(초)
    hop = float(np.median(np.diff(t))) if len(t) > 2 else 0.01
    need = max(6, int(round(beat * 0.28 / hop)))     # 이만큼 이어져야 '음'
    runs, s = [], None
    for k in range(len(good)):
        if good[k]:
            if s is None:
                s = k
        elif s is not None:
            if k - s >= need:
                runs.append((s, k))
            s = None
    if s is not None and len(good) - s >= need:
        runs.append((s, len(good)))

    if not runs:                                     # 다 짧으면 예전 방식대로
        return float(t[int(np.argmax(good))])

    target = notes[0]["freq"]
    for a, b in runs:
        med = float(np.median(f[a:b]))
        if med > 0 and abs(_fold(1200 * math.log2(med / target))) < 250:
            return float(t[a])
    return float(t[runs[0][0]])


def analyze(data: bytes, notes, bpm: int, tol_cent: float = 12.0,
            tol_ms: float = 40.0):
    """녹음 파일 + 악보 → 음마다의 결과.

    BPM을 아니까 각 음의 시간이 이미 정해져 있습니다.
    첫 소리가 난 자리만 찾으면 나머지는 계산으로 맞출 수 있습니다.
    """
    #| 흐름  녹음 + 악보 → 음마다의 결과
    #| 입력  녹음 WAV · 악보(음 목록) · BPM · 허용 범위
    #| 호출  decode_wav → 파형
    #| 갈래  녹음이 0.3초보다 짧나 ? 안내하고 멈춘다 : 계속한다
    #| 호출  track_pitch → 음높이 궤적
    #| 단계  불안정도와 음량으로 '소리가 난 구간'을 고른다
    #| 갈래  소리가 하나도 없나 ? 마이크를 확인하라고 한다 : 계속한다
    #| 단계  첫 소리가 난 자리를 첫 음의 시작(t0)으로 잡는다 — 정렬 문제가 여기서 사라진다
    #| 반복  악보의 음마다
        #| 단계     BPM 으로 그 음의 시간 구간을 정한다
        #| 갈래     그 구간에 소리가 있나 ? 계속한다 : '소리 없음'으로 두고 넘어간다
        #| 단계     목표 주파수와의 차이를 센트로 바꾼다 (옥타브는 접는다)
        #| 단계     궤적에 담는다 — 리포트의 넷째 층이 된다
        #| 단계     음의 가운데(18~88%)만 잘라 중앙값=평균, 표준편차=흔들림
        #| 단계     목표 근처로 처음 들어온 시각을 찾아 박자 오차를 낸다
    #| 단계  첫 음의 박자를 0으로 놓고 나머지를 상대값으로 바꾼다
    #| 출력  음별 결과 · 궤적 · 정확도 요약
    sr, x = decode_wav(data)
    if len(x) < sr * 0.3:
        raise ValueError("녹음이 너무 짧습니다.")

    t, f, ap, rms = track_pitch(x, sr)
    if len(t) == 0:
        raise ValueError("녹음이 너무 짧습니다.")

    good = (ap < 0.55) & (rms > max(rms.max() * 0.08, 1e-4))
    if not good.any():
        raise ValueError("소리를 못 찾았습니다. 마이크를 확인해 주세요.")

    beat = 60.0 / bpm
    # 첫 음이 난 자리. 조각의 가운데 시각으로 잡히므로 반 조각만큼 당깁니다.
    #| 호출  _onset → 첫 음의 시작 (메트로놈 '똑' 은 걸러집니다)
    t0 = max(0.0, _onset(t, f, good, notes, beat) - 0.023)

    rows, trace = [], []
    for i, n in enumerate(notes):
        a, b = t0 + i * beat, t0 + (i + 1) * beat
        m = good & (t >= a) & (t < b)
        idx = np.where(m)[0]

        if len(idx) < 4:
            rows.append({**n, "cent": None, "std": None, "ms": None,
                         "ok": False, "detected": False})
            continue

        c_all = np.array([_fold(1200 * math.log2(f[k] / n["freq"])) for k in idx])
        for k, cv in zip(idx, c_all):
            trace.append((i + (t[k] - a) / beat, float(cv)))

        # 음의 **가운데만** 씁니다.
        #   앞: 활을 걸고 자리를 잡는 중이라 아직 그 음이 아님
        #   뒤: 다음 음으로 넘어가는 중이라 이미 그 음이 아님
        # 이걸 안 자르면 옆 음이 섞여 편차가 실제의 대여섯 배로 나옵니다.
        lo = int(len(c_all) * 0.18)
        hi = max(lo + 2, int(len(c_all) * 0.88))
        core = c_all[lo:hi]
        mean = float(np.median(core))
        std = float(np.std(core))

        # 실제로 언제 이 음에 들어왔는지 → 박자 오차
        sw = good & (t >= a - beat * 0.5) & (t < a + beat * 0.5)
        si = np.where(sw)[0]
        ms = None
        for k in si:
            cv = _fold(1200 * math.log2(f[k] / n["freq"]))
            if abs(cv) < 60:
                ms = (t[k] - a) * 1000
                break
        if ms is None:
            ms = 0.0

        rows.append({**n, "cent": mean, "std": std, "ms": float(ms),
                     "ok": abs(mean) <= tol_cent, "detected": True})

    # 박자는 **첫 음을 기준으로 한 상대값**입니다.
    # 녹음을 언제 시작했는지는 연주와 상관없으니, 첫 음을 0으로 놓고 봅니다.
    base = next((r["ms"] for r in rows if r["detected"]), 0.0)
    for r in rows:
        if r["detected"]:
            r["ms"] -= base

    det = [r for r in rows if r["detected"]]
    n_det = max(1, len(det))
    return {
        "rows": rows,
        "trace": trace,
        "t0": t0,
        "duration": float(len(x) / sr),
        "pitch_pct": 100.0 * sum(1 for r in det if r["ok"]) / n_det,
        "time_pct": 100.0 * sum(1 for r in det if abs(r["ms"]) <= tol_ms) / n_det,
        "mean_cent": float(np.mean([r["cent"] for r in det])) if det else 0.0,
        "bow_std": float(np.mean([r["std"] for r in det])) if det else 0.0,
        "missing": [r["ko"] for r in rows if not r["detected"]],
    }


# ══════════════════════════════════════════════════════════════
#  3. 데모 연주 — 마이크 없이 흐름을 확인할 때
# ══════════════════════════════════════════════════════════════
def demo_wav(notes, bpm: int, sr: int = 22050, seed: int = 3) -> bytes:
    """일부러 조금 틀리게 연주한 소리를 만듭니다 (마이크 없이 흐름 확인용).

    학생이 실제로 자주 하는 실수를 넣었습니다.
      · 뒤로 갈수록 음이 낮아짐        — 손이 너트 쪽으로 흘러내림
      · 포지션을 옮긴 직후 크게 내려감  — 손이 덜 올라감
      · 옮긴 다음 음이 늦게 나옴        — 손 옮기는 데 시간이 걸림
      · 뒤로 갈수록 흔들림이 커짐       — 활이 지침
    """
    #| 흐름  학생이 자주 하는 실수를 흉내 낸 소리를 만든다 (마이크 없이 확인용)
    #| 입력  악보(음 목록) · BPM
    #| 단계  음마다 시작 밀림을 정한다 — 포지션 옮긴 자리는 크게 늦게
    #| 반복  음마다
        #| 단계     뒤로 갈수록 낮아지는 치우침 + 활 흔들림을 센트로 만든다
        #| 갈래     포지션 옮긴 직후인가 ? 크게 내려간다 : 그대로 둔다
        #| 단계     그 센트대로 주파수를 흔들며 배음을 쌓아 소리를 만든다
    #| 출력  WAV 바이트
    rnd = np.random.default_rng(seed)
    beat = 60.0 / bpm
    n = len(notes)
    shift = next((i for i in range(1, n)
                  if notes[i]["position"] != notes[i - 1]["position"]), None)

    # 음마다의 시작 밀림(초). 포지션 옮긴 자리에서 크게 늦습니다.
    off = [float(rnd.normal(0, 0.018)) for _ in range(n)]
    off[0] = 0.0
    if shift is not None:
        off[shift] += 0.085

    edges = [i * beat + off[i] for i in range(n)] + [n * beat]
    out = np.zeros(int(sr * (n * beat + 0.2)))
    phase = 0.0

    for i, nt in enumerate(notes):
        s0, s1 = int(edges[i] * sr), int(edges[i + 1] * sr)
        L = max(1, s1 - s0)
        bias = float(rnd.normal(-14 * i / max(1, n - 1), 7))
        wob = 3 + 5 * i / max(1, n - 1)
        for k in range(L):
            u = k / L
            c = bias + 24 * math.exp(-u * 14) * math.sin(u * 40 + i) \
                + wob * math.sin(u * 19 + i)
            if shift is not None and i == shift and u < 0.25:
                c -= 32 * (1 - u / 0.25)
            fr = nt["freq"] * 2 ** (c / 1200)
            phase += 2 * math.pi * fr / sr
            sig = sum(math.sin(phase * h) / h ** 1.35 for h in range(1, 9))
            env = min(1.0, u / 0.04) * min(1.0, (1 - u) / 0.07)
            out[s0 + k] = sig * env

    out /= np.max(np.abs(out)) * 1.05
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 30000).astype("<i2").tobytes())
    return buf.getvalue()


def reference_wav(notes, bpm: int, sr: int = 22050) -> bytes:
    """악보를 **정확한 음정·박자로** 소리 냅니다 — 연주 전에 먼저 들어 보는 용도.

    demo_wav 는 일부러 틀리게 연주합니다(분석 흐름 확인용).
    이건 반대로, 어디 하나 안 틀린 기준 소리입니다.

    바이올린 소리를 흉내 내려는 게 아니라 **음정과 박자를 귀로 확인**하는 것이
    목적이라, 배음을 몇 개 쌓고 활 모양의 세기 곡선만 씌웁니다.
    """
    #| 흐름  음 목록 → 정확한 기준 연주 WAV
    #| 입력  음 목록 · BPM
    #| 반복  음마다
        #| 단계     그 높이로 배음을 쌓아 소리를 만든다 (위 배음일수록 약하게)
        #| 단계     활 모양 세기 곡선 — 걸리고 · 유지되고 · 놓임
        #| 갈래     슬러로 이어지는 음인가 ? 앞뒤를 붙인다 : 사이를 조금 띈다
    #| 출력  WAV 바이트
    total = max(n["t"] + n["dur"] for n in notes) + 0.35
    out = np.zeros(int(sr * total))
    phase = 0.0

    for i, n in enumerate(notes):
        # 슬러로 묶인 다음 음이면 끊지 않고 이어 붙입니다 (한 활이니까)
        tied = (i + 1 < len(notes) and not notes[i + 1]["slur_head"])
        gap = 0.0 if tied else min(0.06, n["dur"] * 0.12)
        s0 = int(n["t"] * sr)
        L = max(1, int((n["dur"] - gap) * sr))
        k = np.arange(L)
        u = k / L

        w = 2 * math.pi * n["freq"] / sr
        ph = phase + w * k
        sig = sum(np.sin(ph * h) / h ** 1.45 for h in range(1, 8))
        phase = float(ph[-1] + w) % (2 * math.pi)

        # 활: 0.04초 걸리고 → 유지 → 0.05초 놓임
        env = np.minimum(1.0, u / max(1e-6, 0.04 / max(n["dur"], 1e-6)))
        env *= np.minimum(1.0, (1 - u) / max(1e-6, 0.05 / max(n["dur"], 1e-6)))
        out[s0:s0 + L] += sig * env

    peak = float(np.max(np.abs(out))) or 1.0
    out = out / (peak * 1.08)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 28000).astype("<i2").tobytes())
    return buf.getvalue()
