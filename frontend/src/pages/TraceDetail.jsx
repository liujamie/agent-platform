import React, { useState } from 'react';

export default function TraceDetail() {
  const [traceId, setTraceId] = useState('');
  const [trace, setTrace] = useState(null);

  const fetchTrace = async () => {
    if (!traceId.trim()) return;
    try {
      const res = await fetch(`/api/v1/workflow/${traceId}/trace`);
      const data = await res.json();
      setTrace(data);
    } catch (e) {
      setTrace({ error: e.message });
    }
  };

  return (
    <div>
      <h1 className="page-title">Trace Detail</h1>
      <p className="page-subtitle">查看 Agent/Workflow 执行链路</p>

      <div className="card">
        <h3>Search Trace</h3>
        <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.5rem' }}>
          Enter a trace ID from a Workflow or Agent execution
        </p>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            value={traceId}
            onChange={e => setTraceId(e.target.value)}
            placeholder="Enter trace ID..."
            style={{ flex: 1, padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
          />
          <button
            onClick={fetchTrace}
            style={{ padding: '0.5rem 1.5rem', background: '#1a1a2e', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Search
          </button>
        </div>
      </div>

      {trace && (
        <div className="card">
          <h3>Trace Details</h3>
          <pre style={{ background: '#f0f0f0', padding: '1rem', borderRadius: '4px', overflow: 'auto', fontSize: '0.85rem' }}>
            {JSON.stringify(trace, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
