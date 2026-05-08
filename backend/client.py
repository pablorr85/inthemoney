from alpaca.trading.client import TradingClient
from config import API_KEY, SECRET_KEY

# Client in paper mode = True
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
