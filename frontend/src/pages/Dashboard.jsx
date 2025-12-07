import React, { useEffect, useState } from 'react';
import api from '../api/client';

const Dashboard = () => {
  const [stats, setStats] = useState({
    activeSessions: '...',
    totalUsers: '...',
    totalNas: '...',
    totalLogs: '...',
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [usersRes, nasRes, sessionsRes, logsRes] = await Promise.all([
            api.get('/radius-users/?limit=1'),
            api.get('/nas/?limit=1'),
            api.get('/sessions/?status=active&limit=1'),
            api.get('/logs/?limit=1')
        ]);
        
        setStats({
            activeSessions: sessionsRes.data.count,
            totalUsers: usersRes.data.count,
            totalNas: nasRes.data.count,
            totalLogs: logsRes.data.count
        });
      } catch (error) {
        console.error("Error fetching stats", error);
        setStats({
            activeSessions: '-',
            totalUsers: '-',
            totalNas: '-',
            totalLogs: '-'
        });
      }
    };
    fetchStats();
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700/50 p-6 rounded-lg shadow-sm">
          <h3 className="text-slate-300 text-sm font-medium">Active Sessions</h3>
          <p className="text-3xl font-bold text-sky-400 drop-shadow-sm">{stats.activeSessions}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700/50 p-6 rounded-lg shadow-sm">
          <h3 className="text-slate-300 text-sm font-medium">Total Users</h3>
          <p className="text-3xl font-bold text-sky-400 drop-shadow-sm">{stats.totalUsers}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700/50 p-6 rounded-lg shadow-sm">
          <h3 className="text-slate-300 text-sm font-medium">Total NAS</h3>
          <p className="text-3xl font-bold text-sky-400 drop-shadow-sm">{stats.totalNas}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700/50 p-6 rounded-lg shadow-sm">
          <h3 className="text-slate-300 text-sm font-medium">Total Logs</h3>
          <p className="text-3xl font-bold text-sky-400 drop-shadow-sm">{stats.totalLogs}</p>
        </div>
      </div>
    </div>
  );
};
export default Dashboard;
