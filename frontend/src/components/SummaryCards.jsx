import React from 'react';

function SummaryCards({ summary, totalTradesCount }) {
  return (
    <div className="grid-cards detailed-summary">
      {/* 1. Cash Card */}
      <div className="card summary-card">
        <h3>💰 Liquidez (Cash)</h3>
        <h2 className="main-value">${summary?.cash?.toFixed(2) || '0.00'}</h2>
        <p className="subtitle">Capital disponible en cuenta</p>
        <div className="metric-row" style={{ marginTop: '1rem' }}>
          <span>Balance Total:</span>
          <span>${summary?.balance_total?.toFixed(2) || '0.00'}</span>
        </div>
      </div>

      {/* 2. Open Positions Card */}
      <div className="card summary-card">
        <h3>📈 Posiciones Abiertas</h3>
        <div className="metric-row">
          <span>Dinero Invertido:</span>
          <span>${summary?.invested?.toFixed(2) || '0.00'}</span>
        </div>
        <div className="metric-row">
          <span>Valor Actual:</span>
          <span>${summary?.market_value?.toFixed(2) || '0.00'}</span>
        </div>
        <div 
          className="metric-row highlight" 
          style={{ 
            marginTop: '0.5rem', 
            paddingTop: '0.5rem', 
            borderTop: '1px solid var(--border)', 
            color: summary?.unrealized_pl >= 0 ? 'var(--success)' : 'var(--danger)' 
          }}
        >
          <span>Beneficio Latente:</span>
          <span style={{ fontWeight: 'bold', color: summary?.unrealized_pl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
            {summary?.unrealized_pl >= 0 ? '+' : ''}${summary?.unrealized_pl?.toFixed(2) || '0.00'} ({summary?.unrealized_pl_pct >= 0 ? '+' : ''}{summary?.unrealized_pl_pct?.toFixed(2) || '0.00'}%)
          </span>
        </div>
      </div>

      {/* 3. Realized P/L Card */}
      <div className="card summary-card">
        <h3>🏦 P&L Realizado</h3>
        <h2 className={summary?.realized_pl >= 0 ? 'value-positive' : 'value-negative'}>
          {summary?.realized_pl >= 0 ? '+' : ''}${summary?.realized_pl?.toFixed(2) || '0.00'}
        </h2>
        <p className="subtitle">P&L Histórico (Operaciones Cerradas)</p>
        <div className="metric-row highlight" style={{ marginTop: '1rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
          <span>P&L de Hoy:</span>
          <span style={{ color: summary?.daily_pl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
            {summary?.daily_pl >= 0 ? '+' : ''}${summary?.daily_pl?.toFixed(2) || '0.00'}
          </span>
        </div>
      </div>

      {/* 4. Bot Activity Card */}
      <div className="card summary-card">
        <h3>⚡ Actividad del Bot</h3>
        <h2 className="main-value">{totalTradesCount}</h2>
        <p className="subtitle">Operaciones totales cerradas</p>
        <div className="metric-row highlight" style={{ marginTop: '1rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
          <span>Estado:</span>
          <span className="value-positive">Activo y vigilando</span>
        </div>
      </div>
    </div>
  );
}

export default SummaryCards;
