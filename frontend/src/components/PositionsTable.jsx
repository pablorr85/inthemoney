import React, { useState } from 'react';
import axios from 'axios';

function PositionsTable({ positions }) {
  const [tickerInfo, setTickerInfo] = useState({});

  const handleMouseEnter = async (ticker) => {
    if (!tickerInfo[ticker]) {
      try {
        const response = await axios.get(`/api/ticker/${ticker}/info`);
        setTickerInfo(prev => ({ ...prev, [ticker]: response.data }));
      } catch (err) {
        setTickerInfo(prev => ({ 
          ...prev, 
          [ticker]: { name: ticker, exchange: 'N/A', summary: 'Error al cargar información' } 
        }));
      }
    }
  };

  return (
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
            {positions.length > 0 ? (
              positions.map((pos) => (
                <tr key={pos.ticker}>
                  <td 
                    className="ticker-cell"
                    onMouseEnter={() => handleMouseEnter(pos.ticker)}
                  >
                    {pos.ticker}
                    <div className="ticker-tooltip">
                      {tickerInfo[pos.ticker] ? (
                        <>
                          <div className="tooltip-name">{tickerInfo[pos.ticker].name}</div>
                          <div className="tooltip-exchange">{tickerInfo[pos.ticker].exchange}</div>
                          <div className="tooltip-summary">{tickerInfo[pos.ticker].summary}</div>
                        </>
                      ) : (
                        <div className="tooltip-loading">
                          <span className="spinner-sm"></span>
                          Cargando...
                        </div>
                      )}
                    </div>
                  </td>
                  <td>{pos.qty}</td>
                  <td>${pos.avg_entry_price.toFixed(2)}</td>
                  <td>${pos.current_price.toFixed(2)}</td>
                  <td className={`font-bold ${pos.unrealized_pl >= 0 ? 'value-positive' : 'value-negative'}`}>
                    ${pos.unrealized_pl.toFixed(2)} ({pos.unrealized_pl_pcnt.toFixed(2)}%)
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="empty-state">
                  El bot no tiene posiciones en este momento.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default PositionsTable;
