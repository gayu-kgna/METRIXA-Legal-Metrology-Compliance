import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../pages/DashboardPage';
import { StatusBadge } from '../components/common/StatusBadge';
import * as inspectionsApi from '../api/inspections';

vi.mock('../api/inspections');

describe('Inspection Dashboard & Statutory Status Suite', () => {
  it('renders metric cards and inspection table with backend data', async () => {
    vi.mocked(inspectionsApi.listInspections).mockResolvedValue([
      {
        id: 'insp-1',
        inspection_number: 'LMR-2026-001',
        overall_status: 'COMPLETED',
        retail_outlet_name: 'Metro Cash & Carry',
        retail_outlet_address: 'Bangalore Central',
        inspector_id: 'user-1',
        initiated_at: '2026-09-20T10:00:00Z',
        created_at: '2026-09-20T10:00:00Z',
        updated_at: '2026-09-20T10:00:00Z',
        product: {
          id: 'prod-1',
          brand_name: 'Tata Tea',
          product_name: 'Gold 500g',
          gtin_barcode: '8901234567890',
        },
      },
      {
        id: 'insp-2',
        inspection_number: 'LMR-2026-002',
        overall_status: 'IN_PROGRESS',
        retail_outlet_name: 'Reliance Smart',
        inspector_id: 'user-1',
        initiated_at: '2026-09-21T10:00:00Z',
        created_at: '2026-09-21T10:00:00Z',
        updated_at: '2026-09-21T10:00:00Z',
      },
    ]);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('LMR-2026-001')).toBeInTheDocument();
      expect(screen.getByText('Metro Cash & Carry')).toBeInTheDocument();
      expect(screen.getByText(/Tata Tea Gold 500g/i)).toBeInTheDocument();
      expect(screen.getByText('LMR-2026-002')).toBeInTheDocument();
    });
  });

  describe('Statutory StatusBadge Rendering', () => {
    it('renders PASS badge with check icon and accessible aria-label', () => {
      render(<StatusBadge status="PASS" />);
      const badge = screen.getByRole('status', { name: /Compliant \/ Pass/i });
      expect(badge).toHaveTextContent('PASS');
    });

    it('renders FAIL badge with alert icon and accessible aria-label', () => {
      render(<StatusBadge status="FAIL" />);
      const badge = screen.getByRole('status', { name: /Non-Compliant \/ Violation/i });
      expect(badge).toHaveTextContent('FAIL');
    });

    it('renders REVIEW badge', () => {
      render(<StatusBadge status="REVIEW" />);
      expect(screen.getByText('REVIEW')).toBeInTheDocument();
    });

    it('renders INDETERMINATE badge', () => {
      render(<StatusBadge status="INDETERMINATE" />);
      expect(screen.getByText('INDETERMINATE')).toBeInTheDocument();
    });

    it('renders NOT_APPLICABLE badge', () => {
      render(<StatusBadge status="NOT_APPLICABLE" />);
      expect(screen.getByText('NOT APPLICABLE')).toBeInTheDocument();
    });
  });
});
