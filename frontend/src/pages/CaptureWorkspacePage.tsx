import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Camera, 
  ArrowRight, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  Layers 
} from 'lucide-react';
import { getInspection } from '../api/inspections';
import { uploadSurfaceImage, getImageContentUrl } from '../api/images';
import { Inspection, SurfaceType, SurfaceRead } from '../types/api';
import { SixSurfaceWorkspace } from '../components/inspection/SixSurfaceWorkspace';
import { CameraHUD } from '../components/camera/CameraHUD';

export const CaptureWorkspacePage: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId: string }>();

  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<{ message: string; type: 'info' | 'success' | 'error' } | null>(null);

  // Active Camera HUD state
  const [activeHUDType, setActiveHUDType] = useState<SurfaceType | null>(null);

  // Selected image modal for detailed review
  const [selectedImage, setSelectedImage] = useState<SurfaceRead | null>(null);

  const fetchInspection = useCallback(async () => {
    if (!inspectionId) return;
    try {
      setLoading(true);
      const data = await getInspection(inspectionId);
      setInspection(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load inspection surfaces');
    } finally {
      setLoading(false);
    }
  }, [inspectionId]);

  useEffect(() => {
    fetchInspection();
  }, [fetchInspection]);

  // Handle capture from Camera HUD
  const handleHUDCapture = async (blob: Blob) => {
    if (!inspectionId || !activeHUDType) return;
    setUploadStatus({ message: `Ingesting captured ${activeHUDType} frame...`, type: 'info' });

    try {
      const filename = `capture_${activeHUDType.toLowerCase()}_${Date.now()}.jpg`;
      const uploaded = await uploadSurfaceImage(inspectionId, activeHUDType, blob, filename);
      setUploadStatus({
        message: `Successfully ingested ${activeHUDType} image [SHA: ${uploaded.sha256_hash.substring(0, 8)}...]`,
        type: 'success',
      });
      setActiveHUDType(null);
      await fetchInspection();
    } catch (err: any) {
      setUploadStatus({ message: `Capture upload failed: ${err.message}`, type: 'error' });
      throw err;
    }
  };

  // Handle manual file upload
  const handleFileUpload = async (surfaceType: SurfaceType, file: File) => {
    if (!inspectionId) return;
    setUploadStatus({ message: `Uploading ${file.name} for ${surfaceType}...`, type: 'info' });

    try {
      const uploaded = await uploadSurfaceImage(inspectionId, surfaceType, file);
      setUploadStatus({
        message: `Uploaded ${file.name} successfully [SHA: ${uploaded.sha256_hash.substring(0, 8)}...]`,
        type: 'success',
      });
      await fetchInspection();
    } catch (err: any) {
      setUploadStatus({ message: `Upload failed: ${err.message}`, type: 'error' });
    }
  };

  if (loading && !inspection) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 60 }}>
        <Clock size={32} className="animate-spin" style={{ margin: '0 auto 16px', color: 'var(--accent-cyan)' }} />
        <div>Loading six-surface capture workspace...</div>
      </div>
    );
  }

  if (error || !inspection) {
    return (
      <div className="page-container">
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <AlertCircle size={36} color="var(--verdict-fail)" style={{ margin: '0 auto 12px' }} />
          <h3>Session Error</h3>
          <p style={{ color: 'var(--text-secondary)' }}>{error || 'Inspection session not found'}</p>
        </div>
      </div>
    );
  }

  const surfaces = inspection.surfaces || [];
  const capturedCount = surfaces.length;

  return (
    <div className="page-container">
      {/* Workspace Header */}
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
            <h1 style={{ fontSize: '1.75rem' }}>Six-Surface Capture Workspace</h1>
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
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Systematic image ingestion for all 6 packaging surfaces pursuant to Rule 6 & 7 of PCR, 2011
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            fontSize: '0.85rem',
            fontFamily: 'var(--font-mono)',
            padding: '6px 12px',
            backgroundColor: 'var(--bg-surface-primary)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}>
            <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{capturedCount}</span>
            <span style={{ color: 'var(--text-muted)' }}> images logged</span>
          </div>

          <Link
            to={`/inspections/${inspection.id}/review`}
            className="btn btn-cyan btn-lg"
            style={{ gap: 8 }}
          >
            <span>Proceed to Pipeline</span>
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      {/* Upload Status Banner */}
      {uploadStatus && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 16px',
          borderRadius: 'var(--radius-sm)',
          marginBottom: 20,
          backgroundColor:
            uploadStatus.type === 'success'
              ? 'var(--verdict-pass-bg)'
              : uploadStatus.type === 'error'
              ? 'var(--verdict-fail-bg)'
              : 'rgba(99, 102, 241, 0.12)',
          border: `1px solid ${
            uploadStatus.type === 'success'
              ? 'var(--verdict-pass-border)'
              : uploadStatus.type === 'error'
              ? 'var(--verdict-fail-border)'
              : 'rgba(99, 102, 241, 0.3)'
          }`,
          color:
            uploadStatus.type === 'success'
              ? 'var(--verdict-pass)'
              : uploadStatus.type === 'error'
              ? '#FCA5A5'
              : 'var(--accent-cyan)',
          fontSize: '0.88rem',
        }}>
          {uploadStatus.type === 'success' ? (
            <CheckCircle2 size={16} />
          ) : uploadStatus.type === 'error' ? (
            <AlertCircle size={16} />
          ) : (
            <Clock size={16} className="animate-spin" />
          )}
          <span>{uploadStatus.message}</span>
        </div>
      )}

      {/* 6-Surface Workspace Component */}
      <SixSurfaceWorkspace
        inspectionId={inspection.id}
        surfaces={surfaces}
        onOpenHUD={(st) => setActiveHUDType(st)}
        onUploadFile={handleFileUpload}
        onSelectImage={(img) => setSelectedImage(img)}
      />

      {/* Camera HUD Modal */}
      {activeHUDType && (
        <CameraHUD
          surfaceType={activeHUDType}
          onCapture={handleHUDCapture}
          onClose={() => setActiveHUDType(null)}
        />
      )}

      {/* Image Inspection Modal */}
      {selectedImage && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(5, 8, 15, 0.88)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 24,
        }}>
          <div className="card" style={{ maxWidth: 760, width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="card-header">
              <div className="card-title">
                <ShieldCheck size={18} color="var(--accent-cyan)" />
                <span>Surface Evidence Details: {selectedImage.surface_type}</span>
              </div>
              <button
                onClick={() => setSelectedImage(null)}
                className="btn btn-outline btn-sm"
              >
                Close
              </button>
            </div>

            <div style={{
              height: 380,
              backgroundColor: '#000',
              borderRadius: 'var(--radius-sm)',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16,
            }}>
              <img
                src={getImageContentUrl(inspection.id, selectedImage.id)}
                alt="Full Evidence"
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, fontSize: '0.85rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Cryptographic SHA-256:</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-cyan)', wordBreak: 'break-all' }}>
                  {selectedImage.sha256_hash}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Dimensions:</span>
                <div style={{ fontFamily: 'var(--font-mono)' }}>
                  {selectedImage.image_width} × {selectedImage.image_height} px ({selectedImage.detected_format || 'JPEG'})
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>File Size:</span>
                <div style={{ fontFamily: 'var(--font-mono)' }}>
                  {selectedImage.file_size_bytes ? `${(selectedImage.file_size_bytes / 1024).toFixed(1)} KB` : 'N/A'}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Captured At:</span>
                <div>
                  {new Date(selectedImage.captured_at).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
