#!/usr/bin/env python3
"""Directional-blur whip transition between two clips (digital slow-shutter wipe).

usage: wipe.py A.mp4 B.mp4 OUT.mp4 [--duration 0.5] [--angle 0] [--peak 0.18]
                                   [--shift 0.6] [--ease 2.2] [--sfx] [--size WxH] [--fps N]
Last duration/2 s of A blur+slide out; first duration/2 s of B slide+unblur in.
Needs: python3 with numpy + opencv-python, ffmpeg on PATH.
"""
import argparse, math, subprocess, sys
import cv2, numpy as np

def read(path, size):
    c = cv2.VideoCapture(path); fps = c.get(cv2.CAP_PROP_FPS); fr = []
    while True:
        ok, f = c.read()
        if not ok: break
        fr.append(cv2.resize(f, size, interpolation=cv2.INTER_AREA))
    return fr, fps

def motion_kernel(length, angle):
    n = max(3, int(length) | 1)
    k = np.zeros((n, n), np.float32)
    c = n // 2
    dx, dy = math.cos(math.radians(angle)), -math.sin(math.radians(angle))
    cv2.line(k, (int(c - dx * c), int(c - dy * c)), (int(c + dx * c), int(c + dy * c)), 1, 1)
    return k / k.sum()

def whip(frame, t, sign, a):
    """t: 0 = clean, 1 = max whip. sign: -1 leaving, +1 arriving."""
    h, w = frame.shape[:2]
    e = t ** a
    L = a_peak * max(h, w) * e
    out = frame
    if e > 0:
        ang = math.radians(a_angle)
        M = np.float32([[1, 0, sign * a_shift * w * e * math.cos(ang)],
                        [0, 1, -sign * a_shift * w * e * math.sin(ang)]])
        out = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_WRAP)
        if L >= 3:
            out = cv2.filter2D(out, -1, motion_kernel(L, a_angle), borderType=cv2.BORDER_REFLECT)
    return out

p = argparse.ArgumentParser()
p.add_argument("a"); p.add_argument("b"); p.add_argument("out")
p.add_argument("--duration", type=float, default=0.5)
p.add_argument("--angle", type=float, default=0, help="deg, 0=right, 90=up")
p.add_argument("--peak", type=float, default=0.18, help="max blur length as fraction of frame")
p.add_argument("--shift", type=float, default=0.25, help="slide as fraction of frame")
p.add_argument("--ease", type=float, default=2.2)
p.add_argument("--size"); p.add_argument("--fps", type=float)
p.add_argument("--sfx", action="store_true")
o = p.parse_args()
a_peak, a_shift, a_angle = o.peak, o.shift, o.angle

c = cv2.VideoCapture(o.a); W, H = int(c.get(3)), int(c.get(4)); c.release()
if o.size: W, H = map(int, o.size.lower().split("x"))
A, fa = read(o.a, (W, H)); B, fb = read(o.b, (W, H))
fps = o.fps or fa
half = max(2, round(o.duration * fps / 2))
if len(A) <= half or len(B) <= half: sys.exit("clips shorter than half the transition")
frames = A[:-half]
for i in range(half):              # A leaving: 0 -> 1
    frames.append(whip(A[len(A) - half + i], (i + 1) / half, -1, o.ease))
for i in range(half):              # B arriving: 1 -> 0
    frames.append(whip(B[i], 1 - i / half, +1, o.ease))
frames += B[half:]

tmp = o.out + ".tmp.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
    "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "16",
    "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
for f in frames: ff.stdin.write(f.tobytes())
ff.stdin.close(); ff.wait()

if o.sfx:   # filtered-noise whoosh centred on the cut
    cut = (len(A) - half) / fps; d = o.duration * 1.6; st = max(0, cut - d / 2)
    af = (f"anoisesrc=d={d}:c=pink:a=0.5,highpass=f=300,lowpass=f=6000,"
          f"afade=t=in:d={d*0.55},afade=t=out:st={d*0.55}:d={d*0.45},volume=1.4,"
          f"adelay={int(st*1000)}|{int(st*1000)}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-f", "lavfi", "-i", af,
        "-filter_complex", "[1:a]apad[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
        "-c:a", "aac", "-shortest", o.out], check=True)
    import os; os.remove(tmp)
else:
    import os; os.replace(tmp, o.out)
print("wrote", o.out, f"{len(frames)} frames @ {fps:.2f}")
