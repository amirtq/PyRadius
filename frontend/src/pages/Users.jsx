import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { Plus, Pencil } from 'lucide-react';
import Modal from '../components/Modal';

const Users = () => {
  const [users, setUsers] = useState([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    max_concurrent_sessions: 1,
    is_active: true,
    allowed_traffic: '',
    expiration_date: '',
    use_cleartext_password: false
  });
  const [error, setError] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/radius-users/');
      setUsers(response.data.results);
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
      use_cleartext_password: false
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
      use_cleartext_password: false
    });
    setIsAddModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const userPayload = {
        ...formData,
        allowed_traffic: formData.allowed_traffic ? parseInt(formData.allowed_traffic) * 1024 * 1024 : null,
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

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-slate-100">Radius Users</h2>
        <button 
            onClick={openAddModal}
            className="flex items-center px-4 py-2 bg-sky-500 text-white rounded-md hover:bg-sky-400 shadow-sm shadow-sky-500/30 transition-all font-medium"
        >
            <Plus className="w-5 h-5 mr-2" />
            Add User
        </button>
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
              <label className="block text-sm font-medium text-slate-400 mb-1">Username</label>
              <input
                type="text"
                name="username"
                required
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2"
                value={formData.username}
                onChange={handleChange}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">
                Password {editingUser && <span className="text-slate-500 font-normal">(leave blank to keep current)</span>}
              </label>
              <input
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
              <label htmlFor="use_cleartext_password" className="ml-2 block text-sm text-slate-300">
                Store as Clear Text Password
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Quota (MB)</label>
              <input
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
              <label className="block text-sm font-medium text-slate-400 mb-1">Expiration Date</label>
              <input
                type="datetime-local"
                name="expiration_date"
                className="block w-full rounded-md border-slate-700 bg-slate-900 text-slate-200 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm border p-2 [color-scheme:dark]"
                value={formData.expiration_date}
                onChange={handleChange}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Max Concurrent Sessions</label>
              <input
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
              <label htmlFor="is_active" className="ml-2 block text-sm text-slate-300">
                Active
              </label>
            </div>

            <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
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
          </div>
        </form>
      </Modal>
      <div className="bg-slate-800 shadow-lg border border-slate-700 sm:rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-slate-700/50">
          <thead className="bg-slate-900/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Username</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Sessions</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Traffic</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50 bg-slate-800">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-slate-700/30 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-200">{user.username}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full border ${
                        user.is_active 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                        : 'bg-red-500/10 text-red-400 border-red-500/20'
                    }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">{user.current_sessions} / {user.max_concurrent_sessions}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">{(user.total_traffic / 1024 / 1024).toFixed(2)} MB</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                  <button 
                    onClick={() => openEditModal(user)}
                    className="text-sky-400 hover:text-sky-300 transition-colors" 
                    title="Edit"
                  >
                    <Pencil className="w-5 h-5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
export default Users;
