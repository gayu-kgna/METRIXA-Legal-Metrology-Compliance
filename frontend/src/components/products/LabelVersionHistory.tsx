import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { LabelVersionDetail } from '../../types/api';
import { Layers, Calendar, ExternalLink, Hash, ArrowRight, GitCompare } from 'lucide-react';

interface LabelVersionHistoryProps {
  productId: string;
  versions: LabelVersionDetail[];
  onCompare: (fromVersionId: string, toVersionId: string) => void;
  loading?: boolean;
}

export const LabelVersionHistory: React.FC<LabelVersionHistoryProps> = ({
  productId,
  versions,
  onCompare,
  loading,
}) => {
  const [selectedFrom, setSelectedFrom] = useState<string>(versions.length > 1 ? versions[0].id : '');
  const [selectedTo, setSelectedTo] = useState<string>(versions.length > 1 ? versions[versions.length - 1].id : '');
  const [selectedVersion, setSelectedVersion] = useState<LabelVersionDetail | null>(
    versions.length > 0 ? versions[versions.length - 1] : null
  );

  if (loading) {
    return (
      <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading packaging label revisions...
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        No historical label versions cataloged for this commodity yet.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Version Comparison Selector Bar */}
      {versions.length > 1 && (
        <div className="card" style={{
          padding: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
          backgroundColor: 'var(--bg-surface-secondary)',
          border: '1px solid var(--border-glow)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <GitCompare size={18} color="var(--accent-cyan)" />
            <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Compare Label Revisions:</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <select
              value={selectedFrom}
              onChange={(e) => setSelectedFrom(e.target.value)}
              className="input"
              style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  Base: {v.version_tag} ({new Date(v.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>

            <ArrowRight size={16} color="var(--text-muted)" />

            <select
              value={selectedTo}
              onChange={(e) => setSelectedTo(e.target.value)}
              className="input"
              style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  Target: {v.version_tag} ({new Date(v.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>

            <button
              onClick={() => {
                if (selectedFrom && selectedTo && selectedFrom !== selectedTo) {
                  onCompare(selectedFrom, selectedTo);
                }
              }}
              disabled={!selectedFrom || !selectedTo || selectedFrom === selectedTo}
              className="btn btn-primary btn-sm"
              style={{ gap: 6 }}
            >
              <span>Run Diff Comparison</span>
            </button>
          </div>
        </div>
      )}

      {/* Version Cards Grid */}
      <div className="grid-3" style={{ gap: 16 }}>
        {versions.map((v) => {
          const isSelected = selectedVersion?.id === v.id;
          const declCount = Object.keys(v.canonical_declarations || {}).length;

          return (
            <div
              key={v.id}
              onClick={() => setSelectedVersion(v)}
              className="card"
              style={{
                cursor: 'pointer',
                borderColor: isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                boxShadow: isSelected ? '0 0 15px rgba(6, 182, 212, 0.2)' : 'none',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Layers size={18} color="var(--accent-cyan)" />
                  <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
                    {v.version_tag}
                  </span>
                </div>
                <span style={{
                  fontSize: '0.72rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                  backgroundColor: 'var(--bg-surface-tertiary)',
                  padding: '2px 6px',
                  borderRadius: 4,
                }}>
                  {declCount} declarations
                </span>
              </div>

              {/* Fingerprint */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
                  Version Fingerprint (SHA-256)
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  color: 'var(--accent-cyan)',
                  wordBreak: 'break-all',
                }}>
                  {v.version_fingerprint ? `${v.version_fingerprint.substring(0, 24)}...` : 'Pre-Phase 9 Unhashed'}
                </div>
              </div>

              {/* Source & Date */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Calendar size={13} />
                  <span>Observed: {new Date(v.created_at).toLocaleDateString()}</span>
                </div>

                {v.source_inspection_id && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Hash size={13} />
                    <span>Inspection: {v.source_inspection_number || v.source_inspection_id.substring(0, 8)}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Version Declaration Inspector */}
      {selectedVersion && (
        <div className="card" style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>
                Canonical Declarations Payload — {selectedVersion.version_tag}
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                Persisted statutory package declarations used for deterministic legal metrology rule evaluations
              </p>
            </div>
            {selectedVersion.source_inspection_id && (
              <Link
                to={`/inspections/${selectedVersion.source_inspection_id}`}
                className="btn btn-outline btn-sm"
                style={{ gap: 6 }}
              >
                <span>View Source Inspection</span>
                <ExternalLink size={14} />
              </Link>
            )}
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '8px 12px', width: '35%' }}>Statutory Field</th>
                  <th style={{ padding: '8px 12px' }}>Canonical Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(selectedVersion.canonical_declarations || {}).map(([key, val], idx) => {
                  const displayVal = typeof val === 'object' && val !== null ? (val.formatted || JSON.stringify(val)) : String(val);
                  return (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-main)' }}>
                        {key.replace(/_/g, ' ')}
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                        {displayVal}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
