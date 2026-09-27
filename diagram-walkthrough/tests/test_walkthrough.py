import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import walkthrough as wt  # noqa: E402

SRC = """// @title T
style s  fill: none
// @view One :: first
node a "A"
// @aside Side :: only here
node x "X"  right of a
// @view Two :: second
node b "B"  below a
"""


class Compose(unittest.TestCase):
    def setUp(self):
        self.lines, self.title, self.pre, self.blocks = wt.parse(SRC)

    def test_parse(self):
        self.assertEqual(self.title, "T")
        self.assertEqual([(b["kind"], b["title"], b["caption"]) for b in self.blocks],
                         [("view", "One", "first"), ("aside", "Side", "only here"), ("view", "Two", "second")])

    def test_views_accumulate_and_asides_drop(self):
        views = [wt.compose(self.lines, self.pre, self.blocks, k) for k in range(3)]
        self.assertIn('node a', views[0])
        self.assertNotIn('node x', views[0])
        self.assertIn('node x', views[1])
        self.assertIn('node b', views[2])
        self.assertNotIn('node x', views[2])

    def test_line_numbers_preserved(self):
        for k in range(3):
            self.assertEqual(len(wt.compose(self.lines, self.pre, self.blocks, k).splitlines()), len(self.lines))

    def test_scope_ids(self):
        svg = '<marker id="arrow-1"/><path marker-end="url(#arrow-1)"/><use href="#arrow-1"/>'
        out = wt.scope_ids(svg, "v2")
        self.assertIn('id="v2-arrow-1"', out)
        self.assertIn('url(#v2-arrow-1)', out)
        self.assertIn('href="#v2-arrow-1"', out)


@unittest.skipUnless(shutil.which("reladraw"), "reladraw not installed")
class Demos(unittest.TestCase):
    def test_every_demo_renders(self):
        for demo in sorted((ROOT / "demos").glob("*.reladraw")):
            with self.subTest(demo=demo.name), tempfile.TemporaryDirectory() as out:
                r = subprocess.run([sys.executable, str(ROOT / "scripts/walkthrough.py"), str(demo), "-o", out],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertTrue((Path(out) / "index.html").exists())

    def test_error_points_at_source(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "bad.reladraw"
            src.write_text('// @view V :: c\nnode a "A"\nnode b "B"  wibble: 1\n')
            r = subprocess.run([sys.executable, str(ROOT / "scripts/walkthrough.py"), str(src)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn(f"{src}:3", r.stderr)


if __name__ == "__main__":
    unittest.main()
