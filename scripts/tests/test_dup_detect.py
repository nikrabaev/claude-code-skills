#!/usr/bin/env python3
import os, sys, json, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dup_detect


PKG = {
    "scripts": {
        "test": "jest",
        "build": "tsc",
        "lint": "eslint .",
        "dev": "vite",
    }
}


class TempRoot(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, relpath, content):
        full = os.path.join(self.root, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full

    def write_pkg(self, data=None):
        return self.write("package.json", json.dumps(data or PKG, indent=2))


class TestFencedBlocks(unittest.TestCase):
    def test_extracts_single_block(self):
        text = "intro\n```\nhello\nworld\n```\noutro\n"
        blocks = dup_detect.fenced_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertIn("hello", blocks[0])
        self.assertIn("world", blocks[0])

    def test_extracts_block_with_language_tag(self):
        text = "```json\n{\"a\": 1}\n```\n"
        blocks = dup_detect.fenced_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertIn("\"a\": 1", blocks[0])
        # language tag must not leak into the content
        self.assertNotIn("json", blocks[0])

    def test_multiple_blocks(self):
        text = "```\none\n```\nmid\n```\ntwo\n```\n"
        blocks = dup_detect.fenced_blocks(text)
        self.assertEqual(len(blocks), 2)

    def test_no_blocks(self):
        self.assertEqual(dup_detect.fenced_blocks("just prose, no fences"), [])

    def test_unterminated_block_ignored(self):
        text = "```\ndangling content with no close fence\n"
        self.assertEqual(dup_detect.fenced_blocks(text), [])


class TestPackageScripts(TempRoot):
    def test_reads_scripts(self):
        self.write_pkg()
        scripts = dup_detect.package_scripts(self.root)
        self.assertEqual(len(scripts), 4)
        self.assertIn("test: jest", scripts)
        self.assertIn("build: tsc", scripts)
        self.assertIn("lint: eslint .", scripts)
        self.assertIn("dev: vite", scripts)

    def test_missing_package_json(self):
        self.assertEqual(dup_detect.package_scripts(self.root), [])

    def test_no_scripts_key(self):
        self.write("package.json", json.dumps({"name": "x"}))
        self.assertEqual(dup_detect.package_scripts(self.root), [])

    def test_malformed_json(self):
        self.write("package.json", "{not valid json")
        self.assertEqual(dup_detect.package_scripts(self.root), [])


class TestJaccard(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(dup_detect.jaccard({"a", "b"}, {"a", "b"}), 1.0)

    def test_disjoint(self):
        self.assertEqual(dup_detect.jaccard({"a"}, {"b"}), 0.0)

    def test_both_empty(self):
        self.assertEqual(dup_detect.jaccard(set(), set()), 0.0)

    def test_partial(self):
        # intersection {a,b} = 2, union {a,b,c} = 3
        self.assertAlmostEqual(dup_detect.jaccard({"a", "b"}, {"a", "b", "c"}), 2.0 / 3.0)


class TestCheckPastedScripts(TempRoot):
    def test_case_a_pasted_scripts_flagged(self):
        self.write_pkg()
        doc = self.write(
            "README.md",
            'Scripts:\n```\n"test": "jest",\n"build": "tsc",'
            '\n"lint": "eslint .",\n"dev": "vite"\n```\n',
        )
        findings = dup_detect.check(self.root, [doc])
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["kind"], "pasted-scripts")
        self.assertEqual(f["source"], "package.json")
        self.assertEqual(f["file"], doc)

    def test_case_b_reference_not_copy(self):
        self.write_pkg()
        doc = self.write(
            "README.md",
            "Build/test commands: see `package.json` scripts for details.\n",
        )
        findings = dup_detect.check(self.root, [doc])
        self.assertEqual(findings, [])

    def test_case_c_unrelated_prose_and_block(self):
        self.write_pkg()
        doc = self.write(
            "GUIDE.md",
            "Here is some unrelated prose explaining a concept.\n\n"
            "```python\nprint('hello world')\n```\n",
        )
        findings = dup_detect.check(self.root, [doc])
        self.assertEqual(findings, [])


class TestCheckConfigDuplication(TempRoot):
    def test_tsconfig_paste_flagged(self):
        tsconfig = json.dumps(
            {
                "compilerOptions": {
                    "target": "es2020",
                    "module": "commonjs",
                    "strict": True,
                    "outDir": "dist",
                    "rootDir": "src",
                }
            },
            indent=2,
        )
        self.write("tsconfig.json", tsconfig)
        self.write_pkg()
        doc = self.write("DOC.md", "Config:\n```json\n" + tsconfig + "\n```\n")
        findings = dup_detect.check(self.root, [doc])
        kinds = [f["kind"] for f in findings]
        self.assertIn("config-duplication", kinds)
        cfg = [f for f in findings if f["kind"] == "config-duplication"][0]
        self.assertEqual(os.path.basename(cfg["source"]), "tsconfig.json")

    def test_config_glob_file_detected(self):
        cfg_text = (
            "export default {\n"
            "  plugins: [react(), tsconfigPaths()],\n"
            "  server: { port: 3000, host: true },\n"
            "  build: { outDir: 'dist', sourcemap: true },\n"
            "}\n"
        )
        self.write("vite.config.ts", cfg_text)
        self.write_pkg()
        doc = self.write("DOC.md", "```ts\n" + cfg_text + "\n```\n")
        findings = dup_detect.check(self.root, [doc])
        sources = [os.path.basename(f["source"]) for f in findings if f["kind"] == "config-duplication"]
        self.assertIn("vite.config.ts", sources)

    def test_below_threshold_not_flagged(self):
        self.write("tsconfig.json", json.dumps({"compilerOptions": {"target": "es2020"}}))
        self.write_pkg()
        doc = self.write("DOC.md", "```\nsomething completely different here\n```\n")
        findings = dup_detect.check(self.root, [doc])
        self.assertEqual([f for f in findings if f["kind"] == "config-duplication"], [])


class TestMain(TempRoot):
    def test_case_a_main_returns_1(self):
        self.write_pkg()
        self.write(
            "README.md",
            'Scripts:\n```\n"test": "jest",\n"build": "tsc",'
            '\n"lint": "eslint .",\n"dev": "vite"\n```\n',
        )
        rc = dup_detect.main(["--root", self.root])
        self.assertEqual(rc, 1)

    def test_case_b_main_returns_0(self):
        self.write_pkg()
        self.write(
            "README.md",
            "Build/test commands: see `package.json` scripts for details.\n",
        )
        rc = dup_detect.main(["--root", self.root])
        self.assertEqual(rc, 0)

    def test_case_c_main_returns_0(self):
        self.write_pkg()
        self.write(
            "GUIDE.md",
            "Unrelated prose.\n\n```python\nprint('hi')\n```\n",
        )
        rc = dup_detect.main(["--root", self.root])
        self.assertEqual(rc, 0)

    def test_case_d_json_roundtrips(self):
        self.write_pkg()
        self.write(
            "README.md",
            'Scripts:\n```\n"test": "jest",\n"build": "tsc",'
            '\n"lint": "eslint .",\n"dev": "vite"\n```\n',
        )
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = dup_detect.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 1)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["kind"], "pasted-scripts")
        self.assertIn("file", data[0])
        self.assertIn("source", data[0])
        self.assertIn("detail", data[0])

    def test_explicit_glob_argument(self):
        self.write_pkg()
        self.write(
            "docs/api.md",
            'Scripts:\n```\n"test": "jest",\n"build": "tsc",'
            '\n"lint": "eslint .",\n"dev": "vite"\n```\n',
        )
        rc = dup_detect.main(["--root", self.root, os.path.join(self.root, "docs", "*.md")])
        self.assertEqual(rc, 1)

    def test_bad_root_returns_2(self):
        rc = dup_detect.main(["--root", os.path.join(self.root, "does-not-exist")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
