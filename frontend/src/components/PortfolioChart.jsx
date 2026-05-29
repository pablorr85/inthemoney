import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function PortfolioChart({ chartData }) {
  return (
    <div className="card chart-card">
      <h3>Evolución del Portfolio (Datos reales)</h3>
      {chartData.length === 0 ? (
        <div className="empty-state">
          Aún no hay datos históricos. Se registrarán automáticamente cada vez que ejecutes el bot.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
            <XAxis 
              dataKey="name" 
              axisLine={false} 
              tickLine={false} 
              stroke="#94a3b8" 
              tickFormatter={(tick) => {
                if (!tick) return '';
                const parts = tick.split('-');
                if (parts.length === 3) {
                  return `${parts[2]}/${parts[1]}/${parts[0]}`;
                }
                return tick;
              }}
              angle={-45}
              textAnchor="end"
              height={60}
              tick={{ fontSize: 12 }}
            />
            <YAxis axisLine={false} tickLine={false} domain={['auto', 'auto']} stroke="#94a3b8" />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#f8fafc' }} 
              itemStyle={{ color: '#60a5fa' }}
              labelFormatter={(label) => {
                if (!label) return '';
                const parts = label.split('-');
                if (parts.length === 3) {
                  return `${parts[2]}/${parts[1]}/${parts[0]}`;
                }
                return label;
              }}
              formatter={(v) => [`$${v.toFixed(2)}`, 'Equity']}
            />
            <Line 
              type="monotone" 
              dataKey="equity" 
              stroke="#60a5fa" 
              strokeWidth={3} 
              dot={{ r: 4, fill: '#60a5fa' }} 
              activeDot={{ r: 8, fill: '#3b82f6' }} 
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default PortfolioChart;
