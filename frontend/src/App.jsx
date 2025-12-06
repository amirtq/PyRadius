import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Nas from './pages/Nas';
import Sessions from './pages/Sessions';
import Logs from './pages/Logs';
import Layout from './components/Layout';

const ProtectedRoute = () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/users" element={<Users />} />
            <Route path="/nas" element={<Nas />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/logs" element={<Logs />} />
          </Route>
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
