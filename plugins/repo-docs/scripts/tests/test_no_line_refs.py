import os, sys, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # adds scripts/ to path
import no_line_refs


def write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


class FindViolationsTest(unittest.TestCase):
    # a) file-with-extension + :NNN
    def test_file_with_extension_and_line_number(self):
        result = no_line_refs.find_violations("See src/app.ts:412 for details")
        self.assertEqual(len(result), 1)
        self.assertIn("src/app.ts:412", result[0]["match"])
        self.assertEqual(result[0]["line"], 1)

    # b) the phrase "line NNN"
    def test_line_phrase(self):
        result = no_line_refs.find_violations("see line 42 of the file")
        self.assertEqual(len(result), 1)
        self.assertIn("line 42", result[0]["match"].lower())

    # b2) case-insensitive "Line NNN"
    def test_line_phrase_case_insensitive(self):
        result = no_line_refs.find_violations("jump to Line 7 now")
        self.assertEqual(len(result), 1)

    # c) host:port must NOT flag
    def test_localhost_port_not_flagged(self):
        result = no_line_refs.find_violations("Dev server runs on localhost:3000")
        self.assertEqual(result, [])

    # d) URL with port must NOT flag
    def test_url_with_port_not_flagged(self):
        result = no_line_refs.find_violations(
            "Health check at https://example.com:8080/health"
        )
        self.assertEqual(result, [])

    # d2) a URL whose path itself ends in name.ext:NN must NOT be flagged [I1]
    def test_url_embedding_line_ref_not_flagged(self):
        result = no_line_refs.find_violations(
            "Source at https://example.com:8080/src/file.ts:42 online"
        )
        self.assertEqual(result, [])

    # d3) a real line ref next to a URL is still flagged (no over-suppression)
    def test_real_line_ref_beside_url_still_flagged(self):
        result = no_line_refs.find_violations(
            "Visit https://example.com/x but fix src/app.ts:412 first"
        )
        self.assertEqual(len(result), 1)
        self.assertIn("src/app.ts:412", result[0]["match"])

    # e) fenced code block content ignored (backtick fence)
    def test_fenced_backtick_block_ignored(self):
        text = "Intro\n```\nsrc/x.ts:9\n```\nOutro\n"
        self.assertEqual(no_line_refs.find_violations(text), [])

    # e2) fenced code block content ignored (tilde fence)
    def test_fenced_tilde_block_ignored(self):
        text = "Intro\n~~~\nsrc/x.ts:9\n~~~\nOutro\n"
        self.assertEqual(no_line_refs.find_violations(text), [])

    # f) C++ scope resolution must NOT flag
    def test_cpp_scope_not_flagged(self):
        result = no_line_refs.find_violations("Use std::vector here")
        self.assertEqual(result, [])

    # extra: line number is mapped back to the original document
    def test_line_number_mapping_after_fence(self):
        text = "Line one\n```\ncode\n```\nSee foo.py:10 here\n"
        result = no_line_refs.find_violations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["line"], 5)

    # extra: a violation inside a fence is skipped but one after it is found
    def test_violation_after_fence_only(self):
        text = "```\nsrc/x.ts:9\n```\nbar.js:3\n"
        result = no_line_refs.find_violations(text)
        self.assertEqual(len(result), 1)
        self.assertIn("bar.js:3", result[0]["match"])


class ScanPathsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_scan_paths_reports_file_and_line(self):
        p = os.path.join(self.root, "doc.md")
        write(p, "intro\nSee app.py:5 now\n")
        result = no_line_refs.scan_paths([p])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file"], p)
        self.assertEqual(result[0]["line"], 2)
        self.assertIn("app.py:5", result[0]["match"])

    def test_scan_paths_clean_file(self):
        p = os.path.join(self.root, "clean.md")
        write(p, "all good here\nlocalhost:3000\nstd::vector\n")
        self.assertEqual(no_line_refs.scan_paths([p]), [])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    # g) clean doc -> exit 0
    def test_main_clean_returns_zero(self):
        write(os.path.join(self.root, "a.md"), "no problems here\nlocalhost:3000\n")
        self.assertEqual(no_line_refs.main(["--root", self.root]), 0)

    # g) doc with foo.py:10 -> exit 1
    def test_main_violation_returns_one(self):
        write(os.path.join(self.root, "b.md"), "broken foo.py:10 ref\n")
        self.assertEqual(no_line_refs.main(["--root", self.root]), 1)

    def test_main_skips_git_and_node_modules(self):
        write(os.path.join(self.root, ".git", "x.md"), "bad foo.py:10\n")
        write(os.path.join(self.root, "node_modules", "y.md"), "bad bar.js:3\n")
        write(os.path.join(self.root, "ok.md"), "all clean\n")
        self.assertEqual(no_line_refs.main(["--root", self.root]), 0)

    def test_main_json_flag_returns_one_on_violation(self):
        write(os.path.join(self.root, "c.md"), "see line 99 here\n")
        self.assertEqual(no_line_refs.main(["--root", self.root, "--json"]), 1)

    def test_main_bad_root_returns_two(self):
        missing = os.path.join(self.root, "does-not-exist")
        self.assertEqual(no_line_refs.main(["--root", missing]), 2)


if __name__ == "__main__":
    unittest.main()
