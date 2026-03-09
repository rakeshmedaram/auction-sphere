from flask import Flask, render_template, request, redirect, url_for, session
from models import db, User, Auction, Bid
from mail_config import mail
from flask_mail import Message
from datetime import datetime
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///auction.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email configuration (example Gmail)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "youremail@gmail.com"
app.config["MAIL_PASSWORD"] = "your_app_password"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)
mail.init_app(app)

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
        email = request.form["email"]
        password = request.form["password"]

        user = User(
            username=username,
            email=email,
            password=password
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:

            session["user_id"] = user.id

            return redirect(url_for("dashboard"))

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard")
def dashboard():

    auctions = Auction.query.all()

    return render_template("dashboard.html", auctions=auctions)


# CREATE AUCTION
@app.route("/create-auction", methods=["GET","POST"])
def create_auction():

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        price = request.form["price"]

        end_time = datetime.strptime(
            request.form["end_time"],
            "%Y-%m-%dT%H:%M"
        )

        auction = Auction(
            title=title,
            description=description,
            starting_price=price,
            end_time=end_time,
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

    auction_ended = datetime.utcnow() > auction.end_time

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

            # send email notification
            send_bid_email(auction.title, amount)

            return redirect(url_for("auction_detail", id=id))

    return render_template(
        "auction_detail.html",
        auction=auction,
        bids=bids,
        highest_bid=highest_bid,
        message=message,
        auction_ended=auction_ended,
        winner=winner
    )


# EMAIL FUNCTION
def send_bid_email(auction_title, amount):

    msg = Message(
        "New Bid Placed",
        sender="youremail@gmail.com",
        recipients=["youremail@gmail.com"]
    )

    msg.body = f"A new bid of ₹{amount} was placed on {auction_title}"

    mail.send(msg)


# ANALYTICS DASHBOARD
@app.route("/analytics")
def analytics():

    total_users = User.query.count()

    total_auctions = Auction.query.count()

    total_bids = Bid.query.count()

    highest_bid = db.session.query(db.func.max(Bid.amount)).scalar()

    return render_template(
        "analytics.html",
        total_users=total_users,
        total_auctions=total_auctions,
        total_bids=total_bids,
        highest_bid=highest_bid
    )


if __name__ == "__main__":
    app.run(debug=True)