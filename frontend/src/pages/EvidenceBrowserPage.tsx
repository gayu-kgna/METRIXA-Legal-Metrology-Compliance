import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  GitBranch, 
  ShieldCheck, 
  Layers, 
  Eye, 
  Scale, 
  Clock, 
  AlertCircle, 
  FileCode, 
  ArrowRight,
  Hash
} from 'lucide-react';
import { getInspectionEvidenceBundle } from '../api/evidence';
import { getInspection } from '../api/inspections';
import { EvidenceBundleResponse, Inspection } from '../types/api';
import { getImageContentUrl } from '../api/images';

export const EvidenceBrowserPage: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId: string }>();

  const [evidenceBundle, setEvidenceBundle] = useState<EvidenceBundleResponse | null>(null);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'provenance' | 'manifest'>('provenance');

  useEffect(() => {
    async function loadEvidence() {
      if (!inspectionId) return;
      try {
        setLoading(true);
        const [bundle, insp] = await Promise.all([
          getInspectionEvidenceBundle(inspectionId),
          getInspection(inspectionId),
        ]);
        setEvidenceBundle(bundle);
        setInspection(insp);
      } catch (err: any) {
        setError(err.message || 'Failed to retrieve evidence bundle');
      } finally {
        setLoading(false);
      }
    }
    loadEvidence();
  }, [inspectionId]);

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 60 }}>
        <Clock size={32} className="animate-spin" style={{ margin: '0 auto 16px', color: 'var(--accent-cyan)' }} />
        <div>Loading cryptographic evidence bundle...</div>
      </div>
    );
  }

  const manifest = evidenceBundle?.manifest || {};
  const surfaces = (manifest.surfaces as any[]) || [];
  const ocrRuns = (manifest.ocr_runs as any[]) || [];
  const observations = (manifest.observations as any[]) || [];
  const evaluations = (manifest.evaluations as any[]) || [];

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h1 style={{ fontSize: '1.75rem' }}>Evidence Traceability Graph</h1>
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
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Cryptographic provenance linking legal findings back to observations, OCR bounding regions, and source SHA-256 digests
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => setActiveTab('provenance')}
            className={`btn ${activeTab === 'provenance' ? 'btn-primary' : 'btn-outline'}`}
            style={{ gap: 6 }}
          >
            <GitBranch size={16} />
            <span>Traceability View</span>
          </button>
          <button
            onClick={() => setActiveTab('manifest')}
            className={`btn ${activeTab === 'manifest' ? 'btn-primary' : 'btn-outline'}`}
            style={{ gap: 6 }}
          >
            <FileCode size={16} />
            <span>Canonical Manifest JSON</span>
          </button>
        </div>
      </div>

      {/* Integrity Seal Bar */}
      <div style={{
        backgroundColor: 'var(--bg-surface-primary)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px 18px',
        marginBottom: 24,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldCheck size={20} color="var(--verdict-pass)" />
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              Immutable Evidence Snapshot Integrity Hash
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: 'var(--accent-cyan)',
              wordBreak: 'break-all',
            }}>
              {`SHA-256: ${evidenceBundle?.integrity_hash || 'Unsealed Draft'}`}
            </div>
          </div>
        </div>

        <div style={{
          display: 'flex',
          gap: 16,
          fontSize: '0.8rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-secondary)',
        }}>
          <div>Surfaces: <span style={{ color: 'var(--text-main)' }}>{surfaces.length}</span></div>
          <div>OCR Runs: <span style={{ color: 'var(--text-main)' }}>{ocrRuns.length}</span></div>
          <div>Observations: <span style={{ color: 'var(--text-main)' }}>{observations.length}</span></div>
          <div>Evaluations: <span style={{ color: 'var(--text-main)' }}>{evaluations.length}</span></div>
        </div>
      </div>

      {activeTab === 'provenance' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Visual Step-by-Step Provenance Cards */}
          {evaluations.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
              <div>No evaluations found in current evidence package. Run pipeline first.</div>
              <Link to={`/inspections/${inspectionId}/review`} className="btn btn-secondary btn-sm" style={{ marginTop: 12 }}>
                Open Pipeline
              </Link>
            </div>
          ) : (
            evaluations.map((evalItem: any, idx: number) => {
              // Find matching observations referenced in evaluation
              const obsIds = Array.isArray(evalItem.evidence_references?.observation_ids)
                ? evalItem.evidence_references.observation_ids
                : (Array.isArray(evalItem.evidence_references) ? evalItem.evidence_references : []);
              const reqFields = Array.isArray(evalItem.evidence_references?.required_fields)
                ? evalItem.evidence_references.required_fields
                : [];

              const relatedObservations = observations.filter((obs: any) => {
                const oId = obs.id || obs.observation_id;
                if (obsIds.includes(oId)) return true;
                const fType = obs.field_type || obs.field_name;
                if (fType && reqFields.includes(fType)) return true;
                return false;
              });

              return (
                <div key={idx} className="card">
                  {/* Step 1: Rule Evaluation Verdict */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '1px solid var(--border-subtle)',
                    paddingBottom: 12,
                    marginBottom: 14,
                  }}>
                    <div>
                      <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}>
                        Statutory Finding • Evaluation ID: <span style={{ fontFamily: 'var(--font-mono)' }}>{evalItem.id || evalItem.evaluation_id}</span>
                      </div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                        {evalItem.rule_code}
                      </div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                        {evalItem.statutory_citation}
                      </div>
                      {evalItem.legal_rationale && (
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginTop: 4 }}>
                          {evalItem.legal_rationale}
                        </div>
                      )}
                    </div>

                    <span className={`badge ${
                      evalItem.outcome === 'PASS'
                        ? 'badge-pass'
                        : evalItem.outcome === 'FAIL'
                        ? 'badge-fail'
                        : evalItem.outcome === 'NOT_APPLICABLE'
                        ? 'badge-secondary'
                        : 'badge-review'
                    }`}>
                      {evalItem.outcome}
                    </span>
                  </div>

                  {/* Backward Trace Chain */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                      Backward Evidence Chain (Rule &rarr; Observation &rarr; OCR Region &rarr; Package Surface &rarr; SHA-256 Digest):
                    </div>

                    {relatedObservations.length > 0 ? (
                      relatedObservations.map((obs: any, oIdx: number) => {
                        const obsSurface = surfaces.find((s) => s.surface_id === obs.surface_id);
                        const ocrRegionId = obs.ocr_region_id || (obs.normalized_value?.source_ocr_region_ids?.[0]) || 'N/A';
                        const imageSha = obsSurface?.sha256_hash || 'N/A';
                        const surfaceName = obsSurface?.surface_type || (obs.surface_id ? 'PACKAGE_SURFACE' : 'N/A');

                        return (
                          <div
                            key={oIdx}
                            style={{
                              padding: 14,
                              borderRadius: 'var(--radius-sm)',
                              backgroundColor: 'var(--bg-surface-secondary)',
                              border: '1px solid var(--border-subtle)',
                              fontSize: '0.85rem',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 6 }}>
                              <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                                Field: {obs.field_type || obs.field_name} • Observation ID: {obs.id || obs.observation_id}
                              </span>
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--verdict-pass)' }}>
                                Confidence: {Math.round((obs.confidence ?? obs.confidence_score ?? 1) * 100)}%
                              </span>
                            </div>

                            <div style={{
                              display: 'grid',
                              gridTemplateColumns: 'repeat(2, 1fr)',
                              gap: 8,
                              fontSize: '0.8rem',
                              color: 'var(--text-secondary)',
                              fontFamily: 'var(--font-mono)',
                              marginBottom: 8,
                            }}>
                              <div>
                                Extracted: <span style={{ color: 'var(--text-main)' }}>"{obs.raw_value || obs.raw_text_extracted || 'N/A'}"</span>
                              </div>
                              <div>
                                Normalized: <span style={{ color: 'var(--text-main)' }}>{JSON.stringify(obs.normalized_value)}</span>
                              </div>
                            </div>

                            {/* Provenance trace metadata */}
                            <div style={{
                              paddingTop: 8,
                              borderTop: '1px dashed var(--border-subtle)',
                              display: 'flex',
                              gap: 16,
                              fontSize: '0.75rem',
                              fontFamily: 'var(--font-mono)',
                              color: 'var(--text-muted)',
                              flexWrap: 'wrap',
                            }}>
                              <div>OCR Region ID: <span style={{ color: 'var(--text-secondary)' }}>{ocrRegionId}</span></div>
                              <div>Surface: <span style={{ color: 'var(--text-secondary)' }}>{surfaceName}</span></div>
                              <div>Image SHA-256: <span style={{ color: 'var(--accent-cyan)' }}>{imageSha}</span></div>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        Evaluated against general package presence or mandatory declaration rules.
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
        /* Manifest JSON View */
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <FileCode size={18} color="var(--accent-cyan)" />
              <span>Full Canonical Evidence Manifest JSON</span>
            </div>
          </div>

          <pre style={{
            backgroundColor: '#070A12',
            padding: 16,
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
            color: '#A5F3FC',
            overflowX: 'auto',
            maxHeight: 600,
          }}>
            {JSON.stringify(manifest, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
