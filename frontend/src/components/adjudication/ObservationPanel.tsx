import React, { useState } from 'react';
import {
  CheckCircle,
  Edit2,
  AlertTriangle,
  XCircle,
  PlusCircle,
  Filter,
  Shield,
  UserCheck,
  Cpu,
  HelpCircle,
} from 'lucide-react';
import {
  AdjudicatedObservation,
  ObservationStatus,
  ObservationCorrectRequest,
} from '../../types/api';

interface ObservationPanelProps {
  observations: AdjudicatedObservation[];
  onVerify: (obsId: string) => Promise<void>;
  onCorrect: (obsId: string, data: ObservationCorrectRequest) => Promise<void>;
  onReject: (obsId: string, reason: string) => Promise<void>;
  onUpdateStatus: (obsId: string, status: ObservationStatus) => Promise<void>;
  onOpenManualDialog: () => void;
  selectedObsId?: string | null;
  onSelectObs?: (obs: AdjudicatedObservation | null) => void;
}

export const ObservationPanel: React.FC<ObservationPanelProps> = ({
  observations,
  onVerify,
  onCorrect,
  onReject,
  onUpdateStatus,
  onOpenManualDialog,
  selectedObsId,
  onSelectObs,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [editingObsId, setEditingObsId] = useState<string | null>(null);
  const [editRawValue, setEditRawValue] = useState<string>('');
  const [editReason, setEditReason] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Filter observations
  const filtered = observations.filter((obs) => {
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'VERIFIED') return obs.status === 'VERIFIED';
    if (statusFilter === 'UNVERIFIED') return obs.status !== 'VERIFIED' && obs.status !== 'REJECTED';
    if (statusFilter === 'CORRECTED') return obs.status === 'CORRECTED' || obs.revision > 1;
    if (statusFilter === 'UNCERTAIN') return obs.status === 'UNCERTAIN';
    if (statusFilter === 'REJECTED') return obs.status === 'REJECTED';
    return true;
  });

  const startEdit = (obs: AdjudicatedObservation) => {
    setEditingObsId(obs.id);
    setEditRawValue(obs.raw_value);
    setEditReason('');
  };

  const handleSaveCorrection = async (obsId: string) => {
    if (!editRawValue.trim()) return;
    setIsSubmitting(true);
    try {
      await onCorrect(obsId, {
        raw_value: editRawValue.trim(),
        reason: editReason.trim() || 'Officer edited statutory declaration value',
        status: 'CORRECTED',
      });
      setEditingObsId(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getProvenanceBadge = (obs: AdjudicatedObservation) => {
    if (obs.source === 'OFFICER_INPUT') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '10px',
            padding: '2px 6px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(168, 85, 247, 0.15)',
            color: '#C084FC',
            border: '1px solid rgba(168, 85, 247, 0.3)',
          }}
        >
          <UserCheck size={11} /> Manual Input
        </span>
      );
    }
    if (obs.revision > 1 || obs.status === 'CORRECTED') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '10px',
            padding: '2px 6px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(6, 182, 212, 0.15)',
            color: 'var(--accent-cyan)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
          }}
        >
          <Shield size={11} /> Rev {obs.revision}
        </span>
      );
    }
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          fontSize: '10px',
          padding: '2px 6px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(59, 130, 246, 0.15)',
          color: '#60A5FA',
          border: '1px solid rgba(59, 130, 246, 0.3)',
        }}
      >
        <Cpu size={11} /> Perception
      </span>
    );
  };

  const getStatusBadge = (status: ObservationStatus) => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--verdict-pass-bg)',
              color: 'var(--verdict-pass)',
              border: '1px solid var(--verdict-pass-border)',
            }}
          >
            VERIFIED
          </span>
        );
      case 'CORRECTED':
        return (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              color: 'var(--accent-cyan)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
            }}
          >
            CORRECTED
          </span>
        );
      case 'UNCERTAIN':
        return (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--verdict-review-bg)',
              color: 'var(--verdict-review)',
              border: '1px solid var(--verdict-review-border)',
            }}
          >
            UNCERTAIN
          </span>
        );
      case 'REJECTED':
        return (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--verdict-fail-bg)',
              color: 'var(--verdict-fail)',
              border: '1px solid var(--verdict-fail-border)',
            }}
          >
            REJECTED
          </span>
        );
      default:
        return (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-secondary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-muted)',
            }}
          >
            OBSERVED
          </span>
        );
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-surface-primary)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        overflow: 'hidden',
      }}
    >
      {/* Header Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-surface-secondary)',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
            Statutory Declarations
          </h3>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 6px',
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'var(--primary-glow)',
              color: 'var(--primary-500)',
              fontWeight: 600,
            }}
          >
            {observations.length}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            id="btn-add-manual-observation"
            onClick={onOpenManualDialog}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--primary-600)',
              color: '#fff',
              border: 'none',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <PlusCircle size={14} /> Add Declaration
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '4px',
          padding: '8px 12px',
          backgroundColor: 'var(--bg-canvas)',
          borderBottom: '1px solid var(--border-subtle)',
          overflowX: 'auto',
        }}
      >
        {['ALL', 'UNVERIFIED', 'VERIFIED', 'CORRECTED', 'UNCERTAIN', 'REJECTED'].map((f) => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            style={{
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '11px',
              fontWeight: 500,
              border: statusFilter === f ? '1px solid var(--accent-cyan)' : '1px solid transparent',
              backgroundColor: statusFilter === f ? 'var(--accent-cyan-glow)' : 'transparent',
              color: statusFilter === f ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Observation Cards List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filtered.length === 0 ? (
          <div
            style={{
              padding: '32px 16px',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '13px',
            }}
          >
            No observations match current filter.
          </div>
        ) : (
          filtered.map((obs) => {
            const isEditing = editingObsId === obs.id;
            const isSelected = selectedObsId === obs.id;

            return (
              <div
                key={obs.id}
                id={`obs-card-${obs.id}`}
                onClick={() => onSelectObs && onSelectObs(obs)}
                style={{
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-surface-secondary)',
                  border: isSelected
                    ? '1px solid var(--primary-500)'
                    : '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  transition: 'border 0.15s ease',
                  cursor: onSelectObs ? 'pointer' : 'default',
                }}
              >
                {/* Field Type and Badges */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        color: 'var(--text-main)',
                        letterSpacing: '0.02em',
                      }}
                    >
                      {obs.field_display_name || obs.field_type.replace(/_/g, ' ')}
                    </span>
                    {obs.surface_name && (
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        ({obs.surface_name})
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {getProvenanceBadge(obs)}
                    {getStatusBadge(obs.status)}
                  </div>
                </div>

                {/* Content Value or Edit Form */}
                {isEditing ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                    <input
                      type="text"
                      value={editRawValue}
                      onChange={(e) => setEditRawValue(e.target.value)}
                      placeholder="Corrected statutory value..."
                      style={{
                        padding: '6px 10px',
                        backgroundColor: 'var(--bg-canvas)',
                        border: '1px solid var(--border-muted)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-main)',
                        fontSize: '13px',
                      }}
                    />
                    <input
                      type="text"
                      value={editReason}
                      onChange={(e) => setEditReason(e.target.value)}
                      placeholder="Audit justification..."
                      style={{
                        padding: '6px 10px',
                        backgroundColor: 'var(--bg-canvas)',
                        border: '1px solid var(--border-muted)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-main)',
                        fontSize: '11px',
                      }}
                    />
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        onClick={() => setEditingObsId(null)}
                        style={{
                          padding: '4px 8px',
                          fontSize: '11px',
                          background: 'none',
                          border: '1px solid var(--border-muted)',
                          borderRadius: 'var(--radius-sm)',
                          color: 'var(--text-secondary)',
                          cursor: 'pointer',
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={() => handleSaveCorrection(obs.id)}
                        style={{
                          padding: '4px 10px',
                          fontSize: '11px',
                          backgroundColor: 'var(--accent-cyan)',
                          color: '#000',
                          fontWeight: 600,
                          border: 'none',
                          borderRadius: 'var(--radius-sm)',
                          cursor: isSubmitting ? 'not-allowed' : 'pointer',
                        }}
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div
                      style={{
                        fontSize: '13px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-main)',
                        fontWeight: 500,
                        backgroundColor: 'rgba(0, 0, 0, 0.25)',
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                        wordBreak: 'break-word',
                      }}
                    >
                      {obs.raw_value}
                    </div>

                    {/* Normalized metadata detail if present */}
                    {obs.normalized_value && Object.keys(obs.normalized_value).length > 0 && (
                      <div
                        style={{
                          fontSize: '11px',
                          color: 'var(--text-muted)',
                          marginTop: '4px',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        Normalized:{' '}
                        {obs.normalized_value.formatted ||
                          obs.normalized_value.display ||
                          JSON.stringify(obs.normalized_value)}
                      </div>
                    )}
                  </div>
                )}

                {/* Bottom Action Strip */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '4px',
                    paddingTop: '6px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.04)',
                  }}
                >
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    Conf: {(obs.confidence * 100).toFixed(0)}%
                  </span>

                  <div style={{ display: 'flex', gap: '6px' }}>
                    {obs.status !== 'VERIFIED' && (
                      <button
                        id={`btn-verify-${obs.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onVerify(obs.id);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--verdict-pass-bg)',
                          border: '1px solid var(--verdict-pass-border)',
                          color: 'var(--verdict-pass)',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                        title="Verify this declaration as legally compliant"
                      >
                        <CheckCircle size={12} /> Verify
                      </button>
                    )}

                    {!isEditing && (
                      <button
                        id={`btn-edit-${obs.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          startEdit(obs);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--bg-surface-primary)',
                          border: '1px solid var(--border-muted)',
                          color: 'var(--text-secondary)',
                          fontSize: '11px',
                          cursor: 'pointer',
                        }}
                        title="Correct or adjust value"
                      >
                        <Edit2 size={12} /> Edit
                      </button>
                    )}

                    {obs.status !== 'UNCERTAIN' && (
                      <button
                        id={`btn-uncertain-${obs.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onUpdateStatus(obs.id, 'UNCERTAIN');
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--verdict-review-bg)',
                          border: '1px solid var(--verdict-review-border)',
                          color: 'var(--verdict-review)',
                          fontSize: '11px',
                          cursor: 'pointer',
                        }}
                        title="Mark uncertain / needs senior review"
                      >
                        <HelpCircle size={12} /> Uncertain
                      </button>
                    )}

                    {obs.status !== 'REJECTED' && (
                      <button
                        id={`btn-reject-${obs.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          const r = window.prompt('Reason for rejecting observation:');
                          if (r !== null) {
                            onReject(obs.id, r || 'Officer rejected declaration');
                          }
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--verdict-fail-bg)',
                          border: '1px solid var(--verdict-fail-border)',
                          color: 'var(--verdict-fail)',
                          fontSize: '11px',
                          cursor: 'pointer',
                        }}
                        title="Reject observation"
                      >
                        <XCircle size={12} /> Reject
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
