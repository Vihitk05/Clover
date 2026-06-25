import React, { useEffect, useState } from 'react';

interface AtsScoreBarProps {
  scoreBefore: number;
  scoreAfter: number;
}

export default function AtsScoreBar({ scoreBefore, scoreAfter }: AtsScoreBarProps) {
  const [animatedBefore, setAnimatedBefore] = useState(0);
  const [animatedAfter, setAnimatedAfter] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedBefore(scoreBefore);
      setAnimatedAfter(scoreAfter);
    }, 300);
    return () => clearTimeout(timer);
  }, [scoreBefore, scoreAfter]);

  const getBarColor = (score: number) => {
    if (score >= 80) return 'var(--clover-400)';
    if (score >= 60) return '#fbbf24';
    return '#f87171';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Before */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.875rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>Original resume readiness</span>
          <span style={{ fontWeight: 600, color: getBarColor(scoreBefore) }}>{scoreBefore}%</span>
        </div>
        <div style={{ height: '8px', background: 'var(--bg-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
          <div 
            style={{ 
              height: '100%', 
              background: getBarColor(scoreBefore),
              width: `${animatedBefore}%`,
              transition: 'width 1s var(--ease-out)',
              opacity: 0.6
            }} 
          />
        </div>
      </div>

      {/* After */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.875rem' }}>
          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Optimized readiness</span>
          <span style={{ fontWeight: 800, color: getBarColor(scoreAfter) }}>{scoreAfter}%</span>
        </div>
        <div style={{ height: '12px', background: 'var(--bg-elevated)', borderRadius: '6px', overflow: 'hidden', position: 'relative' }}>
          <div 
            style={{ 
              height: '100%', 
              background: `linear-gradient(90deg, ${getBarColor(scoreAfter)}, var(--clover-300))`,
              width: `${animatedAfter}%`,
              transition: 'width 1.5s var(--ease-spring)',
              boxShadow: 'var(--glow-sm)'
            }} 
          />
          {scoreAfter > scoreBefore && (
            <div 
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: `${scoreBefore}%`,
                width: '2px',
                background: 'rgba(255,255,255,0.5)',
                boxShadow: '0 0 4px rgba(255,255,255,0.8)'
              }}
            />
          )}
        </div>
        <p style={{ marginTop: '8px', fontSize: '0.75rem', color: 'var(--clover-400)', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="m12 19-7-7 7-7" transform="rotate(90 12 12)" />
          </svg>
          +{scoreAfter - scoreBefore}% improvement
        </p>
      </div>
    </div>
  );
}
