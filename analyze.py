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

# ══════════════════════════════════════════════════════════════
#  0. 파일 읽기
# ══════════════════════════════════════════════════════════════
def decode_wav(data: bytes):
    """녹음 파일 → (샘플레이트, -1~1 사이의 모노 배열)

    st.audio_input 은 WAV로 돌려주므로 파이썬 기본 모듈만으로 읽힙니다.
    (라이브러리를 안 쓰면 배포가 훨씬 가볍고 빨라집니다)
    """
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
    while c > 600:
        c -= 1200
    while c < -600:
        c += 1200
    return c


def analyze(data: bytes, notes, bpm: int, tol_cent: float = 12.0,
            tol_ms: float = 40.0):
    """녹음 파일 + 악보 → 음마다의 결과.

    BPM을 아니까 각 음의 시간이 이미 정해져 있습니다.
    첫 소리가 난 자리만 찾으면 나머지는 계산으로 맞출 수 있습니다.
    """
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
    # 첫 소리가 난 자리. 조각의 가운데 시각으로 잡히므로 반 조각만큼 당깁니다.
    t0 = max(0.0, float(t[np.argmax(good)]) - 0.023)

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
