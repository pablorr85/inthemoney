import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest
from alpaca.trading.enums import OrderStatus, OrderSide, TimeInForce, QueryOrderStatus
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import database
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Alpaca Configuration (Paper Trading)
API_KEY = os.getenv("ALPACA_API_KEY", "TU_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "TU_API_SECRET")

# Client in paper mode = True
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

app = FastAPI(title="InTheMoney Trading Bot API")

# Initialize the SQLite database on startup
database.initialize_db()

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(
        run_bot_all_tickers,
        trigger=CronTrigger(day_of_week="mon-fri", hour="9-22", minute=0),
        id="daily_trading_job",
        replace_existing=True
    )
    scheduler.start()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] APScheduler iniciado: Bot programado de 9:00 a 22:00 cada hora (L-V).")

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] APScheduler apagado.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REST ENDPOINTS ---

@app.get("/api/portfolio/summary")
def get_portfolio_summary():
    try:
        account = trading_client.get_account()
        balance = float(account.portfolio_value)
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        
        daily_pl = equity - last_equity
        daily_pl_pct = (daily_pl / last_equity) * 100 if last_equity > 0 else 0
        
        # Simulating Weekly/Monthly for the frontend
        return {
            "balance_total": balance,
            "equity": equity,
            "daily_pl": daily_pl,
            "daily_pl_pct": daily_pl_pct,
            "weekly_pl": daily_pl * 4,
            "monthly_pl": daily_pl * 20
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/positions")
def get_positions():
    try:
        positions = trading_client.get_all_positions()
        return [{
            "ticker": p.symbol,
            "qty": float(p.qty),
            "market_value": float(p.market_value),
            "avg_entry_price": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_pl_pcnt": float(p.unrealized_plpc) * 100
        } for p in positions]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/trades")
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

@app.get("/api/portfolio/history")
def get_portfolio_history():
    """Returns the historical daily equity from the local SQLite database."""
    history = database.get_historical_equity(days=90)
    return {"history": history}

# --- CONFIGURACIÓN DE MERCADOS ---

MARKETS = {
    "US": {
        "name": "Wall Street (NYSE/NASDAQ)",
        "open_hour": 15,
        "open_minute": 30,
        "close_hour": 22,
        "close_minute": 0,
        "tickers": [
            "MSFT", "AAPL", "NVDA", "ASML", "TSM", "AVGO", "AMD", 
            "META", "GOOGL", "AMZN", "NFLX", "CRM", "ADBE", "INTU",
            "CRWD", "PANW", "FTNT", "PLTR", "DDOG", "SNOW",
            "LMT", "RTX", "NOC", "GD", "CAT", "DE", "HON", "GE", "ETN",
            "LLY", "NVO", "UNH", "JNJ", "ABBV", "MRK", "TMO", "DHR",
            "COST", "WMT", "PG", "KO", "PEP", "MCD", "SBUX",
            "V", "MA", "AXP", "JPM", "BAC", "MS", "GS",
            "XOM", "CVX", "COP", "OXY", "NEE", "GEV", "ENPH", "FSLR",
            "CCJ", "CEG", "BWXT", "SMR", "NXE",
            "GLD", "NEM", "GOLD", "FCX"
        ]
    },
    "ES": {
        "name": "Bolsa Española (BME)",
        "open_hour": 9,
        "open_minute": 0,
        "close_hour": 17,
        "close_minute": 30,
        "tickers": [
            "AMS.MC", "IDR.MC", "TEF.MC", "CLNX.MC",
            "ACS.MC", "AENA.MC", "FER.MC", "IAG.MC", "ANA.MC", "SCYR.MC",
            "ROVI.MC", "PHM.MC", "GRF.MC",
            "ITX.MC", "VIS.MC", "PUIG.MC",
            "SAN.MC", "BBVA.MC", "CABK.MC", "SAB.MC", "BKT.MC", "UNI.MC", "MAP.MC",
            "IBE.MC", "REP.MC", "ELE.MC", "NTGY.MC", "ENG.MC", "RED.MC", "ANE.MC", "SLR.MC",
            "COL.MC", "MRL.MC",
            "ACX.MC", "MTS.MC", "FDR.MC", "LOG.MC"
        ]
    }
}

# --- BRAIN LOGIC (CRON / WORKER) ---

def is_market_open(market_config: dict) -> bool:
    now = datetime.now()
    current_time = now.hour * 60 + now.minute
    open_time = market_config["open_hour"] * 60 + market_config["open_minute"]
    close_time = market_config["close_hour"] * 60 + market_config["close_minute"]
    return open_time <= current_time <= close_time

def execute_daily_trading_strategy(ticker: str):
    """
    Designed to be run by a daily Cron Job at 16:30.
    """

    # 1. Download daily historical using yfinance. 
    # multi_level_index=False is required for latest yfinance to work with pandas-ta
    df = yf.download(ticker, period="1y", interval="1d", multi_level_index=False)
    
    # Check if empty
    if df.empty:
        raise Exception("No data found from yfinance")
        
    # 2. Tech calculations with pandas_ta
    df.ta.sma(length=9, append=True)
    df.ta.sma(length=21, append=True)
    df.ta.rsi(length=14, append=True)
    
    if len(df) < 22:
        raise Exception("Not enough data to calculate SMA/RSI")
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 3. Extract key values
    sma9_last, sma21_last = last_row['SMA_9'], last_row['SMA_21']
    sma9_prev, sma21_prev = prev_row['SMA_9'], prev_row['SMA_21']
    rsi_last = last_row['RSI_14']
    
    # 4. Cross technical logic
    cruce_alcista = (sma9_prev <= sma21_prev) and (sma9_last > sma21_last)
    cruce_bajista = (sma9_prev >= sma21_prev) and (sma9_last < sma21_last)
    
    # 5. Execution
    if cruce_alcista and rsi_last < 70:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] SEÑAL DE COMPRA. RSI es {rsi_last:.2f}")
        try:
            # Control de posición abierta para no comprar duplicados
            try:
                trading_client.get_open_position(ticker)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / YA COMPRADA (Evitando duplicado).")
                return
            except Exception:
                # Alpaca lanza una excepción si la posición no existe. Es el comportamiento esperado.
                pass

            req = MarketOrderRequest(
                symbol=ticker,
                qty=1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(req)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Orden de COMPRA enviada.")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Error al enviar orden: {e}")
    elif cruce_bajista:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] SEÑAL DE VENTA.")
        try:
            # En "El Buen Bolsista" solo operamos en Largo (Long). Nunca nos ponemos cortos.
            # Solo vendemos para cerrar una posición que ya tenemos.
            trading_client.get_open_position(ticker) # Da error si no la tenemos
            trading_client.close_position(ticker)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Orden de VENTA enviada (Se cerró la posición).")
        except Exception:
            print(f"[{ticker}] HOLD / No hay posición abierta para vender.")
    else:
        print(f"[{ticker}] HOLD / SIN SEÑALES RELEVANTES.")

def run_bot_all_tickers():
    total_tickers = sum(len(config["tickers"]) for config in MARKETS.values())
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === INICIANDO EJECUCIÓN DEL BOT PARA {total_tickers} ACTIVOS ===")
    
    results = []
    for market_key, config in MARKETS.items():
        print(f"--- Procesando mercado: {config['name']} ---")
        
        # Validar horario a nivel de mercado completo en vez de por ticker
        if not is_market_open(config):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mercado cerrado. Saltando sus {len(config['tickers'])} tickers.")
            continue
            
        for t in config["tickers"]:
            try:
                execute_daily_trading_strategy(t)
                results.append({"ticker": t, "status": "procesado", "market": config['name']})
            except Exception as e:
                results.append({"ticker": t, "status": "error", "detalle": str(e), "market": config['name']})
    
    # Record today's equity snapshot in the database after the run
    try:
        account = trading_client.get_account()
        database.record_daily_equity(float(account.equity))
    except Exception as e:
        print(f"[DB] Error al guardar equity: {e}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === EJECUCIÓN FINALIZADA ===")
    return results

@app.post("/api/bot/run")
def run_bot_manually():
    """Endpoint para ejecutar el bot manualmente y probarlo sin esperar al Cron Job"""
    results = run_bot_all_tickers()
    
    return {
        "message": f"Ejecución manual del bot finalizada",
        "results": results
    }
