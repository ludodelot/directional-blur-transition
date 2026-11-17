#!/usr/bin/env python3
"""Whip-pan / slow-shutter transition between two clips, simulated physically.

A virtual camera travels across a strip [A | B]. Motion blur comes from averaging
many sub-frames inside the shutter window (in linear light, so highlights streak),
with velocity following an expo-style ease. Extras: chromatic split along the
motion, highlight bloom, overexposure at peak speed, grain, and a synthesised
whoosh + impact. A keeps playing and B starts playing during the move (overlap).

usage: wipe.py A.mp4 B.mp4 OUT.mp4 [--dir left|right|up|down] [--duration 0.45]
       [--shutter 1.6] [--samples 400] [--snap 4] [--chroma 0.012] [--bloom 0.35]
       [--exposure 0.25] [--grain 0.02] [--size WxH] [--fps N] [--sfx] [--keep-audio]
Needs python3 + numpy + opencv-python, and ffmpeg/ffprobe.
"""
import argparse, collections, math, os, subprocess, sys, tempfile, wave
import cv2, numpy as np

GAMMA = 2.2

def cover(frame, W, H):
    h, w = frame.shape[:2]
    s = max(W / w, H / h)
    f = cv2.resize(frame, (math.ceil(w * s), math.ceil(h * s)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    y0, x0 = (f.shape[0] - H) // 2, (f.shape[1] - W) // 2
    return f[y0:y0 + H, x0:x0 + W]

def frames(path, W, H):
    c = cv2.VideoCapture(path)
    while True:
        ok, f = c.read()
        if not ok: break
        yield cover(f, W, H)

def ease(u, k):
    u = min(max(u, 0.0), 1.0)
    return 0.5 * (2 * u) ** k if u < 0.5 else 1 - 0.5 * (2 * (1 - u)) ** k

def whip_frame(a, b, i, D, o, vec, W, H):
    """Render output frame i of D: average of sub-frames along the shutter window."""
    horizontal = o.dir in ("left", "right")
    L = W if horizontal else H
    pair = [a, b] if o.dir in ("left", "up") else [b, a]
    strip = np.concatenate(pair, axis=1 if horizontal else 0).astype(np.float32) / 255.0
    strip = strip ** GAMMA                          # linear light
    acc = np.zeros((H, W, 3), np.float32)
    # one sample per ~2 px of travel inside the shutter window (no ghost steps)
    u0, u1 = (i + 0.5 - o.shutter / 2) / D, (i + 0.5 + o.shutter / 2) / D
    travel = abs(ease(u1, o.snap) - ease(u0, o.snap)) * L
    K = int(min(o.samples, max(4, travel / 2))) if o.samples > 0 else 4
    for s in range(K):
        u = (i + 0.5 + ((s + 0.5) / K - 0.5) * o.shutter) / D
        p = int(round(ease(u, o.snap) * L))
        st = p if o.dir in ("left", "up") else L - p
        acc += strip[:, st:st + W] if horizontal else strip[st:st + H]
    acc /= K
    # speed (px/frame, normalised) at this frame
    e1, e0 = ease((i + 1) / D, o.snap), ease(i / D, o.snap)
    speed = min(1.0, (e1 - e0) * D / 2.2)           # 0..1ish, ~peak at middle
    if o.bloom > 0 and speed > 0.02:
        hi = np.clip(acc - 0.5, 0, None)
        k = int(max(W, H) * 0.04) | 1
        acc += o.bloom * speed * cv2.GaussianBlur(hi, (k, k), 0)
    acc *= 1.0 + o.exposure * speed
    if o.chroma > 0 and speed > 0.02:               # split R/B along the motion
        d = o.chroma * L * speed
        dx, dy = (d, 0) if horizontal else (0, d)
        for ch, sg in ((2, +1), (0, -1)):           # BGR: 2=R, 0=B
            M = np.float32([[1, 0, sg * dx], [0, 1, sg * dy]])
            acc[:, :, ch] = cv2.warpAffine(acc[:, :, ch], M, (W, H), borderMode=cv2.BORDER_REPLICATE)
    out = np.clip(acc, 0, 1) ** (1 / GAMMA)
    if o.grain > 0:
        out += np.random.normal(0, o.grain * (0.4 + speed), (H, W, 1)).astype(np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)

def make_whoosh(path, dur, cut_t, total, sr=48000, direction=1):
    """Noise with a sweeping low-pass (rising then falling), asymmetric envelope, plus impact."""
    n = int(total * sr); rng = np.random.default_rng(7)
    noise = rng.standard_normal(n).astype(np.float32)
    t = np.arange(n) / sr
    x = np.clip((t - (cut_t - dur * 0.75)) / (dur * 1.5), 0, 1)     # 0..1 across the whoosh
    env = np.sin(np.pi * x) ** 1.6 * (1.0 - 0.25 * x)
    env[(x <= 0) | (x >= 1)] = 0
    fc = 400 + 5200 * np.sin(np.pi * x) ** 1.3                       # cutoff sweep
    a = 1 - np.exp(-2 * np.pi * fc / sr)
    y = np.empty(n, np.float32); s1 = s2 = 0.0
    for i in range(n):                                               # 2-pole low-pass
        s1 += a[i] * (noise[i] - s1); s2 += a[i] * (s1 - s2); y[i] = s2
    y = y - np.concatenate([[0], y[:-1]]) * 0.55                    # lift highs a little
    y *= env
    m = (t >= cut_t) & (t < cut_t + 0.5)                            # soft thump at the cut
    y[m] += 0.9 * np.sin(2 * np.pi * (70 - 25 * (t[m] - cut_t)) * (t[m] - cut_t)) * np.exp(-9 * (t[m] - cut_t))
    y *= 0.85 / (np.abs(y).max() + 1e-9)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((y * 32767).astype("<i2").tobytes())

def has_audio(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", p], capture_output=True, text=True)
    return bool(r.stdout.strip())

def main():
    p = argparse.ArgumentParser()
    p.add_argument("a"); p.add_argument("b"); p.add_argument("out")
    p.add_argument("--dir", default="left", choices=["left", "right", "up", "down"])
    p.add_argument("--duration", type=float, default=0.45)
    p.add_argument("--shutter", type=float, default=1.6, help="shutter length in frame-times (1.0 = 360deg)")
    p.add_argument("--samples", type=int, default=400, help="max sub-frames per output frame")
    p.add_argument("--snap", type=float, default=4.0, help="ease exponent; higher = more violent whip")
    p.add_argument("--chroma", type=float, default=0.012)
    p.add_argument("--bloom", type=float, default=0.35)
    p.add_argument("--exposure", type=float, default=0.25)
    p.add_argument("--grain", type=float, default=0.02)
    p.add_argument("--size"); p.add_argument("--fps", type=float)
    p.add_argument("--sfx", action="store_true"); p.add_argument("--keep-audio", action="store_true")
    o = p.parse_args()

    c = cv2.VideoCapture(o.a); W, H = int(c.get(3)), int(c.get(4)); fa = c.get(cv2.CAP_PROP_FPS); c.release()
    if o.size: W, H = map(int, o.size.lower().split("x"))
    W, H = W // 2 * 2, H // 2 * 2
    fps = o.fps or fa
    D = max(3, round(o.duration * fps))

    tmp = tempfile.mkdtemp(prefix="wipe_")
    vid = os.path.join(tmp, "v.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p", vid],
        stdin=subprocess.PIPE)
    write = lambda f: ff.stdin.write(f.tobytes())

    tail = collections.deque(); n_before = 0
    for f in frames(o.a, W, H):
        tail.append(f)
        if len(tail) > D:
            write(tail.popleft()); n_before += 1
    if len(tail) < D: sys.exit("clip A shorter than the transition")
    head = []; rest = frames(o.b, W, H)
    for f in rest:
        head.append(f)
        if len(head) == D: break
    if len(head) < D: sys.exit("clip B shorter than the transition")
    for i in range(D):
        write(whip_frame(tail[i], head[i], i, D, o, None, W, H))
    for f in rest: write(f)
    ff.stdin.close(); ff.wait()

    cut_t = (n_before + D / 2) / fps
    inputs = ["-i", vid]; fc = []; amap = None
    if o.keep_audio and has_audio(o.a) and has_audio(o.b):
        dA = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", o.a],
                                  capture_output=True, text=True).stdout)
        inputs += ["-i", o.a, "-i", o.b]
        fc.append(f"[1:a]atrim=0:{dA:.3f}[a1];[a1][2:a]acrossfade=d={D / fps:.3f}[ab]"); amap = "[ab]"
    if o.sfx:
        wav = os.path.join(tmp, "w.wav"); make_whoosh(wav, D / fps, cut_t, cut_t + 1.2)
        idx = len(inputs) // 2; inputs += ["-i", wav]
        if amap:
            fc.append(f"{amap}[{idx}:a]amix=inputs=2:normalize=0:duration=first[am]"); amap = "[am]"
        else:
            fc.append(f"[{idx}:a]apad[am]"); amap = "[am]"
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs
    if amap:
        cmd += ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", amap, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-map", "0:v", "-c:v", "copy"]
    subprocess.run(cmd + [o.out], check=True)
    print(f"wrote {o.out}  {n_before} pre-frames, {D}-frame whip @ {fps:.2f} fps, cut at {cut_t:.2f}s")

if __name__ == "__main__":
    main()
