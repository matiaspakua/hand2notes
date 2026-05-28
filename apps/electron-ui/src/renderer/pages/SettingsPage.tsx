import React, { useEffect, useState } from 'react';

interface VaultConfig {
  vault_root: string | null;
  folder_template: string;
  export_mode: 'overwrite' | 'versioned' | 'merge';
  vlm_runtime: 'ollama' | 'llamacpp';
  vlm_model: string;
  confidence_threshold: number;
}

interface VaultValidation {
  valid: boolean;
  reason?: string;
  md_file_count?: number;
}

const API = (window as any).API_BASE_URL ?? 'http://localhost:8000/api/v1';

async function fetchConfig(): Promise<VaultConfig> {
  const res = await fetch(`${API}/config`);
  return res.json();
}

async function patchConfig(patch: Partial<VaultConfig>): Promise<VaultConfig> {
  const res = await fetch(`${API}/config`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  return res.json();
}

async function validateVault(): Promise<VaultValidation> {
  const res = await fetch(`${API}/config/vault/validate`);
  return res.json();
}

export const SettingsPage: React.FC = () => {
  const [config, setConfig] = useState<VaultConfig | null>(null);
  const [validation, setValidation] = useState<VaultValidation | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig().then(setConfig).catch(e => setError(String(e)));
  }, []);

  const handleVaultRootPick = async () => {
    const paths = await (window as any).electronAPI?.openFileDialog?.({ properties: ['openDirectory'] });
    if (paths && paths.length > 0 && config) {
      const updated = await patchConfig({ vault_root: paths[0] });
      setConfig(updated);
      const v = await validateVault();
      setValidation(v);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await patchConfig({
        folder_template: config.folder_template,
        export_mode: config.export_mode,
        vlm_runtime: config.vlm_runtime,
        vlm_model: config.vlm_model,
        confidence_threshold: config.confidence_threshold,
      });
      setConfig(updated);
      const v = await validateVault();
      setValidation(v);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  if (!config) return <div style={{ padding: 24 }}>Loading settings…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 600 }}>
      <h2>Settings</h2>

      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Vault Root</label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={config.vault_root ?? ''}
            readOnly
            style={{ flex: 1, padding: '6px 10px', border: '1px solid #ccc', borderRadius: 4 }}
          />
          <button onClick={handleVaultRootPick} style={{ padding: '6px 14px' }}>Browse…</button>
        </div>
        {validation && (
          <div style={{ marginTop: 4, fontSize: 12, color: validation.valid ? '#4caf50' : '#f44336' }}>
            {validation.valid
              ? `✓ Valid vault (${validation.md_file_count ?? 0} notes)`
              : `✗ ${validation.reason}`}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Folder Template</label>
        <input
          type="text"
          value={config.folder_template}
          onChange={e => setConfig({ ...config, folder_template: e.target.value })}
          style={{ width: '100%', padding: '6px 10px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
        />
        <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
          Variables: {'{{notebook}}'}, {'{{date}}'}, {'{{topic}}'}, {'{{name}}'}
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Export Mode</label>
        <select
          value={config.export_mode}
          onChange={e => setConfig({ ...config, export_mode: e.target.value as VaultConfig['export_mode'] })}
          style={{ padding: '6px 10px', border: '1px solid #ccc', borderRadius: 4 }}
        >
          <option value="overwrite">Overwrite</option>
          <option value="versioned">Versioned</option>
          <option value="merge">Merge</option>
        </select>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>VLM Runtime</label>
        <select
          value={config.vlm_runtime}
          onChange={e => setConfig({ ...config, vlm_runtime: e.target.value as VaultConfig['vlm_runtime'] })}
          style={{ padding: '6px 10px', border: '1px solid #ccc', borderRadius: 4 }}
        >
          <option value="ollama">Ollama</option>
          <option value="llamacpp">llama.cpp</option>
        </select>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>
          {config.vlm_runtime === 'ollama' ? 'Ollama Model' : 'Model Path (GGUF)'}
        </label>
        <input
          type="text"
          value={config.vlm_model}
          onChange={e => setConfig({ ...config, vlm_model: e.target.value })}
          style={{ width: '100%', padding: '6px 10px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>
          Confidence Threshold ({config.confidence_threshold})
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={config.confidence_threshold}
          onChange={e => setConfig({ ...config, confidence_threshold: parseFloat(e.target.value) })}
          style={{ width: '100%' }}
        />
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        style={{ padding: '8px 20px', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 4, cursor: saving ? 'not-allowed' : 'pointer' }}
      >
        {saving ? 'Saving…' : 'Save Settings'}
      </button>
    </div>
  );
};

export default SettingsPage;
