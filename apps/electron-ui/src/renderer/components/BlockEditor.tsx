import React, { useState } from 'react';
import { ConfidenceBadge } from './ConfidenceBadge';

interface BlockEditorProps {
  blockId: string;
  blockType: string;
  content: string | null;
  correctedContent: string | null;
  confidence: number;
  reviewFlag: boolean;
  onSave: (blockId: string, correctedContent: string) => Promise<void>;
  visualSemantics?: {
    highlight_color?: string | null;
    is_underlined?: boolean;
    is_boxed?: boolean;
    is_circled?: boolean;
    callout_label?: string | null;
  };
}

export const BlockEditor: React.FC<BlockEditorProps> = ({
  blockId,
  blockType,
  content,
  correctedContent,
  confidence,
  reviewFlag,
  onSave,
  visualSemantics,
}) => {
  const [draft, setDraft] = useState(correctedContent ?? content ?? '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleBlur = async () => {
    const currentValue = correctedContent ?? content ?? '';
    if (draft === currentValue) return;
    setSaving(true);
    setSaved(false);
    try {
      await onSave(blockId, draft);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const semanticIcons = [];
  if (visualSemantics?.highlight_color) {
    semanticIcons.push(
      <span key="hl" title={`Highlight: ${visualSemantics.highlight_color}`}
        style={{ background: visualSemantics.highlight_color, width: 12, height: 12, display: 'inline-block', borderRadius: 2, border: '1px solid #ccc' }} />
    );
  }
  if (visualSemantics?.is_underlined) semanticIcons.push(<span key="ul" title="Underlined" style={{ fontSize: 12, color: '#1976d2' }}>U̲</span>);
  if (visualSemantics?.is_boxed) semanticIcons.push(<span key="box" title="Boxed" style={{ fontSize: 12, color: '#7b1fa2' }}>□</span>);
  if (visualSemantics?.is_circled) semanticIcons.push(<span key="circ" title="Circled" style={{ fontSize: 12, color: '#e65100' }}>○</span>);
  if (visualSemantics?.callout_label) semanticIcons.push(<span key="callout" title={`Callout: ${visualSemantics.callout_label}`} style={{ fontSize: 11, color: '#0288d1' }}>📌</span>);

  return (
    <div
      style={{
        border: reviewFlag ? '1px solid #ff9800' : '1px solid #e0e0e0',
        borderRadius: 4,
        padding: '8px 10px',
        marginBottom: 8,
        background: reviewFlag ? '#fff8e1' : '#fff',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: '#888', textTransform: 'uppercase' }}>{blockType}</span>
        <ConfidenceBadge confidence={confidence} reviewFlag={reviewFlag} />
        {semanticIcons.length > 0 && (
          <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>{semanticIcons}</span>
        )}
        {saving && <span style={{ fontSize: 11, color: '#888' }}>saving…</span>}
        {saved && <span style={{ fontSize: 11, color: '#4caf50' }}>✓ saved</span>}
      </div>
      <textarea
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={handleBlur}
        rows={Math.max(2, draft.split('\n').length)}
        style={{
          width: '100%',
          fontFamily: 'monospace',
          fontSize: 13,
          border: 'none',
          outline: 'none',
          resize: 'vertical',
          background: 'transparent',
          boxSizing: 'border-box',
        }}
      />
    </div>
  );
};

export default BlockEditor;
