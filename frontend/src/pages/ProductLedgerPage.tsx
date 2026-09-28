import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listProducts, PaginatedProductLedger } from '../api/products';
import { ProductLedgerItem } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { 
  Layers, 
  Search, 
  Filter, 
  Calendar, 
  FolderKanban, 
  ArrowRight, 
  Clock, 
  CheckCircle2, 
  PlusCircle, 
  Barcode 
} from 'lucide-react';

export const ProductLedgerPage: React.FC = () => {
  const navigate = useNavigate();

  const [products, setProducts] = useState<ProductLedgerItem[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 15,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_previous: false,
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = useCallback(async (page: number = 1) => {
    try {
      setLoading(true);
      setError(null);
      const res = await listProducts({
        q: searchTerm || undefined,
        category: categoryFilter || undefined,
        page,
        page_size: 15,
        sort_by: 'brand_name',
        sort_order: 'asc',
      });
      setProducts(res.data);
      setPagination(res.pagination);
    } catch (err: any) {
      setError(err.message || 'Failed to load product ledger');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, categoryFilter]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchProducts(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [fetchProducts]);

  return (
    <div className="page-container">
      {/* Top Banner */}
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
            <Layers size={24} color="var(--accent-cyan)" />
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>
              National Packaged Commodity Ledger
            </h1>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Persistent historical intelligence repository tracking packaged commodities, inspection lifecycles, and label revisions
          </p>
        </div>

        <Link to="/inspections/new" className="btn btn-primary" style={{ gap: 8 }}>
          <PlusCircle size={16} />
          <span>New Inspection</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{
        padding: '16px 20px',
        marginBottom: 24,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 260 }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: 380 }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search by brand, product name, GTIN/barcode, or manufacturer..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input"
              style={{ paddingLeft: 36, width: '100%' }}
              id="search-products-input"
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Filter size={15} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Filter by category..."
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="input"
              style={{ width: 180 }}
            />
          </div>
        </div>

        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {pagination.total_items} commodities registered
        </div>
      </div>

      {/* Ledger Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          {loading ? (
            <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
              <Clock size={28} className="animate-spin" style={{ margin: '0 auto 12px', color: 'var(--accent-cyan)' }} />
              <div>Querying product ledger...</div>
            </div>
          ) : error ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--verdict-fail)' }}>
              {error}
            </div>
          ) : products.length === 0 ? (
            <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
              No packaged commodities found matching your search.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  color: 'var(--text-muted)',
                  textAlign: 'left',
                }}>
                  <th style={{ padding: '12px 16px' }}>Commodity / Brand</th>
                  <th style={{ padding: '12px 16px' }}>GTIN / SKU</th>
                  <th style={{ padding: '12px 16px' }}>Category</th>
                  <th style={{ padding: '12px 16px' }}>Manufacturer Claimed</th>
                  <th style={{ padding: '12px 16px', textAlign: 'center' }}>Inspections</th>
                  <th style={{ padding: '12px 16px' }}>Latest Version</th>
                  <th style={{ padding: '12px 16px' }}>Latest Date</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => navigate(`/products/${p.id}`)}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      transition: 'background-color 0.15s ease',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-surface-secondary)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
                  >
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                        {p.brand_name}
                      </div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                        {p.product_name}
                      </div>
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      {p.gtin_barcode ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>
                          <Barcode size={14} />
                          <span>{p.gtin_barcode}</span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>Unassigned</span>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      <span style={{
                        fontSize: '0.75rem',
                        padding: '2px 8px',
                        borderRadius: 4,
                        backgroundColor: 'var(--bg-surface-tertiary)',
                        color: 'var(--text-secondary)',
                      }}>
                        {p.category || 'General'}
                      </span>
                    </td>

                    <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {p.manufacturer_claimed || '—'}
                    </td>

                    <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        padding: '3px 8px',
                        borderRadius: 12,
                        backgroundColor: p.inspection_count > 0 ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-surface-tertiary)',
                        color: p.inspection_count > 0 ? 'var(--accent-cyan)' : 'var(--text-muted)',
                      }}>
                        {p.inspection_count}
                      </span>
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      {p.latest_label_version ? (
                        <span style={{
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-mono)',
                          padding: '2px 6px',
                          borderRadius: 4,
                          backgroundColor: 'rgba(99, 102, 241, 0.15)',
                          color: 'var(--primary-500)',
                          fontWeight: 600,
                        }}>
                          {p.latest_label_version}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>None</span>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                      {p.latest_inspection_date ? (
                        new Date(p.latest_inspection_date).toLocaleDateString()
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Never</span>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <Link
                        to={`/products/${p.id}`}
                        className="btn btn-outline btn-sm"
                        style={{ gap: 6 }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span>History</span>
                        <ArrowRight size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination Footer */}
        {pagination.total_pages > 1 && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 20px',
            backgroundColor: 'var(--bg-surface-secondary)',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.85rem',
          }}>
            <span style={{ color: 'var(--text-muted)' }}>
              Showing Page {pagination.page} of {pagination.total_pages} ({pagination.total_items} total)
            </span>

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => fetchProducts(pagination.page - 1)}
                disabled={!pagination.has_previous || loading}
                className="btn btn-outline btn-sm"
              >
                Previous
              </button>
              <button
                onClick={() => fetchProducts(pagination.page + 1)}
                disabled={!pagination.has_next || loading}
                className="btn btn-outline btn-sm"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
