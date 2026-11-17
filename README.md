# directional-blur-transition

A whip-pan / slow-shutter blur transition between two video clips, rendered as real shutter integration instead of a spatial blur. One Python script, no plugins, no sound design.

```bash
python3 scripts/wipe.py a.mp4 b.mp4 out.mp4 --dir right --preset cinematic
python3 scripts/wipe.py a.mp4 b.mp4 whip.mp4 --dir ur --only      # just the whip, as its own clip
```

![Virtual camera over an A|B strip](docs/img/strip.svg)

## What it does

- **Virtual camera.** A and B are joined on a canvas and a window sweeps across them on an expo ease. A keeps playing and B is already moving when it arrives.
- **Shutter integration.** Every output frame averages many sub-frames (about one per 2 px of travel) in linear light, so highlights streak and there are no ghost steps.
- **Speed-driven look.** Chromatic split, bloom, over-exposure and grain scale with the instantaneous speed: zero at rest, strongest at the cut.
- **Eight directions.** `left right up down` plus the diagonals `ur ul dr dl`.
- **Standalone clip.** `--only` writes just the whip segment, so you can drop it on top of a cut in your editor.

![Timing](docs/img/timing.svg)

![Diagonal canvas](docs/img/diagonal.svg)

## Install

Python 3.9+, `numpy`, `opencv-python` (or `opencv-python-headless`) and `ffmpeg` / `ffprobe` on your PATH.

```bash
pip install numpy opencv-python
python3 -m unittest discover -s tests
```

It also works as a Claude Code skill: symlink the folder into `~/.claude/skills/directional-blur-transition`.

## Options

| flag | default | effect |
|---|---|---|
| `--preset` | `default` | `default`, `snappy` (0.33 s, hard hit), `cinematic` (0.7 s, soft), `vertical` (1080×1920) |
| `--dir` | `left` | `left right up down ur ul dr dl`: the direction the content travels |
| `--duration` | preset | seconds of the whip |
| `--shutter` | preset | shutter length in frame-times (1.0 = 360°); higher = longer streaks |
| `--snap` | preset | ease exponent; higher = harder hit |
| `--chroma` `--bloom` `--exposure` `--grain` | preset | speed-driven look controls |
| `--zoom` | 0 | optional zoom punch at peak speed, for example `0.04` |
| `--only` | off | write only the whip segment as its own clip |
| `--keep-audio` | off | crossfade the clips' own audio (never adds sound) |
| `--samples` | 400 | cap on sub-frames per output frame |
| `--size`, `--fps` | A's | output size (cover-crop, never stretched) and frame rate |

Output length is `len(A) + len(B) - overlap` (or just the overlap with `--only`). Both clips need at least `--duration` seconds. Trim A so its end lands where you want the cut; the tool does not sync to music.

### Using the standalone clip

With `--only`, the first frame is A, `D` frames before its end, and the last frame is B, `D` frames after its start (`D = duration × fps`). In your editor cut A `D` frames early, start B `D` frames late, and put the whip in the gap.

## Honest limits

- This is a **synthetic** whip. The two shots are still pictures as far as the transition is concerned, so it reads like an editor's transition. Camera operators get the best result in camera: same direction and speed in both shots, slow shutter, cut at the peak of the blur, matched brightness. If you have real pans, use this to finish the join, not to replace them.
- Diagonals mirror-tile each clip into the empty corners. A very bright sky can leave a symmetric highlight shape at peak blur.
- Not modelled: rolling-shutter skew, true sensor saturation, optical-flow blur, handheld shake.
- Resolve's Temporal Smear mixes neighbouring frames in time; this tool does not.

See [`docs/USAGE.md`](docs/USAGE.md) and [`docs/CONCEPTS.md`](docs/CONCEPTS.md).

## License

MIT.
