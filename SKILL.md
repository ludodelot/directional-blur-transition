---
name: directional-blur-transition
description: Create a digital "slow shutter" whip/wipe transition between two clips using directional motion blur, a short slide and an optional whoosh SFX. Use when the user wants a blur wipe, whip transition, slow-shutter transition or "object passes the lens" cut for Reels/TikTok/Shorts.
---

# Directional-blur wipe transition

Look: the outgoing shot smears sideways (as if shot at ~1/25 s), the cut happens at peak blur, the incoming shot un-smears. A whoosh sells it.

## Run
```
python3 scripts/wipe.py A.mp4 B.mp4 out.mp4 --duration 0.5 --angle 0 --sfx
```
Needs python3 + numpy + opencv-python, and ffmpeg. Output is video only (clip audio is dropped); `--sfx` adds a pink-noise whoosh.

| flag | default | effect |
|---|---|---|
| `--duration` | 0.5 | total transition seconds (0.4-0.7 feels right for Reels) |
| `--angle` | 0 | blur direction in degrees (0 right, 90 up) |
| `--peak` | 0.18 | max blur length as fraction of the frame |
| `--shift` | 0.25 | slide as fraction of the frame |
| `--ease` | 2.2 | higher = blur snaps in later |
| `--size` | A's size | output WxH (use 1080x1920 for vertical) |

## Tips
- Cut on motion already moving in the `--angle` direction; match the motion of both shots.
- Each clip must be longer than half the duration.
- Put the whoosh peak exactly on the cut; layer an impact hit for a harder style.
- In-camera version: pass a hand or object over the lens at slow shutter, start the next shot as it leaves.
