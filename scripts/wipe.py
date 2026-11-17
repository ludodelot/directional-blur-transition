#!/usr/bin/env python3
"""Whip-pan / slow-shutter transition between two clips, simulated physically.

A virtual camera travels across a strip [A | B]. Motion blur comes from averaging
many sub-frames inside the shutter window (in linear light, so highlights streak),
with velocity following an expo-style ease. Extras: chromatic split along the
motion, highlight bloom, overexposure at peak speed and grain.
A keeps playing and B starts playing during the move (overlap). No sound is synthesised.

usage: wipe.py A.mp4 B.mp4 OUT.mp4 [--dir left|right|up|down|ur|ul|dr|dl] [--duration 0.45]
       [--shutter 1.6] [--samples 400] [--snap 4] [--chroma 0.012] [--bloom 0.35]
       [--exposure 0.25] [--grain 0.02] [--zoom 0] [--size WxH] [--fps N]
       [--only] [--keep-audio]
Needs python3 + numpy + opencv-python, and ffmpeg/ffprobe.
"""
import argparse, collections, math, os, subprocess, sys, tempfile
import cv2, numpy as np

GAMMA = 2.2

PRESETS = {
    "default":   dict(duration=0.45, shutter=1.6, snap=4.0, chroma=0.012, bloom=0.35, exposure=0.25, grain=0.02, zoom=0.0),
    "snappy":    dict(duration=0.33, shutter=2.0, snap=5.5, chroma=0.015, bloom=0.30, exposure=0.30, grain=0.02, zoom=0.0),
    "cinematic": dict(duration=0.70, shutter=1.2, snap=3.0, chroma=0.008, bloom=0.50, exposure=0.20, grain=0.03, zoom=0.0),
    "vertical":  dict(duration=0.40, shutter=1.8, snap=4.5, chroma=0.012, bloom=0.35, exposure=0.25, grain=0.02, zoom=0.0, size="1080x1920"),
}

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
    return finish(acc, speed, o, W, H, (1.0, 0.0) if horizontal else (0.0, 1.0), L)

DIAG = {"ur": (1, -1), "ul": (-1, -1), "dr": (1, 1), "dl": (-1, 1)}   # (vx, vy): window travel direction

def whip_frame_diag(a, b, i, D, o, W, H):
    """Diagonal whip. A and B sit on opposite corners of a 2W x 2H canvas; the empty corners are filled by
    mirror-tiling each clip (no seams), and the two are cross-faded while the window travels between them."""
    vx, vy = DIAG[o.dir]
    A = (a.astype(np.float32) / 255.0) ** GAMMA
    B = (b.astype(np.float32) / 255.0) ** GAMMA
    ax, bx = (0, W) if vx > 0 else (W, 0)
    ay, by = (0, H) if vy > 0 else (H, 0)
    def ext(X, qx, qy):
        C = np.zeros((2 * H, 2 * W, 3), np.float32)
        for cx in (0, W):
            for cy in (0, H):
                t = X[::-1] if cy != qy else X
                C[cy:cy + H, cx:cx + W] = t[:, ::-1] if cx != qx else t
        return C
    Ae, Be = ext(A, ax, ay), ext(B, bx, by)
    acc = np.zeros((H, W, 3), np.float32)
    u0, u1 = (i + 0.5 - o.shutter / 2) / D, (i + 0.5 + o.shutter / 2) / D
    travel = abs(ease(u1, o.snap) - ease(u0, o.snap)) * math.hypot(W, H)
    K = int(min(o.samples, max(4, travel / 2))) if o.samples > 0 else 4
    for s_ in range(K):
        u = (i + 0.5 + ((s_ + 0.5) / K - 0.5) * o.shutter) / D
        e = ease(u, o.snap)
        x0 = int(round(ax + (bx - ax) * e)); y0 = int(round(ay + (by - ay) * e))
        w = min(max((e - 0.40) / 0.20, 0.0), 1.0); w = w * w * (3 - 2 * w)
        acc += (1 - w) * Ae[y0:y0 + H, x0:x0 + W] + w * Be[y0:y0 + H, x0:x0 + W]
    acc /= K
    e1, e0 = ease((i + 1) / D, o.snap), ease(i / D, o.snap)
    speed = min(1.0, (e1 - e0) * D / 2.2)
    return finish(acc, speed, o, W, H, (vx / math.sqrt(2), vy / math.sqrt(2)), math.hypot(W, H))

def finish(acc, speed, o, W, H, axis, L):
    """Speed-driven look: optional zoom punch, bloom, overexposure, chromatic split along the motion, grain."""
    if o.zoom > 0 and speed > 0.02:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1.0 + o.zoom * speed)
        acc = cv2.warpAffine(acc, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if o.bloom > 0 and speed > 0.02:
        hi = np.clip(acc - 0.5, 0, None)
        k = int(max(W, H) * 0.04) | 1
        acc += o.bloom * speed * cv2.GaussianBlur(hi, (k, k), 0)
    acc *= 1.0 + o.exposure * speed
    if o.chroma > 0 and speed > 0.02:               # split R/B along the motion
        d = o.chroma * L * speed
        for ch, sg in ((2, +1), (0, -1)):           # BGR: 2=R, 0=B
            M = np.float32([[1, 0, sg * d * axis[0]], [0, 1, sg * d * axis[1]]])
            acc[:, :, ch] = cv2.warpAffine(acc[:, :, ch], M, (W, H), borderMode=cv2.BORDER_REPLICATE)
    out = np.clip(acc, 0, 1) ** (1 / GAMMA)
    if o.grain > 0:
        out += np.random.normal(0, o.grain * (0.4 + speed), (H, W, 1)).astype(np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)

def has_audio(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", p], capture_output=True, text=True)
    return bool(r.stdout.strip())

def main():
    p = argparse.ArgumentParser()
    p.add_argument("a"); p.add_argument("b"); p.add_argument("out")
    p.add_argument("--dir", default="left", choices=["left", "right", "up", "down", "ur", "ul", "dr", "dl"])
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--shutter", type=float, default=None, help="shutter length in frame-times (1.0 = 360deg)")
    p.add_argument("--samples", type=int, default=400, help="max sub-frames per output frame")
    p.add_argument("--snap", type=float, default=None, help="ease exponent; higher = more violent whip")
    p.add_argument("--chroma", type=float, default=None)
    p.add_argument("--bloom", type=float, default=None)
    p.add_argument("--exposure", type=float, default=None)
    p.add_argument("--grain", type=float, default=None)
    p.add_argument("--size", default=None); p.add_argument("--fps", type=float)
    p.add_argument("--zoom", type=float, default=None, help="zoom punch at peak speed, e.g. 0.04")
    p.add_argument("--only", action="store_true", help="write only the whip segment as its own clip")
    p.add_argument("--keep-audio", action="store_true")
    p.add_argument("--preset", default="default", choices=sorted(PRESETS))
    o = p.parse_args()
    for k, v in PRESETS[o.preset].items():     # explicit flags win over the preset
        if getattr(o, k, None) is None: setattr(o, k, v)

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
            f0 = tail.popleft(); n_before += 1
            if not o.only: write(f0)
    if len(tail) < D: sys.exit("clip A shorter than the transition")
    head = []; rest = frames(o.b, W, H)
    for f in rest:
        head.append(f)
        if len(head) == D: break
    if len(head) < D: sys.exit("clip B shorter than the transition")
    for i in range(D):
        write(whip_frame_diag(tail[i], head[i], i, D, o, W, H) if o.dir in DIAG else whip_frame(tail[i], head[i], i, D, o, None, W, H))
    for f in rest:
        if not o.only: write(f)
    ff.stdin.close(); ff.wait()

    cut_t = (n_before + D / 2) / fps
    inputs = ["-i", vid]; fc = []; amap = None
    if o.keep_audio and not o.only and has_audio(o.a) and has_audio(o.b):
        dA = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", o.a],
                                  capture_output=True, text=True).stdout)
        inputs += ["-i", o.a, "-i", o.b]
        fc.append(f"[1:a]atrim=0:{dA:.3f}[a1];[a1][2:a]acrossfade=d={D / fps:.3f}[ab]"); amap = "[ab]"
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs
    if amap:
        cmd += ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", amap, "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-map", "0:v", "-c:v", "copy"]
    subprocess.run(cmd + [o.out], check=True)
    print(f"wrote {o.out}  {n_before} pre-frames, {D}-frame whip @ {fps:.2f} fps, cut at {cut_t:.2f}s")

if __name__ == "__main__":
    main()
