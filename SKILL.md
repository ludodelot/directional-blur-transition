---
name: directional-blur-transition
description: Create a whip-pan / slow-shutter blur transition between two video clips, simulated physically (virtual camera over an A|B strip, shutter-integrated motion blur in linear light, chromatic split, bloom, grain, directional whoosh). Use when asked for a whip pan, blur wipe, slow-shutter wipe, smear transition, motion-blur cut or "object passes the lens" transition for Reels, TikTok or Shorts.
---

# Whip-pan blur transition

Cut between two clips with a fast sideways camera move. The camera sweeps across `[A | B]` on an expo-style ease. Blur is real shutter integration (sub-frames averaged in linear light, about one per 2 px of travel), so highlights streak, there are no ghost steps and no wrap seam. A keeps playing and B is already moving when it arrives.

## When to use
Trigger phrases: "whip pan transition", "slow shutter wipe", "blur wipe", "smear transition", "motion blur cut", "digital wipe like the reel". Not for dissolves or plain slides (use ffmpeg `xfade`).

## Examples
- "Put a whip-pan between clipA.mp4 and clipB.mp4" → `python3 scripts/wipe.py clipA.mp4 clipB.mp4 out.mp4 --sfx`
- "Make it hit harder, for a vertical reel" → `... --preset vertical --snap 5.5 --shutter 2 --sfx --keep-audio`
- "Slow dreamy version going up" → `... --preset cinematic --dir up`

## Steps
1. Check both clips have at least `--duration` seconds (default 0.45 s). Prefer clips whose motion already goes in `--dir`.
2. Pick a preset (`default`, `snappy`, `cinematic`, `vertical`), then override single flags if needed. Explicit flags beat the preset.
3. Run `scripts/wipe.py`. Needs python3, numpy, opencv-python, ffmpeg/ffprobe (a venv with numpy + opencv is enough).
4. Look at the frames around the cut (contact sheet) before delivering. The peak blur should land on the cut, not on a clean frame.

## Flags
`--dir left|right|up|down`, `--duration`, `--shutter` (frame-times, 1.0 = 360°), `--snap` (ease exponent), `--chroma`, `--bloom`, `--exposure`, `--grain`, `--samples` (cap), `--size WxH`, `--fps`, `--sfx` (stereo whoosh panned with the move + impact on the cut), `--keep-audio` (crossfade the clips' audio under the whoosh). Details: docs/USAGE.md, background: docs/CONCEPTS.md.

## Guidelines
- Clips are cover-cropped to the output size, never stretched.
- Output length is lenA + lenB - overlap (the two clips overlap during the whip).
- Do not claim sync to music; the cut sits where A ends. Trim A so its end hits the beat.
- In-camera alternative: pass a hand or object over the lens at slow shutter and start the next shot as it leaves.
