import React from 'react';

export type DiagramDecision = 'pending' | 'approved' | 'rejected' | 'deferred';

export interface DiagramPreviewProps {
  blockId: string;
  diagramType: string;
  cropPath: string | null;
  generatedSourcePath: string | null;
  reconstructionConfidence: number;
  reviewDecision: DiagramDecision;
  onDecision: (blockId: string, decision: DiagramDecision) => void;
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.75) return '#4caf50';
  if (confidence >= 0.5) return '#ff9800';
  return '#f44336';
}

export const DiagramPreview: React.FC<DiagramPreviewProps> = ({
  blockId,
  diagramType,
  cropPath,
  reconstructionConfidence,
  reviewDecision,
  onDecision,
}) => {
  return (
    <div style={{ border: '1px solid #ccc', borderRadius: 6, padding: 12, marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{diagramType}</span>
        <span
          style={{
            background: confidenceColor(reconstructionConfidence),
            color: '#fff',
            borderRadius: 4,
            padding: '2px 7px',
            fontSize: 12,
          }}
        >
          {Math.round(reconstructionConfidence * 100)}%
        </span>
        {reviewDecision !== 'pending' && (
          <span style={{ fontSize: 12, color: '#888' }}>({reviewDecision})</span>
        )}
      </div>

      {cropPath && (
        <img
          src={`file://${cropPath}`}
          alt="diagram crop"
          style={{ maxWidth: '100%', maxHeight: 220, objectFit: 'contain', marginBottom: 8 }}
        />
      )}

      <div style={{ display: 'flex', gap: 6 }}>
        <button
          onClick={() => onDecision(blockId, 'approved')}
          disabled={reviewDecision === 'approved'}
          style={{ background: '#4caf50', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}
        >
          Approve
        </button>
        <button
          onClick={() => onDecision(blockId, 'rejected')}
          disabled={reviewDecision === 'rejected'}
          style={{ background: '#f44336', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}
        >
          Reject
        </button>
        <button
          onClick={() => onDecision(blockId, 'deferred')}
          disabled={reviewDecision === 'deferred'}
          style={{ background: '#9e9e9e', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}
        >
          Defer
        </button>
      </div>
    </div>
  );
};

export default DiagramPreview;
