import React from 'react';
import { LabelDiffResponse } from '../../types/api';
import { 
  GitCompare, 
  ArrowRight, 
  PlusCircle, 
  MinusCircle, 
  RefreshCw, 
  CheckCircle2, 
  ShieldAlert, 
  Info 
} from 'lucide-react';

interface LabelChangeViewerProps {
  diff: LabelDiffResponse | null;
  loading?: boolean;
}

export const LabelChangeViewer: React.FC<LabelChangeViewerProps> = ({ diff, loading }) => {
  if (loading) {
    return (
      <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        Computing deterministic label differences...
      </div>
    );
  }

  if (!diff) {
    return (
      <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        Select two packaging label versions above to run historical change comparison.
      </div>
    );
  }

  const formatValue = (val: any) => {
    if (val === null || val === undefined) return '—';
    if (typeof val === 'object') {
      return val.formatted || JSON.stringify(val);
    }
    return String(val);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Diff Header */}
      <div className="card" style={{
        backgroundColor: 'var(--bg-surface-primary)',
        border: '1px solid var(--border-glow)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: '1.1rem',
              fontWeight: 700,
              fontFamily: 'var(--font-heading)',
            }}>
              <span style={{ color: 'var(--text-secondary)' }}>{diff.from_version_tag}</span>
              <ArrowRight size={18} color="var(--accent-cyan)" />
              <span style={{ color: 'var(--accent-cyan)' }}>{diff.to_version_tag}</span>
            </div>
            <span style={{
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              padding: '3px 8px',
              borderRadius: 4,
              backgroundColor: 'var(--bg-surface-tertiary)',
            }}>
              {diff.total_changes} Changes Detected
            </span>
          </div>
        </div>

        {/* Regulatory Notice Banner */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 10,
          padding: '10px 14px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(99, 102, 241, 0.08)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.4,
        }}>
          <Info size={16} color="var(--primary-500)" style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <strong style={{ color: 'var(--text-main)' }}>Historical Change Record: </strong>
            {diff.legal_disclaimer}
          </div>
        </div>
      </div>

      {/* 1. Changed Fields */}
      {diff.changed_fields.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <RefreshCw size={16} color="var(--accent-amber)" />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-amber)' }}>
              Changed Declarations ({diff.changed_fields.length})
            </h4>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '8px 12px', width: '30%' }}>Statutory Field</th>
                  <th style={{ padding: '8px 12px', width: '35%' }}>Previous ({diff.from_version_tag})</th>
                  <th style={{ padding: '8px 12px', width: '35%' }}>Current ({diff.to_version_tag})</th>
                </tr>
              </thead>
              <tbody>
                {diff.changed_fields.map((f, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
                      {f.field_label}
                    </td>
                    <td style={{
                      padding: '12px',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-muted)',
                      backgroundColor: 'rgba(239, 68, 68, 0.05)',
                    }}>
                      {formatValue(f.prev_value)}
                    </td>
                    <td style={{
                      padding: '12px',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--verdict-pass)',
                      backgroundColor: 'rgba(16, 185, 129, 0.05)',
                      fontWeight: 500,
                    }}>
                      {formatValue(f.curr_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 2. Added Fields */}
      {diff.added_fields.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <PlusCircle size={16} color="var(--verdict-pass)" />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--verdict-pass)' }}>
              Added Declarations ({diff.added_fields.length})
            </h4>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '8px 12px', width: '35%' }}>Statutory Field</th>
                  <th style={{ padding: '8px 12px' }}>New Value Added</th>
                </tr>
              </thead>
              <tbody>
                {diff.added_fields.map((f, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
                      {f.field_label}
                    </td>
                    <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', color: 'var(--verdict-pass)' }}>
                      {formatValue(f.curr_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. Removed Fields */}
      {diff.removed_fields.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <MinusCircle size={16} color="var(--verdict-fail)" />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--verdict-fail)' }}>
              Removed Declarations ({diff.removed_fields.length})
            </h4>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '8px 12px', width: '35%' }}>Statutory Field</th>
                  <th style={{ padding: '8px 12px' }}>Prior Value (Not Observed in Current)</th>
                </tr>
              </thead>
              <tbody>
                {diff.removed_fields.map((f, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
                      {f.field_label}
                    </td>
                    <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textDecoration: 'line-through' }}>
                      {formatValue(f.prev_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. Unchanged Fields */}
      {diff.unchanged_fields.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <CheckCircle2 size={16} color="var(--text-muted)" />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Unchanged Declarations ({diff.unchanged_fields.length})
            </h4>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <tbody>
                {diff.unchanged_fields.map((f, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '8px 12px', width: '35%', color: 'var(--text-secondary)' }}>
                      {f.field_label}
                    </td>
                    <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {formatValue(f.curr_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
