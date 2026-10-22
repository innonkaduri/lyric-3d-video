#!/usr/bin/env python3
"""Map a song before cutting a lyric video: tempo grid, downbeat phase, loudness
structure, drop candidates, and where given keywords are sung.

Prints TIMES AND NUMBERS ONLY — never the transcribed lyric text (song lyrics are
copyrighted; the display text must come from the user's own lyrics file).

usage: analyze_song.py PROJECT_DIR SONG.mp3 [--keywords first,last]
writes PROJECT_DIR/work/song.mp3 (copy), work/song16.wav, work/songw.json (whisper words)
"""
import argparse, json, pathlib, re, shutil, subprocess
import numpy as np, librosa

MODEL = pathlib.Path.home() / ".cache/hyperframes/whisper/models/ggml-large-v3.bin"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("song"); ap.add_argument("--keywords", default="")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()
    work = pathlib.Path(a.project) / "work"; work.mkdir(parents=True, exist_ok=True)
    song = work / "song.mp3"
    if not song.exists():
        shutil.copy(a.song, song)
    y, sr = librosa.load(song, sr=22050, mono=True)
    dur = len(y) / sr
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    ibi = float(np.median(np.diff(beats)))
    print(f"duration {dur:.2f}s  tracker tempo {float(np.atleast_1d(tempo)[0]):.2f} BPM  median beat {ibi:.4f}s ({60/ibi:.2f} BPM)")
    # 8-phase kick/snare pattern on the tracked grid: tells you which beat is the downbeat
    # and whether the 'beat' is really an eighth (snare every 4 tracked beats => half-time feel).
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=256)); f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    fr = librosa.time_to_frames(beats, sr=sr, hop_length=256); fr = np.clip(fr, 0, S.shape[1] - 1)
    lo = S[(f > 30) & (f < 150)].sum(0)[fr]; mid = S[(f > 1500) & (f < 5000)].sum(0)[fr]
    print("phase  kick  snare   (first tracked beat at %.3fs)" % beats[0])
    for ph in range(8):
        print(f"  {ph}   {lo[ph::8].mean():7.0f} {mid[ph::8].mean():7.0f}")
    # loudness per 2 s and drop candidates (a dip followed by a jump)
    h = sr * 2; n = len(y) // h
    r = 20 * np.log10(np.sqrt((y[: n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)
    print("loudness/2s:", " ".join(f"{i*2}:{v:.0f}" for i, v in enumerate(r)))
    q = sr // 4; m = len(y) // q
    rq = 20 * np.log10(np.sqrt((y[: m * q].reshape(m, q) ** 2).mean(1)) + 1e-9)
    drops = [i * 0.25 for i in range(2, m) if rq[i - 1] < rq[i] - 7 and rq[i - 2] < rq[i] - 7]
    print("drop candidates (s):", [round(x, 2) for x in drops[:40]])
    # whisper words (plain clock — DTW squeezes timing under music)
    w16 = work / "song16.wav"; wj = work / "songw.json"
    if not wj.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(song), "-ar", "16000", "-ac", "1", str(w16)], check=True)
        subprocess.run(["whisper-cli", "-m", str(MODEL), "-l", a.lang, "-f", str(w16), "-ml", "1", "-sow", "-ojf", "-of", str(work / "songw")],
                       check=True, capture_output=True)
    d = json.load(open(wj))
    ws = [(s["offsets"]["from"] / 1000, re.sub(r"[^a-z0-9]", "", s["text"].lower())) for s in d["transcription"] if s["text"].strip()]
    print(f"whisper: {len(ws)} words")
    for k in [k.strip().lower() for k in a.keywords.split(",") if k.strip()]:
        print(f"  '{k}' sung at:", [round(t, 2) for t, w in ws if w == re.sub(r'[^a-z0-9]', '', k)])


if __name__ == "__main__":
    main()
