import React, { useEffect } from 'react';

interface CoverLetterModalProps {
  isOpen: boolean;
  onClose: () => void;
  content: string;
}

export default function CoverLetterModal({ isOpen, onClose, content }: CoverLetterModalProps) {
  const [copied, setCopied] = React.useState(false);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        backgroundColor: 'rgba(22, 33, 62, 0.5)',
        backdropFilter: 'blur(8px)',
        animation: 'fadeIn 0.2s var(--ease-out)'
      }}
      onClick={onClose}
    >
      <div 
        className="glass-card animate-fade-in-up"
        style={{
          width: '100%',
          maxWidth: '800px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--bg-secondary)',
          boxShadow: 'var(--shadow-modal)'
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ 
          padding: '24px', 
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <h2 style={{ fontSize: '1.25rem', color: 'var(--text-primary)' }}>Tailored Cover Letter</h2>
          <button 
            onClick={onClose}
            className="btn-ghost"
            style={{ padding: '8px', borderRadius: '50%' }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div style={{ 
          padding: '32px', 
          overflowY: 'auto',
          flex: 1,
          fontFamily: 'var(--font-serif)',
          fontSize: '1.1rem',
          lineHeight: '1.8',
          color: 'var(--text-primary)',
          whiteSpace: 'pre-wrap'
        }}>
          {content}
        </div>

        <div style={{ 
          padding: '24px', 
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '16px'
        }}>
          {copied && <span style={{ color: 'var(--clover-700)', fontSize: '0.875rem' }}>Copied</span>}
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
          <button 
            className="btn btn-primary"
            onClick={() => {
              navigator.clipboard.writeText(content);
              setCopied(true);
              setTimeout(() => setCopied(false), 1400);
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
              <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
            </svg>
            Copy Letter
          </button>
        </div>
      </div>
    </div>
  );
}
