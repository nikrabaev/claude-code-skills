import os, sys, json, io, tempfile, shutil, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import extract_schema


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


class TestPrisma(Base):
    def test_model(self):
        write(self.root, "prisma/schema.prisma",
              "model Order {\n  id Int @id\n}\nmodel User {\n  id Int @id\n}\n")
        rows = extract_schema.extract(self.root)
        got = {(r["entity"], r["kind"], r["source"]) for r in rows}
        self.assertIn(("Order", "model", "prisma"), got)
        self.assertIn(("User", "model", "prisma"), got)


class TestSql(Base):
    def test_create_table(self):
        write(self.root, "migrations/001.sql", "CREATE TABLE orders (id serial);\n")
        rows = extract_schema.extract(self.root)
        self.assertIn(
            {"entity": "orders", "kind": "table", "source": "sql", "file": "migrations/001.sql"},
            rows,
        )

    def test_create_table_if_not_exists_quoted(self):
        write(self.root, "migrations/002.sql", 'CREATE TABLE IF NOT EXISTS "users" (id int);\n')
        rows = extract_schema.extract(self.root)
        entities = {r["entity"] for r in rows}
        self.assertIn("users", entities)


class TestDjango(Base):
    def test_model_class(self):
        write(self.root, "models.py", "class Customer(models.Model):\n    pass\n")
        rows = extract_schema.extract(self.root)
        self.assertIn(
            {"entity": "Customer", "kind": "model", "source": "django", "file": "models.py"},
            rows,
        )

    def test_model_with_mixin_after_base(self):
        # A mixin listed AFTER models.Model is common in real Django code.
        write(self.root, "models.py", "class Invoice(models.Model, TimestampMixin):\n    pass\n")
        rows = extract_schema.extract(self.root)
        self.assertIn("Invoice", {r["entity"] for r in rows})

    def test_model_with_mixin_before_base(self):
        write(self.root, "models.py", "class Note(TimestampMixin, models.Model):\n    pass\n")
        rows = extract_schema.extract(self.root)
        self.assertIn("Note", {r["entity"] for r in rows})

    def test_dotted_base_still_matches(self):
        write(self.root, "models.py", "class User(django.db.models.Model):\n    pass\n")
        rows = extract_schema.extract(self.root)
        self.assertIn("User", {r["entity"] for r in rows})


class TestMainAndEmpty(Base):
    def test_empty(self):
        self.assertEqual(extract_schema.extract(self.root), [])
        self.assertEqual(extract_schema.main(["--root", self.root]), 0)

    def test_json(self):
        write(self.root, "schema.prisma", "model A {\n id Int @id\n}\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = extract_schema.main(["--root", self.root, "--json"])
        self.assertEqual(rc, 0)
        self.assertIsInstance(json.loads(buf.getvalue()), list)

    def test_bad_root(self):
        self.assertEqual(extract_schema.main(["--root", os.path.join(self.root, "x")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
