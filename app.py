import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename

# =========================
# APP CONFIG
# =========================
app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DB = "database.db"


# =========================
# DATABASE CONNECTION
# =========================
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# HOME
# =========================
@app.route("/")
def index():
    db = get_db()
    auctions = db.execute("SELECT * FROM auctions ORDER BY id DESC").fetchall()
    return render_template("index.html", auctions=auctions)


# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password),
        )
        db.commit()
        return redirect("/login")

    return render_template("register.html")


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password),
        ).fetchone()

        if user:
            session["user"] = username
            return redirect("/")
        else:
            return "Invalid credentials"

    return render_template("login.html")


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# CREATE AUCTION
# =========================
@app.route("/create_auction", methods=["GET", "POST"])
def create_auction():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        base_price = int(request.form["base_price"])
        description = request.form["description"]
        end_time = request.form["end_time"]

        # image upload
        image = request.files["image"]
        filename = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        db = get_db()
        db.execute(
            """
            INSERT INTO auctions (title, base_price, description, image, end_time, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, base_price, description, filename, end_time, session["user"]),
        )
        db.commit()

        return redirect("/")

    return render_template("create_auction.html")


# =========================
# VIEW AUCTION
# =========================
@app.route("/auction/<int:auction_id>", methods=["GET", "POST"])
def view_auction(auction_id):
    db = get_db()

    auction = db.execute(
        "SELECT * FROM auctions WHERE id=?", (auction_id,)
    ).fetchone()

    bids = db.execute(
        "SELECT * FROM bids WHERE auction_id=? ORDER BY amount DESC",
        (auction_id,),
    ).fetchall()

    if not auction:
        return "Auction not found"

    now = datetime.now()
    end_time = datetime.strptime(auction["end_time"], "%Y-%m-%dT%H:%M")
    ended = now > end_time

    # =========================
    # PLACE BID
    # =========================
    if request.method == "POST":
        if "user" not in session:
            return redirect("/login")

        if ended:
            return "❌ Auction ended. No more bids allowed."

        bid_amount = int(request.form["bid"])

        current_price = (
            bids[0]["amount"] if bids else auction["base_price"]
        )

        if bid_amount <= current_price:
            return "❌ Bid must be higher than current price"

        db.execute(
            """
            INSERT INTO bids (auction_id, username, amount, time)
            VALUES (?, ?, ?, ?)
            """,
            (auction_id, session["user"], bid_amount, datetime.now()),
        )
        db.commit()

        return redirect(f"/auction/{auction_id}")

    # =========================
    # WINNER LOGIC
    # =========================
    winner = None
    if ended and bids:
        winner = bids[0]

    return render_template(
        "view_auction.html",
        auction=auction,
        bids=bids,
        ended=ended,
        winner=winner,
        now=datetime.now(),
    )


# =========================
# DELETE AUCTION
# =========================
@app.route("/delete/<int:auction_id>")
def delete_auction(auction_id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    db.execute("DELETE FROM auctions WHERE id=?", (auction_id,))
    db.execute("DELETE FROM bids WHERE auction_id=?", (auction_id,))
    db.commit()

    return redirect("/")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)