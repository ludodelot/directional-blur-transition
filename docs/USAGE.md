# Usage

```bash
python3 scripts/wipe.py A.mp4 B.mp4 out.mp4 [flags]
```

| flag | default | effect |
|---|---|---|
| `--preset` | default | `default`, `snappy` (0.33 s, violent), `cinematic` (0.7 s, soft), `vertical` (1080x1920) |
| `--dir` | left | direction content travels; match the motion in your shots |
| `--duration` | preset | seconds of the whip |
| `--shutter` | preset | shutter length in frame-times; higher = longer streaks |
| `--snap` | preset | ease exponent; higher = harder hit |
| `--chroma` / `--bloom` / `--exposure` / `--grain` | preset | speed-driven look controls |
| `--samples` | 400 | cap on sub-frames per output frame |
| `--size`, `--fps` | A's | output size (cover-crop) and rate |
| `--sfx` | off | stereo whoosh + impact on the cut |
| `--keep-audio` | off | crossfade clip audio, mixed under the whoosh |

Tests: `python -m unittest discover -s tests` (needs numpy, opencv, ffmpeg).
