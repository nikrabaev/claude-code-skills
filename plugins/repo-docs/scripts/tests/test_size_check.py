import os, sys, json, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import size_check

try:
    from io import StringIO
    from contextlib import redirect_stdout
except ImportError:  # pragma: no cover
    raise


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class SizeCheckTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    # a) small root CLAUDE.md -> not over, not near; main returns 0
    def test_a_small_root_under_budget(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "x" * 100)
        result = size_check.check(self.root)
        self.assertFalse(result["over_budget"])
        self.assertFalse(result["near_budget"])
        self.assertEqual(len(result["chain_files"]), 1)
        self.assertEqual(result["chain_bytes"], 100)
        self.assertEqual(size_check.main(["--root", self.root]), 0)

    # b) two ~20000 byte files with --cwd sub -> 2 files, >= budget, over_budget True; main returns 1
    def test_b_two_files_over_budget(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "x" * 20000)
        write_file(os.path.join(self.root, "sub", "CLAUDE.md"), "x" * 20000)
        result = size_check.check(self.root, cwd="sub")
        self.assertEqual(len(result["chain_files"]), 2)
        self.assertGreaterEqual(result["chain_bytes"], 32768)
        self.assertTrue(result["over_budget"])
        self.assertEqual(size_check.main(["--root", self.root, "--cwd", "sub"]), 1)

    # c) single file between 0.9*budget and budget -> near_budget True, over_budget False; main returns 0; prints WARNING
    def test_c_near_budget_warning(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "x" * 30000)
        result = size_check.check(self.root)
        self.assertTrue(result["near_budget"])
        self.assertFalse(result["over_budget"])
        buf = StringIO()
        with redirect_stdout(buf):
            rc = size_check.main(["--root", self.root])
        self.assertEqual(rc, 0)
        self.assertIn("WARNING", buf.getvalue())

    # d) empty root CLAUDE.md skipped, only non-empty sub counted
    def test_d_empty_file_skipped(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "")
        write_file(os.path.join(self.root, "sub", "CLAUDE.md"), "x" * 100)
        files = size_check.chain_files(self.root, "sub")
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith(os.path.join("sub", "CLAUDE.md")))
        result = size_check.check(self.root, cwd="sub")
        self.assertEqual(len(result["chain_files"]), 1)
        self.assertEqual(result["chain_bytes"], 100)

    # e) --json output round-trips through json.loads with documented keys
    def test_e_json_output(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "x" * 100)
        buf = StringIO()
        with redirect_stdout(buf):
            rc = size_check.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        for key in ("chain_files", "chain_bytes", "budget", "over_budget", "near_budget", "files"):
            self.assertIn(key, data)
        self.assertEqual(data["chain_bytes"], 100)
        self.assertIsInstance(data["files"], list)
        self.assertIn("path", data["files"][0])
        self.assertIn("bytes", data["files"][0])

    # extra: nested chain ordering root-first, deepest-last
    def test_f_chain_ordering(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "a")
        write_file(os.path.join(self.root, "a", "CLAUDE.md"), "b")
        write_file(os.path.join(self.root, "a", "b", "CLAUDE.md"), "c")
        files = size_check.chain_files(self.root, os.path.join("a", "b"))
        self.assertEqual(len(files), 3)
        self.assertEqual(files[0], os.path.join(self.root, "CLAUDE.md"))
        self.assertEqual(files[1], os.path.join(self.root, "a", "CLAUDE.md"))
        self.assertEqual(files[2], os.path.join(self.root, "a", "b", "CLAUDE.md"))

    # extra: chain files are joined with a blank line ("\n\n")
    def test_g_blank_line_join_bytes(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "ab")
        write_file(os.path.join(self.root, "sub", "CLAUDE.md"), "cd")
        result = size_check.check(self.root, cwd="sub")
        # "ab" + "\n\n" + "cd" = 6 bytes
        self.assertEqual(result["chain_bytes"], 6)

    # extra: no CLAUDE.md anywhere -> empty chain, 0 bytes, rc 0
    def test_h_no_files(self):
        result = size_check.check(self.root)
        self.assertEqual(result["chain_files"], [])
        self.assertEqual(result["chain_bytes"], 0)
        self.assertFalse(result["over_budget"])
        self.assertFalse(result["near_budget"])
        self.assertEqual(size_check.main(["--root", self.root]), 0)

    # extra: usage error (nonexistent root) -> exit code 2
    def test_i_bad_root_exit_2(self):
        buf = StringIO()
        from io import StringIO as _S
        err = _S()
        from contextlib import redirect_stderr
        with redirect_stdout(buf), redirect_stderr(err):
            rc = size_check.main(["--root", os.path.join(self.root, "does-not-exist")])
        self.assertEqual(rc, 2)

    # extra: a custom --budget lowers the threshold for over_budget
    def test_j_custom_budget(self):
        write_file(os.path.join(self.root, "CLAUDE.md"), "x" * 100)
        self.assertEqual(size_check.main(["--root", self.root, "--budget", "50"]), 1)
        self.assertEqual(size_check.main(["--root", self.root, "--budget", "200"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
