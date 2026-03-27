from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 🔐 SECRET
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret123')

# 🗄 DATABASE
database_url = os.environ.get('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ---------------- MODELS ----------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    category = db.Column(db.String(100))

    starting_price = db.Column(db.Float)
    current_price = db.Column(db.Float)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    end_time = db.Column(db.DateTime)

    image = db.Column(db.String(200))

    bids = db.relationship('Bid', backref='auction', lazy=True)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

# ✅ CREATE TABLES
with app.app_context():
    db.create_all()

# ---------------- LOGIN ----------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- HOME ----------------

@app.route('/')
def home():
    auctions = Auction.query.order_by(Auction.id.desc()).all()
    return render_template('dashboard.html', auctions=auctions)

# ---------------- AUCTION DETAILS ----------------

@app.route('/auction/<int:auction_id>')
def auction_details(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    now = datetime.utcnow()

    last_bid = None
    if auction.bids:
        last_bid = sorted(auction.bids, key=lambda x: x.created_at)[-1]

    winner = None
    if last_bid and auction.end_time and now > auction.end_time:
        winner = last_bid.user.username if last_bid.user else "Unknown"

    return render_template(
        'auction_details.html',
        auction=auction,
        now=now,
        last_bid=last_bid,
        winner=winner
    )

# ---------------- PLACE BID ----------------

@app.route('/place_bid/<int:auction_id>', methods=['POST'])
@login_required
def place_bid(auction_id):
    auction = Auction.query.get_or_404(auction_id)

    if auction.end_time and datetime.utcnow() > auction.end_time:
        flash("Auction ended")
        return redirect(url_for('auction_details', auction_id=auction_id))

    bid_amount = request.form.get('bid_amount')

    if not bid_amount:
        flash("Enter bid")
        return redirect(url_for('auction_details', auction_id=auction_id))

    bid_amount = float(bid_amount)

    current_price = auction.current_price or auction.starting_price

    if bid_amount <= current_price:
        flash("Bid must be higher")
        return redirect(url_for('auction_details', auction_id=auction_id))

    bid = Bid(
        amount=bid_amount,
        user_id=current_user.id,
        auction_id=auction.id
    )

    auction.current_price = bid_amount

    db.session.add(bid)
    db.session.commit()

    return redirect(url_for('auction_details', auction_id=auction_id))

# ---------------- AUTH ----------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=request.form['password']
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()

        if user and user.password == request.form['password']:
            login_user(user)
            return redirect(url_for('home'))

        flash("Invalid credentials")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------------- CREATE AUCTION ----------------

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':

        title = request.form['title']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        end_time = datetime.strptime(request.form['end_time'], "%Y-%m-%dT%H:%M")

        if price <= 0:
            flash("Price must be greater than 0")
            return redirect(url_for('create'))

        if end_time <= datetime.utcnow():
            flash("End time must be in future")
            return redirect(url_for('create'))

        image_file = request.files['image']
        filename = None

        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        auction = Auction(
            title=title,
            description=description,
            category=category,
            starting_price=price,
            current_price=price,
            owner_id=current_user.id,
            end_time=end_time,
            image=filename
        )

        db.session.add(auction)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template('create_auction.html')

# ---------------- DELETE ----------------

@app.route('/delete/<int:auction_id>', methods=['POST'])
@login_required
def delete_auction(auction_id):
    auction = Auction.query.get_or_404(auction_id)

    if auction.owner_id != current_user.id:
        flash("Unauthorized")
        return redirect(url_for('home'))

    if auction.bids and auction.end_time > datetime.utcnow():
        flash("Cannot delete active auction with bids")
        return redirect(url_for('auction_details', auction_id=auction_id))

    for bid in auction.bids:
        db.session.delete(bid)

    db.session.delete(auction)
    db.session.commit()

    flash("Auction deleted")
    return redirect(url_for('home'))

# ---------------- SOCKET ----------------

@socketio.on('place_bid')
def handle_bid(data):
    if not current_user.is_authenticated:
        return

    auction = Auction.query.get(data['auction_id'])
    bid_amount = float(data['amount'])

    if datetime.utcnow() > auction.end_time:
        return

    if bid_amount <= auction.current_price:
        return

    bid = Bid(
        amount=bid_amount,
        user_id=current_user.id,
        auction_id=auction.id
    )

    auction.current_price = bid_amount
    db.session.add(bid)
    db.session.commit()

    emit('new_bid', {
        'auction_id': auction.id,
        'price': auction.current_price,
        'bidder': current_user.username
    }, broadcast=True)

# ---------------- RUN ----------------

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=10000)