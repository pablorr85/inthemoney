import pandas as pd
import sys
from collections import deque

def calculate_fifo(csv_path):
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error al abrir el archivo CSV: {e}")
        sys.exit(1)
        
    # Standardize column names to remove BOM or spaces if present
    df.columns = [c.strip() for c in df.columns]
    
    # Filter only filled orders (normally all exported are filled, but let's be safe)
    if 'Estado' in df.columns:
        df = df[df['Estado'].astype(str).str.lower() == 'filled'].copy()
        
    # Sort chronologically by date
    if 'Fecha Orden (UTC)' in df.columns:
        df['Fecha Orden (UTC)'] = pd.to_datetime(df['Fecha Orden (UTC)'])
        df = df.sort_values('Fecha Orden (UTC)')
    else:
        print("Error: El CSV no contiene la columna 'Fecha Orden (UTC)'.")
        sys.exit(1)
        
    # Dictionary to keep buy queues per Ticker
    # Each entry in queue is a dict: {"qty": float, "price_eur": float}
    wallets = {}
    realized_gains = {}
    
    for _, row in df.iterrows():
        ticker = row['Ticker']
        operation = str(row['Operación']).strip().lower()
        qty = float(row['Cantidad'])
        price_eur = float(row['Precio Fill (EUR)'])
        
        if ticker not in wallets:
            wallets[ticker] = deque()
            realized_gains[ticker] = 0.0
            
        if operation == 'buy':
            wallets[ticker].append({
                "qty": qty,
                "price_eur": price_eur
            })
        elif operation == 'sell':
            sell_qty = qty
            gain = 0.0
            EPSILON = 1e-6
            while sell_qty > EPSILON:
                if not wallets[ticker]:
                    # If no registered buys exist, could be short selling or missing historical buys
                    print(f"⚠️ Advertencia: Venta de {sell_qty:.4f} de {ticker} sin compras registradas previas en este CSV.")
                    break
                
                oldest_buy = wallets[ticker][0]
                if oldest_buy['qty'] <= sell_qty + EPSILON:
                    # Deplete this buy entirely (taking care of float representation margins)
                    matched_qty = oldest_buy['qty']
                    gain += matched_qty * (price_eur - oldest_buy['price_eur'])
                    sell_qty -= matched_qty
                    wallets[ticker].popleft()
                else:
                    # Partially deplete this buy
                    matched_qty = sell_qty
                    gain += matched_qty * (price_eur - oldest_buy['price_eur'])
                    oldest_buy['qty'] -= matched_qty
                    sell_qty = 0
            
            realized_gains[ticker] += gain

    # 1. Realized Gains & Losses Summary (FIFO)
    print("\n" + "=" * 70)
    print("=== RESUMEN DE GANANCIAS/PÉRDIDAS PATRIMONIALES (MÉTODO FIFO - EUR) ===")
    print("=" * 70)
    total_net = 0.0
    for ticker, gain in sorted(realized_gains.items()):
        total_net += gain
        color = "🟢" if gain >= 0 else "🔴"
        print(f" {color} Ticker: {ticker:<6} | Resultado neto realizado: {gain:>8.2f} €")
    print("=" * 70)
    color_total = "🟢" if total_net >= 0 else "🔴"
    print(f" {color_total} RESULTADO NETO TOTAL REALIZADO: {total_net:.2f} €")
    print("=" * 70 + "\n")

    # 2. Remaining Active Holdings Summary (Unrealized Wallet)
    print("=" * 70)
    print("=== CARTERA ACTIVA RESTANTE AL FINAL DEL PERÍODO ===")
    print("=" * 70)
    has_holdings = False
    for ticker, queue in sorted(wallets.items()):
        total_qty = sum(item['qty'] for item in queue)
        if total_qty > 1e-6:
            total_cost = sum(item['qty'] * item['price_eur'] for item in queue)
            avg_price = total_cost / total_qty
            print(f" 💼 Ticker: {ticker:<6} | Cantidad: {total_qty:>8.4f} | Precio medio de adquisición: {avg_price:>8.2f} €")
            has_holdings = True
    if not has_holdings:
        print(" Sin acciones remanentes en cartera al final de este histórico.")
    print("=" * 70 + "\n")

    # 3. Spanish Tax Agency Compliance Notice (Tech Lead Legal Warning)
    print("⚠️" + " NOTA DE CUMPLIMIENTO FISCAL (AGENCIA TRIBUTARIA) " + "⚠️")
    print("-" * 70)
    print("1. Regla de los 2 Meses (Wash-Sale): Si has vendido algún ticker con pérdidas,")
    print("   recuerda que NO podrás deducirte esa pérdida si has comprado acciones homogéneas")
    print("   dentro de los 2 meses anteriores o posteriores a dicha venta.")
    print("2. Operaciones Manuales: Este cálculo se limita exclusivamente a las transacciones")
    print("   registradas en este archivo CSV. Si operas el mismo ticker en otros brókers,")
    print("   debes consolidar ambos históricos bajo el mismo orden FIFO temporal.")
    print("3. Eventos Corporativos: Este script asume cotización ordinaria. Acciones corporativas")
    print("   (splits, contrasplits, fusiones) deben ajustarse previamente en el CSV.")
    print("-" * 70 + "\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python calculate_fifo.py <ruta_al_archivo_csv>")
        sys.exit(1)
    calculate_fifo(sys.argv[1])
