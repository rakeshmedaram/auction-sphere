from flask import Flask, render_template, request, redirect, url_for, session
from models import db, User, Auction, Bid
from datetime import datetime
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///auction.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)

with app.app_context():
    db.create_all()


# HOME
@app.route("/")
def index():

    auctions = Auction.query.all()

    return render_template("index.html", auctions=auctions)


# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            return "Username already exists"

        user = User(username=username,password=password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:

            session["user_id"] = user.id

            return redirect(url_for("dashboard"))

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    auctions = Auction.query.all()

    return render_template("dashboard.html", auctions=auctions)


# CREATE AUCTION
@app.route("/create-auction", methods=["GET","POST"])
def create_auction():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        price = request.form["price"]

        image_file = request.files["image"]

        filename = ""

        if image_file:

            filename = image_file.filename

            image_file.save(
                os.path.join(app.config["UPLOAD_FOLDER"], filename)
            )

        auction = Auction(
            title=title,
            description=description,
            starting_price=price,
            image=filename,
            user_id=session["user_id"]
        )

        db.session.add(auction)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("create_auction.html")


# AUCTION DETAIL
@app.route("/auction/<int:id>", methods=["GET","POST"])
def auction_detail(id):

    auction = Auction.query.get_or_404(id)

    bids = Bid.query.filter_by(auction_id=id).all()

    if bids:
        highest_bid = max([bid.amount for bid in bids])
        winner = max(bids, key=lambda x: x.amount).user
    else:
        highest_bid = auction.starting_price
        winner = None

    message = ""

    if request.method == "POST":

        amount = float(request.form["bid_amount"])

        if amount <= highest_bid:
            message = "Bid must be higher than current highest bid"

        else:

            bid = Bid(
                amount=amount,
                auction_id=id,
                user_id=session["user_id"]
            )

            db.session.add(bid)
            db.session.commit()

            return redirect(url_for("auction_detail", id=id))

    auction_ended = datetime.utcnow() > auction.end_time

    return render_template(
        "auction_detail.html",
        auction=auction,
        bids=bids,
        highest_bid=highest_bid,
        message=message,
        auction_ended=auction_ended,
        winner=winner
    )


# ADMIN PANEL
@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        return "Access denied"

    users = User.query.all()
    auctions = Auction.query.all()

    return render_template(
        "admin.html",
        users=users,
        auctions=auctions
    )


if __name__ == "__main__":
    app.run(debug=True)