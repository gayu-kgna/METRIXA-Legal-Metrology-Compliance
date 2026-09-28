import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Building, 
  Package, 
  Camera, 
  Cpu, 
  Scale, 
  GitBranch, 
  FileText, 
  MapPin, 
  Clock, 
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  Layers
} from 'lucide-react';
import { getInspection } from '../api/inspections';
import { Inspection } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';

export const InspectionDetailPage: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId: string }>();
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadInspection() {
      if (!inspectionId) return;
      try {
        setLoading(true);
        const data = await getInspection(inspectionId);
        setInspection(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load inspection details');
      } finally {
        setLoading(false);
      }
    }
    loadInspection();
  }, [inspectionId]);

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 60 }}>
        <Clock size={32} className="animate-spin" style={{ margin: '0 auto 16px', color: 'var(--accent-cyan)' }} />
        <div>Loading inspection record...</div>
      </div>
    );
  }

  if (error || !inspection) {
    return (
      <div className="page-container">
        <div className="card" style={{ textAlign: 'center', padding: 40, borderColor: 'var(--verdict-fail-border)' }}>
          <AlertCircle size={36} color="var(--verdict-fail)" style={{ margin: '0 auto 12px' }} />
          <h3>Failed to Load Inspection</h3>
          <p style={{ color: 'var(--text-secondary)', marginTop: 8 }}>{error || 'Inspection not found'}</p>
          <Link to="/inspections" className="btn btn-secondary" style={{ marginTop: 20 }}>
            Back to Inspections
          </Link>
        </div>
      </div>
    );
  }

  const surfacesCaptured = inspection.surfaces?.length || 0;

  return (
    <div className="page-container">
      {/* Header Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 28,
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <h1 style={{ fontSize: '1.8rem', fontFamily: 'var(--font-mono)' }}>
              {inspection.inspection_number}
            </h1>
            <StatusBadge status={inspection.overall_status} />
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Packaged Commodity Statutory Verification Session
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <Link to={`/inspections/${inspection.id}/capture`} className="btn btn-primary" style={{ gap: 6 }}>
            <Camera size={16} />
            <span>Capture Surfaces</span>
          </Link>
          <Link to={`/inspections/${inspection.id}/review`} className="btn btn-cyan" style={{ gap: 6 }}>
            <Cpu size={16} />
            <span>Execute Pipeline</span>
          </Link>
        </div>
      </div>

      {/* Main Grid Information */}
      <div className="grid-3" style={{ marginBottom: 28 }}>
        {/* Retail Outlet Card */}
        <div className="card">
          <h3 style={{ fontSize: '1.05rem', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Building size={17} color="var(--accent-cyan)" />
            <span>Retail Establishment</span>
          </h3>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 4 }}>
            {inspection.retail_outlet_name || 'Unspecified Outlet'}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
            {inspection.retail_outlet_address || 'No address registered'}
          </div>
          {inspection.geo_coordinates && (inspection.geo_coordinates.latitude || inspection.geo_coordinates.longitude) && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '0.78rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--accent-cyan)',
              backgroundColor: 'rgba(6, 182, 212, 0.08)',
              padding: '4px 8px',
              borderRadius: 4,
            }}>
              <MapPin size={13} />
              <span>
                {inspection.geo_coordinates.latitude?.toFixed(4)}, {inspection.geo_coordinates.longitude?.toFixed(4)}
              </span>
            </div>
          )}
        </div>

        {/* Product Details Card */}
        <div className="card">
          <h3 style={{ fontSize: '1.05rem', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Package size={17} color="var(--primary-500)" />
            <span>Packaged Commodity</span>
          </h3>
          {inspection.product ? (
            <>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 4 }}>
                {inspection.product.brand_name} {inspection.product.product_name}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 8 }}>
                Category: {inspection.product.category || 'Standard Packaged Good'}
              </div>
              {inspection.product.gtin_barcode && (
                <div style={{
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                }}>
                  Barcode / GTIN: {inspection.product.gtin_barcode}
                </div>
              )}
              <Link
                to={`/products/${inspection.product.id}`}
                className="btn btn-outline btn-sm"
                style={{ marginTop: 10, display: 'inline-flex', gap: 6 }}
              >
                <Layers size={13} />
                <span>View Product Ledger History</span>
              </Link>
            </>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              No master product linked yet. Can be attached via OCR barcode detection.
            </div>
          )}
        </div>

        {/* Session Telemetry Card */}
        <div className="card">
          <h3 style={{ fontSize: '1.05rem', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldCheck size={17} color="var(--verdict-pass)" />
            <span>Inspection Protocol</span>
          </h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.88rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Surfaces Captured:</span>
            <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{surfacesCaptured} / 6 Surfaces</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.88rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Legal Act:</span>
            <span style={{ fontWeight: 500 }}>Legal Metrology Act, 2009</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Rules Provision:</span>
            <span style={{ fontWeight: 500 }}>PCR 2011 (as amended)</span>
          </div>
        </div>
      </div>

      {/* Quick Action Navigation Grid */}
      <h3 style={{ fontSize: '1.15rem', marginBottom: 16 }}>Workflow Navigation</h3>
      <div className="grid-3" style={{ gap: 16 }}>
        <Link to={`/inspections/${inspection.id}/capture`} className="card" style={{ textDecoration: 'none', transition: 'transform 0.15s ease' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <div style={{ padding: 8, borderRadius: 8, background: 'rgba(99, 102, 241, 0.15)', color: 'var(--primary-500)' }}>
              <Camera size={20} />
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>
              6-Surface Workspace
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Capture and manage high-resolution evidence for all 6 package faces using the intelligent Camera HUD.
          </p>
        </Link>

        <Link to={`/inspections/${inspection.id}/review`} className="card" style={{ textDecoration: 'none', transition: 'transform 0.15s ease' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <div style={{ padding: 8, borderRadius: 8, background: 'rgba(6, 182, 212, 0.15)', color: 'var(--accent-cyan)' }}>
              <Cpu size={20} />
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Pipeline Stepper
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Execute multi-variant OCR, statutory entity parsing, PDP geometry, and rule evaluations step-by-step.
          </p>
        </Link>

        <Link to={`/inspections/${inspection.id}/results`} className="card" style={{ textDecoration: 'none', transition: 'transform 0.15s ease' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <div style={{ padding: 8, borderRadius: 8, background: 'rgba(16, 185, 129, 0.15)', color: 'var(--verdict-pass)' }}>
              <Scale size={20} />
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Statutory Compliance
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Review legal verdicts (PASS, FAIL, REVIEW) determined deterministically by the backend rule engine.
          </p>
        </Link>

        <Link to={`/inspections/${inspection.id}/evidence`} className="card" style={{ textDecoration: 'none', transition: 'transform 0.15s ease' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <div style={{ padding: 8, borderRadius: 8, background: 'rgba(245, 158, 11, 0.15)', color: 'var(--accent-amber)' }}>
              <GitBranch size={20} />
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Evidence Traceability
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Trace legal findings back to structured observations, OCR regions, and original image SHA-256 digests.
          </p>
        </Link>

        <Link to={`/inspections/${inspection.id}/reports`} className="card" style={{ textDecoration: 'none', transition: 'transform 0.15s ease' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <div style={{ padding: 8, borderRadius: 8, background: 'rgba(148, 163, 184, 0.15)', color: 'var(--text-main)' }}>
              <FileText size={20} />
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>
              PDF Dossier Reports
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Generate and stream versioned, tamper-evident inspection dossiers with cryptographic SHA-256 seals.
          </p>
        </Link>
      </div>
    </div>
  );
};
