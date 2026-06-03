import os, sys, json, io, tempfile, shutil, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import eval_harness


STRONG = """# proj — agent guide

- Entry: `src/index.ts` parses args.
- Store: `createStore()` in `src/store.ts`.

## Boundaries

- ✅ Always: run `bun test`.
- ⚠️ Ask first: dependency bumps.
- 🚫 Never: commit secrets; reference line numbers.

---
Source of truth: `package.json`. Update when: commands change.
"""

WEAK = """# Our App

A modern scalable application. See `src/gone.ts`.
The flow is at src/app.ts:99. Write clean code.
"""


def write(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or root, exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        # real source so STRONG's refs resolve against root
        write(self.root, "src/index.ts", "export const x = 1\n")
        write(self.root, "src/store.ts", "export function createStore(){}\n")
        write(self.root, "package.json", '{"name":"proj"}\n')
        self.a = os.path.join(self.root, "good")
        self.b = os.path.join(self.root, "base")
        write(self.a, "CLAUDE.md", STRONG)
        write(self.b, "CLAUDE.md", WEAK)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestMeasure(Base):
    def test_strong_beats_weak_on_score(self):
        ma = eval_harness.measure(self.root, [os.path.join(self.a, "CLAUDE.md")])
        mb = eval_harness.measure(self.root, [os.path.join(self.b, "CLAUDE.md")])
        self.assertGreater(ma["score"], mb["score"])

    def test_strong_paths_resolve_better(self):
        ma = eval_harness.measure(self.root, [os.path.join(self.a, "CLAUDE.md")])
        mb = eval_harness.measure(self.root, [os.path.join(self.b, "CLAUDE.md")])
        self.assertEqual(ma["path_resolve_pct"], 100.0)
        self.assertLess(mb["path_resolve_pct"], 100.0)

    def test_weak_has_line_refs(self):
        mb = eval_harness.measure(self.root, [os.path.join(self.b, "CLAUDE.md")])
        self.assertGreaterEqual(mb["line_refs"], 1)


class TestCompare(Base):
    def test_compare_delta_positive_for_better_a(self):
        ma = eval_harness.measure(self.root, [os.path.join(self.a, "CLAUDE.md")])
        mb = eval_harness.measure(self.root, [os.path.join(self.b, "CLAUDE.md")])
        cmp = eval_harness.compare(ma, mb)
        self.assertGreater(cmp["score"]["delta"], 0)
        self.assertEqual(cmp["score"]["delta"], ma["score"] - mb["score"])


class TestMain(Base):
    def test_json_runs(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = eval_harness.main([
                "--root", self.root, "--json",
                "--dir-a", self.a, "--label-a", "repo-docs",
                "--dir-b", self.b, "--label-b", "baseline",
            ])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertIn("a", out)
        self.assertIn("b", out)
        self.assertIn("delta", out)

    def test_bad_dir(self):
        self.assertEqual(eval_harness.main([
            "--root", self.root,
            "--dir-a", os.path.join(self.root, "nope"),
            "--dir-b", self.b,
        ]), 2)

    def test_index_file_loaded_not_passed_as_string(self):
        # A valid --index must RESOLVE a documented `sym() in file` ref, not be
        # passed through as a path string (which made every symbol "not in index"
        # -> spurious drift -> depressed score). With-index score must be >= the
        # no-index score, never below it.
        idx = os.path.join(self.root, "index.json")
        with open(idx, "w") as fh:
            json.dump([{"symbol": "createStore", "kind": "function",
                        "file": "src/store.ts"}], fh)

        def score_a(extra):
            buf = io.StringIO()
            with redirect_stdout(buf):
                eval_harness.main(["--root", self.root, "--json",
                                   "--dir-a", self.a, "--dir-b", self.b] + extra)
            return json.loads(buf.getvalue())["a"]["score"]

        self.assertGreaterEqual(score_a(["--index", idx]), score_a([]))

    def test_measure_skips_unreadable_doc(self):
        missing = os.path.join(self.root, "does-not-exist.md")
        m = eval_harness.measure(self.root, [missing])
        self.assertEqual(m["count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
