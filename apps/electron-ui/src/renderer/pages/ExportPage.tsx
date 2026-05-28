import React, { useState } from 'react';

interface Artifact {
  artifact_type: string;
  vault_relative_path: string;
  file_path: string;
}

interface ExportStatus {
  session_id: string;
  session_status: string;
  artifacts: Artifact[];
}

const API = (window as any).API_BASE_URL ?? 'http://localhost:8000/api/v1';

interface ExportPageProps {
  sessionId: string;
}

export const ExportPage: React.FC<ExportPageProps> = ({ sessionId }) => {
  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportMode, setExportMode] = useState<'overwrite' | 'versioned' | 'merge'>('overwrite');

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    setExportStatus(null);

    try {
      // Optionally update export mode before triggering
      await fetch(`${API}/config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ export_mode: exportMode }),
      });

      const res = await fetch(`${API}/sessions/${sessionId}/export`, { method: 'POST' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }

      // Poll for status
      const statusRes = await fetch(`${API}/sessions/${sessionId}/export/status`);
      const status: ExportStatus = await statusRes.json();
      setExportStatus(status);
    } catch (e) {
      setError(String(e));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 600 }}>
      <h2>Export to Vault</h2>

      {error && (
        <div style={{ color: 'red', marginBottom: 12, padding: '8px 12px', background: '#fff3f3', borderRadius: 4 }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: 20 }}>
        <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>Export Mode</label>
        <select
          value={exportMode}
          onChange={e => setExportMode(e.target.value as typeof exportMode)}
          style={{ padding: '6px 12px', border: '1px solid #ccc', borderRadius: 4 }}
          disabled={exporting}
        >
          <option value="overwrite">Overwrite — replace existing note</option>
          <option value="versioned">Versioned — keep prior exports</option>
          <option value="merge">Merge — append to existing note</option>
        </select>
      </div>

      <button
        onClick={handleExport}
        disabled={exporting || !!exportStatus}
        style={{
          padding: '10px 24px',
          background: exportStatus ? '#4caf50' : '#1976d2',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          cursor: exporting || exportStatus ? 'not-allowed' : 'pointer',
          fontSize: 15,
        }}
      >
        {exporting ? 'Exporting…' : exportStatus ? '✓ Exported' : 'Export Now'}
      </button>

      {exportStatus && (
        <div style={{ marginTop: 24 }}>
          <h3 style={{ marginBottom: 8 }}>Export Complete</h3>
          <p style={{ color: '#666', marginBottom: 12 }}>
            Status: <strong>{exportStatus.session_status}</strong>
          </p>
          <div>
            <strong>Files written:</strong>
            <ul style={{ marginTop: 6, paddingLeft: 20 }}>
              {exportStatus.artifacts.map((a, i) => (
                <li key={i} style={{ marginBottom: 4, fontFamily: 'monospace', fontSize: 13 }}>
                  <span style={{ color: '#666', fontSize: 11 }}>[{a.artifact_type}]</span>{' '}
                  {a.vault_relative_path}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExportPage;
