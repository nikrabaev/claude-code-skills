import os, sys, json, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import symbol_exists

import io
from contextlib import redirect_stdout, redirect_stderr


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


INDEX = [{"symbol": "processPayment", "kind": "function", "file": "src/billing/charge.ts"}]


class BaseTmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.index_path = os.path.join(self.root, "index.json")
        write(self.index_path, json.dumps(INDEX))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_doc(self, name, content):
        path = os.path.join(self.root, name)
        write(path, content)
        return path


# ---------------------------------------------------------------------------
# extract_refs
# ---------------------------------------------------------------------------
class TestExtractRefs(unittest.TestCase):
    def test_with_parens(self):
        refs = symbol_exists.extract_refs(
            "see `processPayment()` in `src/billing/charge.ts` for details"
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["symbol"], "processPayment")
        self.assertEqual(refs[0]["file"], "src/billing/charge.ts")
        self.assertEqual(refs[0]["line"], 1)

    def test_e_without_parens(self):
        refs = symbol_exists.extract_refs("`processPayment` in `src/billing/charge.ts`")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["symbol"], "processPayment")
        self.assertEqual(refs[0]["file"], "src/billing/charge.ts")

    def test_d_bare_backtick_ignored(self):
        refs = symbol_exists.extract_refs("call `helper()` somewhere with no clause")
        self.assertEqual(refs, [])

    def test_line_numbers_multiline(self):
        text = "intro\n`a()` in `f1.ts`\nmiddle\n`b` in `dir/f2.ts`\n"
        refs = symbol_exists.extract_refs(text)
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0]["symbol"], "a")
        self.assertEqual(refs[0]["line"], 2)
        self.assertEqual(refs[1]["symbol"], "b")
        self.assertEqual(refs[1]["line"], 4)

    def test_dotted_symbol(self):
        refs = symbol_exists.extract_refs("`obj.method()` in `src/x.ts`")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["symbol"], "obj.method")


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------
class TestCheck(unittest.TestCase):
    def test_resolves(self):
        refs = [{"symbol": "processPayment", "file": "src/billing/charge.ts", "line": 1}]
        self.assertEqual(symbol_exists.check(refs, INDEX, "/root"), [])

    def test_symbol_not_in_index(self):
        refs = [{"symbol": "notReal", "file": "src/billing/charge.ts", "line": 1}]
        misses = symbol_exists.check(refs, INDEX, "/root")
        self.assertEqual(len(misses), 1)
        self.assertIn("not in index", misses[0]["reason"])

    def test_file_mismatch(self):
        refs = [{"symbol": "processPayment", "file": "src/wrong.ts", "line": 1}]
        misses = symbol_exists.check(refs, INDEX, "/root")
        self.assertEqual(len(misses), 1)
        self.assertIn("file mismatch", misses[0]["reason"])

    def test_basename_match_resolves(self):
        refs = [{"symbol": "processPayment", "file": "charge.ts", "line": 1}]
        self.assertEqual(symbol_exists.check(refs, INDEX, "/root"), [])

    def test_endswith_match_resolves(self):
        refs = [{"symbol": "processPayment", "file": "billing/charge.ts", "line": 1}]
        self.assertEqual(symbol_exists.check(refs, INDEX, "/root"), [])


# ---------------------------------------------------------------------------
# main / end to end
# ---------------------------------------------------------------------------
class TestMain(BaseTmp):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = symbol_exists.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_a_resolves_returns_0(self):
        self.write_doc("doc.md", "`processPayment()` in `src/billing/charge.ts`\n")
        rc, out, err = self.run_main(["--root", self.root, "--index", self.index_path])
        self.assertEqual(rc, 0)

    def test_b_symbol_not_in_index_returns_1(self):
        self.write_doc("doc.md", "`notReal()` in `src/billing/charge.ts`\n")
        rc, out, err = self.run_main(["--root", self.root, "--index", self.index_path])
        self.assertEqual(rc, 1)
        self.assertIn("notReal", out)
        self.assertIn("not in index", out)

    def test_c_file_mismatch_returns_1(self):
        self.write_doc("doc.md", "`processPayment()` in `src/wrong.ts`\n")
        rc, out, err = self.run_main(["--root", self.root, "--index", self.index_path])
        self.assertEqual(rc, 1)
        self.assertIn("file mismatch", out)

    def test_d_bare_ref_ignored_returns_0(self):
        self.write_doc("doc.md", "just `helper()` here, no clause at all\n")
        rc, out, err = self.run_main(["--root", self.root, "--index", self.index_path])
        self.assertEqual(rc, 0)

    def test_e_without_parens_resolves_returns_0(self):
        self.write_doc("doc.md", "`processPayment` in `src/billing/charge.ts`\n")
        rc, out, err = self.run_main(["--root", self.root, "--index", self.index_path])
        self.assertEqual(rc, 0)

    def test_json_output_violation(self):
        self.write_doc("doc.md", "`notReal()` in `src/billing/charge.ts`\n")
        rc, out, err = self.run_main(
            ["--root", self.root, "--index", self.index_path, "--json"]
        )
        self.assertEqual(rc, 1)
        parsed = json.loads(out)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["symbol"], "notReal")

    def test_missing_index_skips_with_2(self):
        # No --index: auto-build runs extract_symbols.sh against this root, which
        # has no source files -> empty index -> skip rather than flag everything.
        self.write_doc("doc.md", "`processPayment()` in `src/billing/charge.ts`\n")
        rc, out, err = self.run_main(["--root", self.root])
        self.assertEqual(rc, 2)
        self.assertTrue(err.strip())

    def test_bad_index_json_returns_2(self):
        bad = os.path.join(self.root, "bad.json")
        write(bad, "{ not json")
        self.write_doc("doc.md", "`processPayment()` in `src/billing/charge.ts`\n")
        rc, out, err = self.run_main(["--root", self.root, "--index", bad])
        self.assertEqual(rc, 2)

    def test_explicit_path_argument(self):
        doc = self.write_doc("doc.md", "`notReal()` in `src/billing/charge.ts`\n")
        rc, out, err = self.run_main(["--root", self.root, "--index", self.index_path, doc])
        self.assertEqual(rc, 1)

    def test_no_docs_returns_0(self):
        rc, out, err = self.run_main(["--root", self.root, "--index", self.index_path])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
