from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime
import csv
import io
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

import database
from client import trading_client
from bot import run_bot_all_tickers
import yfinance as yf
from config import STARTING_BALANCE

router = APIRouter()

# Simple in-memory cache for ticker information
ticker_info_cache = {}

@router.get("/ticker/{ticker}/info")
def get_ticker_info(ticker: str):
    if ticker in ticker_info_cache:
        return ticker_info_cache[ticker]
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        sector_map = {
            "Technology": "Tecnología",
            "Communication Services": "Telecomunicaciones",
            "Consumer Defensive": "Alimentación y Consumo Básico",
            "Consumer Cyclical": "Consumo Cíclico",
            "Financial Services": "Finanzas y Banca",
            "Healthcare": "Salud y Farmacia",
            "Industrials": "Industria y Construcción",
            "Energy": "Energía",
            "Utilities": "Servicios Públicos",
            "Real Estate": "Inmobiliario",
            "Basic Materials": "Materiales Básicos"
        }
        
        sector_en = info.get("sector", "Sector Desconocido")
        sector_es = sector_map.get(sector_en, sector_en)
        
        # Add the industry to provide more context
        industry = info.get("industry", "")
        summary = f"{sector_es}" + (f" ({industry})" if industry else "")
        
        data = {
            "name": info.get("shortName", info.get("longName", ticker)),
            "exchange": info.get("exchange", "Bolsa"),
            "summary": summary
        }
        ticker_info_cache[ticker] = data
        return data
    except Exception as e:
        return {"name": ticker, "exchange": "N/A", "summary": "Info no disponible"}

@router.get("/portfolio/summary")
def get_portfolio_summary():
    try:
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
        
        # Approximate realized P/L assuming configured starting balance
        realized_pl = equity - STARTING_BALANCE - unrealized_pl
        
        daily_pl = equity - last_equity
        daily_pl_pct = (daily_pl / last_equity) * 100 if last_equity > 0 else 0
        
        # Simulating Weekly/Monthly for the frontend
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
    except Exception as e:
        return {"error": str(e)}

@router.get("/positions")
def get_positions():
    try:
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
        
        # Sort from highest gain to highest loss
        pos_list.sort(key=lambda x: x["unrealized_pl"], reverse=True)
        return pos_list
    except Exception as e:
        return {"error": str(e)}

@router.get("/trades")
def get_trades():
    try:
        req = GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=100)
        orders = trading_client.get_orders(req)
        
        trades = [{
            "id": str(o.id),
            "ticker": o.symbol,
            "side": o.side.value if o.side else None,
            "qty": float(o.qty) if o.qty else 0,
            "filled_avg_price": float(o.filled_avg_price) if o.filled_avg_price else 0,
            "status": o.status.value,
            "created_at": o.created_at
        } for o in orders]
        
        return {
            "total_trades": len(trades),
            "history": trades
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/export/trades")
def export_trades():
    """Generates a CSV file of all executed trades for tax purposes, with automatic USD to EUR conversion."""
    try:
        current_year = datetime.now().year
        after_date = datetime(current_year, 1, 1)
        current_until = datetime.now()
        
        all_orders = []
        
        # Loop to fetch all orders of the year (paginating 500 at a time)
        while True:
            req = GetOrdersRequest(
                status=QueryOrderStatus.CLOSED, 
                limit=500,
                after=after_date,
                until=current_until
            )
            batch = trading_client.get_orders(req)
            if not batch:
                break
                
            all_orders.extend(batch)
            
            if len(batch) < 500:
                break
                
            # Alpaca returns in descending order, we take the date of the oldest for the next page
            current_until = batch[-1].created_at
        
        # Fetch historical EUR/USD rates (official ECB rates preferred)
        from datetime import timedelta
        import pandas as pd
        import urllib.request
        import json
        
        rates_map = {}
        ecb_success = False
        
        # Method 1: Try official ECB reference rates via Frankfurter API
        try:
            start_str = (after_date - timedelta(days=15)).strftime("%Y-%m-%d")
            end_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            url = f"https://api.frankfurter.dev/v1/{start_str}..{end_str}?from=USD&to=EUR"
            req = urllib.request.Request(url, headers={'User-Agent': 'InTheMoneyTaxBot/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if 'rates' in data:
                    for d_str, rates in data['rates'].items():
                        if 'EUR' in rates and float(rates['EUR']) > 0:
                            # Convert 1 USD = X EUR into 1 EUR = Y USD (ECB reference format)
                            rates_map[d_str] = 1.0 / float(rates['EUR'])
                    ecb_success = True
                    print(f"[Tax CSV] Successfully fetched exact ECB rates from Frankfurter API.")
        except Exception as e:
            print(f"[Tax CSV] Frankfurter ECB API failed, trying Yahoo Finance fallback: {e}")
            
        # Method 2: Fallback to yfinance EURUSD=X if ECB API failed
        if not ecb_success:
            try:
                rates_start = after_date - timedelta(days=15)
                rates_df = yf.download(
                    "EURUSD=X", 
                    start=rates_start.strftime("%Y-%m-%d"), 
                    end=(datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"), 
                    multi_level_index=False, 
                    threads=False
                )
                if not rates_df.empty and 'Close' in rates_df:
                    close_col = rates_df['Close']
                    for idx, val in close_col.items():
                        date_str = idx.strftime("%Y-%m-%d")
                        try:
                            if isinstance(val, pd.Series):
                                float_val = float(val.iloc[0])
                            else:
                                float_val = float(val)
                            if pd.notna(float_val) and float_val > 0:
                                rates_map[date_str] = float_val
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Tax CSV] Error downloading exchange rates from yfinance: {e}")

        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header for Spanish Tax purposes
        writer.writerow([
            "ID Orden", 
            "Ticker", 
            "Operación", 
            "Cantidad", 
            "Precio Fill (USD)", 
            "Total (USD)", 
            "Tipo Cambio (EUR/USD)", 
            "Fecha Tipo Cambio",
            "Precio Fill (EUR)", 
            "Total (EUR)", 
            "Estado", 
            "Fecha Orden (UTC)"
        ])
        
        for o in all_orders:
            # Resolve the closest available exchange rate for the order's date
            rate = 1.0
            rate_used_date = "N/A"
            if o.created_at:
                # Loop back up to 15 days to handle weekends and long market holidays
                for i in range(15):
                    check_date = (o.created_at - timedelta(days=i)).strftime("%Y-%m-%d")
                    if check_date in rates_map:
                        rate = rates_map[check_date]
                        rate_used_date = check_date
                        break
            
            qty = float(o.qty) if o.qty else 0.0
            price_usd = float(o.filled_avg_price) if o.filled_avg_price else 0.0
            total_usd = qty * price_usd
            
            # Convert to Euros: EUR = USD / (EUR/USD rate)
            # e.g., if 1 EUR = 1.08 USD, then $108 USD = 100 EUR
            price_eur = price_usd / rate if rate > 0 else price_usd
            total_eur = total_usd / rate if rate > 0 else total_usd
            
            writer.writerow([
                str(o.id),
                o.symbol,
                o.side.value if o.side else "N/A",
                qty,
                round(price_usd, 4),
                round(total_usd, 2),
                round(rate, 4) if rate_used_date != "N/A" else "N/A",
                rate_used_date,
                round(price_eur, 4),
                round(total_eur, 2),
                o.status.value,
                o.created_at.strftime("%Y-%m-%d %H:%M:%S") if o.created_at else "N/A"
            ])
            
        csv_data = output.getvalue()
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=inthemoney_operaciones_{current_year}.csv"}
        )
    except Exception as e:
        return {"error": str(e)}

@router.get("/portfolio/history")
def get_portfolio_history():
    """Returns the historical daily equity from the local SQLite database."""
    history = database.get_historical_equity(days=90)
    return {"history": history}

@router.post("/bot/run")
def run_bot_manually():
    """Endpoint to run the bot manually and test it without waiting for the scheduled job."""
    results = run_bot_all_tickers()
    
    return {
        "message": f"Ejecución manual del bot finalizada",
        "results": results
    }
