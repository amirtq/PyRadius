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
    <div className="flex h-screen bg-slate-900 text-slate-200">
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <button 
          type="button"
          className="fixed inset-0 z-40 bg-slate-900/80 backdrop-blur-sm md:hidden w-full h-full cursor-default" 
          onClick={() => setIsMobileMenuOpen(false)}
          aria-label="Close mobile menu"
        ></button>
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 transform transition-transform duration-300 md:relative md:translate-x-0 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex justify-between items-center p-6">
          <h1 className="text-2xl font-bold text-sky-400 tracking-tight">PyRadius</h1>
          <button className="md:hidden" onClick={() => setIsMobileMenuOpen(false)}>
            <X className="w-6 h-6 text-slate-400" />
          </button>
        </div>
        <nav className="mt-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              onClick={() => setIsMobileMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center px-6 py-3 transition-colors ${
                  isActive 
                    ? 'bg-slate-800/50 text-sky-400 border-r-2 border-sky-400' 
                    : 'text-slate-400 hover:bg-slate-800/30 hover:text-slate-200'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon className={`w-5 h-5 mr-3 ${isActive ? 'text-sky-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                  {item.name}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 w-64 p-4 border-t border-slate-800 bg-slate-900">
           <button
            onClick={handleLogout}
            className="flex items-center px-4 py-2 text-sm font-medium text-red-400 rounded-md hover:bg-slate-800 w-full transition-colors"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-900">
        {/* Mobile Header */}
        <header className="bg-slate-900 border-b border-slate-800 md:hidden z-10">
            <div className="px-4 py-4 flex justify-between items-center">
                <button onClick={() => setIsMobileMenuOpen(true)} className="text-slate-400 hover:text-white focus:outline-none">
                    <Menu className="w-6 h-6" />
                </button>
                <div className="text-lg font-semibold text-sky-400">PyRadius</div>
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
