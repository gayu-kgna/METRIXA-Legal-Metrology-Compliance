import React from 'react';
import {
  AlertTriangle,
  CheckCircle,
  GitMerge,
  ShieldCheck,
  Check,
  XCircle,
} from 'lucide-react';
import { ConflictGroup, AdjudicatedObservation } from '../../types/api';

interface ConflictResolutionPanelProps {
  conflicts: ConflictGroup[];
  onSelectAuthoritative: (fieldType: string, winningObsId: string) => Promise<void>;
  onVerifySingle: (obsId: string) => Promise<void>;
  onRejectSingle: (obsId: string, reason: string) => Promise<void>;
}

export const ConflictResolutionPanel: React.FC<ConflictResolutionPanelProps> = ({
  conflicts,
  onSelectAuthoritative,
  onVerifySingle,
  onRejectSingle,
}) => {
  const activeConflicts = conflicts.filter((c) => c.has_conflict);

  if (activeConflicts.length === 0) {
    return (
      <div
        id="no-conflicts-banner"
        style={{
          padding: '16px 20px',
          backgroundColor: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid var(--verdict-pass-border)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <ShieldCheck size={20} style={{ color: 'var(--verdict-pass)', flexShrink: 0 }} />
        <div>
          <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--verdict-pass)' }}>
            No Multi-Surface Declaration Conflicts Detected
          </h4>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            All statutory declarations across captured faces are consistent and unambiguous.
          </p>
        </div>
      </div>
    );
  }

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
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <AlertTriangle size={18} style={{ color: 'var(--verdict-review)' }} />
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
            Multi-Surface Declaration Conflicts ({activeConflicts.length})
          </h3>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Multiple differing statutory values were detected across surfaces. Select the authoritative declaration.
          </p>
        </div>
      </div>

      {/* Conflict Groups */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {activeConflicts.map((group) => (
          <div
            key={group.field_type}
            id={`conflict-group-${group.field_type}`}
            style={{
              backgroundColor: 'var(--bg-canvas)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-muted)',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  color: 'var(--accent-amber)',
                  textTransform: 'uppercase',
                }}
              >
                {group.field_type.replace(/_/g, ' ')}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                {group.observation_count} Conflicting Values
              </span>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {group.description}
            </p>

            {/* Side-by-side cards for candidates */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '12px',
              }}
            >
              {group.observations.map((obs) => {
                const isVerified = obs.status === 'VERIFIED';
                const isRejected = obs.status === 'REJECTED';

                return (
                  <div
                    key={obs.id}
                    id={`conflict-card-${obs.id}`}
                    style={{
                      padding: '12px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: isVerified
                        ? 'rgba(16, 185, 129, 0.1)'
                        : isRejected
                        ? 'rgba(239, 68, 68, 0.08)'
                        : 'var(--bg-surface-secondary)',
                      border: isVerified
                        ? '1px solid var(--verdict-pass)'
                        : isRejected
                        ? '1px dashed var(--verdict-fail-border)'
                        : '1px solid var(--border-muted)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '8px',
                    }}
                  >
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '11px',
                          color: 'var(--text-muted)',
                          marginBottom: '4px',
                        }}
                      >
                        <span>{obs.surface_name || 'Surface'}</span>
                        <span>{(obs.confidence * 100).toFixed(0)}% conf</span>
                      </div>

                      <div
                        style={{
                          fontSize: '14px',
                          fontWeight: 600,
                          color: isRejected ? 'var(--text-muted)' : 'var(--text-main)',
                          fontFamily: 'var(--font-mono)',
                          textDecoration: isRejected ? 'line-through' : 'none',
                        }}
                      >
                        {obs.raw_value}
                      </div>

                      {obs.normalized_value && (
                        <div
                          style={{
                            fontSize: '11px',
                            color: 'var(--text-secondary)',
                            marginTop: '2px',
                          }}
                        >
                          Norm: {obs.normalized_value.formatted || JSON.stringify(obs.normalized_value)}
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                      {!isVerified && !isRejected && (
                        <button
                          id={`btn-authoritative-${obs.id}`}
                          onClick={() => onSelectAuthoritative(group.field_type, obs.id)}
                          style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            padding: '6px 10px',
                            backgroundColor: 'var(--primary-600)',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '11px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          <Check size={12} /> Set Authoritative
                        </button>
                      )}

                      {isVerified && (
                        <span
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '11px',
                            fontWeight: 600,
                            color: 'var(--verdict-pass)',
                          }}
                        >
                          <CheckCircle size={14} /> Authoritative Choice
                        </span>
                      )}

                      {!isRejected && (
                        <button
                          onClick={() => onRejectSingle(obs.id, 'Superseded by conflicting declaration')}
                          style={{
                            padding: '6px 8px',
                            backgroundColor: 'transparent',
                            color: 'var(--text-muted)',
                            border: '1px solid var(--border-muted)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '11px',
                            cursor: 'pointer',
                          }}
                          title="Reject this alternative"
                        >
                          <XCircle size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
