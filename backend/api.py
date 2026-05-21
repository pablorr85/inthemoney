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
        
        # Añadir la industria para dar más contexto
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
        
        # Approximate realized P/L assuming 100k starting balance (Alpaca Paper Default)
        realized_pl = equity - 100000 - unrealized_pl
        
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
        
        # Ordenar de mayor ganancia a mayor pérdida
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
    """Generates a CSV file of all executed trades for tax purposes."""
    try:
        current_year = datetime.now().year
        after_date = datetime(current_year, 1, 1)
        current_until = datetime.now()
        
        all_orders = []
        
        # Bucle para obtener todas las órdenes del año (paginación de 500 en 500)
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
                
            # Alpaca devuelve en orden descendente, cogemos la fecha de la más antigua para la siguiente página
            current_until = batch[-1].created_at
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabecera para Excel/Sheets
        writer.writerow(["ID Orden", "Ticker", "Operación", "Cantidad", "Precio Medio Fill", "Estado", "Fecha (UTC)"])
        
        for o in all_orders:
            writer.writerow([
                str(o.id),
                o.symbol,
                o.side.value if o.side else "N/A",
                float(o.qty) if o.qty else 0,
                float(o.filled_avg_price) if o.filled_avg_price else 0,
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
    """Endpoint para ejecutar el bot manualmente y probarlo sin esperar al Cron Job"""
    results = run_bot_all_tickers()
    
    return {
        "message": f"Ejecución manual del bot finalizada",
        "results": results
    }
