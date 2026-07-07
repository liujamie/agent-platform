import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import WorkflowBuilder from './pages/WorkflowBuilder';
import TraceDetail from './pages/TraceDetail';
import './style.css';

function Layout() {
  return (
    <div className="app-layout">
      <nav className="nav">
        <div className="nav-title">Agent Platform</div>
        <div className="nav-links">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/workflow">Workflow</NavLink>
          <NavLink to="/trace">Traces</NavLink>
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/workflow" element={<WorkflowBuilder />} />
          <Route path="/trace" element={<TraceDetail />} />
        </Routes>
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/*" element={<Layout />} />
    </Routes>
  </BrowserRouter>
);
