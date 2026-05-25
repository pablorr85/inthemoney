import os
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
    # Run at the 15th minute of each hour during Wall Street market hours (10:15 AM to 3:15 PM New York Time).
    # This provides a 45-minute "courtesy" buffer after market open (9:30 AM),
    # thereby avoiding the extreme volatility of the opening minutes, and evaluates hourly.
    scheduler.add_job(
        run_bot_all_tickers,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="10-15",
            minute=15,
            timezone=ZoneInfo("America/New_York")
        ),
        id="daily_trading_job",
        replace_existing=True
    )
    scheduler.start()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] APScheduler started: Bot scheduled from 10:15 to 15:15 hourly NY Time (M-F).")

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] APScheduler shutdown.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes from api.py
app.include_router(api_router, prefix="/api")

# Serve the frontend statically
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"Warning: Frontend dist folder no encontrada en {frontend_path}")
