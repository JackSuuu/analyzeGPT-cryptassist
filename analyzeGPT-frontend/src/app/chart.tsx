import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const generateChartData = () => {
  let data = [];
  let baseValue = 42000;
  for (let i = 0; i < 30; i++) {
    baseValue += (Math.random() - 0.5) * 500;
    data.push({ timestamp: `Day ${i + 1}`, value: baseValue });
  }
  return data;
};

const PredictionChart = () => {
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    setChartData(generateChartData());
  }, []);

  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip />
          <Area type="monotone" dataKey="value" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.3} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PredictionChart;
