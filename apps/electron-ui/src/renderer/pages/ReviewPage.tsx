import React, { useCallback, useEffect } from 'react';
import { BlockEditor } from '../components/BlockEditor';
import { DiagramReviewControls } from '../components/DiagramReviewControls';
import { MarkdownPreview } from '../components/MarkdownPreview';
import { useReviewStore } from '../stores/reviewStore';

const API = (window as any).API_BASE_URL ?? 'http://localhost:8000/api/v1';

interface ReviewPageProps {
  sessionId: string;
  pageId: string;
  totalPages?: number;
  onNext?: () => void;
  onExport?: () => void;
}

export const ReviewPage: React.FC<ReviewPageProps> = ({
  sessionId,
  pageId,
  totalPages: _totalPages = 1,
  onNext,
  onExport,
}) => {
  const {
    currentPageData,
    loading,
    error,
    loadPageReview,
    setDiagramDecision,
    isReviewComplete,
  } = useReviewStore();

  useEffect(() => {
    loadPageReview(API, sessionId, pageId);
  }, [sessionId, pageId]);

  const handleBlockSave = useCallback(async (blockId: string, correctedContent: string) => {
    await fetch(`${API}/sessions/${sessionId}/pages/${pageId}/blocks/${blockId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ corrected_content: correctedContent, review_flag: false }),
    });
    // Reload page data to get updated review_flag and markdown_preview
    await loadPageReview(API, sessionId, pageId);
  }, [sessionId, pageId]);

  const handleDiagramDecision = useCallback((blockId: string, decision: string) => {
    setDiagramDecision(blockId, decision);
  }, []);

  if (loading) return <div style={{ padding: 24 }}>Loading review…</div>;
  if (error) return <div style={{ padding: 24, color: 'red' }}>Error: {error}</div>;
  if (!currentPageData) return <div style={{ padding: 24 }}>No review data.</div>;

  const reviewDone = isReviewComplete();

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Left panel: original + preprocessed images */}
      <div style={{ width: '40%', padding: 16, overflowY: 'auto', borderRight: '1px solid #e0e0e0' }}>
        <h3 style={{ marginTop: 0 }}>Page {currentPageData.sequence}</h3>

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>ORIGINAL</div>
          <img
            src={currentPageData.source_url}
            alt="original"
            style={{ width: '100%', borderRadius: 4, border: '1px solid #e0e0e0' }}
          />
        </div>

        {currentPageData.preprocessed_url && (
          <div>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>PREPROCESSED</div>
            <img
              src={currentPageData.preprocessed_url}
              alt="preprocessed"
              style={{ width: '100%', borderRadius: 4, border: '1px solid #e0e0e0' }}
            />
          </div>
        )}
      </div>

      {/* Right panel: blocks, markdown preview, diagram controls */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {/* Text blocks */}
          <h4 style={{ marginTop: 0 }}>Text Blocks</h4>
          {currentPageData.blocks.map(block => (
            <BlockEditor
              key={block.block_id}
              blockId={block.block_id}
              blockType={block.block_type}
              content={block.content}
              correctedContent={block.corrected_content}
              confidence={block.confidence}
              reviewFlag={block.review_flag}
              onSave={handleBlockSave}
            />
          ))}

          {/* Diagram review controls */}
          {currentPageData.diagram_previews.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <DiagramReviewControls
                sessionId={sessionId}
                pageId={pageId}
                diagramPreviews={currentPageData.diagram_previews}
                apiBase={API}
                onDecisionChange={handleDiagramDecision}
              />
            </div>
          )}

          {/* Markdown preview */}
          <div style={{ marginTop: 16 }}>
            <h4>Markdown Preview</h4>
            <MarkdownPreview content={currentPageData.markdown_preview} />
          </div>
        </div>

        {/* Navigation bar */}
        <div style={{
          padding: '10px 16px',
          borderTop: '1px solid #e0e0e0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{ fontSize: 12, color: '#666' }}>
            Overall confidence: {Math.round(currentPageData.overall_confidence * 100)}%
            &nbsp;|&nbsp;Status: {currentPageData.review_status}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {onNext && (
              <button onClick={onNext} style={{ padding: '6px 16px' }}>
                Next Page →
              </button>
            )}
            {onExport && (
              <button
                onClick={onExport}
                disabled={!reviewDone}
                title={reviewDone ? undefined : 'Resolve all flagged blocks and diagram decisions first'}
                style={{
                  padding: '6px 16px',
                  background: reviewDone ? '#4caf50' : '#ccc',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 4,
                  cursor: reviewDone ? 'pointer' : 'not-allowed',
                }}
              >
                Export to Vault
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewPage;
