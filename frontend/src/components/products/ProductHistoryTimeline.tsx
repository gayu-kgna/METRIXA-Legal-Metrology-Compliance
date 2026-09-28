import React from 'react';
import { Link } from 'react-router-dom';
import { TimelineEvent } from '../../types/api';
import { 
  Package, 
  FolderKanban, 
  Camera, 
  CheckCircle, 
  FileCheck, 
  Scale, 
  Layers, 
  FileText,
  UserCheck,
  Calendar,
  ExternalLink
} from 'lucide-react';

interface ProductHistoryTimelineProps {
  events: TimelineEvent[];
  loading?: boolean;
}

export const ProductHistoryTimeline: React.FC<ProductHistoryTimelineProps> = ({ events, loading }) => {
  if (loading) {
    return (
      <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading historical event timeline...
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        No historical lifecycle events recorded for this commodity yet.
      </div>
    );
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'PRODUCT_REGISTERED':
        return <Package size={16} color="var(--primary-500)" />;
      case 'INSPECTION_CREATED':
        return <FolderKanban size={16} color="var(--accent-cyan)" />;
      case 'EVIDENCE_CAPTURED':
        return <Camera size={16} color="var(--accent-amber)" />;
      case 'HUMAN_ADJUDICATION':
        return <UserCheck size={16} color="#A855F7" />;
      case 'RULES_EVALUATED':
        return <Scale size={16} color="var(--verdict-pass)" />;
      case 'LABEL_VERSION_OBSERVED':
        return <Layers size={16} color="var(--accent-cyan)" />;
      case 'REPORT_GENERATED':
        return <FileText size={16} color="var(--verdict-pass)" />;
      default:
        return <CheckCircle size={16} color="var(--text-secondary)" />;
    }
  };

  const getEventBadgeColor = (type: string) => {
    switch (type) {
      case 'PRODUCT_REGISTERED':
        return 'rgba(99, 102, 241, 0.15)';
      case 'INSPECTION_CREATED':
        return 'rgba(6, 182, 212, 0.15)';
      case 'EVIDENCE_CAPTURED':
        return 'rgba(245, 158, 11, 0.15)';
      case 'HUMAN_ADJUDICATION':
        return 'rgba(168, 85, 247, 0.15)';
      case 'RULES_EVALUATED':
        return 'rgba(16, 185, 129, 0.15)';
      case 'LABEL_VERSION_OBSERVED':
        return 'rgba(6, 182, 212, 0.15)';
      case 'REPORT_GENERATED':
        return 'rgba(16, 185, 129, 0.15)';
      default:
        return 'var(--bg-surface-tertiary)';
    }
  };

  return (
    <div style={{ position: 'relative', paddingLeft: 24, margin: '16px 0' }}>
      {/* Vertical line */}
      <div style={{
        position: 'absolute',
        top: 10,
        bottom: 10,
        left: 11,
        width: 2,
        backgroundColor: 'var(--border-muted)',
      }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {events.map((evt, idx) => (
          <div key={evt.event_id || idx} style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: 16 }}>
            {/* Circle Node */}
            <div style={{
              position: 'absolute',
              left: -24,
              top: 2,
              width: 24,
              height: 24,
              borderRadius: '50%',
              backgroundColor: 'var(--bg-surface-primary)',
              border: '2px solid var(--border-highlight)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 2,
            }}>
              {getEventIcon(evt.event_type)}
            </div>

            {/* Event Content Card */}
            <div className="card" style={{ flex: 1, padding: '14px 18px', backgroundColor: 'var(--bg-surface-primary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    padding: '2px 8px',
                    borderRadius: 4,
                    backgroundColor: getEventBadgeColor(evt.event_type),
                    color: 'var(--text-main)',
                  }}>
                    {evt.event_type.replace(/_/g, ' ')}
                  </span>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
                    {evt.title}
                  </h4>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  <Calendar size={13} />
                  <span>{new Date(evt.timestamp).toLocaleString()}</span>
                </div>
              </div>

              <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '4px 0 8px', lineHeight: 1.4 }}>
                {evt.description}
              </p>

              {/* Event Metadata & Links */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', fontSize: '0.78rem' }}>
                {evt.actor_name && (
                  <span style={{ color: 'var(--text-muted)' }}>
                    Actor: <strong style={{ color: 'var(--text-main)' }}>{evt.actor_name}</strong> {evt.badge_number && `(${evt.badge_number})`}
                  </span>
                )}

                {evt.inspection_id && (
                  <Link
                    to={`/inspections/${evt.inspection_id}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      color: 'var(--accent-cyan)',
                      textDecoration: 'none',
                    }}
                  >
                    <span>View Inspection ({evt.inspection_number || 'Details'})</span>
                    <ExternalLink size={12} />
                  </Link>
                )}

                {evt.metadata?.sha256 && (
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                    SHA-256: {evt.metadata.sha256.substring(0, 16)}...
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
