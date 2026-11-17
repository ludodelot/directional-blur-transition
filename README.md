# directional-blur-transition

Digital slow-shutter whip transition for short-form video. One Python script, no plugins.

```bash
python3 scripts/wipe.py a.mp4 b.mp4 out.mp4 --dir left --duration 0.45 --sfx
```

See SKILL.md and docs/USAGE.md for options (presets: default, snappy, cinematic, vertical). Works as a Claude Code skill (symlink the folder into `~/.claude/skills/`). Tests: `python -m unittest discover -s tests`.

License: MIT.
