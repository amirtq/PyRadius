import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { Search, ChevronLeft, ChevronRight, RefreshCw, AlertCircle, Info, AlertTriangle, Bug } from 'lucide-react';

const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', fraction: undefined
  });
};

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState('INFO');
  const [loading, setLoading] = useState(false);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1); 
    }, 500);

    return () => {
      clearTimeout(handler);
    };
  }, [searchQuery]);

  useEffect(() => {
    fetchLogs();
  }, [page, pageSize, debouncedSearch, levelFilter]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = {
        page: page,
        page_size: pageSize,
      };
      if (debouncedSearch) {
        params.search = debouncedSearch;
      }
      if (levelFilter) {
        params.level = levelFilter;
      }

      const response = await api.get('/logs/', { params });
      setLogs(response.data.results);
      setTotalCount(response.data.count);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  const getLevelConfig = (level) => {
    const normalizedLevel = (level || '').toUpperCase();
    switch (normalizedLevel) {
      case 'ERROR':
      case 'CRITICAL':
        return {
          color: 'bg-red-500/10 text-red-400 border-red-500/20',
          icon: <AlertCircle className="w-3 h-3 mr-1" />
        };
      case 'WARNING':
      case 'WARN':
        return {
          color: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
          icon: <AlertTriangle className="w-3 h-3 mr-1" />
        };
      case 'INFO':
        return {
          color: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
          icon: <Info className="w-3 h-3 mr-1" />
        };
      case 'DEBUG':
        return {
          color: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
          icon: <Bug className="w-3 h-3 mr-1" />
        };
      default:
        return {
          color: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
          icon: null
        };
    }
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-slate-100">System Logs</h2>
            <button 
                onClick={fetchLogs}
                className="p-2 bg-slate-800 text-slate-400 rounded-full hover:text-sky-400 hover:bg-slate-700 transition-colors"
                title="Refresh"
            >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
        </div>
        
        <div className="flex gap-2 w-full sm:w-auto">
            <select
                value={levelFilter}
                onChange={(e) => {
                    setLevelFilter(e.target.value);
                    setPage(1);
                }}
                className="block pl-3 pr-8 py-2 border border-slate-700 rounded-md bg-slate-900 text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500 sm:text-sm"
            >
                <option value="">All Levels</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
                <option value="DEBUG">DEBUG</option>
                <option value="CRITICAL">CRITICAL</option>
            </select>

            <div className="relative flex-grow sm:flex-grow-0">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-slate-300" />
                </div>
                <input
                    type="text"
                    className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-md leading-5 bg-slate-900 text-slate-200 placeholder-slate-400 focus:outline-none focus:bg-slate-900 focus:ring-1 focus:ring-sky-500 focus:border-sky-500 sm:text-sm"
                    placeholder="Search logs..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between">
         <div className="flex items-center text-sm text-slate-300">
             <span className="mr-2">Show</span>
             <select
                value={pageSize}
                onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setPage(1);
                }}
                className="bg-slate-900 border border-slate-700 text-slate-200 rounded focus:ring-sky-500 focus:border-sky-500 p-1"
             >
                 <option value={10}>10</option>
                 <option value={20}>20</option>
                 <option value={50}>50</option>
                 <option value={100}>100</option>
             </select>
             <span className="ml-2">entries</span>
         </div>
      </div>

      <div className="bg-slate-800 shadow-lg border border-slate-700 sm:rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-700/50">
            <thead className="bg-slate-900/50">
                <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider w-40">Timestamp</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider w-24">Level</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider w-40">Source</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Message</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50 bg-slate-800">
                {logs.length > 0 ? (
                    logs.map((log) => {
                        const levelConfig = getLevelConfig(log.level);
                        return (
                        <tr key={log.id} className="hover:bg-slate-700/30 transition-colors">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono text-xs">
                                {formatDate(log.timestamp)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <span className={`px-2 py-0.5 inline-flex items-center text-xs leading-5 font-semibold rounded-full border ${levelConfig.color}`}>
                                    {levelConfig.icon}
                                    {log.level}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                                <span className="font-mono text-xs">{log.logger}</span>
                            </td>
                            <td className="px-6 py-4 text-sm text-slate-200 break-words max-w-xl">
                                {log.message}
                            </td>
                        </tr>
                        );
                    })
                ) : (
                    <tr>
                        <td colSpan="4" className="px-6 py-8 text-center text-slate-400 italic">
                            No logs found.
                        </td>
                    </tr>
                )}
            </tbody>
            </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-slate-300">
              Showing <span className="font-medium">{Math.min((page - 1) * pageSize + 1, totalCount)}</span> to <span className="font-medium">{Math.min(page * pageSize, totalCount)}</span> of <span className="font-medium">{totalCount}</span> results
          </div>
          <div className="flex bg-slate-800 rounded-md shadow-sm">
              <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-slate-700 bg-slate-800 text-sm font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                  <ChevronLeft className="h-5 w-5" />
              </button>
              <div className="relative inline-flex items-center px-4 py-2 border-t border-b border-slate-700 bg-slate-800 text-sm font-medium text-slate-200">
                  Page {page} of {totalPages || 1}
              </div>
              <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-slate-700 bg-slate-800 text-sm font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                  <ChevronRight className="h-5 w-5" />
              </button>
          </div>
      </div>
    </div>
  );
};
export default Logs;
