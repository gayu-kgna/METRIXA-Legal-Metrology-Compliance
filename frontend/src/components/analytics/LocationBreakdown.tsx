import React from 'react';
import { LocationDistributionItem } from '../../types/api';
import { MapPin } from 'lucide-react';

interface LocationBreakdownProps {
  locations: LocationDistributionItem[];
  loading?: boolean;
}

export const LocationBreakdown: React.FC<LocationBreakdownProps> = ({ locations, loading }) => {
  if (loading) {
    return (
      <div className="card" style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading location activity...</div>
      </div>
    );
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Inspection Activity by Retail Outlet</h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 2 }}>
            Factual distribution across field inspection sites
          </p>
        </div>
        <MapPin size={18} color="var(--accent-amber)" />
      </div>

      <div style={{ overflowX: 'auto', flex: 1 }}>
        {locations.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px 0' }}>
            No location records available.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '8px 4px' }}>Outlet / Location</th>
                <th style={{ padding: '8px 4px', textAlign: 'center' }}>Total</th>
                <th style={{ padding: '8px 4px', textAlign: 'center' }}>Pass</th>
                <th style={{ padding: '8px 4px', textAlign: 'center' }}>Action</th>
                <th style={{ padding: '8px 4px', textAlign: 'center' }}>Review</th>
              </tr>
            </thead>
            <tbody>
              {locations.slice(0, 5).map((loc, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 4px', fontWeight: 500, color: 'var(--text-main)' }}>
                    {loc.location}
                  </td>
                  <td style={{ padding: '10px 4px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
                    {loc.count}
                  </td>
                  <td style={{ padding: '10px 4px', textAlign: 'center', color: 'var(--verdict-pass)', fontFamily: 'var(--font-mono)' }}>
                    {loc.pass_count}
                  </td>
                  <td style={{ padding: '10px 4px', textAlign: 'center', color: 'var(--verdict-fail)', fontFamily: 'var(--font-mono)' }}>
                    {loc.fail_count}
                  </td>
                  <td style={{ padding: '10px 4px', textAlign: 'center', color: 'var(--verdict-review)', fontFamily: 'var(--font-mono)' }}>
                    {loc.review_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
