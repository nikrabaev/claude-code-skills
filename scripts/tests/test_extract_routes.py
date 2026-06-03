import os, sys, json, io, tempfile, shutil, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import extract_routes


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


class TestExpress(Base):
    def test_get_with_handler(self):
        write(self.root, "src/api.ts", "router.get('/orders', listOrders)\n")
        rows = extract_routes.extract(self.root)
        self.assertIn(
            {"method": "GET", "path": "/orders", "handler": "listOrders", "file": "src/api.ts"},
            rows,
        )

    def test_post_double_quotes(self):
        write(self.root, "src/api.ts", 'app.post("/orders", createOrder)\n')
        rows = extract_routes.extract(self.root)
        self.assertIn(
            {"method": "POST", "path": "/orders", "handler": "createOrder", "file": "src/api.ts"},
            rows,
        )

    def test_anonymous_handler_empty(self):
        write(self.root, "src/api.ts", "app.get('/ping', (req, res) => res.send('ok'))\n")
        rows = extract_routes.extract(self.root)
        self.assertIn(
            {"method": "GET", "path": "/ping", "handler": "", "file": "src/api.ts"}, rows
        )


class TestFlaskFastapi(Base):
    def test_fastapi_decorator(self):
        write(self.root, "app.py", '@router.post("/items")\ndef create_item():\n    pass\n')
        rows = extract_routes.extract(self.root)
        self.assertIn(
            {"method": "POST", "path": "/items", "handler": "create_item", "file": "app.py"},
            rows,
        )

    def test_flask_route_default_get(self):
        write(self.root, "app.py", '@app.route("/health")\ndef health():\n    return "ok"\n')
        rows = extract_routes.extract(self.root)
        self.assertIn(
            {"method": "GET", "path": "/health", "handler": "health", "file": "app.py"}, rows
        )

    def test_flask_route_methods_list(self):
        write(self.root, "app.py",
              '@app.route("/submit", methods=["GET", "POST"])\ndef submit():\n    pass\n')
        rows = extract_routes.extract(self.root)
        methods = sorted(r["method"] for r in rows if r["path"] == "/submit")
        self.assertEqual(methods, ["GET", "POST"])


class TestComments(Base):
    def test_js_commented_route_ignored(self):
        write(self.root, "src/api.ts",
              "// router.get('/commented', h)\nrouter.get('/real', realH)\n")
        rows = extract_routes.extract(self.root)
        paths = [r["path"] for r in rows]
        self.assertNotIn("/commented", paths)
        self.assertIn("/real", paths)

    def test_python_commented_decorator_ignored(self):
        write(self.root, "app.py",
              '# @app.get("/commented")\n@app.get("/real")\n'
              "async def real_handler():\n    pass\n")
        rows = extract_routes.extract(self.root)
        paths = [r["path"] for r in rows]
        self.assertNotIn("/commented", paths)
        real = [r for r in rows if r["path"] == "/real"]
        self.assertEqual(len(real), 1)
        self.assertEqual(real[0]["handler"], "real_handler")


class TestMainAndEmpty(Base):
    def test_empty_repo(self):
        self.assertEqual(extract_routes.extract(self.root), [])
        self.assertEqual(extract_routes.main(["--root", self.root]), 0)

    def test_json_output(self):
        write(self.root, "src/api.ts", "router.get('/x', h)\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = extract_routes.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        self.assertIsInstance(json.loads(buf.getvalue()), list)

    def test_bad_root(self):
        self.assertEqual(extract_routes.main(["--root", os.path.join(self.root, "nope")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
