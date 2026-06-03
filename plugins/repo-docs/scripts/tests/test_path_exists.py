import os, sys, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import path_exists


def write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def mkdir(path):
    os.makedirs(path, exist_ok=True)


class BaseTmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestCheckDoc(BaseTmp):
    # a) referenced file exists -> no violation
    def test_a_existing_file_no_violation(self):
        write(os.path.join(self.root, "src", "exists.ts"), "x")
        text = "See `src/exists.ts` for details.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    # b) referenced file missing -> one violation
    def test_b_missing_file_one_violation(self):
        text = "See `src/missing.ts` for details.\n"
        violations = path_exists.check_doc(text, self.root)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["token"], "src/missing.ts")
        self.assertEqual(violations[0]["line"], 1)

    # c) URL -> skipped
    def test_c_url_skipped(self):
        text = "Visit `https://x.com/y` now.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_c_scheme_url_skipped(self):
        text = "Use `ftp://host/path` here.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_c_mailto_skipped(self):
        text = "Email `mailto:a@b.com` ok.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    # dotted identifiers (Bun.argv, process.env, React.FC) are NOT file paths:
    # a slash-less token is only a path when its extension is a real file extension.
    def test_dotted_identifier_skipped(self):
        text = "Parses `Bun.argv` and reads `process.env` then `React.FC`.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    # a bare filename with a REAL extension is still checked (flagged if missing)
    def test_bare_known_extension_still_checked(self):
        text = "See `config.yaml` for setup.\n"
        violations = path_exists.check_doc(text, self.root)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["token"], "config.yaml")

    def test_bare_known_extension_exists_ok(self):
        write(os.path.join(self.root, "config.yaml"), "k: v\n")
        text = "See `config.yaml` for setup.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    # d) symbol/call -> skipped
    def test_d_symbol_call_skipped(self):
        text = "Call `processPayment()` to charge.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_d_paren_token_skipped(self):
        text = "The `foo(bar)` thing.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    # e) directory exists -> no violation
    def test_e_existing_dir_no_violation(self):
        mkdir(os.path.join(self.root, "src"))
        text = "Look in `src/` folder.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    # f) env var -> skipped
    def test_f_env_var_skipped(self):
        text = "Set `MENV_PASSPHRASE` first.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_f_simple_envvar_skipped(self):
        text = "Set `PATH` carefully.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    # extra coverage of extraction rules
    def test_whitespace_span_skipped(self):
        text = "Run `npm install foo` to begin.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_glob_skipped(self):
        text = "Match `src/*.ts` glob.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_question_glob_skipped(self):
        text = "Match `file?.ts` glob.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_plain_word_not_a_path(self):
        # No slash, no extension -> not a path token, ignored.
        text = "The word `hello` here.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_filename_with_extension_is_path(self):
        # Bare filename with extension counts as a path; missing -> violation.
        text = "Open `README.md` please.\n"
        violations = path_exists.check_doc(text, self.root)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["token"], "README.md")

    def test_filename_with_extension_exists(self):
        write(os.path.join(self.root, "README.md"), "hi")
        text = "Open `README.md` please.\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_trailing_punctuation_stripped(self):
        write(os.path.join(self.root, "src", "exists.ts"), "x")
        text = "See `src/exists.ts.`\n"
        # trailing '.' stripped, then resolves to existing file
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_trailing_slash_stripped_for_file(self):
        write(os.path.join(self.root, "src", "exists.ts"), "x")
        text = "See `src/exists.ts/`\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])

    def test_line_number_reported(self):
        text = "line one\nline two `src/missing.ts`\nline three\n"
        violations = path_exists.check_doc(text, self.root)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["line"], 2)

    def test_double_backtick_span_not_treated_as_inline(self):
        # Triple/double-backtick code fences are not single-backtick inline spans.
        text = "```\nsrc/missing.ts\n```\n"
        self.assertEqual(path_exists.check_doc(text, self.root), [])


class TestExtractPathTokens(BaseTmp):
    def test_returns_only_path_tokens(self):
        text = (
            "`src/a.ts` and `processPayment()` and `PATH` and "
            "`https://x.com` and `config.json` and `plainword`\n"
        )
        tokens = path_exists.extract_path_tokens(text)
        self.assertEqual(tokens, ["src/a.ts", "config.json"])


class TestScanPaths(BaseTmp):
    def test_scan_paths_reports_file_line_token(self):
        doc = os.path.join(self.root, "doc.md")
        write(doc, "intro\n`src/missing.ts`\n")
        records = path_exists.scan_paths([doc], self.root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["file"], doc)
        self.assertEqual(records[0]["line"], 2)
        self.assertEqual(records[0]["token"], "src/missing.ts")

    def test_scan_paths_clean_doc_empty(self):
        write(os.path.join(self.root, "src", "exists.ts"), "x")
        doc = os.path.join(self.root, "doc.md")
        write(doc, "`src/exists.ts`\n")
        self.assertEqual(path_exists.scan_paths([doc], self.root), [])


class TestMain(BaseTmp):
    # g) clean doc -> 0 ; missing path -> 1
    def test_g_clean_doc_returns_zero(self):
        write(os.path.join(self.root, "src", "exists.ts"), "x")
        write(os.path.join(self.root, "doc.md"), "`src/exists.ts`\n")
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = path_exists.main(["--root", self.root])
        self.assertEqual(rc, 0)

    def test_g_missing_path_returns_one(self):
        write(os.path.join(self.root, "doc.md"), "`src/missing.ts`\n")
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = path_exists.main(["--root", self.root])
        self.assertEqual(rc, 1)
        out = buf.getvalue()
        self.assertIn("src/missing.ts", out)
        self.assertIn("not found", out)

    def test_main_json_output(self):
        write(os.path.join(self.root, "doc.md"), "`src/missing.ts`\n")
        import io, json
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = path_exists.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 1)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["token"], "src/missing.ts")
        self.assertEqual(data[0]["line"], 1)
        self.assertIn("doc.md", data[0]["file"])

    def test_main_json_clean_empty_list(self):
        write(os.path.join(self.root, "src", "exists.ts"), "x")
        write(os.path.join(self.root, "doc.md"), "`src/exists.ts`\n")
        import io, json
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = path_exists.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue()), [])

    def test_main_skips_git_and_node_modules(self):
        # Docs inside ignored dirs must not be scanned.
        write(os.path.join(self.root, ".git", "bad.md"), "`x/missing.ts`\n")
        write(os.path.join(self.root, "node_modules", "p", "bad.md"), "`y/missing.ts`\n")
        write(os.path.join(self.root, "good.md"), "clean\n")
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = path_exists.main(["--root", self.root])
        self.assertEqual(rc, 0)

    def test_main_explicit_path_arg(self):
        write(os.path.join(self.root, "doc.md"), "`src/missing.ts`\n")
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = path_exists.main(["--root", self.root, os.path.join(self.root, "doc.md")])
        self.assertEqual(rc, 1)

    def test_main_missing_root_usage_error(self):
        rc = path_exists.main(["--root", os.path.join(self.root, "nope")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
