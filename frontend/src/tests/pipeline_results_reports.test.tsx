import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ResultsPage } from '../pages/ResultsPage';
import { EvidenceBrowserPage } from '../pages/EvidenceBrowserPage';
import { ReportsPage } from '../pages/ReportsPage';
import * as rulesApi from '../api/rules';
import * as evidenceApi from '../api/evidence';
import * as reportsApi from '../api/reports';
import * as inspectionsApi from '../api/inspections';

vi.mock('../api/rules');
vi.mock('../api/evidence');
vi.mock('../api/reports');
vi.mock('../api/inspections');

describe('Results, Evidence, and Reports Suites', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(inspectionsApi.getInspection).mockResolvedValue({
      id: 'insp-100',
      inspection_number: 'LMR-2026-TEST',
      overall_status: 'IN_PROGRESS',
      retail_outlet_name: 'Big Bazaar',
      inspector_id: 'user-1',
      initiated_at: '2026-09-22T10:00:00Z',
      created_at: '2026-09-22T10:00:00Z',
      updated_at: '2026-09-22T10:00:00Z',
    });
  });

  describe('Statutory Results Page', () => {
    it('renders evaluated rules with PASS and FAIL badges and statutory citations', async () => {
      vi.mocked(rulesApi.getInspectionRuleEvaluations).mockResolvedValue([
        {
          id: 'eval-1',
          inspection_id: 'insp-100',
          evaluation_run_id: 'run-1',
          rule_definition_id: 'rdef-1',
          rule_code: 'LMR-PCR-R06-NET-QTY',
          rule_version: '2024-v1',
          outcome: 'PASS',
          statutory_citation: 'Rule 6(1)(b) of PCR, 2011',
          legal_rationale: 'Mandatory net quantity declaration is present and uses standard metric units (g).',
          evaluated_at: '2026-09-22T10:05:00Z',
          rule_definition: {
            id: 'rdef-1',
            rule_code: 'LMR-PCR-R06-NET-QTY',
            legal_act: 'Legal Metrology Act, 2009',
            rule_reference: 'Rule 6(1)(b)',
            title: 'Mandatory Net Quantity Declaration',
            description: 'Check net quantity',
            severity: 'CRITICAL',
            version: '2024-v1',
          },
        },
        {
          id: 'eval-2',
          inspection_id: 'insp-100',
          evaluation_run_id: 'run-1',
          rule_definition_id: 'rdef-2',
          rule_code: 'LMR-PCR-R06-MRP',
          rule_version: '2024-v1',
          outcome: 'FAIL',
          statutory_citation: 'Rule 6(1)(e) of PCR, 2011',
          legal_rationale: 'Maximum Retail Price does not include mandatory statutory phrasing "incl. of all taxes".',
          evaluated_at: '2026-09-22T10:05:00Z',
          rule_definition: {
            id: 'rdef-2',
            rule_code: 'LMR-PCR-R06-MRP',
            legal_act: 'Legal Metrology Act, 2009',
            rule_reference: 'Rule 6(1)(e)',
            title: 'Maximum Retail Price Declaration',
            description: 'Check MRP',
            severity: 'CRITICAL',
            version: '2024-v1',
          },
        },
      ]);

      render(
        <MemoryRouter initialEntries={['/inspections/insp-100/results']}>
          <Routes>
            <Route path="/inspections/:inspectionId/results" element={<ResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('LMR-PCR-R06-NET-QTY')).toBeInTheDocument();
        expect(screen.getByText('Rule 6(1)(b) of PCR, 2011')).toBeInTheDocument();
        expect(screen.getByText('LMR-PCR-R06-MRP')).toBeInTheDocument();
        expect(screen.getByText('Rule 6(1)(e) of PCR, 2011')).toBeInTheDocument();
      });
    });
  });

  describe('Evidence Browser Page', () => {
    it('renders evidence snapshot integrity hash and canonical manifest toggle', async () => {
      vi.mocked(evidenceApi.getInspectionEvidenceBundle).mockResolvedValue({
        manifest: {
          surfaces: [{ id: 's-1' }],
          observations: [{ id: 'o-1', field_name: 'NET_QUANTITY', raw_text_extracted: '500g' }],
          evaluations: [
            {
              rule_code: 'LMR-PCR-R06-NET-QTY',
              outcome: 'PASS',
              statutory_citation: 'Rule 6(1)(b)',
              evidence_references: ['o-1'],
            },
          ],
        },
        integrity_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
      });

      render(
        <MemoryRouter initialEntries={['/inspections/insp-100/evidence']}>
          <Routes>
            <Route path="/inspections/:inspectionId/evidence" element={<EvidenceBrowserPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/SHA-256: 9f86d081884c/i)).toBeInTheDocument();
        expect(screen.getByText('LMR-PCR-R06-NET-QTY')).toBeInTheDocument();
        expect(screen.getByText(/Field: NET_QUANTITY/i)).toBeInTheDocument();
      });

      // Toggle to Canonical JSON view
      fireEvent.click(screen.getByRole('button', { name: /Canonical Manifest JSON/i }));
      expect(screen.getByText(/Full Canonical Evidence Manifest JSON/i)).toBeInTheDocument();
    });
  });

  describe('PDF Dossier Reports Page', () => {
    it('lists generated reports with version and SHA-256 digest', async () => {
      vi.mocked(reportsApi.listInspectionReports).mockResolvedValue([
        {
          id: 'rep-1',
          inspection_id: 'insp-100',
          evidence_snapshot_id: 'snap-1',
          report_type: 'FULL_INSPECTION_DOSSIER',
          report_version: 1,
          pdf_filename: 'dossier_LMR-2026-TEST_v1.pdf',
          storage_path: 'reports/dossier_v1.pdf',
          sha256_hash: 'a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890',
          generated_at: '2026-09-22T10:10:00Z',
          generated_by_id: 'user-1',
        },
      ]);

      vi.mocked(reportsApi.downloadReportPdfBlob).mockResolvedValue(
        new Blob(['%PDF-1.4 mock content'], { type: 'application/pdf' })
      );

      render(
        <MemoryRouter initialEntries={['/inspections/insp-100/reports']}>
          <Routes>
            <Route path="/inspections/:inspectionId/reports" element={<ReportsPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Report Versions (1)')).toBeInTheDocument();
        expect(screen.getByText('Version 1')).toBeInTheDocument();
        expect(screen.getByText(/SHA-256 Digest: a1b2c3d4e5f6/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Download PDF/i })).toBeInTheDocument();
      });
    });
  });
});
