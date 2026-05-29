import yfinance as yf
import pandas as pd

def get_technical_indicators(ticker: str):
    """
    Download historical daily price data and calculate SMA_9, SMA_21, and RSI_14 indicators.
    Returns today's and yesterday's metrics for crossover strategy evaluation.
    """
    # 1. Download daily historical using yfinance. 
    # multi_level_index=False is required for latest yfinance to work with pandas-ta
    df = yf.download(ticker, period="1y", interval="1d", multi_level_index=False, threads=False)
    
    if df.empty:
        raise Exception(f"No data found from yfinance for ticker {ticker}")
        
    # 2. Technical Calculations (Indicators)
    # SMA (Simple Moving Average): Average price of the last X days.
    df['SMA_9'] = df['Close'].rolling(window=9).mean()
    df['SMA_21'] = df['Close'].rolling(window=21).mean()
    
    # RSI (Relative Strength Index) manual calculation
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    if len(df) < 22:
        raise Exception(f"Not enough data to calculate SMA/RSI for ticker {ticker}")
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    return {
        "current_price": float(last_row['Close']),
        "sma9_last": float(last_row['SMA_9']),
        "sma21_last": float(last_row['SMA_21']),
        "sma9_prev": float(prev_row['SMA_9']),
        "sma21_prev": float(prev_row['SMA_21']),
        "rsi_last": float(last_row['RSI_14'])
    }
