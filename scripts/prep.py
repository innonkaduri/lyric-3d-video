#!/usr/bin/env python3
"""Song section -> timing data for the 3D lyric engine (lib/data.js) + the audio stem.

Reads PROJECT/song.json:
  {"title": "Song Title", "artist": "Artist",  # shown on the opening title + end tag
   "start": 84.546, "end": 123.18,        # section in the song (seconds)
   "bpm": 161.499, "bar_eighths": 8,      # grid unit = one tracked beat; bar length in units
   "bar0": 1.486,                          # first downbeat, in CLIP time
   "drop": 13.374, "stop": 12.75,          # chorus hit / the silence before it (clip time; null if none)
   "tail": 1.4}                            # visual hold after the audio cut
and PROJECT/work/songw.json (whisper words, from analyze_song.py).

Display text comes ONLY from PROJECT/lyrics.txt (one sung line per line; [Section]
headers ignored) — supplied by the user. Without it, placeholder words keep the layout
testable. Lyric text is never printed.

usage: prep.py PROJECT_DIR
"""
import json, pathlib, re, difflib, subprocess, sys
import numpy as np, librosa, soundfile as sf

PH = ["NEON", "PAPER", "ORBIT", "SIGNAL", "VELVET", "STATIC", "MIRROR", "ECHO", "GLASS", "CIRCUIT", "SATELLITE", "HONEY"]


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("е", "e"))


def main(root):
    root = pathlib.Path(root)
    cfg = json.load(open(root / "song.json"))
    A, B = cfg["start"], cfg["end"]
    E8 = 60 / cfg["bpm"]; BAR = E8 * cfg.get("bar_eighths", 8); BAR0 = cfg["bar0"]
    DROP = cfg.get("drop"); STOP = cfg.get("stop"); TAIL = cfg.get("tail", 1.4)
    clip = root / "work/clip.wav"
    if not clip.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(A), "-to", str(B), "-i", str(root / "work/song.mp3"), "-ar", "48000", "-ac", "2", str(clip)], check=True)
    d = json.load(open(root / "work/songw.json"))
    ws = [(s["offsets"]["from"] / 1000 - A, s["text"].strip()) for s in d["transcription"] if s["text"].strip()]
    ws = [w for w in ws if 0 <= w[0] <= B - A]
    # snap each word onset to the nearest onset in the vocal band (±0.12 s)
    y, sr = librosa.load(clip, sr=22050, mono=True)
    S = np.abs(librosa.stft(librosa.effects.harmonic(y), n_fft=1024, hop_length=128))
    f = librosa.fft_frequencies(sr=sr, n_fft=1024)
    env = np.maximum(0, np.diff(np.log1p(S[(f > 250) & (f < 3500)].sum(0)), prepend=0))
    on = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=128, units="time")
    times = []
    for a, _ in ws:
        c = on[np.abs(on - a) < 0.12]
        times.append(float(c[np.argmin(np.abs(c - a))]) if len(c) else a)
    for i in range(1, len(times)):
        times[i] = max(times[i], times[i - 1] + 0.06)

    lyr = root / "lyrics.txt"
    if lyr.exists():
        lines = [l.strip() for l in lyr.read_text().replace("е", "e").splitlines() if l.strip() and not l.strip().startswith("[")]
        toks = [l.split() for l in lines]; flat = [t for l in toks for t in l]
        sm = difflib.SequenceMatcher(None, [norm(t) for t in flat], [norm(w[1]) for w in ws], autojunk=False)
        tmap = {blk.a + k: blk.b + k for blk in sm.get_matching_blocks() for k in range(blk.size)}
        known = sorted(tmap); T = []
        for i in range(len(flat)):
            if i in tmap: T.append(times[tmap[i]]); continue
            lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
            if lo is None: T.append(times[tmap[hi]] - 0.2 * (hi - i))
            elif hi is None: T.append(times[tmap[lo]] + 0.25 * (i - lo))
            else: T.append(times[tmap[lo]] + (times[tmap[hi]] - times[tmap[lo]]) * (i - lo) / (hi - lo))
        src = "lyrics.txt"
        print(f"lyrics.txt: {len(lines)} lines, {len(flat)} words, {len(tmap)} matched to the vocal")
    else:
        # placeholder lines: split the sung words at pauses > 0.35 s
        toks, cur, k = [], [], 0
        for i, t in enumerate(times):
            if cur and t - times[i - 1] > 0.35: toks.append(cur); cur = []
            cur.append(PH[k % len(PH)]); k += 1
        if cur: toks.append(cur)
        T = times; src = "placeholder"
        print(f"lyrics.txt missing -> {len(toks)} placeholder lines")
    out, k = [], 0
    for li, l in enumerate(toks):
        ww = []
        for w in l:
            ww.append({"w": w, "t": round(T[k] if k < len(T) else T[-1] + 0.3, 3)}); k += 1
        out.append({"i": li, "t0": ww[0]["t"], "words": ww})
    for li in range(len(out)):
        out[li]["t1"] = round(out[li + 1]["t0"] if li + 1 < len(out) else out[li]["words"][-1]["t"] + 1.0, 3)
    dur = round(B - A + TAIL, 3)
    beats = [round(BAR0 + k * E8, 3) for k in range(-16, 2000) if 0 <= BAR0 + k * E8 < dur]
    bars = [round(BAR0 + k * BAR, 3) for k in range(-2, 400) if 0 <= BAR0 + k * BAR < dur]
    # final audio + audio-reactive envelopes (60 fps) on it
    yy, sr2 = sf.read(clip)
    fo, fi = int(0.9 * sr2), int(0.02 * sr2)
    yy = yy.copy(); yy[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2; yy[:fi] *= np.linspace(0, 1, fi)[:, None]
    full = np.vstack([yy, np.zeros((int(TAIL * sr2), 2))])
    (root / "assets/audio").mkdir(parents=True, exist_ok=True)
    sf.write(root / "assets/audio/song.wav", full, sr2, subtype="PCM_16")
    ya = librosa.resample(full.mean(1), orig_sr=sr2, target_sr=22050)
    Sa = np.abs(librosa.stft(ya, n_fft=1024, hop_length=int(22050 / 60))); fa = librosa.fft_frequencies(sr=22050, n_fft=1024)
    def envf(lo, hi):
        e = Sa[(fa > lo) & (fa < hi)].sum(0); e = np.maximum(0, np.diff(e, prepend=e[0])); e = e / (np.percentile(e, 99) + 1e-9)
        o, v = np.zeros_like(e), 0
        for i, x in enumerate(np.clip(e, 0, 1)): v = max(x, v * 0.82); o[i] = v
        return [round(float(x), 3) for x in o]
    data = {"title": cfg.get("title", ""), "artist": cfg.get("artist", ""), "env": {"kick": envf(30, 150), "hat": envf(2000, 8000)}, "hook": {"len": 0, "rew": 0, "from": 0},
            "dur": dur, "main": dur, "audio": round(B - A, 3), "bpm": cfg["bpm"], "e8": round(E8, 5), "bar": round(BAR, 4),
            "drop": DROP if DROP is not None else 1e9, "stop": STOP if STOP is not None else 1e9,
            "beats": beats, "bars": bars, "lines": out, "src": src}
    (root / "lib/data.js").write_text("// generated by prep.py — do not edit\nwindow.SONG = " + json.dumps(data, ensure_ascii=False) + ";\n")
    idx = root / "index.html"
    idx.write_text(re.sub(r'data-duration="[0-9.]+"', f'data-duration="{dur}"', idx.read_text()))
    print("dur", dur, "lines", [(l["t0"], len(l["words"])) for l in out])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
