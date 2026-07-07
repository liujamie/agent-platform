import React, { useState } from 'react';

const DEFAULT_WORKFLOW = JSON.stringify({
  nodes: [
    { id: "planner", type: "agent", config: { agent_type: "planner" } },
    { id: "search", type: "tool", config: { tool: "web_search" } },
    { id: "writer", type: "agent", config: { agent_type: "writer" } },
  ],
  edges: [
    { source: "planner", target: "search" },
    { source: "search", target: "writer" },
  ],
}, null, 2);

export default function WorkflowBuilder() {
  const [workflowJson, setWorkflowJson] = useState(DEFAULT_WORKFLOW);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);

  const runWorkflow = async () => {
    setRunning(true);
    setResult(null);
    try {
      const parsed = JSON.parse(workflowJson);
      const res = await fetch('/api/v1/workflow/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setRunning(false);
  };

  return (
    <div>
      <h1 className="page-title">Workflow Builder</h1>
      <p className="page-subtitle">编辑 DAG Workflow JSON 并执行</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card">
          <h3 style={{ marginBottom: '0.5rem' }}>Workflow Definition</h3>
          <textarea
            value={workflowJson}
            onChange={e => setWorkflowJson(e.target.value)}
            style={{ width: '100%', height: '300px', fontFamily: 'monospace', fontSize: '0.85rem', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
          />
          <button
            onClick={runWorkflow}
            disabled={running}
            style={{ marginTop: '0.5rem', padding: '0.5rem 1.5rem', background: '#1a1a2e', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            {running ? 'Running...' : 'Run Workflow'}
          </button>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: '0.5rem' }}>Result</h3>
          {!result && <p style={{ color: '#999' }}>Click "Run Workflow" to execute</p>}
          {result && (
            <pre style={{ background: '#f0f0f0', padding: '1rem', borderRadius: '4px', overflow: 'auto', maxHeight: '350px', fontSize: '0.85rem' }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
