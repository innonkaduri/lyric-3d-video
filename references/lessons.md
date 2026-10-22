# Lessons — what the client asked for, and what broke

Learned on a real client project; each item cost a full render round.  Check them before the first render of a new video.

## Taste (from direct feedback)
- **Words on screen at every moment.** The client rejected anything that empties the frame of text: lens wipes that
  filled the frame with a colour or a giant letter, camera flights between sets (mid-flight was empty cream),
  a drop moment with only particles. On a drop, put the words that are sung there on screen at the hit.
- **No tape-rewind / cold-open-then-rewind hooks** (rejected outright). The hook is a frame-0 that already shows strong 3D type
  (title partly assembled at t=0), then the song plays straight.
- **"3D you can feel"**: deep extrusion (≈0.5 em), letters that sway so their sides show, many glossy elements at
  different depths, DOF so near/far separate, camera always moving. Flat head-on type reads as 2D — angle it.
- **Lyric-tied elements** land well (3D hearts on "love", interlocking rings on "together") — one or two per video,
  tied to a sung word, not decoration everywhere.
- **Smooth = continuous motion + short whips**, not long transitions. A cut on the drop is fine (it's the hit).

## Technical gotchas
- Portrait frames are narrow: horizontal half-FOV ≈ 0.56 × vertical. Fit words to 3–4.6 units at camera
  distance 10–15 and keep the global ×1.55 camera pull-back.
- DOF aperture `0.0055 × distance`. 0.022 blurred the type into mush.
- Whip yaw ±0.26 rad / 0.1 s. 0.75 rad made 3–4 frames per cut unreadable.
- Orbits around a word must stay on its front arc (±0.95 rad): a 360° orbit shows mirrored text.
- Text bands on cylinders: MeshBasicMaterial (lit Standard material looks grey from inside), `texture.repeat.x = -1`
  when seen from inside.
- CFF fonts (SignPainter) need `ShapePath.toShapes(true)`; TrueType `false`. Thin script strokes need thin depth (≈0.12 em) or they read as a block.
- Very glossy transparent floors can produce NaN/inf in the half-float target → black hole with a halo.
  Keep roughness ≥0.4 and the shader clamp.
- A prop toggled visible/hidden between subframes ghosts as a translucent bubble — shrink it smoothly instead.
- `immediateRender:false` tweens leave elements visible before their start — set opacity 0 first (DOM layers).
- Ring-tunnel camera must stay above the lowest rings (looking straight down at close range puts them outside the frame).
- Whisper timing: under music, the plain whisper clock (full song) is right; `-dtw` on a short clip squeezed every word to the start.
  Snap onsets to a 250–3500 Hz harmonic onset. Expect 100% matches when lyrics.txt is the real lyric.
- Downbeat: on the 8-phase table, kicks on phases (1,2,5,6) and snare on (3,7) meant half-time — bar = 8 tracked
  beats, downbeat at phase 5, confirmed by the stop-then-hit at the chorus. Verify the drop by ear-shaped evidence
  (a quarter-second dip then a jump in loudness) before trusting the phase.
- Renders: 40 s at 10 subframes ≈ 7 min on this Mac; the master is ~420 MB because of grain — always make the
  <30 MB 2-pass upload copy (phone delivery limit is 30 MB).

## Lyrics and rights
- Never type, transcribe-to-screen, or print song lyrics from memory or from the whisper transcript. The display text
  comes from lyrics the user supplies (saved to `lyrics.txt`; if they paste them in chat, saving their pasted text is
  fine). Tool output prints times and counts only.
- Instagram/TikTok may mute uploaded copyrighted audio: deliver a `_nomusic` copy too and tell the user the
  song timestamp to start from in the platform's music library.
