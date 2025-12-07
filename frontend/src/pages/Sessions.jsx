import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { Search, ChevronLeft, ChevronRight, RefreshCw, Clock, ArrowDownCircle, ArrowUpCircle } from 'lucide-react';

const formatBytes = (bytes) => {
  if (bytes === 0 || bytes === null || bytes === undefined) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDuration = (seconds) => {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds < 60) return `${seconds}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
};

const Sessions = () => {
  const [sessions, setSessions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('active'); // '' = all, 'active', 'stopped'
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
    fetchSessions();
  }, [page, pageSize, debouncedSearch, statusFilter]);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const params = {
        page: page,
        page_size: pageSize,
      };
      if (debouncedSearch) {
        params.search = debouncedSearch;
      }
      if (statusFilter) {
        params.status = statusFilter;
      }

      const response = await api.get('/sessions/', { params });
      setSessions(response.data.results);
      setTotalCount(response.data.count);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'stopped':
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-slate-100">Sessions</h2>
            <button 
                onClick={fetchSessions}
                className="p-2 bg-slate-800 text-slate-400 rounded-full hover:text-sky-400 hover:bg-slate-700 transition-colors"
                title="Refresh"
            >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <select
                value={statusFilter}
                onChange={(e) => {
                    setStatusFilter(e.target.value);
                    setPage(1);
                }}
                className="block pl-3 pr-8 py-2 border border-slate-700 rounded-md bg-slate-900 text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500 sm:text-sm"
            >
                <option value="">All</option>
                <option value="active">Active</option>
                <option value="stopped">Stopped</option>
            </select>

            <div className="relative flex-grow sm:flex-grow-0">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-slate-300" />
                </div>
                <input
                    type="text"
                    className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-md leading-5 bg-slate-900 text-slate-200 placeholder-slate-400 focus:outline-none focus:bg-slate-900 focus:ring-1 focus:ring-sky-500 focus:border-sky-500 sm:text-sm"
                    placeholder="Search sessions..."
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
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Username</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">IP Address</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Duration</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Traffic</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Started</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">NAS</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50 bg-slate-800">
                {sessions.length > 0 ? (
                    sessions.map((session) => (
                    <tr key={session.id} className="hover:bg-slate-700/30 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full border ${getStatusColor(session.status)}`}>
                                {session.status}
                            </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-200">
                            {session.username}
                            <div className="text-xs text-slate-200 italic font-normal" title={session.session_id}>
                                {session.session_id}
                            </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                            <div>{session.framed_ip_address || '-'}</div>
                            <div className="text-xs text-slate-300 italic">{session.calling_station_id || '-'}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                            <div className="flex items-center gap-1">
                                <Clock className="w-3 h-3 text-slate-500" />
                                {formatDuration(session.session_time)}
                            </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                            <div className="flex flex-col gap-0.5">
                                <span className="flex items-center gap-1 text-xs text-emerald-400/80">
                                    <ArrowDownCircle className="w-3 h-3" />
                                    {formatBytes(session.input_octets)}
                                </span>
                                <span className="flex items-center gap-1 text-xs text-sky-400/80">
                                    <ArrowUpCircle className="w-3 h-3" />
                                    {formatBytes(session.output_octets)}
                                </span>
                            </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                            {formatDate(session.start_time)}
                            {session.status === 'stopped' && session.stop_time && (
                                <div className="text-xs text-slate-300 italic" title="Stopped">
                                    Ended: {formatDate(session.stop_time)}
                                </div>
                            )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                            <div>{session.nas_identifier || '-'}</div>
                            <div className="text-xs text-slate-300 italic">{session.nas_ip_address}</div>
                        </td>
                    </tr>
                    ))
                ) : (
                    <tr>
                        <td colSpan="7" className="px-6 py-8 text-center text-slate-400 italic">
                            No sessions found.
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
export default Sessions;
