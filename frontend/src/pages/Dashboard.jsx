import React, { useState, useEffect } from 'react';

function MetricCard({ title, value, unit }) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <div className="card-value">{value}<span style={{ fontSize: '1rem', color: '#666', marginLeft: '0.25rem' }}>{unit}</span></div>
    </div>
  );
}

export default function Dashboard() {
  const [tools, setTools] = useState([]);

  useEffect(() => {
    fetch('/api/v1/tool/list')
      .then(r => r.json())
      .then(d => setTools(d.tools || []))
      .catch(() => setTools([]));
  }, []);

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">Agent Platform 运行状态概览</p>

      <div className="grid-4">
        <MetricCard title="已注册工具" value={tools.length} unit="" />
      </div>

      <div className="card">
        <h3 style={{ marginBottom: '1rem' }}>Available Tools</h3>
        {tools.length === 0 && <p style={{ color: '#999' }}>No tools registered</p>}
        {tools.map(t => (
          <div key={t.name} style={{ padding: '0.5rem 0', borderBottom: '1px solid #eee' }}>
            <strong>{t.name}</strong>
            <p style={{ color: '#666', fontSize: '0.85rem' }}>{t.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
