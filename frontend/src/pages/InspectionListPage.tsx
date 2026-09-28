import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  FolderKanban, 
  PlusCircle, 
  Search, 
  Filter, 
  ArrowUpRight, 
  Clock,
  Layers
} from 'lucide-react';
import { listInspections } from '../api/inspections';
import { Inspection, InspectionOverallStatus } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';

export const InspectionListPage: React.FC = () => {
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchInspections = async () => {
    try {
      setLoading(true);
      const filter = statusFilter === 'ALL' ? undefined : (statusFilter as InspectionOverallStatus);
      const data = await listInspections(filter);
      setInspections(data);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve inspections');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInspections();
  }, [statusFilter]);

  const filtered = inspections.filter((i) => {
    const q = searchTerm.toLowerCase();
    return (
      i.inspection_number.toLowerCase().includes(q) ||
      (i.retail_outlet_name && i.retail_outlet_name.toLowerCase().includes(q)) ||
      (i.product?.brand_name && i.product.brand_name.toLowerCase().includes(q)) ||
      (i.product?.product_name && i.product.product_name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="page-container">
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', marginBottom: 4 }}>
            Inspection Registry
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Complete historical and active packaged commodity inspection logs
          </p>
        </div>

        <Link to="/inspections/new" className="btn btn-primary" style={{ gap: 8 }}>
          <PlusCircle size={16} />
          <span>New Inspection</span>
        </Link>
      </div>

      <div className="card">
        {/* Filter Controls */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 16,
          marginBottom: 20,
          flexWrap: 'wrap',
        }}>
          <div style={{ position: 'relative', width: 320 }}>
            <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 11 }} />
            <input
              type="text"
              placeholder="Search by ID, outlet, or brand..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ paddingLeft: 36, fontSize: '0.88rem' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Filter size={15} color="var(--text-muted)" />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="form-select"
              style={{ width: 170, fontSize: '0.85rem' }}
            >
              <option value="ALL">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            <Clock size={28} className="animate-spin" style={{ margin: '0 auto 12px' }} />
            <div>Loading inspections...</div>
          </div>
        ) : error ? (
          <div style={{ padding: 24, color: 'var(--verdict-fail)', textAlign: 'center' }}>
            {error}
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            <div>No matching inspections found.</div>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Inspection Number</th>
                  <th>Retail Outlet</th>
                  <th>Product</th>
                  <th>Initiated</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((insp) => (
                  <tr key={insp.id}>
                    <td>
                      <Link
                        to={`/inspections/${insp.id}`}
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 600,
                          color: 'var(--accent-cyan)',
                        }}
                      >
                        {insp.inspection_number}
                      </Link>
                    </td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{insp.retail_outlet_name || 'N/A'}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {insp.retail_outlet_address || 'Unspecified address'}
                      </div>
                    </td>
                    <td>
                      {insp.product ? (
                        <div>
                          <div style={{ fontWeight: 500 }}>
                            {insp.product.brand_name} {insp.product.product_name}
                          </div>
                          {insp.product.gtin_barcode && (
                            <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                              GTIN: {insp.product.gtin_barcode}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Unlinked Product</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {new Date(insp.initiated_at).toLocaleDateString()}
                    </td>
                    <td>
                      <StatusBadge status={insp.overall_status} />
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <Link
                          to={`/inspections/${insp.id}/capture`}
                          className="btn btn-secondary btn-sm"
                        >
                          Capture
                        </Link>
                        <Link
                          to={`/inspections/${insp.id}/review`}
                          className="btn btn-primary btn-sm"
                          style={{ gap: 4 }}
                        >
                          <span>Review</span>
                          <ArrowUpRight size={12} />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
