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

**Note on Credentials**: Ensure you have a `.env` file in the `backend` folder containing your Alpaca paper trading keys:
```env
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
```

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
