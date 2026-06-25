import React from 'react';

interface GapRadarProps {
  scoreBreakdown: {
    semantic: number;
    skills: number;
    seniority: number;
    location: number;
    experience: number;
  };
}

export default function GapRadar({ scoreBreakdown }: GapRadarProps) {
  // SVG Radar Dimensions
  const size = 300;
  const center = size / 2;
  const radius = (size - 60) / 2; // Leave room for labels
  
  // Categories
  const categories = [
    { key: 'skills', label: 'Skills' },
    { key: 'semantic', label: 'Semantic Fit' },
    { key: 'seniority', label: 'Level' },
    { key: 'experience', label: 'Experience' },
    { key: 'location', label: 'Location' }
  ];

  const getCoordinates = (value: number, min: number, max: number, angle: number) => {
    // Normalize value to 0-1 range based on weight context
    const normalized = Math.max(0, Math.min(1, (value - min) / (max - min)));
    const r = normalized * radius;
    const x = center + r * Math.cos(angle - Math.PI / 2);
    const y = center + r * Math.sin(angle - Math.PI / 2);
    return { x, y };
  };

  // Background Grid (3 levels)
  const gridLevels = [0.33, 0.66, 1];
  
  // Calculate points for the actual score polygon
  const angleStep = (Math.PI * 2) / categories.length;
  
  const scorePoints = categories.map((cat, i) => {
    const angle = i * angleStep;
    const absValue = scoreBreakdown[cat.key as keyof typeof scoreBreakdown];
    const normalizedValue = Math.max(0, Math.min(1, absValue / 100));
    return getCoordinates(normalizedValue, 0, 1, angle);
  });

  const polygonPath = scorePoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';

  return (
    <div style={{ position: 'relative', width: size, height: size, margin: '0 auto' }}>
      <svg width={size} height={size} style={{ overflow: 'visible' }}>
        {/* Draw Web Lines */}
        {categories.map((_, i) => {
          const angle = i * angleStep;
          const { x, y } = getCoordinates(1, 0, 1, angle);
          return (
            <line 
              key={`web-${i}`}
              x1={center} y1={center} 
              x2={x} y2={y} 
              stroke="var(--border-subtle)" 
              strokeWidth="1" 
              strokeDasharray="4 4"
            />
          );
        })}

        {/* Draw Grid Polygons */}
        {gridLevels.map((level, levelIdx) => {
          const points = categories.map((_, i) => {
            const angle = i * angleStep;
            return getCoordinates(level, 0, 1, angle);
          });
          const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';
          return (
            <path
              key={`grid-${levelIdx}`}
              d={path}
              fill="none"
              stroke="var(--border-subtle)"
              strokeWidth="1"
            />
          );
        })}

        {/* Draw Score Polygon */}
        <path
          d={polygonPath}
          fill="rgba(16, 185, 129, 0.2)"
          stroke="var(--clover-400)"
          strokeWidth="2"
          strokeLinejoin="round"
          className="animate-fade-in"
          style={{ transformOrigin: 'center', animationDuration: '1s' }}
        />

        {/* Draw Score Points */}
        {scorePoints.map((p, i) => (
          <circle
            key={`point-${i}`}
            cx={p.x}
            cy={p.y}
            r="4"
            fill="var(--clover-400)"
            stroke="var(--bg-card)"
            strokeWidth="2"
            className="animate-fade-in delay-300"
          />
        ))}

        {/* Draw Labels */}
        {categories.map((cat, i) => {
          const angle = i * angleStep;
          // Push labels out extra 20px
          const { x, y } = getCoordinates(1.2, 0, 1, angle);
          return (
            <text
              key={`label-${i}`}
              x={x}
              y={y}
              fill="var(--text-secondary)"
              fontSize="12"
              fontWeight="600"
              textAnchor="middle"
              alignmentBaseline="middle"
            >
              {cat.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
