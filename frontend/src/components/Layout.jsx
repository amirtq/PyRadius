import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Server, Activity, FileText, LogOut, Menu, X } from 'lucide-react';

const Layout = () => {
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Users', path: '/users', icon: Users },
    { name: 'NAS Clients', path: '/nas', icon: Server },
    { name: 'Sessions', path: '/sessions', icon: Activity },
    { name: 'Logs', path: '/logs', icon: FileText },
  ];

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 md:hidden" onClick={() => setIsMobileMenuOpen(false)}></div>
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 md:relative md:translate-x-0 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex justify-between items-center p-6">
          <h1 className="text-2xl font-bold text-indigo-600">PyRadius</h1>
          <button className="md:hidden" onClick={() => setIsMobileMenuOpen(false)}>
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>
        <nav className="mt-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              onClick={() => setIsMobileMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center px-6 py-3 text-gray-700 transition-colors ${
                  isActive ? 'bg-indigo-50 text-indigo-600 border-r-4 border-indigo-600' : 'hover:bg-gray-50'
                }`
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 w-64 p-4 border-t border-gray-200 bg-white">
           <button
            onClick={handleLogout}
            className="flex items-center px-4 py-2 text-sm font-medium text-red-600 rounded-md hover:bg-red-50 w-full"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <header className="bg-white shadow md:hidden z-10">
            <div className="px-4 py-4 flex justify-between items-center">
                <button onClick={() => setIsMobileMenuOpen(true)} className="text-gray-500 focus:outline-none">
                    <Menu className="w-6 h-6" />
                </button>
                <div className="text-lg font-semibold text-gray-700">PyRadius</div>
                <div className="w-6"></div>
            </div>
        </header>

        <main className="flex-1 overflow-auto p-4 md:p-8">
            <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
