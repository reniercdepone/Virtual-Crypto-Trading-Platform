# Crypto Trading Platform 
#### Video Demo:  <URL HERE>

## Description
This is a paper trading platform for cryptocurrencies, allowing users to practice trading with fake currency. Users can register, log in, buy/sell cryptocurrencies, view their portfolio, and track transaction history.

## Features
- User registration and login with password hashing.
- Simulated cryptocurrency prices (BTC, ETH, LTC).
- Buy and sell cryptocurrencies using fake currency.
- Portfolio tracking with profit/loss calculations.
- Transaction history.

## Tech Stack
- Backend: Flask (Python), Flask-SQLAlchemy
- Database: SQLite
- Frontend: HTML, CSS (Bootstrap), JavaScript
- Dependencies: bcrypt, requests

## Setup Instructions
1. Clone the repository: `git clone <repository-url>`
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment: `source venv/bin/activate` (Windows: `venv\Scripts\activate`)
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python app.py`
6. Open `http://127.0.0.1:5000` in your browser.

## Usage
1. Register a new account or log in with existing credentials.
2. View your dashboard to see your balance, portfolio, and market prices.
3. Go to the "Trade" page to buy or sell cryptocurrencies.
4. Check your transaction history on the "History" page.

## Challenges
- Implementing portfolio calculations (e.g., average buy price, profit/loss).
- Debugging trade validation (e.g., insufficient balance/coins).

## Future Improvements
- Add real-time price updates using a free API (e.g., CoinGecko).
- Implement portfolio charts using Chart.js.
- Add a leaderboard to rank users by portfolio value.
- Make the platform mobile-friendly with responsive design.