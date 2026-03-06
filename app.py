from flask import Flask, render_template, redirect, url_for, request, flash
from models import db, User, Auction, Bid
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'auctionsecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    auctions = Auction.query.all()
    return render_template('index.html', auctions=auctions)


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully")
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid login")
    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    auctions = Auction.query.filter_by(owner_id=current_user.id).all()
    return render_template('dashboard.html', auctions=auctions)


@app.route('/create', methods=['GET','POST'])
@login_required
def create_auction():
    if request.method == 'POST':
        file = request.files['image']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        auction = Auction(
            title=request.form['title'],
            description=request.form['description'],
            base_price=float(request.form['base_price']),
            end_time=datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M'),
            owner_id=current_user.id,
            image=filename
        )
        db.session.add(auction)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('create_auction.html')


@app.route('/auction/<int:auction_id>', methods=['GET','POST'])
@login_required
def auction_detail(auction_id):
    auction = Auction.query.get_or_404(auction_id)
    bids = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.amount.desc()).all()
    highest_bid = bids[0].amount if bids else auction.base_price
    now = datetime.now()

    if auction.end_time < now and auction.winner_id is None and bids:
        auction.winner_id = bids[0].user_id
        db.session.commit()

    if request.method == 'POST':
        if auction.owner_id == current_user.id:
            flash("You cannot bid on your own auction")
        elif auction.end_time < now:
            flash("Auction ended")
        else:
            amount = float(request.form['bid_amount'])
            if amount > highest_bid:
                bid = Bid(amount=amount, user_id=current_user.id, auction_id=auction.id)
                db.session.add(bid)
                db.session.commit()
                return redirect(url_for('auction_detail', auction_id=auction.id))
            else:
                flash("Bid must be higher than current bid")

    return render_template('auction_detail.html',
                           auction=auction,
                           bids=bids,
                           highest_bid=highest_bid,
                           now=now)


@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return "Access Denied"
    users = User.query.all()
    auctions = Auction.query.all()
    return render_template('admin.html', users=users, auctions=auctions)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
