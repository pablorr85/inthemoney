import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timezone
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

import database
from client import trading_client
from config import MARKETS

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
        
    # 2. Cálculos Técnicos (Indicadores)
    # SMA (Simple Moving Average): Media del precio de los últimos X días.
    # Usamos la de 9 días (rápida) y la de 21 días (lenta).
    df.ta.sma(length=9, append=True)
    df.ta.sma(length=21, append=True)
    
    # RSI (Relative Strength Index): Mide si una acción ha subido demasiado rápido.
    # Va de 0 a 100. Valores por encima de 70 indican "Sobrecompra" (peligro de caída).
    df.ta.rsi(length=14, append=True)
    
    if len(df) < 22:
        raise Exception("Not enough data to calculate SMA/RSI")
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 3. Extraer valores clave de hoy y ayer
    sma9_last, sma21_last = last_row['SMA_9'], last_row['SMA_21']
    sma9_prev, sma21_prev = prev_row['SMA_9'], prev_row['SMA_21']
    rsi_last = last_row['RSI_14']
    
    # 4. Lógica de Cruce de Medias (La estrategia principal)
    # CRUCE ALCISTA (Golden Cross): La media rápida (9) cruza hacia arriba a la lenta (21).
    # Significa que la tendencia a corto plazo es fuerte y está subiendo.
    cruce_alcista = (sma9_prev <= sma21_prev) and (sma9_last > sma21_last)
    
    # CRUCE BAJISTA (Death Cross): La media rápida (9) cruza hacia abajo a la lenta (21).
    # Significa que la tendencia a corto plazo se debilita y empieza a caer.
    cruce_bajista = (sma9_prev >= sma21_prev) and (sma9_last < sma21_last)
    
    # 5. Ejecución
    if not (cruce_alcista and rsi_last < 70) and not cruce_bajista:
        print(f"[{ticker}] HOLD / SIN SEÑALES RELEVANTES.")
        return

    # Anti-Spam: Verificar si ya hay una orden en curso para no duplicarla
    try:
        open_orders = trading_client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[ticker]))
        if open_orders:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / Ya hay una orden pendiente. Esperando ejecución.")
            return
    except Exception:
        pass

    # Para COMPRAR, exigimos el cruce alcista Y que el RSI sea menor a 70 (que no esté sobrecomprada/inflada).
    if cruce_alcista and rsi_last < 70:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] SEÑAL DE COMPRA. RSI es {rsi_last:.2f}")
        try:
            # Control de posición abierta para no comprar duplicados
            try:
                pos = trading_client.get_open_position(ticker)
                if float(pos.qty) > 0:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / YA COMPRADA (Evitando duplicado).")
                    return
                elif float(pos.qty) < 0:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] PELIGRO / Posición Corta detectada. El bot no operará sobre ella.")
                    return
            except Exception:
                # Alpaca lanza una excepción si la posición no existe. Es el comportamiento esperado.
                pass
                
            # Control de Cooldown Fiscal (Regla 2 meses España)
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
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] HOLD / COOLDOWN FISCAL (Vendida hace {days_since_sell} días).")
                        return
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Error verificando cooldown: {e}")

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
            # Solo vendemos para cerrar una posición que ya tenemos (y que sea en positivo/largo).
            pos = trading_client.get_open_position(ticker) # Da error si no la tenemos
            if float(pos.qty) > 0:
                trading_client.close_position(ticker)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{ticker}] Orden de VENTA enviada (Se cerró la posición).")
            else:
                print(f"[{ticker}] HOLD / Posición Corta detectada. Se ignora la venta.")
        except Exception:
            print(f"[{ticker}] HOLD / No hay posición abierta para vender.")

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
