import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const BinanceChart = () => {
  const [chartData, setChartData] = useState([]);
  const [dataKey, setDataKey] = useState('Close');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://0.0.0.0:8000/download/binance-data');
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const csvText = await response.text();
        const lines = csvText.split('\n');
        const parsedData = [];
        let headers: string[] = [];

        // Detect and process headers
        const firstLine = lines[0].split(',');
        if (isNaN(Number(firstLine[1]))) {
          headers = firstLine.map(h => h.trim());
          lines.shift();
        }

        // Process each line of CSV
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i].trim();
          if (!line) continue;

          const parts = line.split(',').map(p => p.trim());
          
          // Validate row format
          if (parts.length < 11) {
            throw new Error(`Invalid CSV format in line ${i + 1}`);
          }

          // Create data entry
          const entry = headers.length 
            ? Object.fromEntries(headers.map((h, idx) => [h, parts[idx]]))
            : {
                Timestamp: parts[0],
                Open: parts[1],
                High: parts[2],
                Low: parts[3],
                Close: parts[4],
                Volume: parts[5]
              };

          // Convert numeric fields
          const numericFields = ['Open', 'High', 'Low', 'Close', 'Volume'];
          numericFields.forEach(field => {
            const value = parseFloat(entry[field]);
            if (isNaN(value)) {
              throw new Error(`Invalid ${field} value in line ${i + 1}`);
            }
            entry[field] = value;
          });

          parsedData.push({
            timestamp: entry.Timestamp,
            Close: entry.Close,
            Open: entry.Open,
            High: entry.High,
            Low: entry.Low,
            Volume: entry.Volume
          });
        }

        setChartData(parsedData);
        setError('');
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading market data...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="chart-container">
      <div className="controls">
        <select
          value={dataKey}
          onChange={(e) => setDataKey(e.target.value)}
          className="data-selector"
        >
          <option value="Close">Close Price</option>
          <option value="Open">Open Price</option>
          <option value="High">High Price</option>
          <option value="Low">Low Price</option>
          <option value="Volume">Volume</option>
        </select>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={chartData}>
            <XAxis
            dataKey="timestamp"
            stroke="#ffffff" // Axis line color
            tick={{
              fill: '#ffffff', // Tick text color
              fontSize: 13,
            }}
            angle={-45}
            axisLine={{ stroke: '#ffffff' }} // Explicit axis line color
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="#ffffff" // Axis line color
            tick={{
              fill: '#ffffff', // Tick text color
              fontSize: 13
            }}
            axisLine={{ stroke: '#ffffff' }} // Explicit axis line color
          />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #ddd',
                borderRadius: '4px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            />
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke="#3B82F6"
              fill="#3B82F6"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default BinanceChart;