# InTheMoney Trading Bot

This repository contains a full-stack algorithmic trading bot application called "InTheMoney". The system uses Alpaca for paper trading and technical analysis (SMA and RSI crosses) to generate buy/sell signals on a specific universe of stocks.

## Prerequisites

- Python 3.x
- Node.js & npm
- An [Alpaca](https://alpaca.markets/) account (Paper Trading API Keys)

---

## 1. Running the Backend

The backend is built with Python and FastAPI. It handles the trading logic, database interaction, and serves the REST API.

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Start the FastAPI server
uvicorn main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`. 
API Documentation (Swagger UI) is automatically generated and can be viewed at `http://localhost:8000/docs`.

**Note on Credentials and Environment Variables**: Ensure you have a `.env` file in the `backend` folder containing your credentials. The system supports full configurability for running separate Paper and Live (real-money) trading instances:

```env
# Essential Alpaca API Keys (obtained from your Alpaca Dashboard)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here

# Trading Mode (True = Paper/Simulated, False = Live/Real Money)
# Default is True to prevent accidental live execution.
ALPACA_PAPER=True

# Starting Portfolio Balance (Used for correct P&L dashboard calculations)
# Default is 100000.0 (Alpaca Paper standard). Adjust to your real deposit (e.g., 500.0) for live trading.
STARTING_BALANCE=100000.0

# Max Budget Per Trade (Upper price boundary per single asset purchase)
# Default is 5000.0. For real-money small accounts, limit this to e.g. 50.0.
MAX_BUDGET_PER_TRADE=5000.0
```

### Multi-Instance Raspberry Pi Deployment Guidelines

To run both a **Paper** and a **Live** instance side-by-side on the same server or Raspberry Pi without conflicts:
1. Clone the project into two distinct directories (e.g., `/home/pi/inthemoney-paper` and `/home/pi/inthemoney-real`). This ensures their local SQLite databases (`history.db`) remain fully isolated.
2. Maintain separate `.env` files in each directory as described above (ensuring `ALPACA_PAPER=False` for your live folder).
3. Bind them to different network ports when launching the FastAPI servers:
   - **Paper instance:** `uvicorn main:app --host 0.0.0.0 --port 8000` (Access at `http://<ip>:8000`)
   - **Live instance:** `uvicorn main:app --host 0.0.0.0 --port 8001` (Access at `http://<ip>:8001`)

---

## 2. Running the Frontend

The frontend is a modern web application (React/Vite based).

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Start the development server
npm run dev
```

The frontend will typically run on `http://localhost:5173` (or the port indicated in your terminal).

---

## 3. Running the Trading Bot (Buying & Selling Stocks)

The core trading algorithm relies on fetching historical data and calculating the 9-day and 21-day Simple Moving Averages (SMA) along with the Relative Strength Index (RSI).

The bot is designed to be executed periodically (e.g., via a daily Cron Job around market close at 16:30). 

**To manually trigger the trading bot to buy/sell:**

The bot logic is exposed via a REST API endpoint. With the backend running, you can trigger a full run over all configured stocks by making a `POST` request to `/api/bot/run`.

Using `curl` from your terminal:
```bash
curl -X POST http://localhost:8000/api/bot/run
```

Or you can use a tool like Postman or simply trigger it from the frontend UI if a button is implemented. When called, the bot will:
1. Loop through all predefined tickers in `main.py`.
2. Analyze their daily trends.
3. Submit BUY/SELL orders to Alpaca automatically.
4. Update the daily portfolio equity snapshot in the SQLite database.
