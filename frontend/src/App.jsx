import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Header from './components/Header';
import SummaryCards from './components/SummaryCards';
import PortfolioChart from './components/PortfolioChart';
import PositionsTable from './components/PositionsTable';

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
        axios.get('/api/portfolio/summary'),
        axios.get('/api/positions'),
        axios.get('/api/trades'),
        axios.get('/api/portfolio/history')
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
      await axios.post('/api/bot/run');
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
      {/* Upper Navigation and Actions branding */}
      <Header isBotRunning={isBotRunning} onRunBot={handleRunBot} />

      {/* Main KPI metrics summary */}
      <SummaryCards summary={summary} totalTradesCount={totalTradesCount} />

      {/* Historical Equity Evolution Chart */}
      <PortfolioChart chartData={chartData} />

      {/* Active held positions table */}
      <PositionsTable positions={positions} />
    </div>
  );
}

export default App;
