import { useState } from 'react';
import { api } from '../services/api';
import { useSessionStore } from '../stores/sessionStore';

interface Props {
  onSessionCreated: (sessionId: string) => void;
}

export function ImportPage({ onSessionCreated }: Props) {
  const [name, setName] = useState('');
  const [notebook, setNotebook] = useState('');
  const [topic, setTopic] = useState('');
  const [tags, setTags] = useState('');
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { addSession, addPages, setCurrentSession, setCurrentPages } = useSessionStore();

  const handlePickFiles = async () => {
    const paths = await window.h2n.openImageFiles();
    setSelectedPaths((prev) => [...prev, ...paths.filter((p) => !prev.includes(p))]);
  };

  const handleRemovePath = (path: string) => {
    setSelectedPaths((prev) => prev.filter((p) => p !== path));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !notebook.trim()) {
      setError('Name and notebook are required.');
      return;
    }
    if (selectedPaths.length === 0) {
      setError('Select at least one image.');
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      const session = await api.createSession({
        name: name.trim(),
        notebook: notebook.trim(),
        topic: topic.trim() || null,
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      addSession(session);
      setCurrentSession(session);

      const uploadedPages = await api.uploadPages(session.id, selectedPaths);
      addPages(uploadedPages);
      setCurrentPages(uploadedPages);

      onSessionCreated(session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filename = (path: string) => path.split('/').pop() ?? path;

  return (
    <main style={{ padding: '2rem', maxWidth: 600 }}>
      <h1>Import Notebook Pages</h1>

      <form onSubmit={handleSubmit}>
        <section style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1rem' }}>Session metadata</h2>
          <label style={labelStyle}>
            Name *
            <input style={inputStyle} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. CS101 Week 3" />
          </label>
          <label style={labelStyle}>
            Notebook *
            <input style={inputStyle} value={notebook} onChange={(e) => setNotebook(e.target.value)} placeholder="e.g. Computer Science" />
          </label>
          <label style={labelStyle}>
            Topic
            <input style={inputStyle} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Algorithms" />
          </label>
          <label style={labelStyle}>
            Tags (comma-separated)
            <input style={inputStyle} value={tags} onChange={(e) => setTags(e.target.value)} placeholder="e.g. lecture, algorithms" />
          </label>
        </section>

        <section style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1rem' }}>Page images</h2>
          <button type="button" onClick={handlePickFiles} style={secondaryBtnStyle}>
            + Add images
          </button>
          {selectedPaths.length > 0 && (
            <ul style={{ marginTop: '0.75rem', padding: 0, listStyle: 'none' }}>
              {selectedPaths.map((p, i) => (
                <li key={p} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <span style={{ color: '#666', minWidth: 24 }}>{i + 1}.</span>
                  <span style={{ flex: 1, fontSize: '0.875rem' }}>{filename(p)}</span>
                  <button type="button" onClick={() => handleRemovePath(p)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#cc0000' }}>✕</button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {error && <p style={{ color: '#cc0000', marginBottom: '1rem' }}>{error}</p>}

        <button type="submit" disabled={isSubmitting} style={primaryBtnStyle}>
          {isSubmitting ? 'Uploading…' : 'Start Processing →'}
        </button>
      </form>
    </main>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', marginBottom: '0.75rem', fontSize: '0.875rem', fontWeight: 500,
};
const inputStyle: React.CSSProperties = {
  marginTop: '0.25rem', padding: '0.4rem 0.6rem', borderRadius: 4, border: '1px solid #ccc', fontSize: '0.9rem',
};
const primaryBtnStyle: React.CSSProperties = {
  padding: '0.6rem 1.4rem', background: '#0066cc', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: '1rem',
};
const secondaryBtnStyle: React.CSSProperties = {
  padding: '0.4rem 1rem', background: '#eee', border: '1px solid #ccc', borderRadius: 6, cursor: 'pointer', fontSize: '0.875rem',
};
