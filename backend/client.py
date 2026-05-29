from alpaca.trading.client import TradingClient
from config import API_KEY, SECRET_KEY, ALPACA_PAPER

# Client in paper mode or live mode depending on configuration
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=ALPACA_PAPER)
