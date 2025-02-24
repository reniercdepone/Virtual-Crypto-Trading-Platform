from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from datetime import datetime
import requests
from functools import wraps
from cachetools import TTLCache
import logging
from requests.exceptions import RequestException, HTTPError, Timeout

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'test_secret_key'  # Change this for security
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=10000.0)  # Starting balance $10,000

# Portfolio model
class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coin = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    average_buy_price = db.Column(db.Float, nullable=False)

# Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coin = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(4), nullable=False)  # "buy" or "sell"
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create a cache with 5-minute TTL (300 seconds)
price_cache = TTLCache(maxsize=1, ttl=1500)

# Default fallback prices
FALLBACK_PRICES = {
    'BTC': 50000.00,
    'ETH': 3000.00,
    'LTC': 150.00
}

class CoinGeckoAPI:
    BASE_URL = 'https://api.coingecko.com/api/v3'
    COIN_MAPPING = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'LTC': 'litecoin'
    }

    @staticmethod
    def fetch_prices():
        """Fetch prices from CoinGecko API with caching."""
        cache_key = 'crypto_prices'
        
        # Check cache first
        if cache_key in price_cache:
            logger.info("Returning cached prices")
            return price_cache[cache_key]

        try:
            # Prepare API request
            coins = list(CoinGeckoAPI.COIN_MAPPING.values())
            url = f"{CoinGeckoAPI.BASE_URL}/simple/price"
            params = {
                'ids': ','.join(coins),
                'vs_currencies': 'usd'
            }

            # Make API request with timeout
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            # Parse response
            prices = response.json()
            
            # Map CoinGecko IDs back to our symbols
            price_map = {}
            for symbol, coingecko_id in CoinGeckoAPI.COIN_MAPPING.items():
                if coingecko_id in prices and 'usd' in prices[coingecko_id]:
                    price_map[symbol] = prices[coingecko_id]['usd']
                else:
                    logger.warning(f"Price not found for {symbol}, using fallback")
                    price_map[symbol] = FALLBACK_PRICES.get(symbol, 0)

            # Store in cache
            price_cache[cache_key] = price_map
            logger.info("Successfully fetched and cached new prices")
            return price_map

        except Timeout:
            logger.error("CoinGecko API request timed out")
        except HTTPError as e:
            logger.error(f"CoinGecko API HTTP error: {e}")
        except RequestException as e:
            logger.error(f"CoinGecko API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching prices: {e}")

        # Return cached prices if available, otherwise fallback prices
        if cache_key in price_cache:
            logger.warning("API failed, returning cached prices")
            return price_cache[cache_key]
        
        logger.warning("API failed and no cache available, returning fallback prices")
        return FALLBACK_PRICES

    @staticmethod
    def get_price(symbol):
        """Get price for a specific symbol."""
        prices = CoinGeckoAPI.fetch_prices()
        return prices.get(symbol, FALLBACK_PRICES.get(symbol, 0))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    user = User.query.get(session['user_id'])
    portfolio = Portfolio.query.filter_by(user_id=user.id).all()
    
    # Fetch current prices
    crypto_prices = CoinGeckoAPI.fetch_prices()

    # Calculate portfolio value and profit/loss
    portfolio_data = []
    total_value = user.balance
    for item in portfolio:
        current_price = crypto_prices.get(item.coin, 0)
        value = item.quantity * current_price
        cost = item.quantity * item.average_buy_price
        profit_loss = value - cost
        total_value += value
        portfolio_data.append({
            'coin': item.coin,
            'quantity': item.quantity,
            'average_buy_price': item.average_buy_price,
            'current_price': current_price,
            'value': value,
            'profit_loss': profit_loss
        })

    return render_template('index.html', user=user, portfolio=portfolio_data, 
                         prices=crypto_prices, total_value=total_value)

@app.route('/trade', methods=['GET', 'POST'])
@login_required
def trade():
    user = User.query.get(session['user_id'])
    crypto_prices = CoinGeckoAPI.fetch_prices()

    if request.method == 'POST':
        coin = request.form['coin']
        action = request.form['action']
        try:
            quantity = float(request.form['quantity'])
        except ValueError:
            flash('Invalid quantity.', 'error')
            return redirect(url_for('trade'))

        if quantity <= 0:
            flash('Quantity must be greater than 0.', 'error')
            return redirect(url_for('trade'))

        current_price = CoinGeckoAPI.get_price(coin)
        if current_price == 0:
            flash('Invalid cryptocurrency or price unavailable.', 'error')
            return redirect(url_for('trade'))

        total_cost = quantity * current_price

        if action == 'buy':
            if user.balance < total_cost:
                flash('Insufficient balance.', 'error')
                return redirect(url_for('trade'))

            user.balance -= total_cost
            portfolio_item = Portfolio.query.filter_by(user_id=user.id, coin=coin).first()
            if portfolio_item:
                old_cost = portfolio_item.quantity * portfolio_item.average_buy_price
                new_cost = total_cost
                total_quantity = portfolio_item.quantity + quantity
                portfolio_item.average_buy_price = (old_cost + new_cost) / total_quantity
                portfolio_item.quantity = total_quantity
            else:
                new_portfolio = Portfolio(
                    user_id=user.id,
                    coin=coin,
                    quantity=quantity,
                    average_buy_price=current_price
                )
                db.session.add(new_portfolio)

        elif action == 'sell':
            portfolio_item = Portfolio.query.filter_by(user_id=user.id, coin=coin).first()
            if not portfolio_item or portfolio_item.quantity < quantity:
                flash('Insufficient coins to sell.', 'error')
                return redirect(url_for('trade'))

            user.balance += total_cost
            portfolio_item.quantity -= quantity
            if portfolio_item.quantity == 0:
                db.session.delete(portfolio_item)

        else:
            flash('Invalid action.', 'error')
            return redirect(url_for('trade'))

        new_transaction = Transaction(
            user_id=user.id,
            coin=coin,
            type=action,
            quantity=quantity,
            price=current_price,
            total=total_cost
        )
        db.session.add(new_transaction)
        db.session.commit()

        flash(f'{action.capitalize()} successful!', 'success')
        return redirect(url_for('index'))

    return render_template('trade.html', prices=crypto_prices)

@app.route('/history')
@login_required
def history():
    user = User.query.get(session['user_id'])
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('history.html', transactions=transactions)