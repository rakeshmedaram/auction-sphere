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
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

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

    # 🔴 HARD BLOCK bidding after end
    if request.method == "POST":
        if closed:
            return "⛔ Auction already ended!"

        try:
            amount = int(request.form['amount'])
        except:
            return "Invalid bid!"

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
            return "Bid must be higher than current highest!"

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