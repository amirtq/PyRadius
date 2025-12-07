import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { Plus, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import Modal from '../components/Modal';

const Nas = () => {
  const [nasClients, setNasClients] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [formData, setFormData] = useState({
    identifier: '',
    ip_address: '',
    shared_secret: '',
    auth_port: 1812,
    acct_port: 1813,
    description: '',
    is_active: true
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
    fetchNasClients();
  }, [page, pageSize, debouncedSearch]);

  const fetchNasClients = async () => {
    try {
      const params = {
        page: page,
        page_size: pageSize,
      };
      if (debouncedSearch) {
        params.search = debouncedSearch;
      }

      const response = await api.get('/nas/', { params });
      setNasClients(response.data.results);
      setTotalCount(response.data.count);
    } catch (error) {
      console.error(error);
    }
  };

  const openAddModal = () => {
    setEditingClient(null);
    setFormData({
      identifier: '',
      ip_address: '',
      shared_secret: '',
      auth_port: 1812,
      acct_port: 1813,
      description: '',
      is_active: true
    });
    setError('');
    setIsAddModalOpen(true);
  };

  const openEditModal = (client) => {
    setEditingClient(client);
    setFormData({
      identifier: client.identifier,
      ip_address: client.ip_address,
      shared_secret: client.shared_secret,
      auth_port: client.auth_port,
      acct_port: client.acct_port,
      description: client.description || '',
      is_active: client.is_active
    });
    setError('');
    setIsAddModalOpen(true);
  };

  const handleDelete = async () => {
    if (!editingClient) return;
    
    if (window.confirm('Are you sure you want to delete this NAS client? This action cannot be undone.')) {
      try {
        await api.delete(`/nas/${editingClient.id}/`);
        setIsAddModalOpen(false);
        fetchNasClients();
      } catch (error) {
        console.error(error);
        setError('Failed to delete NAS client. Please try again.');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (editingClient) {
        await api.patch(`/nas/${editingClient.id}/`, formData);
      } else {
        await api.post('/nas/', formData);
      }

      setIsAddModalOpen(false);
      fetchNasClients();
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.detail || 
                      (typeof error.response?.data === 'object' ? JSON.stringify(error.response.data) : 'Failed to save NAS client.');
      setError(errorMsg);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <h2 className="text-2xl font-bold text-slate-100">NAS Clients</h2>
        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-grow sm:flex-grow-0">
             <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-300" />
             </div>
             <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-md leading-5 bg-slate-900 text-slate-200 placeholder-slate-400 focus:outline-none focus:bg-slate-900 focus:ring-1 focus:ring-sky-500 focus:border-sky-500 sm:text-sm"
                placeholder="Search NAS..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
             />
          </div>
          <button 
              onClick={openAddModal}
              className="flex items-center px-4 py-2 bg-sky-500 text-white rounded-md hover:bg-sky-400 shadow-sm shadow-sky-500/30 transition-all font-medium whitespace-nowrap"
          >
              <Plus className="w-5 h-5 mr-2" />
              Add NAS
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
        title={editingClient ? "Edit NAS Client" : "Add NAS Client"}
      >
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            {error && (
              <div className="p-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded break-words">
                {error}
              </div>
            )}
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="identifier" className="block text-sm font-medium text-slate-300 mb-1">Identifier</label>
                <input
                  id="identifier"
                  type="text"
                  name="identifier"
                  required
                  className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                  value={formData.identifier}
                  onChange={handleChange}
                  placeholder="e.g. router-01"
                />
              </div>

              <div>
                <label htmlFor="ip_address" className="block text-sm font-medium text-slate-300 mb-1">IP Address</label>
                <input
                  id="ip_address"
                  type="text"
                  name="ip_address"
                  required
                  className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                  value={formData.ip_address}
                  onChange={handleChange}
                  placeholder="e.g. 192.168.1.1"
                />
              </div>
            </div>

            <div>
              <label htmlFor="shared_secret" className="block text-sm font-medium text-slate-300 mb-1">Shared Secret</label>
              <input
                id="shared_secret"
                type="text"
                name="shared_secret"
                required
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.shared_secret}
                onChange={handleChange}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="auth_port" className="block text-sm font-medium text-slate-300 mb-1">Auth Port</label>
                <input
                  id="auth_port"
                  type="number"
                  name="auth_port"
                  required
                  className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                  value={formData.auth_port}
                  onChange={handleChange}
                />
              </div>

              <div>
                <label htmlFor="acct_port" className="block text-sm font-medium text-slate-300 mb-1">Acct Port</label>
                <input
                  id="acct_port"
                  type="number"
                  name="acct_port"
                  required
                  className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                  value={formData.acct_port}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-slate-300 mb-1">Description</label>
              <textarea
                id="description"
                name="description"
                rows="2"
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.description}
                onChange={handleChange}
                placeholder="Optional description"
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
                  {editingClient ? "Update" : "Create"}
                </button>
                <button
                  type="button"
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-slate-600 shadow-sm px-4 py-2 bg-slate-800 text-base font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                  onClick={() => setIsAddModalOpen(false)}
                >
                  Cancel
                </button>
              </div>
              
              {editingClient && (
                 <button
                   type="button"
                   onClick={handleDelete}
                   className="w-full inline-flex justify-center rounded-md border border-red-500/30 shadow-sm px-4 py-2 bg-red-500/10 text-base font-medium text-red-400 hover:bg-red-500/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:text-sm transition-colors"
                 >
                   Delete NAS Client
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
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Identifier</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">IP Address</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Ports (Auth/Acct)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50 bg-slate-800">
            {nasClients.length > 0 ? (
                nasClients.map((client) => (
                <tr key={client.id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-200">
                      <button 
                        onClick={() => openEditModal(client)}
                        className="text-sky-400 hover:text-sky-300 hover:underline focus:outline-none"
                      >
                        {client.identifier}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                        {client.ip_address}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                        {client.auth_port} / {client.acct_port}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full border ${
                            client.is_active 
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                            : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                        }`}>
                            {client.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300 max-w-xs truncate" title={client.description}>
                        {client.description || '-'}
                    </td>
                </tr>
                ))
            ) : (
                <tr>
                    <td colSpan="5" className="px-6 py-8 text-center text-slate-400 italic">
                        No NAS clients found.
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
export default Nas;
