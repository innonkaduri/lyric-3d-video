# The engine — `compositions/world.html`

One HyperFrames sub-composition that owns a single Three.js world. Everything on screen is a
pure function of song time `t`, driven by a seek-safe GSAP clock (`K.clock`). That purity is what
makes the 10-subframe motion blur + depth of field possible: the frame is re-posed at 10 slightly
earlier times / lens positions and averaged.

## Contents
1. Data in (`window.SONG`, `window.GLYPHS`)
2. Building blocks (Word, motion helpers, props)
3. Shots
4. Frame pipeline (pose → render → post)
5. Adapting the template to a new song
6. Shot recipe catalog (what the template ships)

## 1. Data in
- `lib/data.js` (prep.py): `SONG.lines[i].words[j] = {w, t}` (display text from lyrics.txt, `t` = sung onset in clip time),
  `SONG.bars`, `SONG.e8` (grid unit), `SONG.bar`, `SONG.drop`, `SONG.stop`, `SONG.dur`, `SONG.env.kick/hat` (60 fps 0..1).
- `lib/glyphs.js` (fontjson.py): outlines for FC (Futura Condensed ExtraBold), AVC (Avenir Next Condensed Heavy Italic),
  BODB (Bodoni 72 Bold), SCR (SignPainter script, CFF → `toShapes(true)`), RND (Arial Rounded).
  A character missing from GLYPHS renders as a gap — normalise exotic characters (curly quotes, Cyrillic look-alikes) in lyrics.txt.

## 2. Building blocks
- `Word(text, font, size, faceColor, sideColor, {depth, noSway})` → `{g, inner, letters[], W, cap}`.
  Real extruded letters (bevel, clearcoat face, matte side), centred on the group. `depth` is in em and ×1.45 internally.
  Each letter has a home pose `hx, hy`. `inner` carries a gentle global sway (so the sides read as 3D);
  pass `noSway` when the word sits on/in another object (slabs, pills, a typewriter line).
  Words are added to `CUR` (the current set root) — always call inside a shot block after `setRoot(n)`.
- `fitSize(text, font, maxWidth, maxSize)` — size so the word fits a width in world units.
  Portrait frames are narrow: think 3–4.6 units of width for a camera ~10–15 units away.
- Motion (all pure functions of t — call every frame):
  `slamIn(wd, t, at, {z, rx, ry, rz, y, sx})` letters arrive from depth with overshoot, staggered;
  `explode(wd, t, at, power)` blast outward with spin + gravity;
  `assemble(wd, t, at, dur, spread)` fly in from a scattered cloud;
  `writeOn(wd, t, at, dur)` letters grow up in reading order (script);
  `home(wd)` reset; `live(wd, on)` show/hide.
- Elements: `makeProps(parent, n, seed, avoidRadius)` / `runProps(...)` — a field of glossy primitives
  (sphere, torus, box, cone, knot, capsule, cylinder, heart) with stripe/checker materials, bobbing and
  pulsing on the kick; they shrink away when they come between the lens and the words.
  `HEART` geometry and `PM` materials are shared — use them for lyric-specific elements.

## 3. Shots
Each shot is a set at its own place in the world (`setRoot(n)` → origin `SET_O(n)`), pushed in order:
```js
setRoot(N);
// ---- N: description
{ const i = LINE_INDEX, ws = W_(i);
  const words = ws.map((w, k) => Word(clean(w.w), "FC", fitSize(...), ...));
  shots.push({ a: L[i].t0 - 0.04, b: tEnd(i), objs: words, extra: [otherObjects], zoom: 1.55 /*default*/, run(t) {
    words.forEach((wd, k) => { live(wd, t >= ws[k].t - 0.05); slamIn(wd, t, ws[k].t - 0.05, { z: -14 }); });
    return { pos: P(x, y, z), look: P(0, 2.5, 0), fov: 46, roll: 0 };   // local to the set
  } }); }
```
- `a`/`b`: the shot's window; shots must tile the timeline in order. `a` ≈ first word − 0.04 s so the cut lands on the word.
- `objs` (Words) and `extra` (anything else) are hidden automatically outside the shot.
- `zoom` scales the camera's distance from `look` (1.55 default because portrait is narrow; use 1 for shots
  whose camera is *inside* something — rings, tunnels, tracking shots).
- Return `up` only for looking straight down (ring tunnel).

## 4. Frame pipeline
- `pose(t)`: hides everything, runs the active shot, applies hit shake (`HITS` from bars/drop), the whip yaw
  at cuts (`whipAt`, ±0.26 rad over 0.1 s, alternating direction), places sun + rim light, runs that set's props
  and the word sway.
- `render(t)`: 10 subframes over half a frame of shutter; each subframe also shifts the eye across a
  golden-angle aperture disk (`ap = 0.0055 × focus distance`) and re-aims at `look` → motion blur + thin-lens DOF.
  The kick envelope punches the FOV per subframe.
- Post shader (`fin` uniforms): `uCA` chromatic aberration, `uDist` barrel, `uZoom` radial zoom blur,
  `uGlitch` slice displacement, `uMono` desaturate (used for the freeze before the drop), `uInv` invert frame
  (one frame on the drop), `uFlash`/`uFlashC` colour strobe (first bar after the drop), grain, vignette,
  S-curve grade. Values are clamped and NaN-guarded (a glossy floor once produced a black NaN hole).
- Song-specific timed effects live in `render`: freeze `STOP→DROP`, invert at `DROP`, strobe on even eighths
  of the first bar after `DROP`, `GLITCH` list (stop, drop, chorus line starts, the final pile).

## 5. Adapting the template to a new song
The template's 13 shots are bound to the Self Aware structure (12 lines: 4 pre-chorus + 8 chorus; drop before line 4).
For another song:
1. Count lines in `SONG.lines`. Plan one shot per line (+ shot 0 for the title before the first line).
   Pick recipes from the catalog below — vary them; never two of the same in a row.
2. In each shot block set `const i = <line index>`. Delete or duplicate blocks to match the line count,
   keeping `setRoot(n)` numbers sequential (0..N) in the same order as `shots.push`.
3. Song-specific references to fix: the drop shot uses `L[3].words.slice(-2)` ("LOVE ME" — the words sung
   across the drop); `GLITCH` uses `L.slice(4)` (chorus lines); shot 9 looks for `/together/i`; the final shot
   keeps its last word on screen. Re-point these at the new song's equivalents (or remove).
4. If the section has no stop/drop, set `"drop": null, "stop": null` in song.json — the freeze/invert/strobe never fire.
5. Title: shot 0 builds "SELF" / "AWARE" — replace with the new song title.

## 6. Shot recipe catalog (template shot number → what it does)
0. Title assembles from scattered letters (already partly formed on frame 0), camera dives.
1. Word-by-word slams: each word smashes in from z −30, the previous word explodes; new camera angle per word.
2. Tower: words stacked bottom-up with a measuring rule (+2.1 M tags); one continuous crane up.
3. Serif row (Bodoni) + the last word written on in script (SignPainter); camera swings ±0.4 rad.
4. Ring tunnel: the line printed on 4 rotating text bands; camera descends through them looking down
   (stop at y≈12 or the rings leave the frame); rings light up as their words are sung; freezes mono at STOP.
5. The drop: shockwave ring + primitive burst + hearts; the words sung across the drop smash in, then the
   chorus line assembles into a poster wall; strobe-cut camera for one bar.
6. Slabs: each word lands on a coloured slab forming a tower; low hero angle.
7. Typewriter tracking shot: letters pop along a wavy line as sung; camera dollies with the write head.
8. Mirror: head words above, the last word huge with a reflection and echo copies; front-arc orbit only.
9. Split: words alternate above/below and part slowly while the camera flies forward; interlocking rings on a keyword.
10. Pills: words on 3D capsules orbiting one big pill (the last word) in a swarm of small ones.
11. Inside two giant rotating text rings; each word slams at the centre, facing the orbiting camera.
12. Lockup poster (mixed fonts) → everything but the last word explodes, a pre-simulated pile of 64 objects
    rains down, the last word rises in front, artist/title tag.
