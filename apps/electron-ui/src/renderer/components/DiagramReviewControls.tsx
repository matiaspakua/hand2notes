import React from 'react';
import { DiagramPreview, DiagramDecision } from './DiagramPreview';

interface DiagramReviewControlsProps {
  sessionId: string;
  pageId: string;
  diagramPreviews: Array<{
    block_id: string;
    diagram_type: string;
    crop_path: string | null;
    generated_source_path: string | null;
    reconstruction_confidence: number;
    review_decision: DiagramDecision;
  }>;
  apiBase?: string;
  onDecisionChange?: (blockId: string, decision: DiagramDecision) => void;
}

const DEFAULT_API = (window as any).API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const DiagramReviewControls: React.FC<DiagramReviewControlsProps> = ({
  sessionId,
  pageId,
  diagramPreviews,
  apiBase = DEFAULT_API,
  onDecisionChange,
}) => {
  const handleDecision = async (blockId: string, decision: DiagramDecision) => {
    try {
      await fetch(`${apiBase}/sessions/${sessionId}/pages/${pageId}/diagrams/${blockId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_decision: decision }),
      });
      onDecisionChange?.(blockId, decision);
    } catch (e) {
      console.error('Failed to update diagram decision:', e);
    }
  };

  if (diagramPreviews.length === 0) return null;

  return (
    <div>
      <h4 style={{ marginBottom: 8 }}>Diagrams ({diagramPreviews.length})</h4>
      {diagramPreviews.map(dp => (
        <DiagramPreview
          key={dp.block_id}
          blockId={dp.block_id}
          diagramType={dp.diagram_type}
          cropPath={dp.crop_path}
          generatedSourcePath={dp.generated_source_path}
          reconstructionConfidence={dp.reconstruction_confidence}
          reviewDecision={dp.review_decision}
          onDecision={handleDecision}
        />
      ))}
    </div>
  );
};

export default DiagramReviewControls;
