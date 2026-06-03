import os, sys, json, io, time, tempfile, shutil, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import drift_check


def write(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or root, exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestDeadPath(Base):
    def test_dead_path_flagged(self):
        write(self.root, "docs/a.md", "See `src/gone.ts` for details.\n")
        findings = drift_check.find_drift(self.root, [os.path.join(self.root, "docs/a.md")], index=None)
        kinds = [f["kind"] for f in findings]
        self.assertIn("dead-path", kinds)

    def test_advisory_exit_zero_by_default(self):
        write(self.root, "docs/a.md", "See `src/gone.ts`.\n")
        self.assertEqual(drift_check.main(["--root", self.root, "docs/a.md"]), 0)

    def test_strict_exit_one_on_findings(self):
        write(self.root, "docs/a.md", "See `src/gone.ts`.\n")
        self.assertEqual(drift_check.main(["--root", self.root, "--strict", "docs/a.md"]), 1)


class TestDeadSymbol(Base):
    def test_dead_symbol_flagged(self):
        write(self.root, "src/real.ts", "export function realSym(){}\n")
        write(self.root, "docs/a.md", "Call `ghost()` in `src/real.ts`.\n")
        index = [{"symbol": "realSym", "kind": "function", "file": "src/real.ts"}]
        findings = drift_check.find_drift(self.root, [os.path.join(self.root, "docs/a.md")], index=index)
        self.assertIn("dead-symbol", [f["kind"] for f in findings])

    def test_present_symbol_not_flagged(self):
        write(self.root, "src/real.ts", "export function realSym(){}\n")
        write(self.root, "docs/a.md", "Call `realSym()` in `src/real.ts`.\n")
        index = [{"symbol": "realSym", "kind": "function", "file": "src/real.ts"}]
        findings = drift_check.find_drift(self.root, [os.path.join(self.root, "docs/a.md")], index=index)
        self.assertEqual([f for f in findings if f["kind"] == "dead-symbol"], [])


class TestStaleVsCode(Base):
    def test_stale_when_source_newer(self):
        doc = write(self.root, "docs/a.md", "Architecture: `src/m.ts` owns it.\n")
        src = write(self.root, "src/m.ts", "export const x = 1\n")
        old = time.time() - 1000
        new = time.time()
        os.utime(doc, (old, old))
        os.utime(src, (new, new))
        findings = drift_check.find_drift(self.root, [doc], index=None)
        self.assertIn("stale-vs-code", [f["kind"] for f in findings])

    def test_fresh_when_doc_newer(self):
        doc = write(self.root, "docs/a.md", "Architecture: `src/m.ts` owns it.\n")
        src = write(self.root, "src/m.ts", "export const x = 1\n")
        old = time.time() - 1000
        new = time.time()
        os.utime(src, (old, old))
        os.utime(doc, (new, new))
        findings = drift_check.find_drift(self.root, [doc], index=None)
        self.assertEqual([f for f in findings if f["kind"] == "stale-vs-code"], [])


class TestMain(Base):
    def test_clean_repo_exit_zero(self):
        write(self.root, "src/m.ts", "export const x = 1\n")
        write(self.root, "docs/a.md", "All good. See `src/m.ts`.\n")
        # doc newer than src so no stale finding
        os.utime(os.path.join(self.root, "src/m.ts"), (time.time() - 1000,) * 2)
        self.assertEqual(drift_check.main(["--root", self.root, "--strict", "docs/a.md"]), 0)

    def test_json_output(self):
        write(self.root, "docs/a.md", "See `src/gone.ts`.\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = drift_check.main(["--root", self.root, "--json", "docs/a.md"])
        self.assertEqual(rc, 0)
        self.assertIsInstance(json.loads(buf.getvalue()), list)

    def test_bad_root(self):
        self.assertEqual(drift_check.main(["--root", os.path.join(self.root, "no")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
