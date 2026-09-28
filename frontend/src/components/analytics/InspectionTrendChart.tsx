import React from 'react';
import { TrendDataPoint } from '../../types/api';

interface InspectionTrendChartProps {
  trend: TrendDataPoint[];
  loading?: boolean;
}

export const InspectionTrendChart: React.FC<InspectionTrendChartProps> = ({ trend, loading }) => {
  if (loading) {
    return (
      <div className="card" style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading historical trend...</div>
      </div>
    );
  }

  const data = trend.length > 0 ? trend : [
    { date: new Date().toISOString().split('T')[0], count: 0 }
  ];

  const maxCount = Math.max(...data.map((d) => d.count), 5);
  const width = 600;
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 30, left: 35 };

  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const points = data.map((d, i) => {
    const x = padding.left + (data.length > 1 ? (i / (data.length - 1)) * chartW : chartW / 2);
    const y = padding.top + chartH - (d.count / maxCount) * chartH;
    return { x, y, date: d.date, count: d.count };
  });

  const pathD = points.reduce((acc, pt, i) => {
    return i === 0 ? `M ${pt.x},${pt.y}` : `${acc} L ${pt.x},${pt.y}`;
  }, '');

  const areaD = points.length > 0
    ? `${pathD} L ${points[points.length - 1].x},${padding.top + chartH} L ${points[0].x},${padding.top + chartH} Z`
    : '';

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Inspection Volume Over Time</h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 2 }}>
            Factual daily inspection counts recorded across jurisdictions
          </p>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
          {data.reduce((acc, d) => acc + d.count, 0)} Total
        </span>
      </div>

      <div style={{ flex: 1, width: '100%', minHeight: 180 }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '100%', overflow: 'visible' }}>
          <defs>
            <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
            const yVal = padding.top + chartH * (1 - pct);
            const countLabel = Math.round(pct * maxCount);
            return (
              <g key={idx}>
                <line
                  x1={padding.left}
                  y1={yVal}
                  x2={width - padding.right}
                  y2={yVal}
                  stroke="var(--border-subtle)"
                  strokeDasharray="3 3"
                />
                <text
                  x={padding.left - 8}
                  y={yVal + 3}
                  textAnchor="end"
                  fill="var(--text-muted)"
                  fontSize="10"
                  fontFamily="var(--font-mono)"
                >
                  {countLabel}
                </text>
              </g>
            );
          })}

          {/* Area fill */}
          {areaD && <path d={areaD} fill="url(#trendGradient)" />}

          {/* Line stroke */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke="var(--accent-cyan)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Data points */}
          {points.map((pt, i) => (
            <g key={i}>
              <circle
                cx={pt.x}
                cy={pt.y}
                r="3.5"
                fill="var(--bg-surface-primary)"
                stroke="var(--accent-cyan)"
                strokeWidth="2"
              />
            </g>
          ))}

          {/* Date labels on X-axis (first, middle, last) */}
          {points.length > 0 && (
            <>
              <text
                x={points[0].x}
                y={height - 8}
                textAnchor="start"
                fill="var(--text-muted)"
                fontSize="10"
                fontFamily="var(--font-mono)"
              >
                {points[0].date}
              </text>
              {points.length > 2 && (
                <text
                  x={points[Math.floor(points.length / 2)].x}
                  y={height - 8}
                  textAnchor="middle"
                  fill="var(--text-muted)"
                  fontSize="10"
                  fontFamily="var(--font-mono)"
                >
                  {points[Math.floor(points.length / 2)].date}
                </text>
              )}
              <text
                x={points[points.length - 1].x}
                y={height - 8}
                textAnchor="end"
                fill="var(--text-muted)"
                fontSize="10"
                fontFamily="var(--font-mono)"
              >
                {points[points.length - 1].date}
              </text>
            </>
          )}
        </svg>
      </div>
    </div>
  );
};
