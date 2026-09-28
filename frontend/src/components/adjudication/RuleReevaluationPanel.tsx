import React, { useState } from 'react';
import {
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  FileText,
  Activity,
} from 'lucide-react';
import { RuleReevaluationResponse } from '../../types/api';
import { Link } from 'react-router-dom';

interface RuleReevaluationPanelProps {
  inspectionId: string;
  onReevaluate: (justification?: string) => Promise<RuleReevaluationResponse>;
  reevaluationResult: RuleReevaluationResponse | null;
  hasUncommittedAdjudications: boolean;
}

export const RuleReevaluationPanel: React.FC<RuleReevaluationPanelProps> = ({
  inspectionId,
  onReevaluate,
  reevaluationResult,
  hasUncommittedAdjudications,
}) => {
  const [justification, setJustification] = useState(
    'Inspector adjudicated OCR tokens and observations'
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunReevaluation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await onReevaluate(justification.trim() || undefined);
    } catch (err: any) {
      setError(err?.message || 'Failed to re-evaluate rules.');
    } finally {
      setIsLoading(false);
    }
  };

  const getVerdictBadge = (verdict: string) => {
    let color = 'var(--text-main)';
    let bg = 'var(--bg-surface-secondary)';
    let border = 'var(--border-muted)';

    if (verdict === 'PASS') {
      color = 'var(--verdict-pass)';
      bg = 'var(--verdict-pass-bg)';
      border = 'var(--verdict-pass-border)';
    } else if (verdict === 'FAIL') {
      color = 'var(--verdict-fail)';
      bg = 'var(--verdict-fail-bg)';
      border = 'var(--verdict-fail-border)';
    } else if (verdict === 'REVIEW') {
      color = 'var(--verdict-review)';
      bg = 'var(--verdict-review-bg)';
      border = 'var(--verdict-review-border)';
    }

    return (
      <span
        style={{
          padding: '4px 10px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '12px',
          fontWeight: 700,
          color,
          backgroundColor: bg,
          border: `1px solid ${border}`,
          letterSpacing: '0.04em',
        }}
      >
        {verdict}
      </span>
    );
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        backgroundColor: 'var(--bg-surface-primary)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        padding: '16px',
      }}
    >
      {/* Header and Trigger Strip */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <h3
            style={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-main)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Activity size={16} style={{ color: 'var(--accent-cyan)' }} />
            Authoritative Rule Re-Evaluation
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Trigger backend deterministic Legal Metrology rules against active adjudicated declarations.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            id="btn-trigger-reevaluation"
            onClick={handleRunReevaluation}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--accent-cyan)',
              color: '#000',
              border: 'none',
              fontSize: '13px',
              fontWeight: 700,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.6 : 1,
              boxShadow: 'var(--shadow-cyan-glow)',
            }}
          >
            <RotateCcw size={15} style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
            {isLoading ? 'Re-Evaluating Rules...' : 'Re-Evaluate Compliance'}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--verdict-fail-bg)',
            border: '1px solid var(--verdict-fail-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            color: 'var(--verdict-fail)',
          }}
        >
          {error}
        </div>
      )}

      {/* Comparison results when re-evaluation has run */}
      {reevaluationResult && (
        <div
          id="reevaluation-results-block"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            backgroundColor: 'var(--bg-canvas)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-muted)',
            padding: '16px',
          }}
        >
          {/* Verdict Delta Banner */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              backgroundColor: 'var(--bg-surface-secondary)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Overall Verdict:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {getVerdictBadge(reevaluationResult.previous_verdict)}
                <ArrowRight size={14} style={{ color: 'var(--text-muted)' }} />
                {getVerdictBadge(reevaluationResult.new_verdict)}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <span
                style={{
                  fontSize: '12px',
                  color: reevaluationResult.verdict_changed ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  fontWeight: 600,
                }}
              >
                {reevaluationResult.verdict_changed ? 'Verdict Updated' : 'Verdict Unchanged'}
              </span>

              <div style={{ display: 'flex', gap: '8px' }}>
                <Link
                  to={`/inspections/${inspectionId}/evidence`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--primary-glow)',
                    color: 'var(--primary-500)',
                    textDecoration: 'none',
                  }}
                >
                  <ShieldCheck size={12} /> View Evidence Graph
                </Link>

                <Link
                  to={`/inspections/${inspectionId}/reports`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(6, 182, 212, 0.15)',
                    color: 'var(--accent-cyan)',
                    textDecoration: 'none',
                  }}
                >
                  <FileText size={12} /> Dossier Reports
                </Link>
              </div>
            </div>
          </div>

          {/* Rule Outcomes Delta Table */}
          {reevaluationResult.changes && reevaluationResult.changes.length > 0 && (
            <div>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  color: 'var(--text-muted)',
                  display: 'block',
                  marginBottom: '8px',
                }}
              >
                Rule-Level Outcome Changes & Citations
              </span>

              <div
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'hidden',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr
                      style={{
                        backgroundColor: 'var(--bg-surface-secondary)',
                        color: 'var(--text-secondary)',
                        textAlign: 'left',
                        fontSize: '11px',
                      }}
                    >
                      <th style={{ padding: '8px 12px' }}>Rule Code</th>
                      <th style={{ padding: '8px 12px' }}>Rule Title</th>
                      <th style={{ padding: '8px 12px' }}>Statutory Citation</th>
                      <th style={{ padding: '8px 12px' }}>Previous</th>
                      <th style={{ padding: '8px 12px' }}>New Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reevaluationResult.changes.map((ch, idx) => (
                      <tr
                        key={ch.rule_code || idx}
                        style={{
                          borderTop: '1px solid var(--border-subtle)',
                          backgroundColor: ch.changed ? 'rgba(6, 182, 212, 0.04)' : 'transparent',
                        }}
                      >
                        <td
                          style={{
                            padding: '8px 12px',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-main)',
                            fontWeight: 600,
                          }}
                        >
                          {ch.rule_code}
                        </td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>
                          {ch.title}
                        </td>
                        <td
                          style={{
                            padding: '8px 12px',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-muted)',
                            fontSize: '11px',
                          }}
                        >
                          {ch.statutory_citation}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          {ch.previous_outcome ? getVerdictBadge(ch.previous_outcome) : '-'}
                        </td>
                        <td style={{ padding: '8px 12px' }}>{getVerdictBadge(ch.new_outcome)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
