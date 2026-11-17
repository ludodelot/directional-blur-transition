---
name: directional-blur-transition
description: Create a physically simulated whip-pan / slow-shutter blur transition between two clips (virtual camera over an A|B strip, true shutter-integrated motion blur, chromatic split, bloom, grain and a synthesised whoosh). Use when the user wants a blur wipe, whip transition, slow-shutter transition or "object passes the lens" cut for Reels/TikTok/Shorts.
---

# Whip-pan blur transition

A virtual camera travels across a strip `[A | B]` along an expo-style ease. Motion blur is real shutter integration: many sub-frames are averaged in linear light (one per ~2 px of travel), so highlights streak and there are no ghost steps. A keeps playing and B starts playing while the camera moves, so the cut is invisible.

## Run
```bash
python3 scripts/wipe.py A.mp4 B.mp4 out.mp4 --dir left --duration 0.45 --sfx --keep-audio
```
Needs python3 + numpy + opencv-python, and ffmpeg/ffprobe. Clips are cover-cropped (never stretched) to `--size`.

| flag | default | effect |
|---|---|---|
| `--dir` | left | left / right / up / down; match the motion already in the shots |
| `--duration` | 0.45 | seconds of the whip (0.35-0.6 for Reels) |
| `--shutter` | 1.6 | shutter length in frame-times; higher = longer streaks |
| `--snap` | 4 | ease exponent; higher = more violent, with a sharper hit |
| `--chroma` | 0.012 | red/blue split along the motion |
| `--bloom` | 0.35 | highlight glow at peak speed |
| `--exposure` | 0.25 | overexposure at peak speed |
| `--grain` | 0.02 | grain that rises with speed |
| `--samples` | 400 | cap on sub-frames per output frame |
| `--sfx` | off | synthesised whoosh (sweeping filter) plus a low impact on the cut |
| `--keep-audio` | off | crossfade the clips' own audio, mixed under the whoosh |

## Tips
- Cut on motion that already goes in `--dir`: a pan, a walking subject, a passing object.
- Leave at least `--duration` seconds at the end of A and the start of B.
- For a harder look raise `--snap` to 5-6 and `--shutter` to 2; for a soft look lower both.
- In-camera version: pass a hand or object over the lens at slow shutter, start the next shot as it leaves.
