import React, { useState, useEffect } from 'react';
import {
  Edit3,
  Trash2,
  CheckCircle,
  X,
  History,
  ShieldCheck,
  AlertTriangle,
  Plus,
} from 'lucide-react';
import {
  AdjudicatedOCRRegion,
  BoundingBoxNormalized,
  OCRRegionPatchRequest,
} from '../../types/api';
import { normalizeBox } from './BoundingBoxCanvas';

interface OCRRegionEditorProps {
  selectedRegion: AdjudicatedOCRRegion | null;
  pendingNewBox: BoundingBoxNormalized | null;
  onClose: () => void;
  onSaveCorrection: (regionId: string, patch: OCRRegionPatchRequest) => Promise<void>;
  onRejectRegion: (regionId: string, reason: string) => Promise<void>;
  onCreateRegion: (rawText: string, reason: string) => Promise<void>;
}

export const OCRRegionEditor: React.FC<OCRRegionEditorProps> = ({
  selectedRegion,
  pendingNewBox,
  onClose,
  onSaveCorrection,
  onRejectRegion,
  onCreateRegion,
}) => {
  const [editedText, setEditedText] = useState('');
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state with selected region or pending new box
  useEffect(() => {
    if (selectedRegion) {
      setEditedText(selectedRegion.effective_text || selectedRegion.raw_text || '');
      setReason(selectedRegion.reason || selectedRegion.active_adjudication?.reason || '');
      setError(null);
    } else if (pendingNewBox) {
      setEditedText('');
      setReason('Officer declared statutory declaration region');
      setError(null);
    }
  }, [selectedRegion, pendingNewBox]);

  if (!selectedRegion && !pendingNewBox) {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: 'var(--bg-surface-primary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          color: 'var(--text-secondary)',
          textAlign: 'center',
          fontSize: '13px',
        }}
      >
        <Edit3 size={24} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
        <p style={{ fontWeight: 500, color: 'var(--text-main)', marginBottom: '4px' }}>
          No Region Selected
        </p>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          Click an OCR bounding box on the image to inspect and correct its text, or click{' '}
          <strong style={{ color: 'var(--accent-cyan)' }}>Draw Region</strong> to create one.
        </p>
      </div>
    );
  }

  const isCreating = Boolean(pendingNewBox && !selectedRegion);
  const rawBbox = selectedRegion
    ? (selectedRegion.effective_bounding_box || selectedRegion.bounding_box)
    : pendingNewBox!;
  const bbox = normalizeBox(rawBbox);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editedText.trim()) {
      setError('Text content cannot be empty.');
      return;
    }
    setIsSubmitting(true);
    setError(null);

    try {
      if (isCreating) {
        await onCreateRegion(editedText.trim(), reason.trim() || 'Officer drawn region');
      } else if (selectedRegion) {
        await onSaveCorrection(selectedRegion.id, {
          corrected_text: editedText.trim(),
          corrected_bounding_box: selectedRegion.effective_bounding_box || selectedRegion.bounding_box,
          reason: reason.trim() || 'Inspector corrected OCR recognition text',
        });
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to save correction.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRegion) return;
    const confirmReject = window.confirm(
      'Are you sure you want to reject this OCR region as noise / artifact? It will be excluded from statutory evaluation.'
    );
    if (!confirmReject) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await onRejectRegion(
        selectedRegion.id,
        reason.trim() || 'Inspector flagged region as non-statutory artifact'
      );
    } catch (err: any) {
      setError(err?.message || 'Failed to reject region.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '16px',
        backgroundColor: 'var(--bg-surface-primary)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isCreating ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                color: 'var(--accent-cyan)',
                fontSize: '13px',
                fontWeight: 600,
              }}
            >
              <Plus size={15} /> New Bounding Region
            </span>
          ) : (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                color: 'var(--text-main)',
                fontSize: '13px',
                fontWeight: 600,
              }}
            >
              <Edit3 size={15} style={{ color: 'var(--accent-cyan)' }} /> Region Editor
            </span>
          )}

          {selectedRegion?.is_adjudicated && (
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
              Rev {selectedRegion.revision || selectedRegion.active_adjudication?.revision || 1}
            </span>
          )}

          {Boolean(selectedRegion?.is_rejected ?? (selectedRegion?.status === 'REJECTED')) && (
            <span
              style={{
                fontSize: '10px',
                fontWeight: 600,
                padding: '2px 6px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                color: 'var(--verdict-fail)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
              }}
            >
              REJECTED
            </span>
          )}
        </div>

        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
          }}
          title="Close Editor"
        >
          <X size={16} />
        </button>
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
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      {/* Region Metadata Badges */}
      {!isCreating && selectedRegion && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '8px',
            backgroundColor: 'var(--bg-surface-secondary)',
            padding: '10px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Confidence: </span>
            <strong style={{ color: selectedRegion.confidence > 0.8 ? 'var(--verdict-pass)' : 'var(--verdict-review)' }}>
              {(selectedRegion.confidence * 100).toFixed(1)}%
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Provenance: </span>
            <strong style={{ color: selectedRegion.is_adjudicated ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>
              {(selectedRegion.is_manually_created ?? (selectedRegion.status === 'MANUAL'))
                ? 'Manual Input'
                : selectedRegion.is_adjudicated
                ? 'Human Corrected'
                : 'Raw OCR'}
            </strong>
          </div>
        </div>
      )}

      {/* Normalized BBox readout */}
      <div
        style={{
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-secondary)',
          backgroundColor: 'var(--bg-canvas)',
          padding: '8px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>xmin: {bbox.xmin.toFixed(3)}</span>
          <span>ymin: {bbox.ymin.toFixed(3)}</span>
          <span>xmax: {bbox.xmax.toFixed(3)}</span>
          <span>ymax: {bbox.ymax.toFixed(3)}</span>
        </div>
      </div>

      {/* Original Text Display if different */}
      {!isCreating && selectedRegion && selectedRegion.is_adjudicated && (
        <div
          style={{
            fontSize: '12px',
            padding: '8px 10px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: 'var(--radius-sm)',
            border: '1px dashed var(--border-muted)',
          }}
        >
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Original Perception OCR:
          </span>
          <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic', marginTop: '2px' }}>
            "{selectedRegion.original_text || selectedRegion.raw_text}"
          </p>
        </div>
      )}

      {/* Edit Form */}
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div>
          <label
            htmlFor="ocr-edit-text-input"
            style={{
              display: 'block',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--text-secondary)',
              marginBottom: '6px',
            }}
          >
            {isCreating ? 'Declaration Text' : 'Effective Recognized Text'}
          </label>
          <textarea
            id="ocr-edit-text-input"
            rows={3}
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            placeholder="Enter accurate statutory text..."
            style={{
              width: '100%',
              padding: '8px 12px',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-muted)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-main)',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              resize: 'vertical',
            }}
          />
        </div>

        <div>
          <label
            htmlFor="ocr-edit-reason-input"
            style={{
              display: 'block',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--text-secondary)',
              marginBottom: '6px',
            }}
          >
            Legal / Audit Justification
          </label>
          <input
            id="ocr-edit-reason-input"
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason for correction / addition..."
            style={{
              width: '100%',
              padding: '8px 12px',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-muted)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-main)',
              fontSize: '12px',
            }}
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
          <button
            id="btn-save-ocr-correction"
            type="submit"
            disabled={isSubmitting}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--primary-600)',
              color: '#fff',
              border: 'none',
              fontSize: '12px',
              fontWeight: 600,
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              opacity: isSubmitting ? 0.6 : 1,
            }}
          >
            <CheckCircle size={14} />
            {isCreating ? 'Create Region' : 'Save Correction'}
          </button>

          {!isCreating && selectedRegion && !(selectedRegion.is_rejected ?? (selectedRegion.status === 'REJECTED')) && (
            <button
              id="btn-reject-ocr-region"
              type="button"
              onClick={handleReject}
              disabled={isSubmitting}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--verdict-fail-bg)',
                color: 'var(--verdict-fail)',
                border: '1px solid var(--verdict-fail-border)',
                fontSize: '12px',
                fontWeight: 600,
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
              }}
              title="Reject as noise/artifact"
            >
              <Trash2 size={14} />
              Reject
            </button>
          )}
        </div>
      </form>
    </div>
  );
};
