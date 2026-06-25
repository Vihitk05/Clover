import React from 'react';

interface ScoreRingProps {
  score: number;
  size?: number;
}

export default function ScoreRing({ score, size = 64 }: ScoreRingProps) {
  const radius = (size - 8) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;
  
  const getColor = (s: number) => {
    if (s >= 80) return 'var(--clover-400)';
    if (s >= 60) return '#fbbf24';
    return '#f87171';
  };

  const color = getColor(score);

  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="var(--bg-elevated)"
          strokeWidth="6"
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: offset,
            transition: 'stroke-dashoffset 1.5s var(--ease-spring)',
            animation: 'score-fill 1.5s var(--ease-spring)'
          }}
        />
      </svg>
      <div style={{ position: 'absolute', fontSize: size > 80 ? '1.5rem' : '0.875rem', fontWeight: 800, color: 'var(--text-primary)' }}>
        {Math.round(score)}%
      </div>
    </div>
  );
}
