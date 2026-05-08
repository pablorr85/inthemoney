from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import database
from bot import run_bot_all_tickers
from api import router as api_router

app = FastAPI(title="InTheMoney Trading Bot API")

# Initialize the SQLite database on startup
database.initialize_db()

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    # Ejecutamos en el minuto 15 de cada hora.
    # Esto da 15 mins de "cortesía" a la bolsa española (abre a las 9:00, evaluamos a las 9:15)
    # y 45 mins a la bolsa americana (abre a las 15:30, evaluamos a las 16:15)
    # evitando así la altísima volatilidad de los primeros minutos de apertura.
    scheduler.add_job(
        run_bot_all_tickers,
        trigger=CronTrigger(day_of_week="mon-fri", hour="9-22", minute=15),
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

# Incluimos todas las rutas desde api.py
app.include_router(api_router, prefix="/api")
