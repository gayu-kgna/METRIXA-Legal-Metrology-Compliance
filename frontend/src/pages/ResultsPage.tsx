import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Scale, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  MinusCircle, 
  Clock, 
  ArrowRight,
  FileText,
  GitBranch,
  ShieldCheck,
  Crosshair,
} from 'lucide-react';
import { getInspectionRuleEvaluations } from '../api/rules';
import { getInspection } from '../api/inspections';
import { RuleEvaluationRead, Inspection } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';

export const ResultsPage: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId: string }>();

  const [evaluations, setEvaluations] = useState<RuleEvaluationRead[]>([]);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState<string>('ALL');

  useEffect(() => {
    async function loadResults() {
      if (!inspectionId) return;
      try {
        setLoading(true);
        const [evals, insp] = await Promise.all([
          getInspectionRuleEvaluations(inspectionId),
          getInspection(inspectionId),
        ]);
        // If multiple runs exist, display evaluations from the latest run
        const latestRunId = evals[0]?.evaluation_run_id;
        const currentEvals = latestRunId ? evals.filter((e) => e.evaluation_run_id === latestRunId) : evals;
        setEvaluations(currentEvals);
        setInspection(insp);
      } catch (err: any) {
        setError(err.message || 'Failed to load statutory compliance evaluations');
      } finally {
        setLoading(false);
      }
    }
    loadResults();
  }, [inspectionId]);

  const passCount = evaluations.filter((e) => e.outcome === 'PASS').length;
  const failCount = evaluations.filter((e) => e.outcome === 'FAIL').length;
  const reviewCount = evaluations.filter((e) => e.outcome === 'REVIEW').length;
  const indeterminateCount = evaluations.filter((e) => e.outcome === 'INDETERMINATE').length;
  const naCount = evaluations.filter((e) => e.outcome === 'NOT_APPLICABLE').length;

  const filtered = evaluations.filter((e) => {
    if (outcomeFilter === 'ALL') return true;
    return e.outcome === outcomeFilter;
  });

  const canonicalVerdict = failCount > 0
    ? 'NON_COMPLIANT'
    : reviewCount > 0
    ? 'REVIEW_REQUIRED'
    : indeterminateCount > 0
    ? 'INDETERMINATE'
    : (passCount > 0 ? 'COMPLIANT' : 'INDETERMINATE');

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 60 }}>
        <Clock size={32} className="animate-spin" style={{ margin: '0 auto 16px', color: 'var(--accent-cyan)' }} />
        <div>Loading statutory rule evaluations...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Header Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4, flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: '1.75rem' }}>Statutory Compliance Results</h1>
            {inspection && (
              <span style={{
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                padding: '2px 8px',
                borderRadius: 4,
                backgroundColor: 'rgba(99, 102, 241, 0.2)',
                color: 'var(--accent-cyan)',
              }}>
                {inspection.inspection_number}
              </span>
            )}
            <StatusBadge status={canonicalVerdict} size="lg" />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Overall Statutory Verdict: <strong style={{ color: 'var(--text-main)', letterSpacing: '0.5px' }}>{canonicalVerdict}</strong>
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Authoritative deterministic findings under the Legal Metrology (Packaged Commodities) Rules, 2011
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Link to={`/inspections/${inspectionId}/adjudication`} className="btn btn-outline" style={{ gap: 6, borderColor: 'var(--accent-cyan)', color: 'var(--accent-cyan)' }}>
            <Crosshair size={16} />
            <span>Adjudicate Findings</span>
          </Link>
          <Link to={`/inspections/${inspectionId}/evidence`} className="btn btn-secondary" style={{ gap: 6 }}>
            <GitBranch size={16} />
            <span>Trace Evidence</span>
          </Link>
          <Link to={`/inspections/${inspectionId}/reports`} className="btn btn-primary" style={{ gap: 6 }}>
            <FileText size={16} />
            <span>View PDF Dossier</span>
          </Link>
        </div>
      </div>

      {/* Outcome Metric Cards */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <div
          className="card"
          style={{
            cursor: 'pointer',
            borderColor: outcomeFilter === 'PASS' ? 'var(--verdict-pass)' : undefined,
          }}
          onClick={() => setOutcomeFilter(outcomeFilter === 'PASS' ? 'ALL' : 'PASS')}
        >
          <div style={{ color: 'var(--verdict-pass)', fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <CheckCircle2 size={16} />
            <span>PASS (COMPLIANT)</span>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
            {passCount}
          </div>
        </div>

        <div
          className="card"
          style={{
            cursor: 'pointer',
            borderColor: outcomeFilter === 'FAIL' ? 'var(--verdict-fail)' : undefined,
          }}
          onClick={() => setOutcomeFilter(outcomeFilter === 'FAIL' ? 'ALL' : 'FAIL')}
        >
          <div style={{ color: 'var(--verdict-fail)', fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <XCircle size={16} />
            <span>FAIL (VIOLATION)</span>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
            {failCount}
          </div>
        </div>

        <div
          className="card"
          style={{
            cursor: 'pointer',
            borderColor: outcomeFilter === 'REVIEW' ? 'var(--verdict-review)' : undefined,
          }}
          onClick={() => setOutcomeFilter(outcomeFilter === 'REVIEW' ? 'ALL' : 'REVIEW')}
        >
          <div style={{ color: 'var(--verdict-review)', fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <AlertTriangle size={16} />
            <span>REVIEW REQUIRED</span>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
            {reviewCount}
          </div>
        </div>

        <div
          className="card"
          style={{
            cursor: 'pointer',
            borderColor: outcomeFilter === 'INDETERMINATE' ? 'var(--verdict-indeterminate)' : undefined,
          }}
          onClick={() => setOutcomeFilter(outcomeFilter === 'INDETERMINATE' ? 'ALL' : 'INDETERMINATE')}
        >
          <div style={{ color: 'var(--verdict-indeterminate)', fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <HelpCircle size={16} />
            <span>INDETERMINATE / N/A</span>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
            {indeterminateCount + naCount}
          </div>
        </div>
      </div>

      {/* Rules Breakdown List */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Scale size={20} color="var(--accent-cyan)" />
            <span>Statutory Provisions Evaluated ({filtered.length})</span>
          </div>

          <div style={{ display: 'flex', gap: 6 }}>
            {['ALL', 'PASS', 'FAIL', 'REVIEW', 'INDETERMINATE', 'NOT_APPLICABLE'].map((f) => (
              <button
                key={f}
                onClick={() => setOutcomeFilter(f)}
                className={`btn btn-sm ${outcomeFilter === f ? 'btn-primary' : 'btn-outline'}`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            <div>No evaluations match the active filter criteria.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {filtered.map((evalItem) => (
              <div
                key={evalItem.id}
                style={{
                  padding: 16,
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderLeft: `4px solid ${
                    evalItem.outcome === 'PASS'
                      ? 'var(--verdict-pass)'
                      : evalItem.outcome === 'FAIL'
                      ? 'var(--verdict-fail)'
                      : evalItem.outcome === 'REVIEW'
                      ? 'var(--verdict-review)'
                      : 'var(--verdict-indeterminate)'
                  }`,
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: 8,
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        fontSize: '0.95rem',
                        color: 'var(--accent-cyan)',
                      }}>
                        {evalItem.rule_code}
                      </span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        Version {evalItem.rule_version || evalItem.rule_definition?.version || '1.0.0'}
                      </span>
                    </div>

                    <div style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: 2 }}>
                      {evalItem.rule_definition?.title || evalItem.rule_code}
                    </div>

                    <div style={{ fontSize: '0.8rem', color: 'var(--primary-500)', marginTop: 2 }}>
                      {evalItem.statutory_citation}
                    </div>
                  </div>

                  <StatusBadge status={evalItem.outcome} size="lg" />
                </div>

                {/* Legal Rationale */}
                <div style={{
                  fontSize: '0.9rem',
                  color: 'var(--text-main)',
                  lineHeight: 1.5,
                  marginTop: 8,
                  padding: '8px 12px',
                  backgroundColor: 'rgba(0, 0, 0, 0.25)',
                  borderRadius: 4,
                }}>
                  {evalItem.legal_rationale}
                </div>

                {/* Measured values if present */}
                {(evalItem.measured_value !== undefined || evalItem.threshold_value !== undefined) && (
                  <div style={{
                    display: 'flex',
                    gap: 20,
                    marginTop: 10,
                    fontSize: '0.8rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                  }}>
                    {evalItem.measured_value !== undefined && (
                      <div>
                        Measured: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{JSON.stringify(evalItem.measured_value)}</span>
                      </div>
                    )}
                    {evalItem.threshold_value !== undefined && (
                      <div>
                        Mandatory Threshold: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{JSON.stringify(evalItem.threshold_value)}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
