import sys
import os
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

# Add parent directory to path so we can import from backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import trading_client
from config import STARTING_BALANCE

def get_account():
    """Retrieve raw Alpaca account information."""
    return trading_client.get_account()

def get_portfolio_summary():
    """
    Retrieve and calculate a high-level summary of the portfolio.
    Translates raw Alpaca values into clean metrics for the dashboard.
    """
    account = trading_client.get_account()
    balance = float(account.portfolio_value)
    equity = float(account.equity)
    last_equity = float(account.last_equity)
    cash = float(account.cash)
    market_value = float(account.long_market_value)
    
    # Fetch positions to calculate precise invested amount and unrealized P/L
    positions = trading_client.get_all_positions()
    unrealized_pl = sum(float(p.unrealized_pl) for p in positions)
    invested = sum(float(p.avg_entry_price) * float(p.qty) for p in positions)
    unrealized_pl_pct = (unrealized_pl / invested) * 100 if invested > 0 else 0
    
    # Calculate realized profit/loss relative to configured starting balance
    realized_pl = equity - STARTING_BALANCE - unrealized_pl
    
    daily_pl = equity - last_equity
    daily_pl_pct = (daily_pl / last_equity) * 100 if last_equity > 0 else 0
    
    return {
        "balance_total": balance,
        "equity": equity,
        "cash": cash,
        "market_value": market_value,
        "invested": invested,
        "unrealized_pl": unrealized_pl,
        "unrealized_pl_pct": unrealized_pl_pct,
        "realized_pl": realized_pl,
        "daily_pl": daily_pl,
        "daily_pl_pct": daily_pl_pct,
        "weekly_pl": daily_pl * 4,
        "monthly_pl": daily_pl * 20
    }

def get_active_positions():
    """Retrieve and format all active open positions, sorted by highest unrealized profit."""
    positions = trading_client.get_all_positions()
    pos_list = [{
        "ticker": p.symbol,
        "qty": float(p.qty),
        "market_value": float(p.market_value),
        "avg_entry_price": float(p.avg_entry_price),
        "current_price": float(p.current_price),
        "unrealized_pl": float(p.unrealized_pl),
        "unrealized_pl_pcnt": float(p.unrealized_plpc) * 100
    } for p in positions]
    
    pos_list.sort(key=lambda x: x["unrealized_pl"], reverse=True)
    return pos_list

def get_open_position(ticker: str):
    """Retrieve active open position details for a specific ticker."""
    return trading_client.get_open_position(ticker)

def get_closed_orders(limit: int = 100, after=None, until=None):
    """Retrieve historical orders with a CLOSED status."""
    req = GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        limit=limit,
        after=after,
        until=until
    )
    return trading_client.get_orders(req)

def get_active_orders_for_ticker(ticker: str):
    """Check if there are open active orders for a specific ticker to avoid spamming buys."""
    req = GetOrdersRequest(
        status=QueryOrderStatus.OPEN,
        symbols=[ticker]
    )
    return trading_client.get_orders(req)

def submit_market_order(ticker: str, qty: int, side: OrderSide, time_in_force: TimeInForce = TimeInForce.GTC):
    """Submit a market order to Alpaca."""
    req = MarketOrderRequest(
        symbol=ticker,
        qty=qty,
        side=side,
        time_in_force=time_in_force
    )
    return trading_client.submit_order(req)

def close_position(ticker: str):
    """Close an open position for a given ticker."""
    return trading_client.close_position(ticker)

def get_last_closed_order(ticker: str, side: OrderSide):
    """Retrieve the single last closed order (BUY or SELL) for a specific ticker."""
    req = GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        symbols=[ticker],
        side=side,
        limit=1
    )
    orders = trading_client.get_orders(req)
    return orders[0] if orders else None
