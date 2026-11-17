# Usage

```bash
python3 scripts/wipe.py A.mp4 B.mp4 out.mp4 [flags]
```

| flag | default | effect |
|---|---|---|
| `--preset` | default | `default`, `snappy` (0.33 s, violent), `cinematic` (0.7 s, soft), `vertical` (1080x1920) |
| `--dir` | left | `left right up down` or the diagonals `ur ul dr dl`; direction the content travels, match the motion in your shots |
| `--duration` | preset | seconds of the whip |
| `--shutter` | preset | shutter length in frame-times; higher = longer streaks |
| `--snap` | preset | ease exponent; higher = harder hit |
| `--chroma` / `--bloom` / `--exposure` / `--grain` | preset | speed-driven look controls |
| `--zoom` | 0 | zoom punch at peak speed (for example 0.04) |
| `--only` | off | write only the whip segment (a standalone clip, no audio) |
| `--keep-audio` | off | crossfade the clips' own audio; no sound is synthesised |
| `--samples` | 400 | cap on sub-frames per output frame |
| `--size`, `--fps` | A's | output size (cover-crop) and rate |

Tests: `python -m unittest discover -s tests` (needs numpy, opencv, ffmpeg).
