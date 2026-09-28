import React from 'react';
import { 
  Camera, 
  Upload, 
  CheckCircle2, 
  CircleDashed, 
  Image as ImageIcon, 
  Eye, 
  Plus, 
  Layers 
} from 'lucide-react';
import { SurfaceType, SurfaceRead } from '../../types/api';
import { getImageContentUrl } from '../../api/images';

export interface SurfaceCardData {
  type: SurfaceType;
  label: string;
  isPdp: boolean;
  surfaces: SurfaceRead[];
}

const SURFACES_DEF: { type: SurfaceType; label: string; isPdp: boolean }[] = [
  { type: 'FRONT_PDP', label: 'Front (Principal Display Panel)', isPdp: true },
  { type: 'BACK', label: 'Back Surface', isPdp: false },
  { type: 'LEFT', label: 'Left Lateral Surface', isPdp: false },
  { type: 'RIGHT', label: 'Right Lateral Surface', isPdp: false },
  { type: 'TOP', label: 'Top Surface', isPdp: false },
  { type: 'BOTTOM', label: 'Bottom Surface', isPdp: false },
];

interface SixSurfaceWorkspaceProps {
  inspectionId: string;
  surfaces: SurfaceRead[];
  onOpenHUD: (surfaceType: SurfaceType) => void;
  onUploadFile: (surfaceType: SurfaceType, file: File) => void;
  onSelectImage?: (image: SurfaceRead) => void;
}

export const SixSurfaceWorkspace: React.FC<SixSurfaceWorkspaceProps> = ({
  inspectionId,
  surfaces,
  onOpenHUD,
  onUploadFile,
  onSelectImage,
}) => {
  const fileInputRefs = React.useRef<{ [key: string]: HTMLInputElement | null }>({});

  return (
    <div className="grid-3" style={{ gap: 20 }}>
      {SURFACES_DEF.map((def) => {
        const matchingSurfaces = surfaces.filter((s) => s.surface_type === def.type);
        const hasImages = matchingSurfaces.length > 0;
        const latestSurface = hasImages ? matchingSurfaces[matchingSurfaces.length - 1] : null;

        return (
          <div
            key={def.type}
            className="card"
            style={{
              borderColor: def.isPdp ? 'var(--primary-glow)' : undefined,
              boxShadow: def.isPdp ? '0 0 15px rgba(99, 102, 241, 0.15)' : undefined,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            {/* Header */}
            <div>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: 12,
              }}>
                <div>
                  <h4 style={{
                    fontSize: '1rem',
                    color: def.isPdp ? 'var(--accent-cyan)' : 'var(--text-main)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}>
                    {def.label}
                    {def.isPdp && (
                      <span style={{
                        fontSize: '0.65rem',
                        backgroundColor: 'var(--primary-500)',
                        color: '#FFF',
                        padding: '2px 5px',
                        borderRadius: 4,
                      }}>
                        PDP
                      </span>
                    )}
                  </h4>
                  <div style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono)',
                    marginTop: 2,
                  }}>
                    {def.type}
                  </div>
                </div>

                {hasImages ? (
                  <span className="badge badge-pass">
                    <CheckCircle2 size={12} />
                    <span>{matchingSurfaces.length} Image{matchingSurfaces.length > 1 ? 's' : ''}</span>
                  </span>
                ) : (
                  <span className="badge badge-na">
                    <CircleDashed size={12} />
                    <span>Pending</span>
                  </span>
                )}
              </div>

              {/* Thumbnail / Viewport */}
              <div style={{
                height: 180,
                backgroundColor: 'var(--bg-canvas)',
                borderRadius: 'var(--radius-sm)',
                border: '1px dashed var(--border-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                position: 'relative',
                marginBottom: 14,
              }}>
                {latestSurface ? (
                  <>
                    <img
                      src={getImageContentUrl(inspectionId, latestSurface.id)}
                      alt={`Captured ${def.type}`}
                      style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    />
                    <div style={{
                      position: 'absolute',
                      bottom: 0,
                      left: 0,
                      right: 0,
                      backgroundColor: 'rgba(9, 13, 22, 0.85)',
                      padding: '4px 8px',
                      fontSize: '0.68rem',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-secondary)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      backdropFilter: 'blur(4px)',
                    }}>
                      <span>SHA: {latestSurface.sha256_hash.substring(0, 8)}...</span>
                      {latestSurface.image_width && (
                        <span>{latestSurface.image_width}×{latestSurface.image_height}</span>
                      )}
                    </div>
                  </>
                ) : (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                    <ImageIcon size={36} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
                    <div style={{ fontSize: '0.8rem' }}>No image captured yet</div>
                  </div>
                )}
              </div>
            </div>

            {/* Action Bar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <button
                  onClick={() => onOpenHUD(def.type)}
                  className="btn btn-primary btn-sm"
                  style={{ gap: 6 }}
                  id={`btn-take-photo-${def.type.toLowerCase()}`}
                >
                  <Camera size={14} />
                  <span>Take Photo (Camera HUD)</span>
                </button>

                <button
                  onClick={() => fileInputRefs.current[def.type]?.click()}
                  className="btn btn-secondary btn-sm"
                  style={{ gap: 6 }}
                  id={`btn-upload-photo-${def.type.toLowerCase()}`}
                >
                  <Upload size={14} />
                  <span>Upload Photo</span>
                </button>
              </div>

              {/* Hidden File Input */}
              <input
                type="file"
                ref={(el) => { fileInputRefs.current[def.type] = el; }}
                style={{ display: 'none' }}
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    onUploadFile(def.type, e.target.files[0]);
                    e.target.value = '';
                  }
                }}
              />

              {hasImages && onSelectImage && (
                <button
                  onClick={() => onSelectImage(latestSurface!)}
                  className="btn btn-outline btn-sm"
                  style={{ gap: 6, width: '100%' }}
                >
                  <Eye size={14} />
                  <span>Review Evidence ({matchingSurfaces.length})</span>
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
