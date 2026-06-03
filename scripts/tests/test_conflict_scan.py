import os, sys, json, io, tempfile, shutil, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conflict_scan


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


class TestRuleVsRule(Base):
    def test_tabs_vs_spaces(self):
        text = "Use tabs for indentation.\n\nElsewhere: use spaces for indentation.\n"
        cats = [f["category"] for f in conflict_scan.find_conflicts(text)]
        self.assertIn("indentation", cats)

    def test_tabs_only_no_conflict(self):
        self.assertEqual(conflict_scan.find_conflicts("Use tabs for indentation.\n"), [])

    def test_spaces_not_tabs_single_rule_no_conflict(self):
        # one imperative ("use spaces, not tabs") is NOT a contradiction
        self.assertEqual(conflict_scan.find_conflicts("Use spaces, not tabs.\n"), [])

    def test_quotes_conflict(self):
        text = "Use single quotes.\nLater: use double quotes.\n"
        self.assertIn("quotes", [f["category"] for f in conflict_scan.find_conflicts(text)])

    def test_semicolons_conflict(self):
        text = "Always use semicolons.\nNo semicolons in this codebase.\n"
        self.assertIn("semicolons", [f["category"] for f in conflict_scan.find_conflicts(text)])


class TestRuleVsInstance(Base):
    def test_named_only_with_positive_default_export(self):
        text = "Named exports only.\n\n```ts\nexport default function App() {}\n```\n"
        self.assertIn("exports", [f["category"] for f in conflict_scan.find_conflicts(text)])

    def test_named_only_with_prohibited_default_no_conflict(self):
        # the anti-pattern shown as forbidden (🚫) must NOT be flagged — low-FP
        text = "Named exports only. ✅ `export function x()` 🚫 `export default`\n"
        self.assertEqual(conflict_scan.find_conflicts(text), [])

    def test_default_export_without_rule_no_conflict(self):
        text = "```ts\nexport default function App() {}\n```\n"
        self.assertEqual(conflict_scan.find_conflicts(text), [])


class TestMain(Base):
    def test_advisory_exit_zero_with_findings(self):
        write(self.root, "a.md", "Use tabs for indentation.\nUse spaces for indentation.\n")
        self.assertEqual(conflict_scan.main(["--root", self.root, "a.md"]), 0)

    def test_strict_exit_one_with_findings(self):
        write(self.root, "a.md", "Use tabs for indentation.\nUse spaces for indentation.\n")
        self.assertEqual(conflict_scan.main(["--root", self.root, "--strict", "a.md"]), 1)

    def test_clean_doc_exit_zero(self):
        write(self.root, "a.md", "Use spaces for indentation.\n")
        self.assertEqual(conflict_scan.main(["--root", self.root, "--strict", "a.md"]), 0)

    def test_json_output(self):
        write(self.root, "a.md", "Use single quotes.\nUse double quotes.\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = conflict_scan.main(["--root", self.root, "--json", "a.md"])
        self.assertEqual(rc, 0)
        self.assertIsInstance(json.loads(buf.getvalue()), list)

    def test_bad_root(self):
        self.assertEqual(conflict_scan.main(["--root", os.path.join(self.root, "no")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
