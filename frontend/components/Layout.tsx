import React from 'react';
import Link from 'next/link';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <header style={{
        padding: '16px 0',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--bg-card)',
        backdropFilter: 'blur(14px)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
            <div className="brand-mark">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22v-7" />
                <path d="M12 8a4 4 0 1 0-4-4 4 4 0 0 0 4 4z" />
                <path d="M19 15a4 4 0 1 0-4-4 4 4 0 0 0 4 4z" />
                <path d="M5 15a4 4 0 1 0 4-4 4 4 0 0 0-4 4z" />
              </svg>
            </div>
            <span style={{ fontSize: '1.18rem', fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>
              Clover
            </span>
            <span className="badge badge-info" style={{ transform: 'translateY(1px)' }}>Live Beta</span>
          </Link>
          <nav style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <Link href="/" className="btn-ghost">Get Matched</Link>
            <Link href="/results" className="btn-ghost">Recommended Jobs</Link>
            <Link href="/applications" className="btn-ghost">Applications</Link>
            <Link href="/profile" className="btn-ghost">Profile</Link>
          </nav>
        </div>
      </header>

      <main style={{ flex: 1 }}>
        {children}
      </main>

      <footer style={{ 
        padding: '34px 0',
        borderTop: '1px solid var(--border-subtle)',
        marginTop: 'auto'
      }}>
        <div className="container" style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          <p>© {new Date().getFullYear()} Clover. Job intelligence for serious applicants.</p>
        </div>
      </footer>
    </div>
  );
}
