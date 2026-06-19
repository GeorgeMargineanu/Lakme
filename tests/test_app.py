import unittest
from pathlib import Path

from app import app, get_db


class SavrAppTests(unittest.TestCase):
    def setUp(self):
        self.test_database = Path(__file__).with_name("reviews-test.db")
        self.test_database.unlink(missing_ok=True)
        app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            DATABASE=self.test_database,
        )
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["authenticated"] = True

    def tearDown(self):
        self.test_database.unlink(missing_ok=True)

    def test_home_and_recipe_render(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("Tocană orientală".encode(), home.data)
        self.assertIn(b"LA<span>K</span>ME", home.data)
        self.assertIn("Hrănește-ți corpul".encode(), home.data)
        self.assertIn("🫠".encode(), home.data)
        self.assertIn("🔪".encode(), home.data)

        recipe = self.client.get("/recipe/tajine-halloumi-naut")
        self.assertEqual(recipe.status_code, 200)
        self.assertIn("Ia rețeta".encode(), recipe.data)

    def test_checkout_validates_and_unlocks(self):
        invalid = self.client.post("/checkout/tajine-halloumi-naut", data={"name": "A", "email": "bad"})
        self.assertEqual(invalid.status_code, 400)

        valid = self.client.post(
            "/checkout/tajine-halloumi-naut",
            data={"name": "Ada Lovelace", "email": "ada@example.com"},
            follow_redirects=True,
        )
        self.assertEqual(valid.status_code, 200)
        self.assertIn("REȚETĂ DEBLOCATĂ".encode(), valid.data)
        self.assertIn("Descarcă PDF-ul".encode(), valid.data)

        with self.client.session_transaction() as session:
            token = next(iter(session["purchases"]))
        pdf = self.client.get(f"/descarca/{token}")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.mimetype, "application/pdf")
        self.assertTrue(pdf.data.startswith(b"%PDF"))

    def test_unknown_recipe_returns_custom_404(self):
        response = self.client.get("/recipe/not-real")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Drum greșit".encode(), response.data)

    def test_reviews_show_five_and_accept_a_new_review(self):
        page = self.client.get("/recipe/tajine-halloumi-naut")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Vezi toate recenziile (+1)", page.data)
        self.assertEqual(page.data.count(b'class="review-card"'), 5)
        self.assertEqual(page.data.count(b"review-extra"), 1)

        invalid = self.client.post(
            "/recipe/tajine-halloumi-naut",
            data={"name": "A", "rating": "7", "comment": "Nu"},
        )
        self.assertEqual(invalid.status_code, 400)

        valid = self.client.post(
            "/recipe/tajine-halloumi-naut",
            data={"name": "Laura", "rating": "5", "comment": "A ieșit excelent, o voi repeta!"},
            follow_redirects=True,
        )
        self.assertEqual(valid.status_code, 200)
        self.assertIn("Recenzia ta a fost publicată".encode(), valid.data)
        self.assertIn(b"Laura", valid.data)

        with get_db() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM reviews WHERE recipe_slug = ?", ("tajine-halloumi-naut",)
            ).fetchone()[0]
        self.assertEqual(count, 7)

    def test_private_site_login_and_logout(self):
        with self.client.session_transaction() as session:
            session.clear()

        protected = self.client.get("/recipe/tajine-halloumi-naut")
        self.assertEqual(protected.status_code, 302)
        self.assertIn("/login?next=", protected.headers["Location"])

        login_page = self.client.get(protected.headers["Location"])
        self.assertEqual(login_page.status_code, 200)
        self.assertIn(b"noindex, nofollow, noarchive", login_page.data)
        self.assertNotIn(b"Venus", login_page.data)

        invalid = self.client.post(
            "/login",
            data={
                "username": "admin",
                "password": "gresit",
                "next": "/recipe/tajine-halloumi-naut",
            },
        )
        self.assertEqual(invalid.status_code, 401)

        valid = self.client.post(
            "/login",
            data={
                "username": "admin",
                "password": "Venus",
                "next": "/recipe/tajine-halloumi-naut",
            },
            follow_redirects=True,
        )
        self.assertEqual(valid.status_code, 200)
        self.assertIn("Ia rețeta".encode(), valid.data)

        logout = self.client.get("/logout")
        self.assertEqual(logout.status_code, 302)
        self.assertIn("/login", logout.headers["Location"])

        locked_home = self.client.get("/")
        self.assertEqual(locked_home.status_code, 302)
        self.assertNotIn("Hrănește-ți corpul".encode(), locked_home.data)


if __name__ == "__main__":
    unittest.main()
