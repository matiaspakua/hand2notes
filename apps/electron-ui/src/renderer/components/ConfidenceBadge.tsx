import React from 'react';

interface ConfidenceBadgeProps {
  confidence: number;
  reviewFlag?: boolean;
}

function badgeColor(confidence: number): string {
  if (confidence >= 0.75) return '#4caf50';
  if (confidence >= 0.5) return '#ff9800';
  return '#f44336';
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence, reviewFlag }) => {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <span
        style={{
          background: badgeColor(confidence),
          color: '#fff',
          borderRadius: 4,
          padding: '1px 6px',
          fontSize: 11,
          fontWeight: 600,
        }}
      >
        {Math.round(confidence * 100)}%
      </span>
      {reviewFlag && (
        <span title="Flagged for review" style={{ fontSize: 14, color: '#ff9800' }}>⚠</span>
      )}
    </span>
  );
};

export default ConfidenceBadge;
