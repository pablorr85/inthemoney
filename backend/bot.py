from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from alpaca.trading.enums import OrderSide

import database
from services import broker, market_data
from config import MARKETS, MAX_BUDGET_PER_TRADE

def is_market_open(market_config: dict) -> bool:
    tz_name = market_config.get("timezone", "UTC")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    # Do not operate on weekends (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        return False
        
    current_time = now.hour * 60 + now.minute
    open_time = market_config["open_hour"] * 60 + market_config["open_minute"]
    close_time = market_config["close_hour"] * 60 + market_config["close_minute"]
    return open_time <= current_time <= close_time

def execute_daily_trading_strategy(ticker: str, available_cash: float = None) -> float:
    """
    Evaluate technical indicators (SMA, RSI) for a specific ticker
    and place trades dynamically on Alpaca.
    Returns the cash used (positive for buys, negative for sells, 0 for no trade).
    """
    # 1. Download and calculate indicators via clean market data service
    try:
        indicators = market_data.get_technical_indicators(ticker)
    except Exception as e:
        print(f"[{ticker}] Error loading data / indicators: {e}")
        return 0.0
        
    current_price = indicators["current_price"]
    sma9_last = indicators["sma9_last"]
    sma21_last = indicators["sma21_last"]
    sma9_prev = indicators["sma9_prev"]
    sma21_prev = indicators["sma21_prev"]
    rsi_last = indicators["rsi_last"]
    
    # 2. Moving Average Crossover Logic (Golden Cross / Death Cross)
    cruce_alcista = (sma9_prev <= sma21_prev) and (sma9_last > sma21_last)
    cruce_bajista = (sma9_prev >= sma21_prev) and (sma9_last < sma21_last)
    
    if not (cruce_alcista and rsi_last < 75) and not cruce_bajista:
        print(f"[{ticker}] HOLD / NO RELEVANT SIGNALS.")
        return 0.0

    # Anti-Spam: Check if there is already an active order to avoid duplication
    try:
        open_orders = broker.get_active_orders_for_ticker(ticker)
        if open_orders:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Active order already exists. Waiting for execution.")
            return 0.0
    except Exception:
        pass

    # BUY SIGNAL (Crossover & RSI filter)
    if cruce_alcista and rsi_last < 75:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] BUY SIGNAL. RSI is {rsi_last:.2f}")
        try:
            # Check open position first to avoid double purchasing
            try:
                pos = broker.get_open_position(ticker)
                if float(pos.qty) > 0:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / ALREADY BOUGHT (Avoiding duplicate).")
                    return 0.0
                elif float(pos.qty) < 0:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] WARNING / Short position detected. The bot will not operate on it.")
                    return 0.0
            except Exception:
                # Alpaca raises an exception if position does not exist. Expected.
                pass
                
            # Spanish Tax Cooldown Control (2-Month wash sale rule)
            try:
                last_sell = broker.get_last_closed_order(ticker, OrderSide.SELL)
                if last_sell:
                    days_since_sell = (datetime.now(timezone.utc) - last_sell.created_at).days
                    if days_since_sell <= 60:
                        # Check if last buy was a loss
                        last_buy = broker.get_last_closed_order(ticker, OrderSide.BUY)
                        
                        if last_buy and last_sell.filled_avg_price and last_buy.filled_avg_price:
                            sell_price = float(last_sell.filled_avg_price)
                            buy_price = float(last_buy.filled_avg_price)
                            
                            if sell_price < buy_price:
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / TAX COOLDOWN (Sold with loss {days_since_sell} days ago).")
                                return 0.0
                            else:
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] INFO / Rebuy allowed (Previous sale was profitable).")
                        else:
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / TAX COOLDOWN (Sold {days_since_sell} days ago).")
                            return 0.0
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Error checking cooldown: {e}")

            # Get actual cash if not provided
            if available_cash is None:
                try:
                    account = broker.get_account()
                    available_cash = float(account.cash)
                except Exception as e:
                    print(f"[{ticker}] Error retrieving account cash: {e}")
                    return 0.0

            if available_cash <= 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Insufficient cash to buy (${available_cash:.2f} available).")
                return 0.0

            if current_price > MAX_BUDGET_PER_TRADE:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Price ({current_price:.2f}) exceeds the maximum budget ({MAX_BUDGET_PER_TRADE:.2f}).")
                return 0.0
                
            # Limit our budget to available cash
            allowed_budget = min(MAX_BUDGET_PER_TRADE, available_cash)
            qty_to_buy = int(allowed_budget // current_price)
            if qty_to_buy <= 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Insufficient cash/budget (${available_cash:.2f} available) to buy 1 share at price ${current_price:.2f}.")
                return 0.0

            broker.submit_market_order(ticker, qty_to_buy, OrderSide.BUY)
            actual_cost = qty_to_buy * current_price
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] BUY order submitted ({qty_to_buy} shares, estimated cost: ${actual_cost:.2f}).")
            return actual_cost
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Error submitting order: {e}")
            return 0.0
            
    # SELL SIGNAL (Bearish Crossover)
    elif cruce_bajista:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] SELL SIGNAL.")
        try:
            # We only sell to close a position we already hold
            pos = broker.get_open_position(ticker)
            qty_sold = float(pos.qty)
            if qty_sold > 0:
                broker.close_position(ticker)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] SELL order submitted (Position closed).")
                return - (qty_sold * current_price)
            else:
                print(f"[{ticker}] HOLD / Short position detected. Ignoring sell signal.")
        except Exception:
            print(f"[{ticker}] HOLD / No open position to sell.")
            
    return 0.0

def run_bot_all_tickers():
    """Iterate over all markets and assets, executing strategy on open markets."""
    total_tickers = sum(len(config["tickers"]) for config in MARKETS.values())
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === STARTING BOT EXECUTION FOR {total_tickers} ASSETS ===")
    
    # Retrieve initial available cash from Alpaca
    try:
        account = broker.get_account()
        available_cash = float(account.cash)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Initial cash available: ${available_cash:.2f}")
    except Exception as e:
        print(f"Error getting account info: {e}")
        available_cash = 0.0
        
    results = []
    for market_key, config in MARKETS.items():
        print(f"--- Processing market: {config['name']} ---")
        
        # Validate market hours at the market level
        if not is_market_open(config):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Market closed. Skipping its {len(config['tickers'])} tickers.")
            continue
            
        for t in config["tickers"]:
            try:
                cash_used = execute_daily_trading_strategy(t, available_cash)
                available_cash -= cash_used
                results.append({"ticker": t, "status": "processed", "market": config['name']})
            except Exception as e:
                results.append({"ticker": t, "status": "error", "details": str(e), "market": config['name']})
    
    # Record today's equity snapshot in the database after the run
    try:
        account = broker.get_account()
        database.record_daily_equity(float(account.equity))
    except Exception as e:
        print(f"[DB] Error saving equity: {e}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === EXECUTION FINISHED ===")
    return results
