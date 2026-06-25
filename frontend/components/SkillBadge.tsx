import React from 'react';

interface SkillBadgeProps {
  skill: string;
  variant?: 'neutral' | 'success' | 'danger';
}

export default function SkillBadge({ skill, variant = 'neutral' }: SkillBadgeProps) {
  let className = 'badge ';
  
  switch (variant) {
    case 'success':
      className += 'badge-success';
      break;
    case 'danger':
      className += 'badge-danger';
      break;
    default:
      className += 'badge-info';
      break;
  }

  return (
    <span className={className} style={{ whiteSpace: 'nowrap' }}>
      {skill}
    </span>
  );
}
