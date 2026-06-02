import React, { useState } from 'react';

function Header({ isBotRunning, onRunBot }) {
  const startYear = 2026;
  const currentYear = new Date().getFullYear();
  
  // Generate list of years from currentYear down to 2026
  const years = [];
  for (let y = currentYear; y >= startYear; y--) {
    years.push(y);
  }

  const [selectedYear, setSelectedYear] = useState(currentYear);

  return (
    <header className="header">
      <div className="header-titles">
        <h1>
          <img 
            src="/logo.png" 
            alt="InTheMoney Logo" 
            className="header-logo"
          />
          InTheMoney Dashboard
        </h1>
        <p>Estrategia Diaria: SMA 9x21 | RSI &lt; 75</p>
      </div>
      <div className="header-actions">
        {/* Dynamic Year Selector styled for the dashboard aesthetics */}
        <div className="year-selector-container">
          <span className="year-selector-label">Año:</span>
          <select 
            value={selectedYear} 
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            className="year-selector-select"
          >
            {years.map(y => (
              <option key={y} value={y} style={{ backgroundColor: '#1e293b', color: '#f8fafc' }}>
                {y}
              </option>
            ))}
          </select>
        </div>

        <button 
          className="btn-export" 
          onClick={() => window.open(`/api/export/trades?year=${selectedYear}`)}
          title={`Exportar operaciones del año ${selectedYear} para Hacienda`}
        >
          📊 CSV
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
