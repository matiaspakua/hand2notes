import React from 'react';
import { ConfidenceBadge } from './ConfidenceBadge';

interface TablePreviewProps {
  blockId: string;
  headers: string[];
  rows: string[][];
  caption?: string | null;
  reconstructionConfidence: number;
  fallbackType?: 'csv' | 'image' | null;
  fallbackPath?: string | null;
}

export const TablePreview: React.FC<TablePreviewProps> = ({
  blockId: _blockId,
  headers,
  rows,
  caption,
  reconstructionConfidence,
  fallbackType,
  fallbackPath,
}) => {
  const canRenderTable = reconstructionConfidence >= 0.5 && (headers.length > 0 || rows.length > 0);

  return (
    <div style={{ border: '1px solid #e0e0e0', borderRadius: 4, padding: 10, marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>Table</span>
        <ConfidenceBadge confidence={reconstructionConfidence} reviewFlag={reconstructionConfidence < 0.5} />
        {fallbackType && (
          <span style={{ fontSize: 11, color: '#888' }}>({fallbackType} fallback)</span>
        )}
      </div>

      {caption && (
        <div style={{ fontSize: 12, color: '#555', marginBottom: 6, fontStyle: 'italic' }}>{caption}</div>
      )}

      {canRenderTable ? (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', fontSize: 13, minWidth: '100%' }}>
            {headers.length > 0 && (
              <thead>
                <tr>
                  {headers.map((h, i) => (
                    <th key={i} style={{ border: '1px solid #ccc', padding: '4px 8px', background: '#f5f5f5', textAlign: 'left' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{ border: '1px solid #ccc', padding: '4px 8px' }}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : fallbackPath ? (
        <div>
          {fallbackType === 'csv' ? (
            <a href={`file://${fallbackPath}`} style={{ fontSize: 13 }}>
              Download CSV fallback →
            </a>
          ) : (
            <img src={`file://${fallbackPath}`} alt="table crop" style={{ maxWidth: '100%', borderRadius: 4 }} />
          )}
        </div>
      ) : (
        <div style={{ color: '#999', fontSize: 13 }}>Table could not be reconstructed.</div>
      )}
    </div>
  );
};

export default TablePreview;
