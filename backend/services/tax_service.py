import csv
import io
import urllib.request
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

def get_ecb_exchange_rates(start_date: datetime, end_date: datetime):
    """
    Fetch daily EUR/USD reference exchange rates published by the European Central Bank (ECB)
    using the Frankfurter API, with a fallback to Yahoo Finance EURUSD=X if unavailable.
    """
    rates_map = {}
    ecb_success = False
    
    # Method 1: Try official ECB reference rates via Frankfurter API
    try:
        start_str = (start_date - timedelta(days=15)).strftime("%Y-%m-%d")
        end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
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
                print(f"[Tax Service] Successfully fetched exact ECB rates from Frankfurter API.")
    except Exception as e:
        print(f"[Tax Service] Frankfurter ECB API failed, trying Yahoo Finance fallback: {e}")
        
    # Method 2: Fallback to yfinance EURUSD=X if ECB API failed
    if not ecb_success:
        try:
            rates_start = start_date - timedelta(days=15)
            rates_df = yf.download(
                "EURUSD=X", 
                start=rates_start.strftime("%Y-%m-%d"), 
                end=(end_date + timedelta(days=2)).strftime("%Y-%m-%d"), 
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
                print(f"[Tax Service] Fallback successfully fetched rates from Yahoo Finance.")
        except Exception as e:
            print(f"[Tax Service] Error downloading exchange rates from yfinance: {e}")
            
    return rates_map

def generate_tax_csv_content(all_orders, after_date: datetime):
    """
    Generate a detailed CSV string containing all orders with exact USD to EUR currency conversions
    for Spanish Tax Agency compliance, using official ECB daily rates.
    """
    # Fetch rates from start date to today
    rates_map = get_ecb_exchange_rates(after_date, datetime.now())
    
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
        
    return output.getvalue()
