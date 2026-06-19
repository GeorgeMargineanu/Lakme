from __future__ import annotations

import secrets
import sqlite3
import hmac
import os
from urllib.parse import urlsplit
from contextlib import contextmanager
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, send_file, session, url_for
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("LAKME_SECRET_KEY", "dev-only-change-me-before-deploying")
app.config["DATABASE"] = Path(__file__).with_name("reviews.db")
app.config["ACCESS_USERNAME"] = os.getenv("LAKME_ACCESS_USER", "admin")
app.config["ACCESS_PASSWORD"] = os.getenv("LAKME_ACCESS_PASSWORD", "Venus")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("LAKME_HTTPS_ONLY", "0") == "1",
)


PDF_PATH = Path(__file__).with_name("Retetele lui Lakme - Vegetarian.pdf")

# Nume, bucătărie, zonă, pagini în PDF, proteine/calorii, simbol și slug.
RECIPE_DATA = [
    ("Tocană orientală Tajine cu halloumi & năut", "Marocan", "Orient & Africa", 3, 4, "31,5 g · 660 kcal", "🥘", "tajine-halloumi-naut"),
    ("Shakshouka grecească cu măsline & oregano", "Mediteranean", "Mediteranean", 5, 5, "31 g · 585 kcal", "🍳", "shakshouka-greceasca"),
    ("Veggie dil · cheese kebab cu legume", "Turcesc", "Orient & Africa", 6, 7, "33 g · 650 kcal", "🌯", "veggie-dil"),
    ("Gyros cu halloumi", "Grecesc", "Mediteranean", 8, 8, "32 g · 575 kcal", "🥙", "gyros-halloumi"),
    ("Frigărui halloumi Ras-el-hanout & sos tahini", "Marocan", "Orient & Africa", 9, 9, "31 g · 575 kcal", "🍢", "frigarui-halloumi"),
    ("Melanzane alla parmigiana & piadine proteice", "Italian", "Mediteranean", 10, 10, "37,5 g · 630 kcal", "🍆", "melanzane-parmigiana"),
    ("Manakish cu legume coapte, feta & hummus", "Libanez", "Orient & Africa", 11, 12, "31,5 g · 620 kcal", "🫓", "manakish-legume"),
    ("Lipie libaneză cu halloumi, hummus & rodie", "Libanez", "Orient & Africa", 13, 13, "30 g · 515 kcal", "🥙", "lipie-halloumi-rodie"),
    ("Cheese-egg-burger cu «carne» din linte", "American", "America de Nord", 14, 15, "37 g · 630 kcal", "🍔", "cheese-egg-burger"),
    ("Burrito cu soia, fasole & porumb în sos Mole", "Mexican", "America Latină", 16, 17, "31 g · 640 kcal", "🌯", "burrito-sos-mole"),
    ("Indian butter halloumi cu năut", "Indian", "India", 18, 19, "34 g · 575 kcal", "🍛", "indian-butter-halloumi"),
    ("Pappardelle cu ragu din linte & ciuperci", "Italian", "Mediteranean", 20, 21, "37,5 g · 620 kcal", "🍝", "pappardelle-ragu-linte"),
    ("Imam bayildi · vinete umplute veggie", "Turcesc", "Orient & Africa", 22, 23, "36,5 g · 575 kcal", "🍆", "imam-bayildi"),
    ("Papricaș de ciuperci cu halloumi & găluște", "Unguresc", "Europa de Est", 24, 25, "33,5 g · 605 kcal", "🍲", "papricas-ciuperci"),
    ("Lipie libaneză cu falafel de casă & rodie", "Libanez", "Orient & Africa", 26, 27, "30 g · 620 kcal", "🧆", "lipie-falafel"),
    ("Burger smoky cu halloumi & chips din dovleac", "American", "America de Nord", 28, 29, "30 g · 630 kcal", "🍔", "burger-smoky-halloumi"),
    ("Indian palak «paneer» cu tofu", "Indian", "India", 30, 31, "30,5 g · 575 kcal", "🍛", "palak-paneer-tofu"),
    ("Rulouri de dovlecei cu brânză & pomodori", "Italian", "Mediteranean", 32, 32, "34 g · 545 kcal", "🥒", "rulouri-dovlecei"),
    ("Mac & cheese cu dovleac și brie", "American", "America de Nord", 33, 33, "34,5 g · 640 kcal", "🧀", "mac-cheese-dovleac"),
    ("Tacos cu fasole neagră, halloumi & mango", "Mexican", "America Latină", 34, 35, "31 g · 630 kcal", "🌮", "tacos-halloumi-mango"),
    ("Flatbread pizza cu halloumi & piersici", "Grecesc", "Mediteranean", 36, 37, "31,5 g · 620 kcal", "🍕", "flatbread-halloumi-piersici"),
    ("Rigatoni cu pesto proteic de mazăre & rucola", "Italian", "Mediteranean", 38, 38, "31 g · 620 kcal", "🍝", "rigatoni-pesto-proteic"),
]

ACCENTS = ("coral", "sun", "lime", "berry", "violet", "aqua")
RECIPES = [
    {
        "name": name,
        "cuisine": cuisine,
        "region": region,
        "page_start": page_start,
        "page_end": page_end,
        "nutrition": nutrition,
        "emoji": emoji,
        "slug": slug,
        "diet": "Vegetariană",
        "portions": 8,
        "accent": ACCENTS[index % len(ACCENTS)],
        "description": f"O rețetă cu specific {cuisine.lower()}, bogată în proteine, cu gramaje clare și indicații pas cu pas.",
    }
    for index, (name, cuisine, region, page_start, page_end, nutrition, emoji, slug) in enumerate(RECIPE_DATA)
]

SAMPLE_REVIEWS = [
    ("tajine-halloumi-naut", "Andreea", 5, "Combinația de caise, migdale și halloumi este genială. A intrat direct în rotația noastră de meal prep.", "2026-06-18 19:42:00"),
    ("tajine-halloumi-naut", "Mihai", 5, "Foarte aromată și sățioasă. Gramajele per porție mi-au făcut viața mult mai simplă.", "2026-06-17 12:15:00"),
    ("tajine-halloumi-naut", "Ioana", 4, "Excelentă, mai ales a doua zi. Data viitoare pun puțin mai multă harissa.", "2026-06-15 20:08:00"),
    ("tajine-halloumi-naut", "Radu", 5, "Prima mea încercare de tajine și a ieșit impecabil. Instrucțiunile sunt foarte clare.", "2026-06-13 18:31:00"),
    ("tajine-halloumi-naut", "Cristina", 5, "Gust complex fără să fie complicat de făcut. Cous cous-ul cu mentă e detaliul perfect.", "2026-06-10 09:20:00"),
    ("tajine-halloumi-naut", "Sorin", 4, "Porții generoase și echilibrate. Am redus puțin mierea și a fost exact pe gustul meu.", "2026-06-08 14:05:00"),
    ("gyros-halloumi", "Elena", 5, "Tzatziki-ul proaspăt și halloumi rumenit sunt o combinație pe care o voi repeta des.", "2026-06-16 21:10:00"),
    ("burrito-sos-mole", "Vlad", 4, "Sosul Mole face toată diferența. Un prânz foarte bun și după două zile la frigider.", "2026-06-14 13:25:00"),
    ("palak-paneer-tofu", "Diana", 5, "În sfârșit o rețetă cu tofu care are mult gust și chiar ține de foame.", "2026-06-12 17:50:00"),
    ("tacos-halloumi-mango", "Alex", 5, "Mango, fasole neagră și halloumi: neașteptat de bun și foarte fresh.", "2026-06-09 20:44:00"),
]


@contextmanager
def get_db():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_reviews_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_slug TEXT NOT NULL,
                name TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        count = connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        if count == 0:
            connection.executemany(
                "INSERT INTO reviews (recipe_slug, name, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                SAMPLE_REVIEWS,
            )


def reviews_for(slug: str):
    init_reviews_db()
    with get_db() as connection:
        return connection.execute(
            "SELECT * FROM reviews WHERE recipe_slug = ? ORDER BY created_at DESC, id DESC",
            (slug,),
        ).fetchall()


def find_recipe(slug: str) -> dict:
    recipe = next((item for item in RECIPES if item["slug"] == slug), None)
    if not recipe:
        abort(404)
    return recipe


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now(timezone.utc).year}


@app.before_request
def require_private_access():
    if request.endpoint in {"login", "static"} or session.get("authenticated"):
        return None
    destination = request.full_path.rstrip("?")
    return redirect(url_for("login", next=destination))


@app.get("/")
def index():
    return render_template("index.html", recipes=RECIPES)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username_ok = hmac.compare_digest(
            request.form.get("username", ""), app.config["ACCESS_USERNAME"]
        )
        password_ok = hmac.compare_digest(
            request.form.get("password", ""), app.config["ACCESS_PASSWORD"]
        )
        if username_ok and password_ok:
            destination = request.form.get("next", "")
            parsed_destination = urlsplit(destination)
            if not destination.startswith("/") or destination.startswith("//") or parsed_destination.netloc:
                destination = url_for("index")
            session.clear()
            session["authenticated"] = True
            return redirect(destination)
        error = "Utilizator sau parolă incorectă."

    destination = request.form.get("next", request.args.get("next", ""))
    return render_template(
        "login.html", error=error, destination=destination
    ), (401 if error else 200)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/recipe/<slug>", methods=["GET", "POST"])
def recipe_detail(slug: str):
    recipe = find_recipe(slug)
    review_error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        comment = request.form.get("comment", "").strip()
        try:
            rating = int(request.form.get("rating", ""))
        except ValueError:
            rating = 0

        if not 2 <= len(name) <= 40:
            review_error = "Numele trebuie să aibă între 2 și 40 de caractere."
        elif rating not in range(1, 6):
            review_error = "Alege un rating de la 1 la 5 stele."
        elif not 5 <= len(comment) <= 800:
            review_error = "Comentariul trebuie să aibă între 5 și 800 de caractere."
        else:
            init_reviews_db()
            with get_db() as connection:
                connection.execute(
                    "INSERT INTO reviews (recipe_slug, name, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                    (slug, name, rating, comment, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
                )
            return redirect(url_for("recipe_detail", slug=slug, review_added=1) + "#recenzii")

    reviews = reviews_for(slug)
    average = round(sum(review["rating"] for review in reviews) / len(reviews), 1) if reviews else 0
    return render_template(
        "recipe.html",
        recipe=recipe,
        reviews=reviews,
        review_average=average,
        review_error=review_error,
        review_added=request.args.get("review_added") == "1",
    ), (400 if review_error else 200)


@app.route("/checkout/<slug>", methods=["GET", "POST"])
def checkout(slug: str):
    recipe = find_recipe(slug)
    if request.method == "POST":
        buyer_name = request.form.get("name", "").strip()
        buyer_email = request.form.get("email", "").strip()
        if not buyer_name or "@" not in buyer_email:
            return render_template("checkout.html", recipe=recipe, error="Adaugă numele și o adresă de email validă."), 400

        token = secrets.token_urlsafe(12)
        purchases = session.setdefault("purchases", {})
        purchases[token] = {"slug": slug, "name": buyer_name, "email": buyer_email}
        session.modified = True
        return redirect(url_for("purchase", token=token))
    return render_template("checkout.html", recipe=recipe)


@app.get("/purchase/<token>")
def purchase(token: str):
    order = session.get("purchases", {}).get(token)
    if not order:
        abort(404)
    return render_template("purchase.html", recipe=find_recipe(order["slug"]), order=order, token=token)


@app.get("/descarca/<token>")
def download_recipe(token: str):
    order = session.get("purchases", {}).get(token)
    if not order:
        abort(404)
    recipe = find_recipe(order["slug"])
    if not PDF_PATH.exists():
        abort(404)

    source = PdfReader(PDF_PATH)
    writer = PdfWriter()
    for page_number in range(recipe["page_start"], recipe["page_end"] + 1):
        writer.add_page(source.pages[page_number - 1])
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Lakme - {recipe['slug']}.pdf",
    )


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
