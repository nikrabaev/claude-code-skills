import os, sys, json, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import extract_scripts


def write(path, content):
    with open(path, "w") as fh:
        fh.write(content)


class BaseTmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestPackageJson(BaseTmp):
    def test_a_scripts_object(self):
        write(
            os.path.join(self.root, "package.json"),
            json.dumps({"scripts": {"test": "jest", "build": "tsc -p ."}}),
        )
        entries = extract_scripts.extract(self.root)
        names = sorted(e["name"] for e in entries)
        self.assertEqual(names, ["build", "test"])
        self.assertEqual(len(entries), 2)
        by_name = {e["name"]: e for e in entries}
        self.assertEqual(by_name["test"]["command"], "jest")
        self.assertEqual(by_name["build"]["command"], "tsc -p .")
        for e in entries:
            self.assertEqual(e["source"], "package.json")

    def test_no_scripts_key(self):
        write(os.path.join(self.root, "package.json"), json.dumps({"name": "x"}))
        self.assertEqual(extract_scripts.extract(self.root), [])

    def test_malformed_json_ignored(self):
        write(os.path.join(self.root, "package.json"), "{ not json")
        self.assertEqual(extract_scripts.extract(self.root), [])


class TestMakefile(BaseTmp):
    def test_b_makefile(self):
        content = ".PHONY: build test\nbuild:\n\ttsc\ntest:\n\tjest\n"
        write(os.path.join(self.root, "Makefile"), content)
        entries = extract_scripts.extract(self.root)
        names = sorted(e["name"] for e in entries)
        self.assertEqual(names, ["build", "test"])
        self.assertNotIn(".PHONY", names)
        by_name = {e["name"]: e for e in entries}
        self.assertEqual(by_name["build"]["command"], "tsc")
        self.assertEqual(by_name["test"]["command"], "jest")
        for e in entries:
            self.assertEqual(e["source"], "Makefile")

    def test_pattern_rule_skipped(self):
        content = "%.o:\n\tcc -c\nreal:\n\techo hi\n"
        write(os.path.join(self.root, "Makefile"), content)
        names = sorted(e["name"] for e in extract_scripts.extract(self.root))
        self.assertEqual(names, ["real"])

    def test_target_without_recipe(self):
        content = "all:\nclean:\n\trm -rf build\n"
        write(os.path.join(self.root, "Makefile"), content)
        by_name = {e["name"]: e for e in extract_scripts.extract(self.root)}
        self.assertEqual(by_name["all"]["command"], "")
        self.assertEqual(by_name["clean"]["command"], "rm -rf build")


class TestJustfile(BaseTmp):
    def test_justfile(self):
        content = "build:\n    cargo build\ntest arg:\n    cargo test\n"
        write(os.path.join(self.root, "justfile"), content)
        entries = extract_scripts.extract(self.root)
        by_name = {e["name"]: e for e in entries}
        self.assertEqual(sorted(by_name), ["build", "test"])
        self.assertEqual(by_name["build"]["command"], "cargo build")
        self.assertEqual(by_name["test"]["command"], "cargo test")
        for e in entries:
            self.assertEqual(e["source"], "justfile")


class TestTaskfile(BaseTmp):
    def test_taskfile(self):
        content = (
            "version: '3'\n"
            "tasks:\n"
            "  build:\n"
            "    cmds:\n"
            "      - go build\n"
            "  test:\n"
            "    cmds:\n"
            "      - go test\n"
        )
        write(os.path.join(self.root, "Taskfile.yml"), content)
        entries = extract_scripts.extract(self.root)
        names = sorted(e["name"] for e in entries)
        self.assertEqual(names, ["build", "test"])
        for e in entries:
            self.assertEqual(e["source"], "Taskfile.yml")
            self.assertEqual(e["command"], "")


class TestDedupAndEmpty(BaseTmp):
    def test_c_empty_root(self):
        self.assertEqual(extract_scripts.extract(self.root), [])
        self.assertEqual(extract_scripts.main(["--root", self.root]), 0)

    def test_dedup_by_source_name(self):
        # Two Makefile-style targets with same name collapse to one entry.
        content = "build:\n\tfirst\nbuild:\n\tsecond\n"
        write(os.path.join(self.root, "Makefile"), content)
        entries = [e for e in extract_scripts.extract(self.root) if e["name"] == "build"]
        self.assertEqual(len(entries), 1)


class TestMain(BaseTmp):
    def test_d_json_output(self):
        write(
            os.path.join(self.root, "package.json"),
            json.dumps({"scripts": {"test": "jest"}}),
        )
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = extract_scripts.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIsInstance(parsed, list)
        self.assertEqual(parsed[0]["name"], "test")

    def test_d_empty_json_output(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = extract_scripts.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue()), [])

    def test_missing_root_is_usage_error(self):
        rc = extract_scripts.main(["--root", os.path.join(self.root, "nope")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
