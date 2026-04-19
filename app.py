from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- HOME ----------------
@app.route('/')
def home():
    db = get_db()
    auctions = db.execute("SELECT * FROM auctions").fetchall()

    return render_template(
        "index.html",
        auctions=auctions,
        now=datetime.now(),
        user=session.get('username')
    )

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()

        # check if user exists
        existing = db.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if existing:
            error = "Username already exists ❌"
        else:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            db.commit()
            return redirect('/login')

    return render_template("register.html", error=error)

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            error = "Invalid username or password ❌"

    return render_template("login.html", error=error)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- CREATE AUCTION ----------------
@app.route('/create_auction', methods=['GET','POST'])
def create_auction():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        price = int(request.form['price'])
        description = request.form['description']
        end_time = request.form['end_time']

        image = request.files.get('image')

        filename = None
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db = get_db()
        db.execute(
            "INSERT INTO auctions (name, price, description, end_time, created_by, image) VALUES (?, ?, ?, ?, ?, ?)",
            (name, price, description, end_time, session['user_id'], filename)
        )
        db.commit()

        return redirect('/')

    return render_template("create_auction.html")
# ---------------- VIEW AUCTION ----------------
@app.route('/auction/<int:id>')
def view_auction(id):
    db = get_db()

    auction = db.execute(
        "SELECT * FROM auctions WHERE id=?",
        (id,)
    ).fetchone()

    bids = db.execute(
        """SELECT users.username, bids.amount, bids.time
           FROM bids
           JOIN users ON bids.user_id = users.id
           WHERE auction_id=?
           ORDER BY amount DESC""",
        (id,)
    ).fetchall()

    winner = None
    end_time = datetime.fromisoformat(auction['end_time'])

    if datetime.now() > end_time and bids:
        winner = bids[0]

    return render_template(
        "view_auction.html",
        auction=auction,
        bids=bids,
        winner=winner,
        now=datetime.now()
    )

# ---------------- BID ----------------
@app.route('/bid/<int:id>', methods=['POST'])
def bid(id):
    if 'user_id' not in session:
        return redirect('/login')

    amount = int(request.form['amount'])
    db = get_db()

    auction = db.execute(
        "SELECT * FROM auctions WHERE id=?",
        (id,)
    ).fetchone()

    end_time = datetime.fromisoformat(auction['end_time'])

    if datetime.now() > end_time:
        return "Auction ended ❌"

    base_price = auction['price']

    highest = db.execute(
        "SELECT MAX(amount) as max_bid FROM bids WHERE auction_id=?",
        (id,)
    ).fetchone()['max_bid']

    if highest:
        if amount <= highest:
            return "Bid must be higher than current bid ❌"
    else:
        if amount < base_price:
            return "Bid must be >= base price ❌"

    db.execute(
        "INSERT INTO bids (auction_id, user_id, amount, time) VALUES (?, ?, ?, ?)",
        (id, session['user_id'], amount, datetime.now())
    )
    db.commit()

    return redirect(f'/auction/{id}')

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>')
def delete(id):
    db = get_db()
    db.execute("DELETE FROM auctions WHERE id=?", (id,))
    db.execute("DELETE FROM bids WHERE auction_id=?", (id,))
    db.commit()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)