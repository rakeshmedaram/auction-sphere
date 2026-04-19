from flask import Flask, render_template, request, redirect, session, send_from_directory
import sqlite3, os
from datetime import datetime
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "secret123"
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    return sqlite3.connect("database.db", check_same_thread=False)

# IMAGE ROUTE
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# HOME
@app.route('/')
def home():
    db = get_db()
    auctions = db.execute("SELECT * FROM auctions").fetchall()
    return render_template("index.html", auctions=auctions)

# REGISTER
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            "INSERT INTO users(username,password,role) VALUES (?,?,?)",
            (request.form['username'], request.form['password'], 'user')
        )
        db.commit()
        return redirect('/login')
    return render_template("register.html")

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form['username'], request.form['password'])
        ).fetchone()

        if user:
            session['user'] = user[1]
            return redirect('/')

    return render_template("login.html")

# CREATE AUCTION
@app.route('/create_auction', methods=['GET','POST'])
def create_auction():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['image']
        filename = file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        db = get_db()
        db.execute(
            "INSERT INTO auctions(title,price,image,end_time,owner,description) VALUES (?,?,?,?,?,?)",
            (
                request.form['title'],
                request.form['price'],
                filename,
                request.form['end_time'],
                session['user'],
                request.form['description']
            )
        )
        db.commit()
        return redirect('/')

    return render_template("create_auction.html")

# VIEW AUCTION
@app.route('/auction/<int:id>')
def view_auction(id):
    db = get_db()

    auction = db.execute(
        "SELECT * FROM auctions WHERE id=?",
        (id,)
    ).fetchone()

    bids = db.execute(
        "SELECT user, amount, time FROM bids WHERE auction_id=? ORDER BY id DESC",
        (id,)
    ).fetchall()

    winner = None
    if auction:
        if datetime.now() > datetime.fromisoformat(auction[4]):
            winner = db.execute(
                "SELECT user, MAX(amount) FROM bids WHERE auction_id=?",
                (id,)
            ).fetchone()

    return render_template(
    "view_auction.html",
    auction=auction,
    bids=bids,
    winner=winner,
    now=datetime.now().isoformat()
)

# DELETE
@app.route('/delete/<int:id>')
def delete(id):
    db = get_db()
    auction = db.execute("SELECT owner FROM auctions WHERE id=?", (id,)).fetchone()

    if auction and auction[0] == session.get("user"):
        db.execute("DELETE FROM auctions WHERE id=?", (id,))
        db.commit()

    return redirect('/')

# REAL-TIME BID
@socketio.on("place_bid")
def place_bid(data):
    db = get_db()

    auction = db.execute(
        "SELECT price, end_time FROM auctions WHERE id=?",
        (data['auction_id'],)
    ).fetchone()

    if not auction:
        emit("error", {"msg": "Auction not found"})
        return

    current_price = auction[0]
    end_time = datetime.fromisoformat(auction[1])

    # ❌ BLOCK AFTER END
    if datetime.now() > end_time:
        emit("error", {"msg": "Auction has ended"})
        return

    # ❌ BLOCK LOWER BID
    if int(data['amount']) <= current_price:
        emit("error", {"msg": "Bid must be higher than current price"})
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        "INSERT INTO bids(auction_id,user,amount,time) VALUES (?,?,?,?)",
        (data['auction_id'], data['user'], data['amount'], now)
    )

    db.execute(
        "UPDATE auctions SET price=? WHERE id=?",
        (data['amount'], data['auction_id'])
    )

    db.commit()

    emit("new_bid", {
        "user": data['user'],
        "amount": data['amount'],
        "time": now
    }, broadcast=True)
    # RUN
if __name__ == "__main__":
    socketio.run(app)