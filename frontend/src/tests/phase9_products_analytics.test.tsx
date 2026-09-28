import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProductLedgerPage } from '../pages/ProductLedgerPage';
import { ProductDetailPage } from '../pages/ProductDetailPage';
import { CaptureWorkspacePage } from '../pages/CaptureWorkspacePage';
import { LabelChangeViewer } from '../components/products/LabelChangeViewer';
import { ProductHistoryTimeline } from '../components/products/ProductHistoryTimeline';
import { OutcomeChart } from '../components/analytics/OutcomeChart';
import { InspectionTrendChart } from '../components/analytics/InspectionTrendChart';
import { CategoryBreakdown } from '../components/analytics/CategoryBreakdown';
import { LocationBreakdown } from '../components/analytics/LocationBreakdown';
import * as productsApi from '../api/products';
import * as inspectionsApi from '../api/inspections';

vi.mock('../api/products');
vi.mock('../api/inspections');

describe('Phase 9: Product Ledger, Timeline & Dashboard Analytics Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Product Ledger Page', () => {
    it('renders product ledger table, search bar, and inspection counts', async () => {
      vi.mocked(productsApi.listProducts).mockResolvedValue({
        data: [
          {
            id: 'prod-001',
            brand_name: 'Himalayan Gold',
            product_name: 'Organic Green Tea 250g',
            category: 'Beverages & Tea',
            gtin_barcode: '8901234567890',
            manufacturer_claimed: 'Himalayan Estates Ltd',
            inspection_count: 3,
            latest_inspection_date: '2026-09-23T10:00:00Z',
            latest_label_version: 'v2.0',
            latest_status: 'COMPLETED',
            created_at: '2026-09-01T00:00:00Z',
          },
        ],
        pagination: {
          page: 1,
          page_size: 15,
          total_items: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      });

      render(
        <MemoryRouter>
          <ProductLedgerPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('National Packaged Commodity Ledger')).toBeInTheDocument();
        expect(screen.getByText('Himalayan Gold')).toBeInTheDocument();
        expect(screen.getByText('Organic Green Tea 250g')).toBeInTheDocument();
        expect(screen.getByText('8901234567890')).toBeInTheDocument();
        expect(screen.getByText('Beverages & Tea')).toBeInTheDocument();
        expect(screen.getByText('v2.0')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
      });
    });
  });

  describe('Product Detail Page', () => {
    it('renders product overview, tabs, and known declarations', async () => {
      vi.mocked(productsApi.getProduct).mockResolvedValue({
        id: 'prod-001',
        brand_name: 'Himalayan Gold',
        product_name: 'Organic Green Tea 250g',
        category: 'Beverages & Tea',
        gtin_barcode: '8901234567890',
        manufacturer_claimed: 'Himalayan Estates Ltd',
        metadata_json: {},
        known_declarations: {
          MRP: 'Rs. 490.00',
          NET_QUANTITY: '250 g',
          MANUFACTURER_NAME: 'Himalayan Estates Ltd',
        },
        inspection_count: 2,
        first_inspection_date: '2026-09-10T10:00:00Z',
        latest_inspection_date: '2026-09-23T10:00:00Z',
        latest_status: 'COMPLETED',
        latest_label_version: 'v2.0',
        created_at: '2026-09-01T00:00:00Z',
        updated_at: '2026-09-23T10:00:00Z',
      });

      render(
        <MemoryRouter initialEntries={['/products/prod-001']}>
          <Routes>
            <Route path="/products/:productId" element={<ProductDetailPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Himalayan Gold Organic Green Tea 250g/i)).toBeInTheDocument();
        expect(screen.getByText('Rs. 490.00')).toBeInTheDocument();
        expect(screen.getByText('250 g')).toBeInTheDocument();
        expect(screen.getByText(/Inspection History/i)).toBeInTheDocument();
        expect(screen.getByText(/Label Versions & Changes/i)).toBeInTheDocument();
        expect(screen.getByText(/Lifecycle Timeline/i)).toBeInTheDocument();
      });
    });
  });

  describe('Deterministic Label Change Detection Component', () => {
    it('displays changed, added, removed declarations with legal disclaimer', () => {
      const mockDiff = {
        from_version_id: 'v1',
        from_version_tag: 'v1.0',
        to_version_id: 'v2',
        to_version_tag: 'v2.0',
        changed_fields: [
          {
            field: 'MRP',
            field_label: 'Maximum Retail Price (MRP)',
            prev_value: 'Rs. 450.00',
            curr_value: 'Rs. 490.00',
            prev_source: 'Version v1.0',
            curr_source: 'Version v2.0',
          },
        ],
        added_fields: [
          {
            field: 'EXPIRY_DATE',
            field_label: 'Expiry Date',
            curr_value: '08/2027',
            curr_source: 'Current Label Version',
          },
        ],
        removed_fields: [],
        unchanged_fields: [
          {
            field: 'NET_QUANTITY',
            field_label: 'Net Quantity',
            curr_value: '250 g',
          },
        ],
        total_changes: 2,
        legal_disclaimer:
          'A changed value is a factual historical difference between packaging revisions. The deterministic rule engine remains the sole authority for legal compliance evaluations.',
      };

      render(<LabelChangeViewer diff={mockDiff} />);

      expect(screen.getByText('v1.0')).toBeInTheDocument();
      expect(screen.getByText('v2.0')).toBeInTheDocument();
      expect(screen.getByText('2 Changes Detected')).toBeInTheDocument();
      expect(screen.getByText('Rs. 450.00')).toBeInTheDocument();
      expect(screen.getByText('Rs. 490.00')).toBeInTheDocument();
      expect(screen.getByText('08/2027')).toBeInTheDocument();
      expect(screen.getByText(/deterministic rule engine remains the sole authority/i)).toBeInTheDocument();
    });
  });

  describe('Product Lifecycle Timeline Component', () => {
    it('renders chronological sequential events with actors and inspection links', () => {
      const mockEvents = [
        {
          event_id: 'ev-1',
          event_type: 'PRODUCT_REGISTERED',
          timestamp: '2026-09-01T10:00:00Z',
          title: 'Commodity Registered',
          description: 'Packaged commodity registered under Beverages & Tea',
          metadata: {},
        },
        {
          event_id: 'ev-2',
          event_type: 'INSPECTION_CREATED',
          timestamp: '2026-09-10T10:00:00Z',
          title: 'Inspection Initiated (LMR-20260910-001)',
          description: 'Physical inspection at Modern Bazaar',
          actor_name: 'Inspector Sharma',
          badge_number: 'LM-DEL-8801',
          inspection_id: 'insp-1',
          inspection_number: 'LMR-20260910-001',
          metadata: {},
        },
        {
          event_id: 'ev-3',
          event_type: 'RULES_EVALUATED',
          timestamp: '2026-09-10T10:15:00Z',
          title: 'Deterministic Rule Evaluation: PASS',
          description: 'Rule engine evaluated all rules. Verdict: PASS',
          inspection_id: 'insp-1',
          inspection_number: 'LMR-20260910-001',
          metadata: {},
        },
      ];

      render(
        <MemoryRouter>
          <ProductHistoryTimeline events={mockEvents} />
        </MemoryRouter>
      );

      expect(screen.getByText('Commodity Registered')).toBeInTheDocument();
      expect(screen.getByText(/Inspection Initiated \(LMR-20260910-001\)/i)).toBeInTheDocument();
      expect(screen.getByText('Inspector Sharma')).toBeInTheDocument();
      expect(screen.getByText(/LM-DEL-8801/i)).toBeInTheDocument();
      expect(screen.getByText(/Deterministic Rule Evaluation: PASS/i)).toBeInTheDocument();
    });
  });

  describe('Historical Operational Analytics & Charts', () => {
    it('renders OutcomeChart with PASS, REVIEW, FAIL distribution', () => {
      render(
        <OutcomeChart
          distribution={{
            pass_count: 45,
            review_count: 10,
            fail_count: 5,
            uncertain_count: 0,
            total_evaluations: 60,
          }}
        />
      );

      expect(screen.getByText('Rule Evaluation Outcome Distribution')).toBeInTheDocument();
      expect(screen.getByText('60 evaluations')).toBeInTheDocument();
      expect(screen.getByText('45')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('renders InspectionTrendChart with SVG line and points', () => {
      render(
        <InspectionTrendChart
          trend={[
            { date: '2026-09-20', count: 5 },
            { date: '2026-09-21', count: 12 },
            { date: '2026-09-22', count: 18 },
          ]}
        />
      );

      expect(screen.getByText('Inspection Volume Over Time')).toBeInTheDocument();
      expect(screen.getByText('35 Total')).toBeInTheDocument();
    });

    it('renders CategoryBreakdown with commodity percentages', () => {
      render(
        <CategoryBreakdown
          categories={[
            { category: 'Beverages & Tea', count: 30, percentage: 60 },
            { category: 'Edible Oils', count: 20, percentage: 40 },
          ]}
        />
      );

      expect(screen.getByText('Commodity Categories')).toBeInTheDocument();
      expect(screen.getByText('Beverages & Tea')).toBeInTheDocument();
      expect(screen.getByText('(60%)')).toBeInTheDocument();
      expect(screen.getByText('Edible Oils')).toBeInTheDocument();
      expect(screen.getByText('(40%)')).toBeInTheDocument();
    });

    it('renders LocationBreakdown table with pass/fail counts', () => {
      render(
        <LocationBreakdown
          locations={[
            {
              location: 'Modern Bazaar, Connaught Place',
              count: 15,
              pass_count: 12,
              fail_count: 2,
              review_count: 1,
            },
          ]}
        />
      );

      expect(screen.getByText('Inspection Activity by Retail Outlet')).toBeInTheDocument();
      expect(screen.getByText('Modern Bazaar, Connaught Place')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getByText('12')).toBeInTheDocument();
    });
  });

  describe('Camera Capture Workflow Guard', () => {
    it('does NOT open camera or HUD automatically on page load; opens only after explicit button click', async () => {
      const mockStream = {
        getTracks: () => [{ stop: vi.fn() }],
      };
      const mockGetUserMedia = vi.fn().mockResolvedValue(mockStream);
      Object.defineProperty(navigator, 'mediaDevices', {
        value: { getUserMedia: mockGetUserMedia },
        configurable: true,
      });
      window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);

      vi.mocked(inspectionsApi.getInspection).mockResolvedValue({
        id: 'insp-test',
        inspection_number: 'LMR-2026-TEST',
        overall_status: 'IN_PROGRESS',
        inspector_id: 'user-1',
        surfaces: [],
        initiated_at: '2026-09-23T10:00:00Z',
        created_at: '2026-09-23T10:00:00Z',
        updated_at: '2026-09-23T10:00:00Z',
      });

      render(
        <MemoryRouter initialEntries={['/inspections/insp-test/capture']}>
          <Routes>
            <Route path="/inspections/:inspectionId/capture" element={<CaptureWorkspacePage />} />
          </Routes>
        </MemoryRouter>
      );

      // Verify that initially the SixSurfaceWorkspace is rendered and CameraHUD is NOT open
      await waitFor(() => {
        expect(screen.getByText(/Front \(Principal Display Panel\)/i)).toBeInTheDocument();
      });

      // Camera HUD overlay should NOT be present initially
      expect(screen.queryByText(/SURFACE: FRONT_PDP/i)).not.toBeInTheDocument();
      expect(mockGetUserMedia).not.toHaveBeenCalled();

      // Click "Take Photo (Camera HUD)" on Front PDP surface
      const takePhotoBtns = screen.getAllByRole('button', { name: /Take Photo/i });
      fireEvent.click(takePhotoBtns[0]);

      // Only after explicit user click should CameraHUD open and getUserMedia be called
      await waitFor(() => {
        expect(screen.getByText(/SURFACE: FRONT_PDP/i)).toBeInTheDocument();
        expect(mockGetUserMedia).toHaveBeenCalled();
      });
    });
  });
});
