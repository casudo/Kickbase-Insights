import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// Import data
import allPlayerData from '../data/all_players_data.json';

function MarketValueChart() {
  // State to store selected player and chart scale
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [chartScale, setChartScale] = useState('all'); // Possible values: 'all', '1year', '3months', '1week'

  // Get a list of unique player IDs
  const uniquePlayerIds = Array.from(new Set(allPlayerData.map((player) => player.playerId)));

  // Logic to filter data based on selectedPlayer and chartScale
  const filteredData = allPlayerData
    .filter((player) => player.playerId === selectedPlayer)
    .map((player) => {
      // Add logic here to filter marketValues based on chartScale
      // For simplicity, let's assume player.marketValues is an array of objects with 'd' (date) and 'm' (market value) properties.

      // Filter based on chartScale
      let filteredValues = player.marketValues;

      switch (chartScale) {
        case '1year':
          // Filter for the last 365 days
          const oneYearAgo = new Date();
          oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
          filteredValues = filteredValues.filter((entry) => new Date(entry.d) > oneYearAgo);
          break;

        case '3months':
          // Filter for the last 90 days
          const threeMonthsAgo = new Date();
          threeMonthsAgo.setDate(threeMonthsAgo.getDate() - 90);
          filteredValues = filteredValues.filter((entry) => new Date(entry.d) > threeMonthsAgo);
          break;

        case '1week':
          // Filter for the last 7 days
          const oneWeekAgo = new Date();
          oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
          filteredValues = filteredValues.filter((entry) => new Date(entry.d) > oneWeekAgo);
          break;

        default:
          // No additional filtering for 'all'
          break;
      }

      return filteredValues;
    })[0] || [];

  // Render the chart
  return (
    <div style={{ margin: '20px' }}>
      {/* Dropdown for selecting player */}
      <label>
        Select a Player:{' '}
        <select onChange={(e) => setSelectedPlayer(e.target.value)}>
          <option value="">All Players</option>
          {uniquePlayerIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </label>

      {/* Dropdown for selecting chart scale */}
      <label>
        Select Chart Scale:{' '}
        <select onChange={(e) => setChartScale(e.target.value)}>
          <option value="all">All</option>
          <option value="1year">1 Year</option>
          <option value="3months">3 Months</option>
          <option value="1week">1 Week</option>
        </select>
      </label>

      {/* Render the chart */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={filteredData}>
          <XAxis dataKey="d" type="category" angle={-45} textAnchor="end" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="m" name="Market Value" stroke="#8884d8" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MarketValueChart;
