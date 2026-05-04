import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function App() {
  const [summary, setSummary] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isBotRunning, setIsBotRunning] = useState(false);

  const fetchDashboardData = async () => {
    try {
      const [sumRes, posRes, tradesRes, historyRes] = await Promise.all([
        axios.get('http://localhost:8000/api/portfolio/summary'),
        axios.get('http://localhost:8000/api/positions'),
        axios.get('http://localhost:8000/api/trades'),
        axios.get('http://localhost:8000/api/portfolio/history')
      ]);
      
      setSummary(sumRes.data);
      if (Array.isArray(posRes.data)) setPositions(posRes.data);
      setTrades(tradesRes.data);
      if (Array.isArray(historyRes.data?.history)) setChartData(historyRes.data.history);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleRunBot = async () => {
    setIsBotRunning(true);
    try {
      await axios.post('http://localhost:8000/api/bot/run');
      // Refresh data after running
      await fetchDashboardData();
    } catch (error) {
      console.error("Error running bot:", error);
      alert("Hubo un error al ejecutar el bot. Revisa la consola.");
    } finally {
      setIsBotRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <div>Cargando datos del bróker...</div>
      </div>
    );
  }

  const totalTradesCount = trades?.total_trades || trades?.history?.length || 0;

  return (
    <div className="container">
      <header className="header">
        <div className="header-titles">
          <h1>🤖 InTheMoney Dashboard</h1>
          <p>Estrategia Diaria: SMA 9x21 | RSI &lt; 70</p>
        </div>
        <button 
          className="btn-run" 
          onClick={handleRunBot}
          disabled={isBotRunning}
        >
          {isBotRunning ? (
            <>
              <span className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }}></span>
              Ejecutando...
            </>
          ) : (
            <>🚀 Ejecutar Bot Ahora</>
          )}
        </button>
      </header>

      {/* 1. Summary Cards */}
      <div className="grid-cards">
        <div className="card">
          <h3>Balance Total</h3>
          <h2>${summary?.balance_total?.toFixed(2) || '0.00'}</h2>
        </div>
        <div className="card">
          <h3>P&L Diario</h3>
          <h2 className={summary?.daily_pl >= 0 ? 'value-positive' : 'value-negative'}>
            ${summary?.daily_pl?.toFixed(2) || '0.00'} 
            <span className="percentage">
              ({summary?.daily_pl_pct?.toFixed(2) || '0.00'}%)
            </span>
          </h2>
        </div>
        <div className="card">
          <h3>Operaciones Cerradas</h3>
          <h2>{totalTradesCount} {totalTradesCount === 0 && <span style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>(Sin historial)</span>}</h2>
        </div>
      </div>

      {/* 2. Recharts Graph Component */}
      <div className="card chart-card">
        <h3>Evolución del Portfolio (Datos reales)</h3>
        {chartData.length === 0 ? (
          <div className="empty-state">
            Aún no hay datos históricos. Se registrarán automáticamente cada vez que ejecutes el bot.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="85%">
            <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)"/>
              <XAxis dataKey="name" axisLine={false} tickLine={false} stroke="#94a3b8" />
              <YAxis axisLine={false} tickLine={false} domain={['auto', 'auto']} stroke="#94a3b8" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#f8fafc' }} 
                itemStyle={{ color: '#60a5fa' }}
                formatter={(v) => [`$${v.toFixed(2)}`, 'Equity']}
              />
              <Line type="monotone" dataKey="equity" stroke="#60a5fa" strokeWidth={3} dot={{ r: 4, fill: '#60a5fa' }} activeDot={{ r: 8, fill: '#3b82f6' }}/>
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 3. Active Positions Table */}
      <div className="card">
        <h3>Posiciones Activas (Valores Comprados)</h3>
        <div className="table-container">
          <table className="styled-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Cant.</th>
                <th>Precio Compra</th>
                <th>Precio Actual</th>
                <th>Ganancia/Pérdida</th>
              </tr>
            </thead>
            <tbody>
              {positions.length > 0 ? positions.map((pos) => (
                <tr key={pos.ticker}>
                  <td><strong>{pos.ticker}</strong></td>
                  <td>{pos.qty}</td>
                  <td>${pos.avg_entry_price.toFixed(2)}</td>
                  <td>${pos.current_price.toFixed(2)}</td>
                  <td className={pos.unrealized_pl >= 0 ? 'value-positive' : 'value-negative'} style={{ fontWeight: 'bold' }}>
                    ${pos.unrealized_pl.toFixed(2)} ({pos.unrealized_pl_pcnt.toFixed(2)}%)
                  </td>
                </tr>
              )) : (
                <tr><td colSpan="5" className="empty-state">El bot no tiene posiciones en este momento.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default App;
