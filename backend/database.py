import sqlite3
from datetime import datetime, date
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")

def initialize_db():
    """Create the DB and the daily_equity table if they don't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_equity (
            date TEXT PRIMARY KEY,
            equity REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def record_daily_equity(equity: float):
    """Insert or replace today's equity value in the database."""
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO daily_equity (date, equity) VALUES (?, ?)",
        (today, equity)
    )
    conn.commit()
    conn.close()
    print(f"[DB] Equity registrada: {today} -> ${equity:.2f}")

def get_historical_equity(days: int = 90):
    """Return the last `days` records of equity, ordered chronologically."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, equity FROM daily_equity ORDER BY date DESC LIMIT ?",
        (days,)
    )
    rows = cursor.fetchall()
    conn.close()
    # Reverse so earliest date is first (for the chart)
    rows = list(reversed(rows))
    return [{"name": row[0], "equity": row[1]} for row in rows]
