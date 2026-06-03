import os, sys, json, io, tempfile, shutil, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import extract_events


def write(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestVerbs(Base):
    def test_emit(self):
        write(self.root, "src/bus.ts", 'bus.emit("orders.created", payload)\n')
        rows = extract_events.extract(self.root)
        self.assertIn(
            {"name": "orders.created", "action": "emit", "file": "src/bus.ts"}, rows
        )

    def test_publish(self):
        write(self.root, "src/q.ts", "queue.publish('payments', msg)\n")
        rows = extract_events.extract(self.root)
        self.assertIn({"name": "payments", "action": "publish", "file": "src/q.ts"}, rows)

    def test_subscribe(self):
        write(self.root, "src/s.ts", 'sub.subscribe("user.signup", fn)\n')
        rows = extract_events.extract(self.root)
        self.assertIn({"name": "user.signup", "action": "subscribe", "file": "src/s.ts"}, rows)

    def test_consume(self):
        write(self.root, "src/w.ts", 'worker.consume("jobs", fn)\n')
        rows = extract_events.extract(self.root)
        self.assertIn({"name": "jobs", "action": "consume", "file": "src/w.ts"}, rows)

    def test_on_excluded(self):
        write(self.root, "src/p.ts", 'process.on("exit", fn)\n')
        rows = extract_events.extract(self.root)
        self.assertEqual([r for r in rows if r["action"] == "on"], [])
        self.assertEqual(rows, [])


class TestMainAndEmpty(Base):
    def test_empty(self):
        self.assertEqual(extract_events.extract(self.root), [])
        self.assertEqual(extract_events.main(["--root", self.root]), 0)

    def test_json(self):
        write(self.root, "src/b.ts", 'b.emit("x")\n')
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = extract_events.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        self.assertIsInstance(json.loads(buf.getvalue()), list)

    def test_bad_root(self):
        self.assertEqual(extract_events.main(["--root", os.path.join(self.root, "no")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
