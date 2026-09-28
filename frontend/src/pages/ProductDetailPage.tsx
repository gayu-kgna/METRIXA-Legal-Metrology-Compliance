import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  getProduct, 
  getProductInspections, 
  getProductLabelVersions, 
  getProductTimeline, 
  getLabelVersionChanges 
} from '../api/products';
import { 
  ProductDetail, 
  ProductInspectionItem, 
  LabelVersionDetail, 
  TimelineEvent, 
  LabelDiffResponse 
} from '../types/api';
import { ProductHistoryTimeline } from '../components/products/ProductHistoryTimeline';
import { LabelVersionHistory } from '../components/products/LabelVersionHistory';
import { LabelChangeViewer } from '../components/products/LabelChangeViewer';
import { InspectionHistoryTable } from '../components/products/InspectionHistoryTable';
import { 
  Layers, 
  ArrowLeft, 
  Calendar, 
  Clock, 
  FolderKanban, 
  Barcode, 
  Building2, 
  Tag, 
  GitCompare, 
  History, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';

export const ProductDetailPage: React.FC = () => {
  const { productId } = useParams<{ productId: string }>();

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'inspections' | 'labels' | 'timeline'>('overview');

  // Inspections tab state
  const [inspections, setInspections] = useState<ProductInspectionItem[]>([]);
  const [inspPagination, setInspPagination] = useState({
    page: 1,
    page_size: 10,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_previous: false,
  });
  const [statusFilter, setStatusFilter] = useState('');

  // Labels & Changes tab state
  const [labelVersions, setLabelVersions] = useState<LabelVersionDetail[]>([]);
  const [activeDiff, setActiveDiff] = useState<LabelDiffResponse | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  // Timeline tab state
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

  // Loading & error
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProduct = useCallback(async () => {
    if (!productId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getProduct(productId);
      setProduct(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load product details');
    } finally {
      setLoading(false);
    }
  }, [productId]);

  const fetchInspections = useCallback(async (page: number = 1) => {
    if (!productId) return;
    try {
      const res = await getProductInspections(productId, {
        status_filter: statusFilter || undefined,
        page,
        page_size: 10,
      });
      setInspections(res.data);
      setInspPagination(res.pagination);
    } catch (err: any) {
      console.error('Failed to load product inspections:', err);
    }
  }, [productId, statusFilter]);

  const fetchLabelVersions = useCallback(async () => {
    if (!productId) return;
    try {
      const lvs = await getProductLabelVersions(productId);
      setLabelVersions(lvs);
      if (lvs.length > 1) {
        // Auto-load diff between first and latest
        setDiffLoading(true);
        const diffRes = await getLabelVersionChanges(productId, lvs[0].id, lvs[lvs.length - 1].id);
        setActiveDiff(diffRes);
        setDiffLoading(false);
      }
    } catch (err: any) {
      console.error('Failed to load label versions:', err);
      setDiffLoading(false);
    }
  }, [productId]);

  const fetchTimeline = useCallback(async () => {
    if (!productId) return;
    try {
      const events = await getProductTimeline(productId);
      setTimelineEvents(events);
    } catch (err: any) {
      console.error('Failed to load product timeline:', err);
    }
  }, [productId]);

  useEffect(() => {
    fetchProduct();
  }, [fetchProduct]);

  useEffect(() => {
    if (activeTab === 'inspections') fetchInspections(1);
    if (activeTab === 'labels') fetchLabelVersions();
    if (activeTab === 'timeline') fetchTimeline();
  }, [activeTab, fetchInspections, fetchLabelVersions, fetchTimeline]);

  const handleCompareVersions = async (fromId: string, toId: string) => {
    if (!productId) return;
    try {
      setDiffLoading(true);
      const diff = await getLabelVersionChanges(productId, fromId, toId);
      setActiveDiff(diff);
    } catch (err: any) {
      console.error('Failed to compare versions:', err);
    } finally {
      setDiffLoading(false);
    }
  };

  if (loading && !product) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 80 }}>
        <Clock size={32} className="animate-spin" style={{ margin: '0 auto 16px', color: 'var(--accent-cyan)' }} />
        <div>Loading product history profile...</div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="page-container">
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <AlertCircle size={36} color="var(--verdict-fail)" style={{ margin: '0 auto 12px' }} />
          <h3>Error Loading Product</h3>
          <p style={{ color: 'var(--text-secondary)', margin: '8px 0 16px' }}>{error}</p>
          <Link to="/products" className="btn btn-primary btn-sm">Back to Product Ledger</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Back Link */}
      <div style={{ marginBottom: 16 }}>
        <Link to="/products" style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          color: 'var(--text-secondary)',
          textDecoration: 'none',
          fontSize: '0.85rem',
        }}>
          <ArrowLeft size={16} />
          <span>Back to Product Ledger</span>
        </Link>
      </div>

      {/* Product Hero Header */}
      <div className="card" style={{ marginBottom: 24, padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                padding: '2px 8px',
                borderRadius: 4,
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                color: 'var(--primary-500)',
              }}>
                {product.category || 'General Commodity'}
              </span>
              {product.gtin_barcode && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <Barcode size={14} />
                  <span>GTIN: {product.gtin_barcode}</span>
                </div>
              )}
            </div>

            <h1 style={{ fontSize: '1.8rem', fontWeight: 700, margin: '4px 0' }}>
              {product.brand_name} {product.product_name}
            </h1>

            {product.manufacturer_claimed && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                <Building2 size={14} color="var(--text-muted)" />
                <span>{product.manufacturer_claimed}</span>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <div style={{
              textAlign: 'center',
              padding: '10px 16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--bg-surface-secondary)',
            }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Inspections</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: 'var(--accent-cyan)' }}>
                {product.inspection_count}
              </div>
            </div>

            <div style={{
              textAlign: 'center',
              padding: '10px 16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--bg-surface-secondary)',
            }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Latest Version</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: 'var(--primary-500)' }}>
                {product.latest_label_version || 'v1.0'}
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div style={{
          display: 'flex',
          gap: 12,
          borderTop: '1px solid var(--border-subtle)',
          marginTop: 20,
          paddingTop: 16,
        }}>
          <button
            onClick={() => setActiveTab('overview')}
            className={`btn ${activeTab === 'overview' ? 'btn-primary' : 'btn-outline'} btn-sm`}
            style={{ gap: 6 }}
          >
            <span>Overview</span>
          </button>

          <button
            onClick={() => setActiveTab('inspections')}
            className={`btn ${activeTab === 'inspections' ? 'btn-primary' : 'btn-outline'} btn-sm`}
            style={{ gap: 6 }}
          >
            <FolderKanban size={14} />
            <span>Inspection History ({product.inspection_count})</span>
          </button>

          <button
            onClick={() => setActiveTab('labels')}
            className={`btn ${activeTab === 'labels' ? 'btn-primary' : 'btn-outline'} btn-sm`}
            style={{ gap: 6 }}
          >
            <Layers size={14} />
            <span>Label Versions & Changes</span>
          </button>

          <button
            onClick={() => setActiveTab('timeline')}
            className={`btn ${activeTab === 'timeline' ? 'btn-primary' : 'btn-outline'} btn-sm`}
            style={{ gap: 6 }}
          >
            <History size={14} />
            <span>Lifecycle Timeline</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Product Overview */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Quick Metrics */}
          <div className="grid-3" style={{ gap: 16 }}>
            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                First Observed Inspection
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                {product.first_inspection_date ? new Date(product.first_inspection_date).toLocaleDateString() : 'None Recorded'}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                Most Recent Inspection
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                {product.latest_inspection_date ? new Date(product.latest_inspection_date).toLocaleDateString() : 'None Recorded'}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                Latest Operational Status
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                {product.latest_status || 'DRAFT'}
              </div>
            </div>
          </div>

          {/* Known Statutory Declarations */}
          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 6 }}>
              Known Package Declarations (Current Profile)
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
              Accumulated statutory declarations verified through inspections and human adjudication
            </p>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px', width: '35%' }}>Statutory Field</th>
                    <th style={{ padding: '8px 12px' }}>Latest Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(product.known_declarations || {}).length === 0 ? (
                    <tr>
                      <td colSpan={2} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                        No statutory declarations recorded for this product yet.
                      </td>
                    </tr>
                  ) : (
                    Object.entries(product.known_declarations).map(([key, val], idx) => {
                      const displayVal = typeof val === 'object' && val !== null ? (val.formatted || JSON.stringify(val)) : String(val);
                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-main)' }}>
                            {key.replace(/_/g, ' ')}
                          </td>
                          <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                            {displayVal}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Inspection History */}
      {activeTab === 'inspections' && (
        <InspectionHistoryTable
          inspections={inspections}
          pagination={inspPagination}
          onPageChange={(page) => fetchInspections(page)}
          statusFilter={statusFilter}
          onStatusFilterChange={(s) => setStatusFilter(s)}
        />
      )}

      {/* Tab 3: Label Versions & Changes */}
      {activeTab === 'labels' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <LabelVersionHistory
            productId={product.id}
            versions={labelVersions}
            onCompare={handleCompareVersions}
          />

          <LabelChangeViewer
            diff={activeDiff}
            loading={diffLoading}
          />
        </div>
      )}

      {/* Tab 4: Historical Timeline */}
      {activeTab === 'timeline' && (
        <ProductHistoryTimeline
          events={timelineEvents}
        />
      )}
    </div>
  );
};
