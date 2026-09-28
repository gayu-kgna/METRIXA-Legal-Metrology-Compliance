import React, { useState } from 'react';
import { X, PlusCircle, AlertCircle, ShieldCheck } from 'lucide-react';
import { ManualObservationCreateRequest, SurfaceRead } from '../../types/api';

interface ManualObservationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ManualObservationCreateRequest) => Promise<void>;
  surfaces: SurfaceRead[];
  selectedSurfaceId?: string | null;
}

const STATUTORY_FIELDS = [
  { value: 'MAXIMUM_RETAIL_PRICE', label: 'Maximum Retail Price (MRP)' },
  { value: 'NET_QUANTITY', label: 'Net Quantity / Count' },
  { value: 'UNIT_SALE_PRICE', label: 'Unit Sale Price (USP)' },
  { value: 'DATE_OF_MANUFACTURE', label: 'Date of Manufacture / Packing' },
  { value: 'BEST_BEFORE_DATE', label: 'Best Before / Expiry Date' },
  { value: 'MANUFACTURER_NAME', label: 'Manufacturer / Packer Name' },
  { value: 'MANUFACTURER_ADDRESS', label: 'Manufacturer / Packer Address' },
  { value: 'CONSUMER_CARE_EMAIL', label: 'Consumer Care (Email/Phone)' },
  { value: 'COUNTRY_OF_ORIGIN', label: 'Country of Origin' },
  { value: 'GENERIC_NAME', label: 'Generic / Common Commodity Name' },
  { value: 'OTHER_DECLARATION', label: 'Other Statutory Declaration' },
];

export const ManualObservationDialog: React.FC<ManualObservationDialogProps> = ({
  isOpen,
  onClose,
  onSubmit,
  surfaces,
  selectedSurfaceId,
}) => {
  const [surfaceId, setSurfaceId] = useState<string>(selectedSurfaceId || surfaces[0]?.id || '');
  const [fieldType, setFieldType] = useState<string>('MAXIMUM_RETAIL_PRICE');
  const [rawValue, setRawValue] = useState<string>('');
  const [reason, setReason] = useState<string>('Officer physical inspection declaration');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawValue.trim()) {
      setError('Please provide the raw declaration value.');
      return;
    }
    if (!reason.trim()) {
      setError('An audit justification is mandatory for manual officer declarations.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    // Simple automatic normalization helper based on field type
    const normalized: Record<string, any> = { display: rawValue.trim() };
    if (fieldType === 'MAXIMUM_RETAIL_PRICE') {
      const match = rawValue.match(/(\d+(?:\.\d+)?)/);
      if (match) {
        normalized.amount = parseFloat(match[1]);
        normalized.currency = 'INR';
      }
    } else if (fieldType === 'NET_QUANTITY') {
      const match = rawValue.match(/(\d+(?:\.\d+)?)\s*([a-zA-Z]+)/);
      if (match) {
        normalized.value = parseFloat(match[1]);
        normalized.unit = match[2];
      }
    }

    try {
      await onSubmit({
        surface_id: surfaceId || undefined,
        field_type: fieldType,
        raw_value: rawValue.trim(),
        normalized_value: normalized,
        reason: reason.trim(),
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to create manual observation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        id="manual-observation-modal"
        style={{
          width: '100%',
          maxWidth: '520px',
          backgroundColor: 'var(--bg-surface-primary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-highlight)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            backgroundColor: 'var(--bg-surface-secondary)',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={20} style={{ color: '#C084FC' }} />
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)' }}>
                Add Manual Statutory Declaration
              </h3>
              <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Provenance: OFFICER_INPUT | Full Audit Log Trail
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {error && (
            <div
              style={{
                padding: '10px 14px',
                backgroundColor: 'var(--verdict-fail-bg)',
                border: '1px solid var(--verdict-fail-border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--verdict-fail)',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={15} />
              {error}
            </div>
          )}

          {/* Surface face select */}
          {surfaces.length > 0 && (
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '6px',
                }}
              >
                Package Surface
              </label>
              <select
                id="select-manual-obs-surface"
                value={surfaceId}
                onChange={(e) => setSurfaceId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: 'var(--bg-canvas)',
                  border: '1px solid var(--border-muted)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-main)',
                  fontSize: '13px',
                }}
              >
                {surfaces.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.surface_type} {s.original_filename ? `(${s.original_filename})` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Statutory Field Type */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              Statutory Field Type
            </label>
            <select
              id="select-manual-obs-field"
              value={fieldType}
              onChange={(e) => setFieldType(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-muted)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-main)',
                fontSize: '13px',
              }}
            >
              {STATUTORY_FIELDS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          {/* Raw Text Value */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              Declaration Text (as printed on physical package)
            </label>
            <input
              id="input-manual-obs-value"
              type="text"
              value={rawValue}
              onChange={(e) => setRawValue(e.target.value)}
              placeholder="e.g. ₹ 199.00 (Incl. of all taxes) or 500 g"
              style={{
                width: '100%',
                padding: '10px 12px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-muted)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-main)',
                fontFamily: 'var(--font-mono)',
                fontSize: '13px',
              }}
            />
          </div>

          {/* Legal / Audit Justification */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
              }}
            >
              Inspector Legal Justification (Mandatory)
            </label>
            <textarea
              id="input-manual-obs-reason"
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="State why this declaration was added manually..."
              style={{
                width: '100%',
                padding: '8px 12px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-muted)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-main)',
                fontSize: '12px',
                resize: 'none',
              }}
            />
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '8px 16px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'transparent',
                border: '1px solid var(--border-muted)',
                color: 'var(--text-secondary)',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              id="btn-submit-manual-observation"
              type="submit"
              disabled={isSubmitting}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 18px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#7C3AED',
                color: '#fff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                opacity: isSubmitting ? 0.6 : 1,
              }}
            >
              <PlusCircle size={15} />
              {isSubmitting ? 'Saving...' : 'Add Declaration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
