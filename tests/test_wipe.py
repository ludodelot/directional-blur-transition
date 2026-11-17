"""Stdlib-only tests. Generates tiny clips with ffmpeg, runs wipe.py, checks with ffprobe."""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIPE = os.path.join(ROOT, "scripts", "wipe.py")
FPS, W, H = 25, 320, 568

def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout

def make_clip(path, src, secs=1.5, audio=False):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{src}=size={W}x{H}:rate={FPS}:duration={secs}"]
    if audio: cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}", "-shortest"]
    run(*cmd, "-pix_fmt", "yuv420p", path)

def probe(path):
    out = run("ffprobe", "-v", "error", "-count_frames", "-show_entries",
              "stream=codec_type,width,height,nb_read_frames", "-of", "json", path)
    return {s["codec_type"]: s for s in json.loads(out)["streams"]}

class WipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.tmp.name
        cls.a, cls.b = os.path.join(d, "a.mp4"), os.path.join(d, "b.mp4")
        make_clip(cls.a, "testsrc2", audio=True); make_clip(cls.b, "smptebars", audio=True)
        cls.n = int(probe(cls.a)["video"]["nb_read_frames"])      # frames per clip (both equal)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def wipe(self, name, *flags):
        out = os.path.join(self.tmp.name, name)
        subprocess.run([sys.executable, WIPE, self.a, self.b, out, *flags], check=True, capture_output=True)
        return out

    def test_frame_count_dims_and_overlap(self):
        out = self.wipe("o.mp4", "--duration", "0.4")
        v = probe(out)["video"]
        D = round(0.4 * FPS)
        self.assertEqual(int(v["nb_read_frames"]), 2 * self.n - D)   # lenA + lenB - overlap
        self.assertEqual((int(v["width"]), int(v["height"])), (W, H))

    def test_all_directions(self):
        for d in ("left", "right", "up", "down"):
            with self.subTest(d=d):
                v = probe(self.wipe(f"{d}.mp4", "--dir", d, "--samples", "24"))["video"]
                self.assertEqual(int(v["nb_read_frames"]), 2 * self.n - round(0.45 * FPS))

    def test_preset_size_and_flag_override(self):
        v = probe(self.wipe("p.mp4", "--preset", "vertical", "--size", "160x284"))["video"]
        self.assertEqual((int(v["width"]), int(v["height"])), (160, 284))   # explicit flag beats preset

    def test_sfx_is_stereo_aac_and_keeps_duration(self):
        out = self.wipe("s.mp4", "--sfx", "--keep-audio")
        self.assertIn("audio", probe(out))
        ch = run("ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=channels", "-of", "csv=p=0", out).strip()
        self.assertEqual(ch, "2")

    def test_too_short_clip_fails(self):
        short = os.path.join(self.tmp.name, "short.mp4"); make_clip(short, "testsrc2", secs=0.1)
        r = subprocess.run([sys.executable, WIPE, short, self.b, os.path.join(self.tmp.name, "x.mp4")], capture_output=True)
        self.assertNotEqual(r.returncode, 0)

    def test_peak_frame_is_blurred(self):
        """Sharpness (Laplacian variance) collapses at the peak of the whip (grain off so it cannot add edges)."""
        import cv2
        out = self.wipe("m.mp4", "--duration", "0.4", "--grain", "0")
        cap = cv2.VideoCapture(out); sharp = []
        while True:
            ok, f = cap.read()
            if not ok: break
            sharp.append(cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
        D = round(0.4 * FPS); start = self.n - D
        peak = min(sharp[start:start + D])
        self.assertLess(peak, 0.25 * sharp[0])            # blurred mid-whip

if __name__ == "__main__":
    unittest.main()
