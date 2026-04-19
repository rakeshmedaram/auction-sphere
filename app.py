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

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    db = get_db()
    auctions = db.execute("SELECT * FROM auctions").fetchall()

    now = datetime.datetime.now()
    data = []

    for a in auctions:
        end = datetime.datetime.strptime(a[4], "%Y-%m-%dT%H:%M")
        status = "LIVE" if now < end else "CLOSED"
        data.append((a, status))

    return render_template("dashboard.html", auctions=data)

# ---------------- AUCTION ----------------
@app.route("/auction/<int:id>", methods=["GET","POST"])
def auction(id):
    db = get_db()
    auction = db.execute("SELECT * FROM auctions WHERE id=?", (id,)).fetchone()

    end_time = datetime.datetime.strptime(auction[4], "%Y-%m-%dT%H:%M")
    now = datetime.datetime.now()

    # 🔴 STRICT CHECK
    closed = now >= end_time

    if request.method == "POST":
        # 🔴 HARD BLOCK
        if datetime.datetime.now() >= end_time:
            return redirect(f"/auction/{id}")

        try:
            amount = int(request.form['amount'])
        except:
            return "Invalid bid"

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
        elif amount > highest:
            db.execute("INSERT INTO bids VALUES(NULL,?,?,?,?)",
                       (id, session['user'], amount, now_time))
            db.commit()

    bids = db.execute(
        "SELECT * FROM bids WHERE auction_id=? ORDER BY amount DESC",
        (id,)
    ).fetchall()

    winner = bids[0][2] if closed and bids else None
    highest_amount = bids[0][3] if bids else None

    return render_template("auction_detail.html",
                           auction=auction,
                           bids=bids,
                           closed=closed,
                           winner=winner,
                           highest_amount=highest_amount)
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