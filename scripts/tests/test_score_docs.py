import os, sys, json, io, tempfile, shutil, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import score_docs


GOOD = """# proj — agent guide

Bun-runtime TypeScript CLI; an age-encrypted env vault with an Ink + React TUI.

## Commands

- Run (dev): `bun run src/index.ts`
- Test one file: `bun test tests/ui/edit.test.ts`
- (Full command list: see `package.json` scripts — not duplicated here.)

## Project structure

- `src/index.ts` — entry point; parses `Bun.argv` and dispatches subcommands.
- `src/store/` — repo model load/save (`createStore()` in `src/store/store.ts`).

## Code style

- Named exports — ✅ `export function runSet()`  🚫 `export default`.
- Imports keep `.ts` extensions — ✅ `import x from "./a.ts"`  🚫 omit it.

## Boundaries

- ✅ Always: run `bun test` before done.
- ⚠️ Ask first: changes to `src/crypto/` or dependency bumps.
- 🚫 Never: commit secrets; reference line numbers; duplicate `package.json`.

---
Source of truth: `package.json`, `src/`. Update when: commands or stack change.
"""

BAD = """# Our App

A modern, scalable TypeScript application using a microservices architecture.

The auth flow is implemented at src/auth/session.ts:412.

We are currently mid-migration to the v2 API; for now use the old client.

Write clean code and follow best practices.
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

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestDimensions(Base):
    def test_evidence_high_vs_low(self):
        hi = score_docs.score_doc(GOOD)["dimensions"]["evidence"]["score"]
        lo = score_docs.score_doc(BAD)["dimensions"]["evidence"]["score"]
        self.assertGreater(hi, 0.8)
        self.assertLess(lo, 0.4)

    def test_ref_stability_penalizes_line_refs(self):
        clean = score_docs.score_doc("- see `f()` in `src/a.ts`\n")["dimensions"]["ref_stability"]["score"]
        dirty = score_docs.score_doc("the auth is at src/auth/session.ts:412 here\n")["dimensions"]["ref_stability"]["score"]
        self.assertEqual(clean, 1.0)
        self.assertLess(dirty, 1.0)

    def test_boundaries_present_vs_absent(self):
        self.assertEqual(score_docs.score_doc(GOOD)["dimensions"]["boundaries"]["score"], 1.0)
        self.assertEqual(score_docs.score_doc(BAD)["dimensions"]["boundaries"]["score"], 0.0)

    def test_examples_present_vs_absent(self):
        self.assertGreater(score_docs.score_doc(GOOD)["dimensions"]["examples"]["score"], 0.8)
        self.assertLess(score_docs.score_doc(BAD)["dimensions"]["examples"]["score"], 0.5)

    def test_size_fit_small_full_large_zero(self):
        small = score_docs.score_doc("# tiny\n\n- `a.ts` ok\n")["dimensions"]["size_fit"]["score"]
        big = score_docs.score_doc("x" * 40000)["dimensions"]["size_fit"]["score"]
        self.assertEqual(small, 1.0)
        self.assertEqual(big, 0.0)

    def test_drift_not_applicable_without_root(self):
        d = score_docs.score_doc(GOOD)["dimensions"]["drift"]
        self.assertFalse(d["applicable"])

    def test_drift_applicable_with_root_and_dead_path(self):
        doc = write(self.root, "docs/a.md", "See `src/gone.ts` for the flow.\n")
        d = score_docs.score_doc(open(doc).read(), root=self.root, doc_path=doc)["dimensions"]["drift"]
        self.assertTrue(d["applicable"])
        self.assertLess(d["score"], 1.0)


class TestCalibration(Base):
    def test_good_above_threshold_bad_below(self):
        good = score_docs.score_doc(GOOD)["score"]
        bad = score_docs.score_doc(BAD)["score"]
        self.assertGreaterEqual(good, 70)
        self.assertLess(bad, 70)
        self.assertGreater(good, bad)


class TestWeights(Base):
    def test_evidence_only_weights(self):
        res = score_docs.score_doc(
            GOOD,
            weights={"size_fit": 0, "evidence": 1, "ref_stability": 0,
                     "examples": 0, "boundaries": 0, "drift": 0},
        )
        ev = res["dimensions"]["evidence"]["score"]
        self.assertEqual(res["score"], round(100 * ev))


class TestMain(Base):
    def test_advisory_exit_zero_for_bad_doc(self):
        write(self.root, "bad.md", BAD)
        self.assertEqual(score_docs.main(["--root", self.root, "bad.md"]), 0)

    def test_strict_exit_one_below_threshold(self):
        write(self.root, "bad.md", BAD)
        self.assertEqual(score_docs.main(["--root", self.root, "--strict", "bad.md"]), 1)

    def test_strict_exit_zero_above_threshold(self):
        write(self.root, "good.md", GOOD)
        self.assertEqual(score_docs.main(["--root", self.root, "--strict", "good.md"]), 0)

    def test_json_output(self):
        write(self.root, "good.md", GOOD)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = score_docs.main(["--root", self.root, "--json", "good.md"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, list)
        self.assertIn("score", data[0])

    def test_bad_root(self):
        self.assertEqual(score_docs.main(["--root", os.path.join(self.root, "nope")]), 2)

    def test_bad_weights(self):
        write(self.root, "good.md", GOOD)
        self.assertEqual(score_docs.main(["--root", self.root, "--weights", "evidence=high", "good.md"]), 2)
        self.assertEqual(score_docs.main(["--root", self.root, "--weights", "nope=0.5", "good.md"]), 2)


class TestHtmlComments(Base):
    def test_comment_tiers_do_not_count_as_boundaries(self):
        text = "# x\n\n<!-- boundaries missing: ✅ ⚠️ \U0001f6ab -->\n\nSome prose with no real boundaries here.\n"
        self.assertEqual(score_docs.score_doc(text)["dimensions"]["boundaries"]["score"], 0.0)

    def test_comment_examples_do_not_count(self):
        text = "# x\n\n<!-- example ✅ good \U0001f6ab bad e.g. foo -->\n\nPlain prose line with several words here.\n"
        self.assertEqual(score_docs.score_doc(text)["dimensions"]["examples"]["score"], 0.0)

    def test_comment_lines_excluded_from_evidence(self):
        # a long HTML comment must not count as a content line for evidence; only
        # the real backticked claim should, and it bears evidence -> 1.0
        text = (
            "# x\n\n"
            "<!-- this is a long explanatory comment with many words but no code -->\n\n"
            "Real claim: `src/a.ts` is the entry point of the app.\n"
        )
        self.assertEqual(score_docs.score_doc(text)["dimensions"]["evidence"]["score"], 1.0)

    def test_multiline_comment_stripped(self):
        text = (
            "# x\n\n"
            "<!--\n  ✅ Always do this\n  ⚠️ Ask first\n  🚫 Never that\n-->\n\n"
            "Just one plain sentence with several words present.\n"
        )
        self.assertEqual(score_docs.score_doc(text)["dimensions"]["boundaries"]["score"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
