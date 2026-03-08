from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from models import db, User, Auction, Bid

app = Flask(__name__)

app.config['SECRET_KEY'] = 'auctionsecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create database tables
with app.app_context():
    db.create_all()


# Home page
@app.route("/")
def index():
    auctions = Auction.query.all()
    return render_template("index.html", auctions=auctions)


# Register
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        existing = User.query.filter_by(username=username).first()

        if existing:
            flash("Username already exists")
            return redirect(url_for("register"))

        user = User(username=username, password=password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful!")
        return redirect(url_for("login"))

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password")

    return render_template("login.html")


# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    auctions = Auction.query.all()
    return render_template("dashboard.html", auctions=auctions)

# Create Auction
@app.route("/create_auction", methods=["GET", "POST"])
@login_required
def create_auction():

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        price = request.form["starting_price"]

        image_file = request.files["image"]

        filename = None

        if image_file:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        auction = Auction(
            title=title,
            description=description,
            starting_price=price,
            image=filename,
            user_id=current_user.id
        )

        db.session.add(auction)
        db.session.commit()

        flash("Auction created successfully")

        return redirect(url_for("dashboard"))

    return render_template("create_auction.html")


# Auction details
@app.route("/auction/<int:auction_id>", methods=["GET", "POST"])
def auction_detail(auction_id):

    auction = Auction.query.get_or_404(auction_id)

    if request.method == "POST":

        amount = request.form["bid_amount"]

        bid = Bid(
            amount=amount,
            user_id=current_user.id,
            auction_id=auction.id
        )

        db.session.add(bid)
        db.session.commit()

        flash("Bid placed successfully!")

    bids = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.amount.desc()).all()

    return render_template("auction_detail.html", auction=auction, bids=bids)


if __name__ == "__main__":
    app.run(debug=True)