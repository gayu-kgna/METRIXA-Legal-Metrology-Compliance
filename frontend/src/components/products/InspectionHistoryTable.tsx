import React from 'react';
import { Link } from 'react-router-dom';
import { ProductInspectionItem } from '../../types/api';
import { StatusBadge } from '../common/StatusBadge';
import { 
  FolderKanban, 
  FileText, 
  Layers, 
  ExternalLink, 
  Eye, 
  Calendar, 
  MapPin, 
  ShieldCheck 
} from 'lucide-react';

interface InspectionHistoryTableProps {
  inspections: ProductInspectionItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
  onPageChange: (newPage: number) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  loading?: boolean;
}

export const InspectionHistoryTable: React.FC<InspectionHistoryTableProps> = ({
  inspections,
  pagination,
  onPageChange,
  statusFilter,
  onStatusFilterChange,
  loading,
}) => {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Filters Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <FolderKanban size={18} color="var(--accent-cyan)" />
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Inspection History</h3>
          <span style={{
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            backgroundColor: 'var(--bg-surface-tertiary)',
            padding: '2px 8px',
            borderRadius: 4,
          }}>
            {pagination.total_items} recorded
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
            className="input"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.82rem' }}
          >
            <option value="">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="PENDING">Pending Review</option>
            <option value="ACTION_REQUIRED">Action Required</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading inspection records...
          </div>
        ) : inspections.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            No inspection records found matching the specified filters.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '10px 12px' }}>Inspection Number</th>
                <th style={{ padding: '10px 12px' }}>Date / Time</th>
                <th style={{ padding: '10px 12px' }}>Location / Outlet</th>
                <th style={{ padding: '10px 12px' }}>Inspector</th>
                <th style={{ padding: '10px 12px' }}>Label Version</th>
                <th style={{ padding: '10px 12px' }}>Status</th>
                <th style={{ padding: '10px 12px' }}>Rule Verdict</th>
                <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {inspections.map((insp) => (
                <tr key={insp.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '12px' }}>
                    <Link
                      to={`/inspections/${insp.id}`}
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        color: 'var(--accent-cyan)',
                        textDecoration: 'none',
                      }}
                    >
                      {insp.inspection_number}
                    </Link>
                  </td>

                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Calendar size={13} />
                      <span>{new Date(insp.initiated_at).toLocaleDateString()}</span>
                    </div>
                  </td>

                  <td style={{ padding: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <MapPin size={13} color="var(--text-muted)" />
                      <span>{insp.retail_outlet_name || 'Field Site'}</span>
                    </div>
                  </td>

                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                    <div>{insp.inspector_name || 'Officer'}</div>
                    {insp.inspector_badge && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {insp.inspector_badge}
                      </div>
                    )}
                  </td>

                  <td style={{ padding: '12px' }}>
                    {insp.label_version_tag ? (
                      <span style={{
                        fontSize: '0.75rem',
                        fontFamily: 'var(--font-mono)',
                        padding: '2px 6px',
                        borderRadius: 4,
                        backgroundColor: 'rgba(6, 182, 212, 0.15)',
                        color: 'var(--accent-cyan)',
                      }}>
                        {insp.label_version_tag}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </td>

                  <td style={{ padding: '12px' }}>
                    <StatusBadge status={insp.overall_status} size="sm" />
                  </td>

                  <td style={{ padding: '12px' }}>
                    {insp.rule_verdict ? (
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        color: insp.rule_verdict === 'PASS' ? 'var(--verdict-pass)' : (insp.rule_verdict === 'FAIL' ? 'var(--verdict-fail)' : 'var(--verdict-review)'),
                      }}>
                        {insp.rule_verdict}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>Pending</span>
                    )}
                  </td>

                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                      <Link
                        to={`/inspections/${insp.id}/results`}
                        className="btn btn-outline btn-sm"
                        style={{ padding: '4px 8px' }}
                        title="View Compliance Results"
                      >
                        <Eye size={13} />
                      </Link>

                      <Link
                        to={`/inspections/${insp.id}/evidence`}
                        className="btn btn-outline btn-sm"
                        style={{ padding: '4px 8px' }}
                        title="View Evidence Browser"
                      >
                        <Layers size={13} />
                      </Link>

                      {insp.has_report && (
                        <Link
                          to={`/inspections/${insp.id}/reports`}
                          className="btn btn-primary btn-sm"
                          style={{ padding: '4px 8px' }}
                          title="View Dossier Report"
                        >
                          <FileText size={13} />
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Controls */}
      {pagination.total_pages > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingTop: 12,
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.85rem',
        }}>
          <span style={{ color: 'var(--text-muted)' }}>
            Page {pagination.page} of {pagination.total_pages} ({pagination.total_items} total)
          </span>

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={!pagination.has_previous}
              className="btn btn-outline btn-sm"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={!pagination.has_next}
              className="btn btn-outline btn-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
