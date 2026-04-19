<<<<<<< HEAD
from flask import Flask, render_template, request, redirect, session
import sqlite3, os, datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secretkey"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db():
    return sqlite3.connect("database.db")

def init_db():
    db = get_db()

    db.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        email TEXT,
        username TEXT,
        password TEXT
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS auctions(
        id INTEGER PRIMARY KEY,
        title TEXT,
        description TEXT,
        image TEXT,
        end_time TEXT,
        base_price INTEGER,
        created_by TEXT
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS bids(
        id INTEGER PRIMARY KEY,
        auction_id INTEGER,
        bidder TEXT,
        amount INTEGER,
        time TEXT
    )
    """)

    db.commit()

init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form['username'], request.form['password'])
        ).fetchone()

        if user:
            session['user'] = request.form['username']
            return redirect("/dashboard")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        db = get_db()
        db.execute("INSERT INTO users(email,username,password) VALUES(?,?,?)",
                   (request.form['email'], request.form['username'], request.form['password']))
        db.commit()
        return redirect("/")
    return render_template("register.html")

# ---------------- LOGOUT ----------------
=======
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
>>>>>>> a4a507517e0c8bbb102fcc5be64a3bed3af99863
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

<<<<<<< HEAD
# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if 'user' not in session:
        return redirect("/")

    db = get_db()
    auctions_db = db.execute("SELECT * FROM auctions").fetchall()

    auctions = []
    now = datetime.datetime.now()

    for a in auctions_db:
        end_time = datetime.datetime.strptime(a[4], "%Y-%m-%dT%H:%M")
        status = "LIVE" if now < end_time else "CLOSED"
        auctions.append((a, status))

    return render_template("dashboard.html", auctions=auctions)

# ---------------- CREATE ----------------
@app.route("/create", methods=["GET","POST"])
def create():
    if 'user' not in session:
        return redirect("/")

    if request.method == "POST":
        file = request.files['image']
        if file.filename == "":
            return "No file selected"

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db = get_db()
        db.execute("""
        INSERT INTO auctions(title,description,image,end_time,base_price,created_by)
        VALUES(?,?,?,?,?,?)
        """, (
            request.form['title'],
            request.form['description'],
            filename,
            request.form['time'],
            request.form['base_price'],
            session['user']
        ))
        db.commit()

        return redirect("/dashboard")

    return render_template("create_auction.html")

# ---------------- AUCTION ----------------
@app.route("/auction/<int:id>", methods=["GET","POST"])
def auction(id):
    if 'user' not in session:
        return redirect("/")

    db = get_db()
    auction = db.execute("SELECT * FROM auctions WHERE id=?", (id,)).fetchone()

    end_time = datetime.datetime.strptime(auction[4], "%Y-%m-%dT%H:%M")
    closed = datetime.datetime.now() > end_time

    if request.method == "POST" and not closed:
        amount = int(request.form['amount'])

        highest = db.execute(
            "SELECT MAX(amount) FROM bids WHERE auction_id=?",
            (id,)
        ).fetchone()[0]

        base_price = auction[5]
        now_time = datetime.datetime.now().strftime("%H:%M:%S")

        if highest is None:
            if amount >= base_price:
                db.execute("INSERT INTO bids VALUES(NULL,?,?,?,?)",
                           (id, session['user'], amount, now_time))
                db.commit()
            else:
                return "Bid must be >= base price!"
        elif amount > highest:
            db.execute("INSERT INTO bids VALUES(NULL,?,?,?,?)",
                       (id, session['user'], amount, now_time))
            db.commit()
        else:
            return "Bid must be higher!"

    bids = db.execute(
        "SELECT * FROM bids WHERE auction_id=? ORDER BY amount DESC",
        (id,)
    ).fetchall()

    winner = bids[0][2] if closed and bids else None
    highest_bidder = bids[0][2] if bids else None
    highest_amount = bids[0][3] if bids else None

    return render_template("auction_detail.html",
                           auction=auction,
                           bids=bids,
                           winner=winner,
                           highest_bidder=highest_bidder,
                           highest_amount=highest_amount,
                           closed=closed)

# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    db = get_db()
    auction = db.execute("SELECT * FROM auctions WHERE id=?", (id,)).fetchone()

    if auction[6] != session.get('user'):
        return "Unauthorized!"

    db.execute("DELETE FROM auctions WHERE id=?", (id,))
    db.execute("DELETE FROM bids WHERE auction_id=?", (id,))
    db.commit()
    return redirect("/dashboard")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
=======

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
>>>>>>> a4a507517e0c8bbb102fcc5be64a3bed3af99863
