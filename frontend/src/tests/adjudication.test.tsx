import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { BoundingBoxCanvas } from '../components/adjudication/BoundingBoxCanvas';
import { OCRRegionEditor } from '../components/adjudication/OCRRegionEditor';
import { ObservationPanel } from '../components/adjudication/ObservationPanel';
import { ConflictResolutionPanel } from '../components/adjudication/ConflictResolutionPanel';
import { RuleReevaluationPanel } from '../components/adjudication/RuleReevaluationPanel';
import { ManualObservationDialog } from '../components/adjudication/ManualObservationDialog';
import {
  AdjudicatedOCRRegion,
  AdjudicatedObservation,
  ConflictGroup,
  RuleReevaluationResponse,
} from '../types/api';

describe('Adjudication & Bounding Box Workspace Suite (Phase 8)', () => {
  const mockRegion: AdjudicatedOCRRegion = {
    id: 'reg-1',
    surface_id: 'surf-1',
    raw_text: 'NET QTY: 500 g',
    effective_text: 'NET QTY: 500 g',
    confidence: 0.98,
    bounding_box: { ymin: 0.1, xmin: 0.1, ymax: 0.2, xmax: 0.3 },
    effective_bounding_box: { ymin: 0.1, xmin: 0.1, ymax: 0.2, xmax: 0.3 },
    is_adjudicated: false,
    is_rejected: false,
    is_manually_created: false,
  };

  const mockObservation: AdjudicatedObservation = {
    id: 'obs-1',
    inspection_id: 'insp-1',
    surface_id: 'surf-1',
    field_type: 'NET_QUANTITY',
    raw_value: '500 g',
    normalized_value: { value: 500, unit: 'g', formatted: '500 g' },
    confidence: 0.95,
    status: 'OBSERVED',
    source: 'PIPELINE_EXTRACTION',
    revision: 1,
    is_latest: true,
    created_at: '2026-09-23T10:00:00Z',
    updated_at: '2026-09-23T10:00:00Z',
    surface_name: 'FRONT_PDP',
    field_display_name: 'Net Quantity',
  };

  it('renders BoundingBoxCanvas with regions, HUD toolbar, and status coordinates', () => {
    const onSelectRegion = vi.fn();
    render(
      <BoundingBoxCanvas
        imageUrl="test-image.jpg"
        regions={[mockRegion]}
        selectedRegionId={null}
        onSelectRegion={onSelectRegion}
        onUpdateRegionBbox={vi.fn()}
        onCreateRegionBox={vi.fn()}
        isDrawingMode={false}
        setIsDrawingMode={vi.fn()}
        showLabels={true}
        setShowLabels={vi.fn()}
        showConfidence={true}
        setShowConfidence={vi.fn()}
        hideRejected={false}
        setHideRejected={vi.fn()}
        surfaceName="Front (PDP)"
      />
    );

    expect(screen.getByText(/Front \(PDP\)/i)).toBeInTheDocument();
    expect(screen.getByText(/1 Regions/i)).toBeInTheDocument();
    expect(screen.getByText(/Draw Region/i)).toBeInTheDocument();
    expect(screen.getByText(/NET QTY: 500 g/i)).toBeInTheDocument();
  });

  it('allows clicking an OCR region on the canvas overlay to select it', () => {
    const onSelectRegion = vi.fn();
    const { container } = render(
      <BoundingBoxCanvas
        imageUrl="test-image.jpg"
        regions={[mockRegion]}
        selectedRegionId={null}
        onSelectRegion={onSelectRegion}
        onUpdateRegionBbox={vi.fn()}
        onCreateRegionBox={vi.fn()}
        isDrawingMode={false}
        setIsDrawingMode={vi.fn()}
        showLabels={true}
        setShowLabels={vi.fn()}
        showConfidence={true}
        setShowConfidence={vi.fn()}
        hideRejected={false}
        setHideRejected={vi.fn()}
        surfaceName="Front (PDP)"
      />
    );

    const rect = container.querySelector('#bbox-reg-1');
    expect(rect).toBeTruthy();
    if (rect) {
      fireEvent.click(rect);
      expect(onSelectRegion).toHaveBeenCalledWith(mockRegion);
    }
  });

  it('renders OCRRegionEditor and allows text correction submission', async () => {
    const onSaveCorrection = vi.fn().mockResolvedValue(undefined);
    render(
      <OCRRegionEditor
        selectedRegion={mockRegion}
        pendingNewBox={null}
        onClose={vi.fn()}
        onSaveCorrection={onSaveCorrection}
        onRejectRegion={vi.fn()}
        onCreateRegion={vi.fn()}
      />
    );

    expect(screen.getByText(/Region Editor/i)).toBeInTheDocument();
    const textInput = screen.getByLabelText(/Effective Recognized Text/i) || screen.getByPlaceholderText(/Enter accurate statutory text/i);
    expect(textInput).toBeInTheDocument();

    fireEvent.change(textInput, { target: { value: 'NET QTY: 750 g' } });
    const saveBtn = screen.getByRole('button', { name: /Save Correction/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(onSaveCorrection).toHaveBeenCalledWith(
        'reg-1',
        expect.objectContaining({ corrected_text: 'NET QTY: 750 g' })
      );
    });
  });

  it('renders ObservationPanel and triggers 1-click verification', async () => {
    const onVerify = vi.fn().mockResolvedValue(undefined);
    render(
      <ObservationPanel
        observations={[mockObservation]}
        onVerify={onVerify}
        onCorrect={vi.fn()}
        onReject={vi.fn()}
        onUpdateStatus={vi.fn()}
        onOpenManualDialog={vi.fn()}
      />
    );

    expect(screen.getByText('Net Quantity')).toBeInTheDocument();
    expect(screen.getByText('500 g')).toBeInTheDocument();
    expect(screen.getByText('OBSERVED')).toBeInTheDocument();

    const verifyBtn = screen.getByRole('button', { name: /Verify/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(onVerify).toHaveBeenCalledWith('obs-1');
    });
  });

  it('renders ConflictResolutionPanel and resolves conflict by selecting authoritative choice', async () => {
    const mockConflicts: ConflictGroup[] = [
      {
        field_type: 'MAXIMUM_RETAIL_PRICE',
        observation_count: 2,
        has_conflict: true,
        description: 'Differing MRP values declared on front vs back surfaces.',
        observations: [
          {
            ...mockObservation,
            id: 'obs-mrp-1',
            field_type: 'MAXIMUM_RETAIL_PRICE',
            raw_value: '₹ 150.00',
            surface_name: 'FRONT_PDP',
          },
          {
            ...mockObservation,
            id: 'obs-mrp-2',
            field_type: 'MAXIMUM_RETAIL_PRICE',
            raw_value: '₹ 160.00',
            surface_name: 'BACK',
          },
        ],
      },
    ];

    const onSelectAuthoritative = vi.fn().mockResolvedValue(undefined);
    render(
      <ConflictResolutionPanel
        conflicts={mockConflicts}
        onSelectAuthoritative={onSelectAuthoritative}
        onVerifySingle={vi.fn()}
        onRejectSingle={vi.fn()}
      />
    );

    expect(screen.getByText(/Multi-Surface Declaration Conflicts/i)).toBeInTheDocument();
    expect(screen.getByText('₹ 150.00')).toBeInTheDocument();
    expect(screen.getByText('₹ 160.00')).toBeInTheDocument();

    const authBtns = screen.getAllByRole('button', { name: /Set Authoritative/i });
    expect(authBtns.length).toBe(2);
    fireEvent.click(authBtns[0]);

    await waitFor(() => {
      expect(onSelectAuthoritative).toHaveBeenCalledWith('MAXIMUM_RETAIL_PRICE', 'obs-mrp-1');
    });
  });

  it('renders RuleReevaluationPanel and shows verdict delta comparison after rule execution', async () => {
    const mockResult: RuleReevaluationResponse = {
      inspection_id: 'insp-1',
      evaluation_run_id: 'run-1',
      previous_verdict: 'REVIEW',
      new_verdict: 'PASS',
      verdict_changed: true,
      total_rules: 1,
      changes: [
        {
          rule_code: 'PCR-2011-R06-1-C',
          title: 'Net Quantity Declaration',
          previous_outcome: 'REVIEW',
          new_outcome: 'PASS',
          statutory_citation: 'Rule 6(1)(c)',
          changed: true,
          legal_rationale: 'Officer verified statutory net quantity.',
        },
      ],
      reevaluated_at: '2026-09-23T11:00:00Z',
      summary: {
        inspection_id: 'insp-1',
        evaluation_run_id: 'run-1',
        evaluated_at: '2026-09-23T11:00:00Z',
        rule_set_version: '2011.1',
        total_rules_evaluated: 1,
        overall_verdict: 'PASS',
        pass_count: 1,
        fail_count: 0,
        review_count: 0,
        indeterminate_count: 0,
        not_applicable_count: 0,
        evaluations: [],
      },
    };

    render(
      <BrowserRouter>
        <RuleReevaluationPanel
          inspectionId="insp-1"
          onReevaluate={vi.fn().mockResolvedValue(mockResult)}
          reevaluationResult={mockResult}
          hasUncommittedAdjudications={false}
        />
      </BrowserRouter>
    );

    expect(screen.getByText(/Authoritative Rule Re-Evaluation/i)).toBeInTheDocument();
    expect(screen.getByText(/Verdict Updated/i)).toBeInTheDocument();
    expect(screen.getByText('PCR-2011-R06-1-C')).toBeInTheDocument();
    expect(screen.getByText('Net Quantity Declaration')).toBeInTheDocument();
  });

  it('opens and submits ManualObservationDialog with mandatory justification', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <ManualObservationDialog
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
        surfaces={[{
          id: 'surf-1',
          inspection_id: 'insp-1',
          surface_type: 'FRONT_PDP',
          image_storage_path: 'p',
          sha256_hash: 'h',
          captured_at: '2026-09-23T10:00:00Z',
          created_at: '2026-09-23T10:00:00Z',
        }]}
      />
    );

    expect(screen.getByText(/Add Manual Statutory Declaration/i)).toBeInTheDocument();

    const valInput = screen.getByPlaceholderText(/e\.g\. ₹ 199\.00/i);
    fireEvent.change(valInput, { target: { value: '₹ 299.00 (Incl. of all taxes)' } });

    const submitBtn = screen.getByRole('button', { name: /Add Declaration/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          raw_value: '₹ 299.00 (Incl. of all taxes)',
          field_type: 'MAXIMUM_RETAIL_PRICE',
        })
      );
    });
  });
});
