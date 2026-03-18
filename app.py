from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secret'

# ================= DATABASE =================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ================= EMAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'medaramrakesh286@gmail.com'
app.config['MAIL_PASSWORD'] = 'jesk esfn kflr dbhn'  # 🔥 use Gmail App Password

mail = Mail(app)

# ================= EMAIL FUNCTION =================
def send_email(to, subject, body):
    try:
        msg = Message(subject,
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[to])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print("Email Error:", e)

# ================= MODELS =================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    price = db.Column(db.Float)
    image = db.Column(db.String(200))
    end_time = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'))

    user = db.relationship('User')


# ================= LOGIN =================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================= ROUTES =================

@app.route('/')
def index():
    auctions = Auction.query.all()
    return render_template('index.html', auctions=auctions)


# ---------- REGISTER ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return redirect('/register')

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()

        # 📧 EMAIL
        send_email(
            email,
            "Welcome to Auction Sphere 🎉",
            f"Hello {username},\n\nYour account has been created successfully!"
        )

        return redirect('/login')

    return render_template('register.html')


# ---------- LOGIN ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            login_user(user)

            # 📧 EMAIL
            send_email(
                user.email,
                "Login Alert 🔐",
                f"Hello {user.username},\n\nYou just logged into Auction Sphere."
            )

            return redirect('/dashboard')

        else:
            flash("Invalid login")

    return render_template('login.html')


# ---------- LOGOUT ----------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


# ---------- DASHBOARD ----------
@app.route('/dashboard')
@login_required
def dashboard():
    auctions = Auction.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', auctions=auctions)


# ---------- CREATE AUCTION ----------
@app.route('/create-auction', methods=['GET','POST'])
@login_required
def create_auction():

    if request.method == 'POST':

        title = request.form.get('title')
        price = request.form.get('price')
        end_time = request.form.get('end_time')

        image = request.files.get('image')
        filename = None

        if image and image.filename != "":
            filename = image.filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        auction = Auction(
            title=title,
            price=float(price),
            image=filename,
            end_time=datetime.strptime(end_time, '%Y-%m-%dT%H:%M'),
            user_id=current_user.id
        )

        db.session.add(auction)
        db.session.commit()

        # 📧 EMAIL
        send_email(
            current_user.email,
            "Auction Created 🏆",
            f"Hello {current_user.username},\n\nYour auction '{title}' has been created successfully!"
        )

        return redirect('/dashboard')

    return render_template('create_auction.html')


# ---------- AUCTION DETAIL + BIDDING ----------
@app.route('/auction/<int:id>', methods=['GET','POST'])
@login_required
def auction_detail(id):

    auction = Auction.query.get_or_404(id)

    highest_bid = db.session.query(db.func.max(Bid.amount))\
        .filter_by(auction_id=id).scalar()

    if highest_bid is None:
        highest_bid = auction.price

    # PLACE BID
    if request.method == 'POST':

        amount = request.form.get('amount')

        if amount:
            amount = float(amount)

            if amount > highest_bid:

                bid = Bid(
                    amount=amount,
                    user_id=current_user.id,
                    auction_id=id
                )

                db.session.add(bid)
                db.session.commit()

                return redirect(url_for('auction_detail', id=id))

            else:
                flash("Bid must be higher!")

    bids = Bid.query.filter_by(auction_id=id).order_by(Bid.amount.desc()).all()

    highest_bid = db.session.query(db.func.max(Bid.amount))\
        .filter_by(auction_id=id).scalar() or auction.price

    highest_bid_obj = Bid.query.filter_by(
        auction_id=id,
        amount=highest_bid
    ).first()

    highest_user = highest_bid_obj.user if highest_bid_obj else None

    # WINNER LOGIC
    auction_ended = datetime.now() > auction.end_time
    winner = highest_user if auction_ended else None

    # 📧 WINNER EMAIL
    if auction_ended and winner:
        send_email(
            winner.email,
            "You Won the Auction 🎉",
            f"Congratulations {winner.username}!\n\nYou won '{auction.title}' with ₹{highest_bid}"
        )

    return render_template(
        'auction_detail.html',
        auction=auction,
        bids=bids,
        highest_bid=highest_bid,
        highest_user=highest_user,
        winner=winner,
        auction_ended=auction_ended
    )


# ---------- PROFILE ----------
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


# ---------- ANALYTICS ----------
@app.route('/analytics')
@login_required
def analytics():

    total_auctions = Auction.query.count()
    total_bids = Bid.query.count()
    total_users = User.query.count()
    highest_bid = db.session.query(db.func.max(Bid.amount)).scalar() or 0
    my_auctions = Auction.query.filter_by(user_id=current_user.id).count()

    return render_template(
        'analytics.html',
        total_auctions=total_auctions,
        total_bids=total_bids,
        total_users=total_users,
        highest_bid=highest_bid,
        my_auctions=my_auctions
    )


# ================= RUN =================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)