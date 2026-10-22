---
name: lyric-3d-video
description: Make or edit a studio-grade 3D kinetic-typography lyric video (vertical Reels/TikTok/Shorts) from a song and its lyrics — real extruded 3D letters synced word-by-word to the vocal, beat-locked camera moves, motion blur, lens depth of field, whip cuts, glossy 3D elements, drop shockwaves — rendered with HyperFrames + Three.js. Use this whenever the user wants a lyric video, kinetic type for a song chorus, "words flying in 3D to the music", an After-Effects/Cinema-4D-style animated lyric clip, or asks to re-edit, re-sync, re-time, restyle or re-render one — even if they only say "make the chorus video crazier" or "sync it to the words".
---

# 3D lyric video

A song section + its lyrics become a 30–60 s vertical video in which every sung word lands as a real 3D object,
on the beat, inside one continuous 3D world. The engine is the template in `assets/template/` (built for a
12-line chorus — see `references/engine.md` §5 to fit another song).

Read `references/lessons.md` before you design anything — it holds what the user explicitly asked for and
rejected, and the technical traps that each cost a render round. Read `references/engine.md` before you
edit `compositions/world.html`.

## Rights, first
Song lyrics are copyrighted. Never type them from memory, and never put the whisper transcript on screen or
in your replies. The words that appear in the video come from lyrics the user gives you: if they paste them,
save their text to `PROJECT/lyrics.txt`; scripts print times and counts, not text. Remind the user that
platforms may mute uploaded songs and deliver a no-music copy as well.

## Workflow

### 1. Project
```bash
~/.claude/skills/lyric-3d-video/scripts/new_project.sh ~/Videos/<name>
```
Copies the engine, vendored three.js/gsap (renders work offline), fonts, and exports the 3D glyph outlines
(system fonts: Futura Condensed ExtraBold, Avenir Next Condensed, Bodoni 72, SignPainter, Arial Rounded).

### 2. Map the song
```bash
python3 ~/.claude/skills/lyric-3d-video/scripts/analyze_song.py PROJECT SONG.mp3 --keywords word1,word2
```
Prints tempo, an 8-phase kick/snare table, loudness per 2 s, drop candidates, and when each keyword is sung.
Use keywords from the user's lyrics (first/last words of the section) to find every occurrence of the chorus;
pick the strongest one (usually the loudest that ends cleanly before a breakdown), 30–45 s long.
Decide the grid: if the snare lands every 4 tracked beats, the tracked beat is an eighth and a bar is 8 of them.
The downbeat is the kick phase that a stop-then-hit at the chorus lands on. Then write `PROJECT/song.json`:
```json
{"title": "Song Title", "artist": "Artist", "start": 84.546, "end": 123.18, "bpm": 161.499, "bar_eighths": 8, "bar0": 1.486, "drop": 13.374, "stop": 12.75, "tail": 1.4}
```
(`bar0`, `drop`, `stop` are in clip time = song time − start. Use `null` for no drop/stop.)

### 3. Sync
Save the user's lyrics to `PROJECT/lyrics.txt` (one sung line per line; `[Chorus]` headers are ignored), then
```bash
python3 ~/.claude/skills/lyric-3d-video/scripts/prep.py PROJECT
```
It cuts the clip, aligns every lyric word to the vocal, writes `lib/data.js`, the audio stem, audio-reactive
kick/hat envelopes, and the index duration. Expect "N words, N matched"; fewer matches means the lyrics file
differs from what is sung — check it with the user instead of guessing.

### 4. Direct the shots
Edit `compositions/world.html` (see `references/engine.md` §5 to remap the template to the new line count).
One shot per sung line, each a different recipe, each in its own set. Principles the user cares about:
the current words are always readable on screen; strong 3D depth (angled type, sway, elements at several
depths, DOF); the drop is the biggest moment and has its sung words on it; one or two lyric-tied 3D
elements; whip cuts, not long transitions.

### 5. Review loop (fast) — before every full render
```bash
cd PROJECT && npx hyperframes@0.8.161 snapshot . --at 0.0,2.5,<each line start>,<drop>,<end> --no-end -o work/snap --describe false --timeout 120000
```
Read `work/snap/contact-sheet*.jpg`. Look for: empty frames, cropped words, mirrored text, a prop covering
words, unreadable blur at cuts. Fix and re-snapshot only the affected times.

### 6. Render + deliver
```bash
~/.claude/skills/lyric-3d-video/scripts/render_and_encode.sh PROJECT <name>_v1
```
≈7 min per 40 s. Produces `_master` (huge, grain), `_upload` (<30 MB, two-pass) and `_upload_nomusic`.
Pull ~16 frames from the master into a contact sheet and check them before sending. Give the user the `_upload` file
and tell them what changed, the files, and anything you saw but did not fix.

## Requirements
macOS (the 3D letters are built from fonts that ship with macOS), `ffmpeg`, `whisper-cli` (whisper.cpp) with
`ggml-large-v3.bin` in `~/.cache/hyperframes/whisper/models/`, Python 3 with `librosa soundfile numpy fonttools`,
and Node (the HyperFrames CLI runs through `npx hyperframes`).
