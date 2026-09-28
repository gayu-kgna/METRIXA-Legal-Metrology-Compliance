import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  FileText, 
  Download, 
  Eye, 
  Plus, 
  ShieldCheck, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  ExternalLink 
} from 'lucide-react';
import { listInspectionReports, generateInspectionReport, downloadReportPdfBlob, getReportPdfUrl } from '../api/reports';
import { getInspection } from '../api/inspections';
import { ReportRead, Inspection } from '../types/api';

export const ReportsPage: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId: string }>();

  const [reports, setReports] = useState<ReportRead[]>([]);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ReportRead | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    if (!inspectionId) return;
    try {
      setLoading(true);
      const [reps, insp] = await Promise.all([
        listInspectionReports(inspectionId),
        getInspection(inspectionId),
      ]);
      setReports(reps);
      setInspection(insp);
      if (reps.length > 0 && !selectedReport) {
        setSelectedReport(reps[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve reports');
    } finally {
      setLoading(false);
    }
  }, [inspectionId, selectedReport]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Load PDF Blob when selected report changes
  useEffect(() => {
    async function loadPdf() {
      if (!inspectionId || !selectedReport) return;
      try {
        const blob = await downloadReportPdfBlob(inspectionId, selectedReport.id);
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
        return () => {
          URL.revokeObjectURL(url);
        };
      } catch (err) {
        console.warn('Could not load PDF blob for inline preview:', err);
      }
    }
    loadPdf();
  }, [inspectionId, selectedReport]);

  // Generate new report version
  const handleGenerateReport = async () => {
    if (!inspectionId) return;
    setGenerating(true);
    setError(null);
    try {
      const newRep = await generateInspectionReport(inspectionId, {
        report_type: 'FULL_INSPECTION_DOSSIER',
      });
      setSelectedReport(newRep);
      await fetchReports();
    } catch (err: any) {
      setError(err.message || 'Report compilation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (rep: ReportRead) => {
    if (!inspectionId) return;
    try {
      const blob = await downloadReportPdfBlob(inspectionId, rep.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = rep.pdf_filename || `dossier_v${rep.report_version}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    }
  };

  if (loading && !inspection) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 60 }}>
        <Clock size={32} className="animate-spin" style={{ margin: '0 auto 16px', color: 'var(--accent-cyan)' }} />
        <div>Loading inspection dossier reports...</div>
      </div>
    );
  }

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
            <h1 style={{ fontSize: '1.75rem' }}>Inspection Dossier Reports</h1>
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
            Versioned, tamper-evident statutory dossiers backed by immutable cryptographic Evidence Snapshots
          </p>
        </div>

        <button
          onClick={handleGenerateReport}
          className="btn btn-primary btn-lg"
          disabled={generating}
          style={{ gap: 8 }}
        >
          {generating ? (
            <>
              <Clock size={16} className="animate-spin" />
              <span>Generating Dossier...</span>
            </>
          ) : (
            <>
              <Plus size={16} />
              <span>Compile New Report Version</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 16px',
          backgroundColor: 'var(--verdict-fail-bg)',
          border: '1px solid var(--verdict-fail-border)',
          borderRadius: 'var(--radius-sm)',
          color: '#FCA5A5',
          marginBottom: 20,
        }}>
          <AlertCircle size={18} color="var(--verdict-fail)" />
          <span>{error}</span>
        </div>
      )}

      {reports.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 50, color: 'var(--text-muted)' }}>
          <FileText size={48} style={{ margin: '0 auto 16px', opacity: 0.4 }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: 8, color: 'var(--text-main)' }}>
            No Dossier Reports Generated Yet
          </h3>
          <p style={{ maxWidth: 460, margin: '0 auto 20px', fontSize: '0.88rem' }}>
            Execute the inspection pipeline and click "Compile New Report Version" to generate a formal Evidence Dossier.
          </p>
          <button onClick={handleGenerateReport} className="btn btn-cyan">
            Compile Initial Dossier (v1)
          </button>
        </div>
      ) : (
        <div className="grid-3" style={{ gap: 24, gridTemplateColumns: '320px 1fr 1fr' }}>
          {/* Versions List */}
          <div className="card" style={{ height: 'fit-content' }}>
            <h4 style={{ fontSize: '0.95rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <FileText size={16} color="var(--accent-cyan)" />
              <span>Report Versions ({reports.length})</span>
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {reports.map((rep) => {
                const isSelected = selectedReport?.id === rep.id;
                return (
                  <div
                    key={rep.id}
                    onClick={() => setSelectedReport(rep)}
                    style={{
                      padding: 12,
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-surface-secondary)',
                      border: `1px solid ${isSelected ? 'var(--primary-500)' : 'var(--border-subtle)'}`,
                      cursor: 'pointer',
                      transition: 'border-color 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem', color: isSelected ? 'var(--accent-cyan)' : 'var(--text-main)' }}>
                        Version {rep.report_version}
                      </span>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {new Date(rep.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      SHA: {rep.sha256_hash.substring(0, 10)}...
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Dossier Viewer & Metadata */}
          <div className="card" style={{ gridColumn: 'span 2', minHeight: 650, display: 'flex', flexDirection: 'column' }}>
            {selectedReport && (
              <>
                <div className="card-header" style={{ marginBottom: 16 }}>
                  <div>
                    <div className="card-title">
                      <ShieldCheck size={18} color="var(--verdict-pass)" />
                      <span>Dossier Version {selectedReport.report_version}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: 2 }}>
                      SHA-256 Digest: {selectedReport.sha256_hash}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => handleDownload(selectedReport)}
                      className="btn btn-secondary btn-sm"
                      style={{ gap: 6 }}
                    >
                      <Download size={14} />
                      <span>Download PDF</span>
                    </button>
                    {pdfBlobUrl && (
                      <a
                        href={pdfBlobUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-primary btn-sm"
                        style={{ gap: 6 }}
                      >
                        <ExternalLink size={14} />
                        <span>Open New Tab</span>
                      </a>
                    )}
                  </div>
                </div>

                {/* Embedded PDF Viewer */}
                <div style={{
                  flex: 1,
                  backgroundColor: '#1E293B',
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'hidden',
                  minHeight: 520,
                  border: '1px solid var(--border-subtle)',
                }}>
                  {pdfBlobUrl ? (
                    <iframe
                      src={pdfBlobUrl}
                      title="PDF Dossier Preview"
                      style={{ width: '100%', height: '100%', minHeight: 520, border: 'none' }}
                    />
                  ) : (
                    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                      <Clock size={28} className="animate-spin" style={{ margin: '0 auto 12px' }} />
                      <div>Streaming PDF dossier bytes...</div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
