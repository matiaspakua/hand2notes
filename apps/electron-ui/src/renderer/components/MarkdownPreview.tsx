import markdownIt from 'markdown-it';
import React, { useMemo } from 'react';

const md = markdownIt({ html: false, linkify: true, typographer: true });

interface MarkdownPreviewProps {
  content: string;
}

export const MarkdownPreview: React.FC<MarkdownPreviewProps> = ({ content }) => {
  const html = useMemo(() => md.render(content), [content]);

  return (
    <div
      className="markdown-preview"
      style={{
        padding: '12px 16px',
        background: '#fafafa',
        border: '1px solid #e0e0e0',
        borderRadius: 4,
        overflowY: 'auto',
        fontFamily: 'Georgia, serif',
        lineHeight: 1.6,
        fontSize: 14,
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

export default MarkdownPreview;
