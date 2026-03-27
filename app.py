from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ✅ SECRET
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret123')

# ✅ DATABASE (Render PostgreSQL or local fallback)
database_url = os.environ.get('DATABASE_URL')

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()
# ✅ SOCKET (Render compatible)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

login_manager = LoginManager()
login_manager.init_app(app)

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

# ---------------- LOGIN ----------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------

@app.route('/')
def home():

    search = request.args.get('search', '')
    category = request.args.get('category', '')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    sort = request.args.get('sort', 'latest')

    query = Auction.query

    if search:
        query = query.filter(
            Auction.title.ilike(f"%{search}%") |
            Auction.description.ilike(f"%{search}%")
        )

    if category:
        query = query.filter_by(category=category)

    if min_price:
        query = query.filter(Auction.current_price >= float(min_price))

    if max_price:
        query = query.filter(Auction.current_price <= float(max_price))

    if sort == "low":
        query = query.order_by(Auction.current_price.asc())
    elif sort == "high":
        query = query.order_by(Auction.current_price.desc())
    else:
        query = query.order_by(Auction.id.desc())

    auctions = query.all()

    return render_template('dashboard.html',
                           auctions=auctions,
                           search=search,
                           category=category,
                           min_price=min_price,
                           max_price=max_price,
                           sort=sort)

@app.route('/auction/<int:auction_id>')
def auction_details(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    return render_template('auction_details.html', auction=auction)

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

@app.route('/profile')
@login_required
def profile():

    my_auctions = Auction.query.filter_by(owner_id=current_user.id).all()
    my_bids = Bid.query.filter_by(user_id=current_user.id).all()

    winning = []
    for auction in Auction.query.all():
        if auction.bids:
            last_bid = auction.bids[-1]
            if last_bid.user_id == current_user.id and auction.end_time < datetime.utcnow():
                winning.append(auction)

    return render_template('profile.html',
                           my_auctions=my_auctions,
                           my_bids=my_bids,
                           winning=winning)

# ---------------- SOCKET ----------------

@socketio.on('place_bid')
def handle_bid(data):

    if not current_user.is_authenticated:
        emit('bid_error', {'message': 'Login required'})
        return

    auction = Auction.query.get(data['auction_id'])
    bid_amount = float(data['amount'])

    if datetime.utcnow() > auction.end_time:
        emit('bid_error', {'message': 'Auction ended'})
        return

    if bid_amount <= auction.current_price:
        emit('bid_error', {'message': 'Bid must be higher'})
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
        'bidder': current_user.username,
        'amount': bid.amount,
        'time': bid.created_at.strftime('%H:%M:%S'),
        'user_id': current_user.id
    }, broadcast=True)

# ---------------- RUN ----------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    socketio.run(app, host="0.0.0.0", port=10000)