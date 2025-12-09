import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { 
  Activity, 
  ArrowUp, 
  ArrowDown, 
  Users, 
  RefreshCw,
  Search,
  PieChart as PieIcon,
  FileText
} from 'lucide-react';
import api from '../api/client';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Data states
  const [serverSessions, setServerSessions] = useState([]);
  const [realTimeActiveSessions, setRealTimeActiveSessions] = useState(0);
  const [serverTraffic, setServerTraffic] = useState([]);
  const [serverTrafficUnit, setServerTrafficUnit] = useState('MB');
  
  // User Data States
  const [userTrafficStats, setUserTrafficStats] = useState([]);
  const [userTrafficUnit, setUserTrafficUnit] = useState('MB');
  const [availableTrafficUsers, setAvailableTrafficUsers] = useState([]);
  
  const [userSessionStats, setUserSessionStats] = useState([]);
  const [availableSessionUsers, setAvailableSessionUsers] = useState([]);
  
  const [userStatusCounts, setUserStatusCounts] = useState([]);
  const [hiddenStatuses, setHiddenStatuses] = useState(new Set());
  
  const [logCounts, setLogCounts] = useState([]);
  const [hiddenLevels, setHiddenLevels] = useState(new Set());
  
  // Filter states
  const [userFilter, setUserFilter] = useState('');
  const [timeRange, setTimeRange] = useState('24h');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');

  // Helper to get best unit and divisor
  const getBestUnitAndDivisor = (bytes) => {
    const k = 1024;
    const mb = Math.pow(k, 2);
    const gb = Math.pow(k, 3);
    const tb = Math.pow(k, 4);
    const pb = Math.pow(k, 5);

    if (bytes < gb) return { unit: 'MB', divisor: mb };
    if (bytes < tb) return { unit: 'GB', divisor: gb };
    if (bytes < pb) return { unit: 'TB', divisor: tb };
    return { unit: 'PB', divisor: pb };
  };

  // Helper to format bytes
  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = Math.max(0, decimals);
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  const fetchStats = async () => {
    setLoading(true);
    try {
      // Calculate start time based on range
      let timeFilter = '';
      
      if (timeRange === 'custom') {
        if (!customStartDate) {
          setLoading(false);
          return;
        }
        timeFilter = `timestamp__gte=${new Date(customStartDate).toISOString()}`;
        if (customEndDate) {
          timeFilter += `&timestamp__lte=${new Date(customEndDate).toISOString()}`;
        }
      } else {
        const now = new Date();
        let startTime = new Date();
        if (timeRange === '1h') startTime.setHours(now.getHours() - 1);
        else if (timeRange === '6h') startTime.setHours(now.getHours() - 6);
        else if (timeRange === '24h') startTime.setHours(now.getHours() - 24);
        else if (timeRange === '7d') startTime.setDate(now.getDate() - 7);
        else if (timeRange === '30d') startTime.setDate(now.getDate() - 30);
        else if (timeRange === '90d') startTime.setDate(now.getDate() - 90);
        
        timeFilter = `timestamp__gte=${startTime.toISOString()}`;
      }

      // Fetch all stats concurrently
      const [sessionsRes, trafficRes, userTrafficRes, userSessionsRes, statusRes, logsRes, currentSessionsRes] = await Promise.all([
        api.get(`/stats/server/sessions/?${timeFilter}`),
        api.get(`/stats/server/traffic/?${timeFilter}`),
        api.get(`/stats/users/traffic/?${timeFilter}&username__icontains=${userFilter}`),
        api.get(`/stats/users/sessions/?${timeFilter}&username__icontains=${userFilter}`),
        api.get(`/stats/users/status-counts/`),
        api.get(`/stats/server/logs/counts/?${timeFilter}`),
        api.get(`/stats/server/sessions/current/`)
      ]);

      // Process server sessions data for chart
      const sessionsData = sessionsRes.data
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
        .map(item => ({
          ...item,
          time: new Date(item.timestamp).toLocaleTimeString(),
          fullDate: new Date(item.timestamp).toLocaleString()
        }));

      // Calculate dynamic unit for Server Traffic
      let maxServerBytes = 0;
      trafficRes.data.forEach(item => {
         maxServerBytes = Math.max(maxServerBytes, item.total_rx || 0, item.total_tx || 0);
      });
      const { unit: sUnit, divisor: sDivisor } = getBestUnitAndDivisor(maxServerBytes);
      setServerTrafficUnit(sUnit);

      // Process server traffic data for chart
      const trafficData = trafficRes.data
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
        .map(item => ({
          ...item,
          time: new Date(item.timestamp).toLocaleTimeString(),
          fullDate: new Date(item.timestamp).toLocaleString(),
          rx: parseFloat((item.total_rx / sDivisor).toFixed(2)),
          tx: parseFloat((item.total_tx / sDivisor).toFixed(2)),
          total: parseFloat((item.total_traffic / sDivisor).toFixed(2))
        }));

      // --- Process User Traffic ---
      const rawUserTraffic = userTrafficRes.data;
      
      let maxUserBytes = 0;
      rawUserTraffic.forEach(item => {
         maxUserBytes = Math.max(maxUserBytes, item.total_traffic || 0);
      });
      const { unit: uUnit, divisor: uDivisor } = getBestUnitAndDivisor(maxUserBytes);
      setUserTrafficUnit(uUnit);
      
      const trafficUsersSet = new Set(rawUserTraffic.map(item => item.username));
      const trafficUsersList = Array.from(trafficUsersSet).sort((a, b) => a.localeCompare(b));
      
      const trafficHistoryMap = {};
      for (const item of rawUserTraffic) {
        const timeKey = new Date(item.timestamp).getTime();
        if (!trafficHistoryMap[timeKey]) {
          trafficHistoryMap[timeKey] = {
            timestamp: item.timestamp,
            time: new Date(item.timestamp).toLocaleTimeString(),
            fullDate: new Date(item.timestamp).toLocaleString(),
          };
        }
        trafficHistoryMap[timeKey][item.username] = parseFloat((item.total_traffic / uDivisor).toFixed(2));
      }
      const processedUserTraffic = Object.values(trafficHistoryMap)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

      // --- Process User Sessions ---
      const rawUserSessions = userSessionsRes.data;
      const sessionUsersSet = new Set(rawUserSessions.map(item => item.username));
      const sessionUsersList = Array.from(sessionUsersSet).sort((a, b) => a.localeCompare(b));

      const sessionHistoryMap = {};
      rawUserSessions.forEach(item => {
        const timeKey = new Date(item.timestamp).getTime();
        if (!sessionHistoryMap[timeKey]) {
          sessionHistoryMap[timeKey] = {
            timestamp: item.timestamp,
            time: new Date(item.timestamp).toLocaleTimeString(),
            fullDate: new Date(item.timestamp).toLocaleString(),
          };
        }
        sessionHistoryMap[timeKey][item.username] = item.active_sessions;
      });
      const processedUserSessions = Object.values(sessionHistoryMap)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));


      setServerSessions(sessionsData);
      setRealTimeActiveSessions(currentSessionsRes.data.active_sessions);
      setServerTraffic(trafficData);
      
      setUserTrafficStats(processedUserTraffic);
      setAvailableTrafficUsers(trafficUsersList);
      
      setUserSessionStats(processedUserSessions);
      setAvailableSessionUsers(sessionUsersList);
      
      setUserStatusCounts(statusRes.data);
      setLogCounts(logsRes.data);
      
      setError(null);
    } catch (err) {
      console.error('Error fetching stats:', err);
      setError('Failed to load statistics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, [timeRange, userFilter, customStartDate, customEndDate]);

  const toggleStatusVisibility = (name) => {
    const newHidden = new Set(hiddenStatuses);
    if (newHidden.has(name)) {
      newHidden.delete(name);
    } else {
      newHidden.add(name);
    }
    setHiddenStatuses(newHidden);
  };
  
  const toggleLevelVisibility = (name) => {
    const newHidden = new Set(hiddenLevels);
    if (newHidden.has(name)) {
      newHidden.delete(name);
    } else {
      newHidden.add(name);
    }
    setHiddenLevels(newHidden);
  };

  // Filter pie data based on hidden statuses
  const pieData = userStatusCounts.map(item => ({
    ...item,
    value: hiddenStatuses.has(item.name) ? 0 : item.value
  }));
  
  // Filter log data based on hidden levels
  const logPieData = logCounts.map(item => ({
    ...item,
    value: hiddenLevels.has(item.name) ? 0 : item.value
  }));

  const totalUserStatusCount = pieData.reduce((sum, item) => sum + item.value, 0);
  const totalLogCount = logPieData.reduce((sum, item) => sum + item.value, 0);

  const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];

  const StatCard = ({ title, value, icon: Icon, color = "sky" }) => (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm relative overflow-hidden">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-slate-400 text-sm font-medium">{title}</p>
          <h3 className="text-2xl font-bold text-white mt-1">{value}</h3>
        </div>
        <div className={`p-3 bg-${color}-500/10 rounded-lg text-${color}-400`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header and Global Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">System Statistics</h1>
          <p className="text-slate-400 mt-1">Real-time monitoring and historical data</p>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap justify-end">
           {timeRange === 'custom' && (
             <div className="flex items-center gap-2">
               <input 
                 type="datetime-local" 
                 value={customStartDate}
                 onChange={(e) => setCustomStartDate(e.target.value)}
                 className="bg-slate-800 border-slate-700 text-slate-300 rounded-lg text-sm p-2.5 focus:ring-sky-500 focus:border-sky-500 outline-none"
               />
               <span className="text-slate-500">to</span>
               <input 
                 type="datetime-local" 
                 value={customEndDate}
                 onChange={(e) => setCustomEndDate(e.target.value)}
                 className="bg-slate-800 border-slate-700 text-slate-300 rounded-lg text-sm p-2.5 focus:ring-sky-500 focus:border-sky-500 outline-none"
               />
             </div>
           )}

           <select 
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="bg-slate-800 border-slate-700 text-slate-300 rounded-lg text-sm p-2.5 focus:ring-sky-500 focus:border-sky-500 outline-none"
          >
            <option value="1h">Last 1 Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="custom">Custom Range</option>
          </select>

          <button 
            onClick={fetchStats} 
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
            title="Refresh Data"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Current Active Sessions" 
          value={realTimeActiveSessions} 
          icon={Users} 
          color="sky"
        />
        <StatCard 
          title="Total Server Traffic" 
          value={serverTraffic.length > 0 ? formatBytes(serverTraffic[serverTraffic.length-1].total_traffic) : '0 B'} 
          icon={Activity} 
          color="emerald"
        />
         <StatCard 
          title="Upload (TX)" 
          value={serverTraffic.length > 0 ? formatBytes(serverTraffic[serverTraffic.length-1].total_tx) : '0 B'} 
          icon={ArrowUp} 
          color="blue"
        />
         <StatCard 
          title="Download (RX)" 
          value={serverTraffic.length > 0 ? formatBytes(serverTraffic[serverTraffic.length-1].total_rx) : '0 B'} 
          icon={ArrowDown} 
          color="indigo"
        />
      </div>

      {/* Server Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Sessions Chart */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm">
          <h3 className="text-lg font-semibold text-white mb-6">Active Sessions History</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={serverSessions}>
                <defs>
                  <linearGradient id="colorSessions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis 
                  dataKey="time" 
                  stroke="#94a3b8" 
                  fontSize={12} 
                  tickLine={false}
                  axisLine={false}
                  minTickGap={30}
                />
                <YAxis 
                  stroke="#94a3b8" 
                  fontSize={12} 
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="active_sessions" 
                  stroke="#0ea5e9" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorSessions)" 
                  name="Active Sessions"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Traffic Chart */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm">
          <h3 className="text-lg font-semibold text-white mb-6">Traffic History ({serverTrafficUnit})</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={serverTraffic}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis 
                  dataKey="time" 
                  stroke="#94a3b8" 
                  fontSize={12} 
                  tickLine={false}
                  axisLine={false}
                  minTickGap={30}
                />
                <YAxis 
                  stroke="#94a3b8" 
                  fontSize={12} 
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="rx" 
                  stroke="#10b981" 
                  strokeWidth={2} 
                  dot={false}
                  name="Download (RX)"
                />
                <Line 
                  type="monotone" 
                  dataKey="tx" 
                  stroke="#3b82f6" 
                  strokeWidth={2} 
                  dot={false}
                  name="Upload (TX)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* User Statistics Divider & Filter */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mt-8 border-t border-slate-700 pt-8">
        <h2 className="text-xl font-bold text-white">User Statistics</h2>
        
        <div className="relative">
          <input
            type="text"
            placeholder="Search users..."
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-sky-500 w-full sm:w-64"
          />
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
        </div>
      </div>

      {/* User Charts Section (Line Charts) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* User Active Sessions */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm overflow-hidden">
          <h3 className="text-lg font-semibold text-white mb-6">User Active Sessions</h3>
          {userSessionStats.length === 0 ? (
            <div className="text-center text-slate-500 py-12">
              No user sessions found for the selected period.
            </div>
          ) : (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={userSessionStats}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis 
                    dataKey="time" 
                    stroke="#94a3b8" 
                    fontSize={12} 
                    tickLine={false}
                    axisLine={false}
                    minTickGap={30}
                  />
                  <YAxis 
                    stroke="#94a3b8" 
                    fontSize={12} 
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Legend />
                  {availableSessionUsers.map((user, index) => (
                    <Line
                      key={user}
                      type="monotone"
                      dataKey={user}
                      stroke={COLORS[index % COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                      name={user}
                      connectNulls={true}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* User Traffic Statistics */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm overflow-hidden">
          <h3 className="text-lg font-semibold text-white mb-6">User Traffic Statistics ({userTrafficUnit})</h3>
          {userTrafficStats.length === 0 ? (
            <div className="text-center text-slate-500 py-12">
              No user statistics found for the selected period.
            </div>
          ) : (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={userTrafficStats}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis 
                    dataKey="time" 
                    stroke="#94a3b8" 
                    fontSize={12} 
                    tickLine={false}
                    axisLine={false}
                    minTickGap={30}
                  />
                  <YAxis 
                    stroke="#94a3b8" 
                    fontSize={12} 
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Legend />
                  {availableTrafficUsers.map((user, index) => (
                    <Line
                      key={user}
                      type="monotone"
                      dataKey={user}
                      stroke={COLORS[index % COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                      name={user}
                      connectNulls={true}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Distribution Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* User Status Distribution Section */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm overflow-hidden h-full flex flex-col">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center">
            <PieIcon className="w-5 h-5 mr-2 text-sky-400" />
            User Status Distribution
          </h3>
          <div className="flex flex-col items-center justify-center gap-6 flex-grow">
            
            {/* Pie Chart */}
            <div className="h-[250px] w-full">
               <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                      ))}
                    </Pie>
                    <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="fill-white text-xl font-bold">
                      {totalUserStatusCount}
                    </text>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                      itemStyle={{ color: '#f8fafc' }}
                    />
                  </PieChart>
               </ResponsiveContainer>
            </div>

            {/* Status Count Table (Filter) */}
            <div className="w-full">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-400">
                  <thead className="bg-slate-700/50 text-xs uppercase font-medium text-slate-300">
                    <tr>
                      <th className="px-4 py-3 rounded-tl-lg">Status</th>
                      <th className="px-4 py-3 rounded-tr-lg text-right">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {userStatusCounts.map((item) => (
                      <tr 
                        key={item.name} 
                        onClick={() => toggleStatusVisibility(item.name)}
                        className={`hover:bg-slate-700/30 cursor-pointer transition-colors ${hiddenStatuses.has(item.name) ? 'opacity-40 grayscale' : ''}`}
                      >
                        <td className="px-4 py-3 font-medium text-white flex items-center gap-2">
                          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></span>
                          {item.name}
                        </td>
                        <td className="px-4 py-3 text-right">{item.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 text-xs text-slate-500 text-center">
                Click row to toggle chart segment
              </div>
            </div>
            
          </div>
        </div>
        
        {/* Server Logs Distribution Section */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm overflow-hidden h-full flex flex-col">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center">
            <FileText className="w-5 h-5 mr-2 text-sky-400" />
            Server Logs Distribution
          </h3>
          <div className="flex flex-col items-center justify-center gap-6 flex-grow">
            
            {/* Pie Chart */}
            <div className="h-[250px] w-full">
               <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={logPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {logPieData.map((entry, index) => (
                        <Cell key={`log-cell-${index}`} fill={entry.color} stroke="none" />
                      ))}
                    </Pie>
                    <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="fill-white text-xl font-bold">
                      {totalLogCount}
                    </text>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                      itemStyle={{ color: '#f8fafc' }}
                    />
                  </PieChart>
               </ResponsiveContainer>
            </div>

            {/* Log Count Table (Filter) */}
            <div className="w-full">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-400">
                  <thead className="bg-slate-700/50 text-xs uppercase font-medium text-slate-300">
                    <tr>
                      <th className="px-4 py-3 rounded-tl-lg">Severity</th>
                      <th className="px-4 py-3 rounded-tr-lg text-right">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {logCounts.map((item) => (
                      <tr 
                        key={item.name} 
                        onClick={() => toggleLevelVisibility(item.name)}
                        className={`hover:bg-slate-700/30 cursor-pointer transition-colors ${hiddenLevels.has(item.name) ? 'opacity-40 grayscale' : ''}`}
                      >
                        <td className="px-4 py-3 font-medium text-white flex items-center gap-2">
                          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></span>
                          {item.name}
                        </td>
                        <td className="px-4 py-3 text-right">{item.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 text-xs text-slate-500 text-center">
                Click row to toggle chart segment
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
