import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { Plus, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import Modal from '../components/Modal';

const formatTraffic = (bytes) => {
  if (bytes === null || bytes === undefined) return '0.00 MB';
  
  const mb = 1024 * 1024;
  const gb = 1024 * 1024 * 1024;
  const tb = 1024 * 1024 * 1024 * 1024;

  if (bytes < gb) {
    return `${(bytes / mb).toFixed(2)} MB`;
  } else if (bytes < tb) {
    return `${(bytes / gb).toFixed(2)} GB`;
  } else {
    return `${(bytes / tb).toFixed(2)} TB`;
  }
};

const Users = () => {
  const [users, setUsers] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    max_concurrent_sessions: 1,
    is_active: true,
    allowed_traffic: '',
    expiration_date: '',
    use_cleartext_password: false,
    notes: ''
  });
  const [error, setError] = useState('');

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1); // Reset to page 1 on search change
    }, 500);

    return () => {
      clearTimeout(handler);
    };
  }, [searchQuery]);

  useEffect(() => {
    fetchUsers();
  }, [page, pageSize, debouncedSearch]);

  const fetchUsers = async () => {
    try {
      const params = {
        page: page,
        page_size: pageSize,
      };
      if (debouncedSearch) {
        params.search = debouncedSearch;
      }

      const response = await api.get('/radius-users/', { params });
      setUsers(response.data.results);
      setTotalCount(response.data.count);
    } catch (error) {
      console.error(error);
    }
  };

  const openAddModal = () => {
    setEditingUser(null);
    setFormData({
      username: '',
      password: '',
      max_concurrent_sessions: 1,
      is_active: true,
      allowed_traffic: '',
      expiration_date: '',
      use_cleartext_password: false,
      notes: ''
    });
    setIsAddModalOpen(true);
  };

  const openEditModal = (user) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      password: '', // Password is not retrieved for editing
      max_concurrent_sessions: user.max_concurrent_sessions,
      is_active: user.is_active,
      allowed_traffic: user.allowed_traffic ? (user.allowed_traffic / (1024 * 1024)).toString() : '',
      expiration_date: user.expiration_date ? user.expiration_date.substring(0, 16) : '', // Format for datetime-local
      use_cleartext_password: false,
      notes: user.notes || ''
    });
    setIsAddModalOpen(true);
  };

  const handleDelete = async () => {
    if (!editingUser) return;
    
    if (globalThis.confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      try {
        await api.delete(`/radius-users/${editingUser.id}/`);
        setIsAddModalOpen(false);
        fetchUsers();
      } catch (error) {
        console.error(error);
        setError('Failed to delete user. Please try again.');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const userPayload = {
        ...formData,
        allowed_traffic: formData.allowed_traffic ? Number.parseInt(formData.allowed_traffic) * 1024 * 1024 : null,
        expiration_date: formData.expiration_date || null
      };

      if (!userPayload.password) {
        delete userPayload.password;
        delete userPayload.use_cleartext_password;
      }

      if (editingUser) {
        await api.patch(`/radius-users/${editingUser.id}/`, userPayload);
      } else {
        await api.post('/radius-users/', userPayload);
      }

      setIsAddModalOpen(false);
      fetchUsers();
    } catch (error) {
      console.error(error);
      setError(`Failed to ${editingUser ? 'update' : 'create'} user. Please try again.`);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'OK':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Expired':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'OverQuota':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
      default:
        return 'bg-slate-500/10 text-slate-300 border-slate-500/20';
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <h2 className="text-2xl font-bold text-slate-100">Radius Users</h2>
        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-grow sm:flex-grow-0">
             <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-300" />
             </div>
             <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-md leading-5 bg-slate-900 text-slate-200 placeholder-slate-400 focus:outline-none focus:bg-slate-900 focus:ring-1 focus:ring-sky-500 focus:border-sky-500 sm:text-sm"
                placeholder="Search users..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
             />
          </div>
          <button 
              onClick={openAddModal}
              className="flex items-center px-4 py-2 bg-sky-500 text-white rounded-md hover:bg-sky-400 shadow-sm shadow-sky-500/30 transition-all font-medium whitespace-nowrap"
          >
              <Plus className="w-5 h-5 mr-2" />
              Add User
          </button>
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

      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title={editingUser ? "Edit User" : "Add New User"}
      >
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            {error && (
              <div className="p-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded">
                {error}
              </div>
            )}
            
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-1">Username</label>
              <input
                id="username"
                type="text"
                name="username"
                required
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.username}
                onChange={handleChange}
              />
            </div>

            <div>
              <label htmlFor="notes" className="block text-sm font-medium text-slate-300 mb-1">Description (Notes)</label>
              <textarea
                id="notes"
                name="notes"
                rows="2"
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.notes}
                onChange={handleChange}
                placeholder="Optional description or notes"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">
                Password {editingUser && <span className="text-slate-400 font-normal">(leave blank to keep current)</span>}
              </label>
              <input
                id="password"
                type="password"
                name="password"
                required={!editingUser}
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.password}
                onChange={handleChange}
              />
            </div>

            <div className="flex items-center">
              <input
                id="use_cleartext_password"
                name="use_cleartext_password"
                type="checkbox"
                className="h-4 w-4 text-sky-500 focus:ring-sky-500 border-slate-700 rounded bg-slate-900"
                checked={formData.use_cleartext_password}
                onChange={handleChange}
              />
              <label htmlFor="use_cleartext_password" className="ml-2 block text-sm text-slate-200">
                Store as Clear Text Password
              </label>
            </div>

            <div>
              <label htmlFor="allowed_traffic" className="block text-sm font-medium text-slate-300 mb-1">Quota (MB)</label>
              <input
                id="allowed_traffic"
                type="number"
                name="allowed_traffic"
                min="0"
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.allowed_traffic}
                onChange={handleChange}
                placeholder="Unlimited if empty"
              />
            </div>

            <div>
              <label htmlFor="expiration_date" className="block text-sm font-medium text-slate-300 mb-1">Expiration Date</label>
              <input
                id="expiration_date"
                type="datetime-local"
                name="expiration_date"
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2 [color-scheme:dark]"
                value={formData.expiration_date}
                onChange={handleChange}
              />
            </div>

            <div>
              <label htmlFor="max_concurrent_sessions" className="block text-sm font-medium text-slate-300 mb-1">Max Concurrent Sessions</label>
              <input
                id="max_concurrent_sessions"
                type="number"
                name="max_concurrent_sessions"
                min="1"
                required
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.max_concurrent_sessions}
                onChange={handleChange}
              />
            </div>

            <div className="flex items-center">
              <input
                id="is_active"
                name="is_active"
                type="checkbox"
                className="h-4 w-4 text-sky-500 focus:ring-sky-500 border-slate-700 rounded bg-slate-900"
                checked={formData.is_active}
                onChange={handleChange}
              />
              <label htmlFor="is_active" className="ml-2 block text-sm text-slate-200">
                Active
              </label>
            </div>

            <div className="mt-5 sm:mt-6 space-y-3">
              <div className="sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                <button
                  type="submit"
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-sky-500 text-base font-medium text-white hover:bg-sky-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 sm:col-start-2 sm:text-sm"
                >
                  {editingUser ? "Update" : "Create"}
                </button>
                <button
                  type="button"
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-slate-600 shadow-sm px-4 py-2 bg-slate-800 text-base font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                  onClick={() => setIsAddModalOpen(false)}
                >
                  Cancel
                </button>
              </div>
              
              {editingUser && (
                 <button
                   type="button"
                   onClick={handleDelete}
                   className="w-full inline-flex justify-center rounded-md border border-red-500/30 shadow-sm px-4 py-2 bg-red-500/10 text-base font-medium text-red-400 hover:bg-red-500/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:text-sm transition-colors"
                 >
                   Delete User
                 </button>
              )}
            </div>
          </div>
        </form>
      </Modal>
      <div className="bg-slate-800 shadow-lg border border-slate-700 sm:rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-slate-700/50">
          <thead className="bg-slate-900/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Username</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Description</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Sessions</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Traffic</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Password</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50 bg-slate-800">
            {users.length > 0 ? (
                users.map((user) => (
                <tr key={user.id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-200">
                      <button 
                        onClick={() => openEditModal(user)}
                        className="text-sky-400 hover:text-sky-300 hover:underline focus:outline-none"
                      >
                        {user.username}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 max-w-xs truncate" title={user.notes}>
                        {user.notes || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full border ${getStatusColor(user.status)}`}>
                            {user.status === 'OK' ? 'Active' : user.status}
                        </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{user.current_sessions} / {user.max_concurrent_sessions}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                      {formatTraffic(user.total_traffic)} / {user.allowed_traffic ? formatTraffic(user.allowed_traffic) : 'Unlimited'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">
                      {user.password_display}
                    </td>
                </tr>
                ))
            ) : (
                <tr>
                    <td colSpan="6" className="px-6 py-8 text-center text-slate-400 italic">
                        No users found.
                    </td>
                </tr>
            )}
          </tbody>
        </table>
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
              {/* Simplified Page Numbers Logic - Just current page context */}
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
export default Users;
