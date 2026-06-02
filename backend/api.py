from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime
import yfinance as yf

import database
from services import broker, tax_service
from bot import run_bot_all_tickers

router = APIRouter()

# Simple in-memory cache for ticker information
ticker_info_cache = {}

@router.get("/ticker/{ticker}/info")
def get_ticker_info(ticker: str):
    """Retrieve basic profile info (name, exchange, sector) for a given ticker."""
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
    except Exception:
        return {"name": ticker, "exchange": "N/A", "summary": "Info no disponible"}

@router.get("/portfolio/summary")
def get_portfolio_summary():
    """Retrieve calculated summary of open balances, equity, and unrealized profit."""
    try:
        return broker.get_portfolio_summary()
    except Exception as e:
        return {"error": str(e)}

@router.get("/positions")
def get_positions():
    """Retrieve open active positions, sorted by highest unrealized profit."""
    try:
        return broker.get_active_positions()
    except Exception as e:
        return {"error": str(e)}

@router.get("/trades")
def get_trades():
    """Retrieve recent closed orders history."""
    try:
        orders = broker.get_closed_orders(limit=100)
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
def export_trades(year: int = None):
    """Generates a CSV file of executed trades for a specific year (defaults to current year), converted to EUR."""
    try:
        from datetime import timezone
        
        if not year:
            year = datetime.now().year
            
        after_date = datetime(year, 1, 1, tzinfo=timezone.utc)
        
        if year == datetime.now().year:
            current_until = datetime.now(timezone.utc)
        else:
            current_until = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        all_orders = []
        
        # Paginate to fetch all closed orders for the requested year
        while True:
            batch = broker.get_closed_orders(
                limit=500,
                after=after_date,
                until=current_until
            )
            if not batch:
                break
                
            all_orders.extend(batch)
            
            if len(batch) < 500:
                break
                
            current_until = batch[-1].created_at
            
        # Delegate CSV formatting and ECB reference currency conversion to the tax service
        csv_data = tax_service.generate_tax_csv_content(all_orders, after_date)
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=inthemoney_operaciones_{year}.csv"}
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
        "message": "Ejecución manual del bot finalizada",
        "results": results
    }
