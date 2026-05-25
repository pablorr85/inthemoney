import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

import database
from client import trading_client
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

def execute_daily_trading_strategy(ticker: str):
    """
    Designed to be run hourly (Mon-Fri, hour 9-22 at minute 15) via APScheduler in main.py.
    """

    # 1. Download daily historical using yfinance. 
    # multi_level_index=False is required for latest yfinance to work with pandas-ta
    df = yf.download(ticker, period="1y", interval="1d", multi_level_index=False, threads=False)
    
    # Check if empty
    if df.empty:
        raise Exception("No data found from yfinance")
        
    # 2. Technical Calculations (Indicators)
    # SMA (Simple Moving Average): Average price of the last X days.
    # We use the 9-day (fast) and 21-day (slow) SMAs.
    df['SMA_9'] = df['Close'].rolling(window=9).mean()
    df['SMA_21'] = df['Close'].rolling(window=21).mean()
    
    # RSI (Relative Strength Index) calculation manually
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    if len(df) < 22:
        raise Exception("Not enough data to calculate SMA/RSI")
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 3. Extract key values from today and yesterday
    sma9_last, sma21_last = last_row['SMA_9'], last_row['SMA_21']
    sma9_prev, sma21_prev = prev_row['SMA_9'], prev_row['SMA_21']
    rsi_last = last_row['RSI_14']
    current_price = last_row['Close']
    
    # 4. Moving Average Crossover Logic (Main Strategy)
    # BULLISH CROSSOVER (Golden Cross): The fast SMA (9) crosses above the slow SMA (21).
    # It indicates that the short-term trend is strong and rising.
    cruce_alcista = (sma9_prev <= sma21_prev) and (sma9_last > sma21_last)
    
    # BEARISH CROSSOVER (Death Cross): The fast SMA (9) crosses below the slow SMA (21).
    # It indicates that the short-term trend is weakening and starting to fall.
    cruce_bajista = (sma9_prev >= sma21_prev) and (sma9_last < sma21_last)
    
    # 5. Execution
    if not (cruce_alcista and rsi_last < 75) and not cruce_bajista:
        print(f"[{ticker}] HOLD / NO RELEVANT SIGNALS.")
        return

    # Anti-Spam: Check if there is already an active order to avoid duplication
    try:
        open_orders = trading_client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[ticker]))
        if open_orders:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Active order already exists. Waiting for execution.")
            return
    except Exception:
        pass

    # To BUY, we require a bullish crossover AND the RSI to be below 75 (not overbought/inflated).
    if cruce_alcista and rsi_last < 75:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] BUY SIGNAL. RSI is {rsi_last:.2f}")
        try:
            # Open position control to avoid duplicate purchases
            try:
                pos = trading_client.get_open_position(ticker)
                if float(pos.qty) > 0:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / ALREADY BOUGHT (Avoiding duplicate).")
                    return
                elif float(pos.qty) < 0:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] WARNING / Short position detected. The bot will not operate on it.")
                    return
            except Exception:
                # Alpaca raises an exception if the position does not exist. This is the expected behavior.
                pass
                
            # Tax Cooldown Control (Spanish 2-Month Rule)
            try:
                req_sell = GetOrdersRequest(
                    status=QueryOrderStatus.CLOSED,
                    symbols=[ticker],
                    side=OrderSide.SELL,
                    limit=1
                )
                last_sell = trading_client.get_orders(req_sell)
                if last_sell:
                    days_since_sell = (datetime.now(timezone.utc) - last_sell[0].created_at).days
                    if days_since_sell <= 60:
                        # Fetch the last buy to check if it was a loss
                        req_buy = GetOrdersRequest(
                            status=QueryOrderStatus.CLOSED,
                            symbols=[ticker],
                            side=OrderSide.BUY,
                            limit=1
                        )
                        last_buy = trading_client.get_orders(req_buy)
                        
                        if last_buy and last_sell[0].filled_avg_price and last_buy[0].filled_avg_price:
                            sell_price = float(last_sell[0].filled_avg_price)
                            buy_price = float(last_buy[0].filled_avg_price)
                            
                            if sell_price < buy_price:
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / TAX COOLDOWN (Sold with loss {days_since_sell} days ago).")
                                return
                            else:
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] INFO / Rebuy allowed (Previous sale was profitable).")
                        else:
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / TAX COOLDOWN (Sold {days_since_sell} days ago).")
                            return
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Error checking cooldown: {e}")

            if current_price > MAX_BUDGET_PER_TRADE:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Price ({current_price:.2f}) exceeds the maximum budget ({MAX_BUDGET_PER_TRADE:.2f}).")
                return
                
            qty_to_buy = int(MAX_BUDGET_PER_TRADE // current_price)
            if qty_to_buy <= 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Insufficient budget to buy 1 share.")
                return

            req = MarketOrderRequest(
                symbol=ticker,
                qty=qty_to_buy,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(req)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] BUY order submitted ({qty_to_buy} shares).")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Error submitting order: {e}")
            
    elif cruce_bajista:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] SELL SIGNAL.")
        try:
            # We only operate in Long positions. We never short.
            # We only sell to close a position we already hold (long).
            pos = trading_client.get_open_position(ticker) # Throws exception if we don't have it
            if float(pos.qty) > 0:
                trading_client.close_position(ticker)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] SELL order submitted (Position closed).")
            else:
                print(f"[{ticker}] HOLD / Short position detected. Ignoring sell signal.")
        except Exception:
            print(f"[{ticker}] HOLD / No open position to sell.")

def run_bot_all_tickers():
    total_tickers = sum(len(config["tickers"]) for config in MARKETS.values())
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === STARTING BOT EXECUTION FOR {total_tickers} ASSETS ===")
    
    results = []
    for market_key, config in MARKETS.items():
        print(f"--- Processing market: {config['name']} ---")
        
        # Validate market hours at the market level instead of per ticker
        if not is_market_open(config):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Market closed. Skipping its {len(config['tickers'])} tickers.")
            continue
            
        for t in config["tickers"]:
            try:
                execute_daily_trading_strategy(t)
                results.append({"ticker": t, "status": "processed", "market": config['name']})
            except Exception as e:
                results.append({"ticker": t, "status": "error", "details": str(e), "market": config['name']})
    
    # Record today's equity snapshot in the database after the run
    try:
        account = trading_client.get_account()
        database.record_daily_equity(float(account.equity))
    except Exception as e:
        print(f"[DB] Error saving equity: {e}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === EXECUTION FINISHED ===")
    return results
