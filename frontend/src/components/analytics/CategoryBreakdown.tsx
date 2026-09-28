import React from 'react';
import { CategoryDistributionItem } from '../../types/api';
import { Layers } from 'lucide-react';

interface CategoryBreakdownProps {
  categories: CategoryDistributionItem[];
  loading?: boolean;
}

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({ categories, loading }) => {
  if (loading) {
    return (
      <div className="card" style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)' }}>Loading category distribution...</div>
      </div>
    );
  }

  const maxCount = Math.max(...categories.map((c) => c.count), 1);

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Commodity Categories</h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 2 }}>
            Inspected volume grouped by statutory commodity classes
          </p>
        </div>
        <Layers size={18} color="var(--primary-500)" />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, flex: 1, justifyContent: 'center' }}>
        {categories.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px 0' }}>
            No commodity categories recorded yet.
          </div>
        ) : (
          categories.slice(0, 5).map((cat, idx) => {
            const barPct = Math.max(5, Math.round((cat.count / maxCount) * 100));
            return (
              <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <span style={{ fontWeight: 500, color: 'var(--text-main)' }}>{cat.category}</span>
                  <div style={{ display: 'flex', gap: 10, fontFamily: 'var(--font-mono)' }}>
                    <span>{cat.count} items</span>
                    <span style={{ color: 'var(--text-muted)' }}>({cat.percentage}%)</span>
                  </div>
                </div>
                <div style={{
                  width: '100%',
                  height: 6,
                  borderRadius: 3,
                  backgroundColor: 'var(--bg-surface-tertiary)',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${barPct}%`,
                    height: '100%',
                    borderRadius: 3,
                    background: 'linear-gradient(90deg, var(--primary-500), var(--accent-cyan))',
                    transition: 'width 0.4s ease',
                  }} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
