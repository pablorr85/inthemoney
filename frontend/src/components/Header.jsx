import React from 'react';

function Header({ isBotRunning, onRunBot }) {
  return (
    <header className="header">
      <div className="header-titles">
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <img 
            src="/logo.png" 
            alt="InTheMoney Logo" 
            style={{ width: '48px', height: '48px', borderRadius: '12px', boxShadow: '0 4px 10px rgba(0,0,0,0.3)' }} 
          />
          InTheMoney Dashboard
        </h1>
        <p>Estrategia Diaria: SMA 9x21 | RSI &lt; 75</p>
      </div>
      <div className="header-actions">
        <button 
          className="btn-export" 
          onClick={() => window.open('/api/export/trades')}
        >
          📊 CSV (Hacienda)
        </button>
        <button 
          className="btn-run" 
          onClick={onRunBot}
          disabled={isBotRunning}
        >
          {isBotRunning ? (
            <>
              <span className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }}></span>
              Ejecutando...
            </>
          ) : (
            <>🚀 Ejecutar Bot</>
          )}
        </button>
      </div>
    </header>
  );
}

export default Header;
