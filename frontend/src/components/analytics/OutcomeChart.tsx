import React from 'react';
import { OutcomeDistribution } from '../../types/api';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';

interface OutcomeChartProps {
  distribution: OutcomeDistribution | null;
  loading?: boolean;
}

export const OutcomeChart: React.FC<OutcomeChartProps> = ({ distribution, loading }) => {
  if (loading || !distribution) {
    return (
      <div className="card" style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading outcome breakdown...</div>
      </div>
    );
  }

  const { pass_count, review_count, fail_count, uncertain_count, total_evaluations } = distribution;
  const total = total_evaluations || 1;

  const passPct = Math.round((pass_count / total) * 100);
  const reviewPct = Math.round((review_count / total) * 100);
  const failPct = Math.round((fail_count / total) * 100);
  const uncertainPct = Math.round((uncertain_count / total) * 100);

  // SVG Donut calculation
  const radius = 64;
  const circumference = 2 * Math.PI * radius;

  const strokeDash = (pct: number) => `${(pct / 100) * circumference} ${circumference}`;

  // Offsets
  const passOffset = 0;
  const reviewOffset = -((passPct / 100) * circumference);
  const failOffset = -(((passPct + reviewPct) / 100) * circumference);
  const uncertainOffset = -(((passPct + reviewPct + failPct) / 100) * circumference);

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Rule Evaluation Outcome Distribution</h3>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {total_evaluations} evaluations
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 24, flex: 1 }}>
        {/* Donut Chart */}
        <div style={{ position: 'relative', width: 148, height: 148, flexShrink: 0 }}>
          <svg width="148" height="148" viewBox="0 0 160 160" style={{ transform: 'rotate(-90deg)' }}>
            <circle
              cx="80"
              cy="80"
              r={radius}
              fill="transparent"
              stroke="var(--bg-surface-tertiary)"
              strokeWidth="20"
            />
            {total_evaluations > 0 && (
              <>
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  fill="transparent"
                  stroke="var(--verdict-pass)"
                  strokeWidth="20"
                  strokeDasharray={strokeDash(passPct)}
                  strokeDashoffset={passOffset}
                  strokeLinecap="round"
                />
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  fill="transparent"
                  stroke="var(--verdict-review)"
                  strokeWidth="20"
                  strokeDasharray={strokeDash(reviewPct)}
                  strokeDashoffset={reviewOffset}
                  strokeLinecap="round"
                />
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  fill="transparent"
                  stroke="var(--verdict-fail)"
                  strokeWidth="20"
                  strokeDasharray={strokeDash(failPct)}
                  strokeDashoffset={failOffset}
                  strokeLinecap="round"
                />
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  fill="transparent"
                  stroke="var(--verdict-indeterminate)"
                  strokeWidth="20"
                  strokeDasharray={strokeDash(uncertainPct)}
                  strokeDashoffset={uncertainOffset}
                  strokeLinecap="round"
                />
              </>
            )}
          </svg>
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}>
            <span style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
              {passPct}%
            </span>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Compliant
            </span>
          </div>
        </div>

        {/* Legend & Breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--verdict-pass)' }} />
              <span style={{ color: 'var(--text-main)' }}>PASS</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{pass_count}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: 34, textAlign: 'right' }}>{passPct}%</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--verdict-review)' }} />
              <span style={{ color: 'var(--text-main)' }}>REVIEW</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{review_count}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: 34, textAlign: 'right' }}>{reviewPct}%</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--verdict-fail)' }} />
              <span style={{ color: 'var(--text-main)' }}>FAIL</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{fail_count}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: 34, textAlign: 'right' }}>{failPct}%</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--verdict-indeterminate)' }} />
              <span style={{ color: 'var(--text-main)' }}>UNCERTAIN</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{uncertain_count}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: 34, textAlign: 'right' }}>{uncertainPct}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
