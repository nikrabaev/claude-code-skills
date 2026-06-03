import os, sys, json, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # adds scripts/ to path
import scan_repo


def write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


class ScanRepoTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    # a)
    def test_stack_detects_react_from_package_json(self):
        write(
            os.path.join(self.root, "package.json"),
            json.dumps({"dependencies": {"react": "^18.2.0"}}),
        )
        result = scan_repo.scan(self.root)
        react = [e for e in result["stack"] if e["name"] == "react"]
        self.assertEqual(len(react), 1)
        self.assertEqual(react[0]["source"], "package.json")
        self.assertIn("18.2.0", react[0]["version"])

    # b)
    def test_top_dirs_includes_src_and_tests(self):
        write(os.path.join(self.root, "src", "a.py"), "print(1)")
        write(os.path.join(self.root, "tests", "b.py"), "print(2)")
        result = scan_repo.scan(self.root)
        self.assertIn("src", result["top_dirs"])
        self.assertIn("tests", result["top_dirs"])

    # c)
    def test_languages_counts_two_python_files(self):
        write(os.path.join(self.root, "one.py"), "x = 1")
        write(os.path.join(self.root, "two.py"), "y = 2")
        result = scan_repo.scan(self.root)
        self.assertEqual(result["languages"]["python"], 2)

    # d)
    def test_monorepo_packages_from_workspaces(self):
        write(
            os.path.join(self.root, "package.json"),
            json.dumps({"workspaces": ["packages/*"]}),
        )
        write(
            os.path.join(self.root, "packages", "a", "package.json"),
            json.dumps({"name": "a"}),
        )
        write(
            os.path.join(self.root, "packages", "b", "package.json"),
            json.dumps({"name": "b"}),
        )
        result = scan_repo.scan(self.root)
        self.assertIn("a", result["monorepo_packages"])
        self.assertIn("b", result["monorepo_packages"])

    # e)
    def test_node_modules_is_pruned(self):
        write(os.path.join(self.root, "node_modules", "pkg", "index.js"), "1")
        write(os.path.join(self.root, "app.js"), "2")
        result = scan_repo.scan(self.root)
        # Only the top-level app.js should be counted, not the one in node_modules.
        self.assertEqual(result["languages"].get("javascript"), 1)

    # f)
    def test_main_json_returns_zero_and_valid_json(self):
        write(os.path.join(self.root, "x.py"), "z = 3")
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = scan_repo.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, dict)
        self.assertEqual(data["languages"]["python"], 1)


if __name__ == "__main__":
    unittest.main()
