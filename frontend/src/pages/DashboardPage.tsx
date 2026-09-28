import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  PlusCircle, 
  FolderKanban, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Layers, 
  ArrowUpRight, 
  Clock,
  Search,
  FileText,
  UserCheck,
  TrendingUp,
  MapPin,
  ExternalLink
} from 'lucide-react';
import { listInspections } from '../api/inspections';
import { 
  getAnalyticsOverview, 
  getInspectionsTrend, 
  getOutcomesBreakdown, 
  getCategoriesBreakdown, 
  getLocationsBreakdown 
} from '../api/analytics';
import { 
  Inspection, 
  AnalyticsOverview, 
  TrendDataPoint, 
  OutcomeDistribution, 
  CategoryDistributionItem, 
  LocationDistributionItem 
} from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { OutcomeChart } from '../components/analytics/OutcomeChart';
import { InspectionTrendChart } from '../components/analytics/InspectionTrendChart';
import { CategoryBreakdown } from '../components/analytics/CategoryBreakdown';
import { LocationBreakdown } from '../components/analytics/LocationBreakdown';

export const DashboardPage: React.FC = () => {
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [trend, setTrend] = useState<TrendDataPoint[]>([]);
  const [outcomes, setOutcomes] = useState<OutcomeDistribution | null>(null);
  const [categories, setCategories] = useState<CategoryDistributionItem[]>([]);
  const [locations, setLocations] = useState<LocationDistributionItem[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        // Fetch parallel analytics and inspection data
        const [
          inspsData,
          overviewData,
          trendData,
          outcomesData,
          categoriesData,
          locationsData,
        ] = await Promise.allSettled([
          listInspections(),
          getAnalyticsOverview(),
          getInspectionsTrend(30),
          getOutcomesBreakdown(),
          getCategoriesBreakdown(),
          getLocationsBreakdown(),
        ]);

        if (inspsData.status === 'fulfilled') setInspections(inspsData.value);
        if (overviewData.status === 'fulfilled') setAnalytics(overviewData.value);
        if (trendData.status === 'fulfilled') setTrend(trendData.value);
        if (outcomesData.status === 'fulfilled') setOutcomes(outcomesData.value);
        if (categoriesData.status === 'fulfilled') setCategories(categoriesData.value);
        if (locationsData.status === 'fulfilled') setLocations(locationsData.value);
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard operational analytics');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const filteredInspections = inspections.filter((i) => {
    const q = searchTerm.toLowerCase();
    return (
      i.inspection_number.toLowerCase().includes(q) ||
      (i.retail_outlet_name && i.retail_outlet_name.toLowerCase().includes(q)) ||
      (i.product?.brand_name && i.product.brand_name.toLowerCase().includes(q)) ||
      (i.product?.product_name && i.product.product_name.toLowerCase().includes(q))
    );
  });

  const totalCount = analytics?.total_inspections ?? inspections.length;
  const inProgressCount = analytics?.inspections_requiring_review ?? inspections.filter((i) => i.overall_status === 'IN_PROGRESS' || i.overall_status === 'PENDING_REVIEW').length;
  const productsCount = analytics?.products_inspected ?? 0;
  const reportsCount = analytics?.reports_generated ?? 0;
  const adjudicationsCount = analytics?.total_adjudications ?? 0;

  return (
    <div className="page-container">
      {/* Top Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 28,
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', marginBottom: 4 }}>
            Inspection Operations Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Legal Metrology (Packaged Commodities) Rules, 2011 — Operations & Intelligence Center
          </p>
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/products" className="btn btn-outline" style={{ gap: 8 }}>
            <Layers size={16} />
            <span>Product Ledger</span>
          </Link>

          <Link to="/inspections/new" className="btn btn-primary" style={{ gap: 8 }}>
            <PlusCircle size={16} />
            <span>New Inspection</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid-4" style={{ marginBottom: 28, gap: 16 }}>
        <div className="card">
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            Total Inspections
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
              {totalCount}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>Repository</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
            {analytics?.inspections_this_month ?? 0} this month • {analytics?.inspections_this_week ?? 0} this week
          </div>
        </div>

        <div className="card">
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            Products Cataloged
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: 'var(--primary-500)' }}>
              {productsCount}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Commodities</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
            Multi-inspection persistent SKU tracking
          </div>
        </div>

        <div className="card">
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            Reports Generated
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: 'var(--verdict-pass)' }}>
              {reportsCount}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--verdict-pass)' }}>SHA-256</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
            Cryptographically sealed PDF dossiers
          </div>
        </div>

        <div className="card">
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            Adjudications Logged
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-heading)', color: '#A855F7' }}>
              {adjudicationsCount}
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Corrections</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
            Human verified bounding boxes & text
          </div>
        </div>
      </div>

      {/* Historical Outcome Visualizations Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 20, marginBottom: 28 }}>
        <OutcomeChart distribution={outcomes} loading={loading} />
        <InspectionTrendChart trend={trend} loading={loading} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 20, marginBottom: 28 }}>
        <CategoryBreakdown categories={categories} loading={loading} />
        <LocationBreakdown locations={locations} loading={loading} />
      </div>

      {/* Recent Inspections Table */}
      <div className="card">
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 18,
          flexWrap: 'wrap',
          gap: 12,
        }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Recent Inspections</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginTop: 2 }}>
              Latest statutory enforcement events and operational workflows
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ position: 'relative' }}>
              <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="Filter inspections..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input"
                style={{ paddingLeft: 32, width: 220, fontSize: '0.85rem' }}
              />
            </div>

            <Link to="/inspections" className="btn btn-outline btn-sm" style={{ gap: 6 }}>
              <span>View All</span>
              <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
              <Clock size={24} className="animate-spin" style={{ margin: '0 auto 8px', color: 'var(--accent-cyan)' }} />
              <div>Loading inspections...</div>
            </div>
          ) : filteredInspections.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
              No inspections found.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 12px' }}>Inspection ID</th>
                  <th style={{ padding: '10px 12px' }}>Commodity / Brand</th>
                  <th style={{ padding: '10px 12px' }}>Outlet / Location</th>
                  <th style={{ padding: '10px 12px' }}>Date</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredInspections.slice(0, 8).map((insp) => (
                  <tr key={insp.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      <Link to={`/inspections/${insp.id}`} style={{ color: 'var(--accent-cyan)', textDecoration: 'none' }}>
                        {insp.inspection_number}
                      </Link>
                    </td>

                    <td style={{ padding: '12px' }}>
                      {insp.product ? (
                        <Link to={`/products/${insp.product.id}`} style={{ color: 'var(--text-main)', textDecoration: 'none' }}>
                          <span style={{ fontWeight: 500 }}>{insp.product.brand_name} {insp.product.product_name}</span>
                        </Link>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Unassigned SKU</span>
                      )}
                    </td>

                    <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                      {insp.retail_outlet_name || 'Field Site'}
                    </td>

                    <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                      {new Date(insp.initiated_at).toLocaleDateString()}
                    </td>

                    <td style={{ padding: '12px' }}>
                      <StatusBadge status={insp.overall_status} size="sm" />
                    </td>

                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                        <Link
                          to={`/inspections/${insp.id}`}
                          className="btn btn-outline btn-sm"
                          style={{ padding: '4px 8px' }}
                        >
                          View
                        </Link>
                        {insp.product_id && (
                          <Link
                            to={`/products/${insp.product_id}`}
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '4px 8px' }}
                            title="Product Ledger"
                          >
                            <Layers size={12} />
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
      </div>
    </div>
  );
};
