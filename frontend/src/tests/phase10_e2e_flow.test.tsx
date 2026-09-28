import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SixSurfaceWorkspace } from '../components/inspection/SixSurfaceWorkspace';
import { CameraHUD } from '../components/camera/CameraHUD';
import { RuleEvaluationResult, SurfaceRead } from '../types/api';

describe('Phase 10 E2E Frontend Flow & Hardening Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockSurfaces: SurfaceRead[] = [
    {
      id: 'surf-pdp-1',
      inspection_id: 'insp-phase10',
      surface_type: 'FRONT_PDP',
      image_storage_path: 'surfaces/surf-pdp-1.jpg',
      sha256_hash: '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
      image_width: 1920,
      image_height: 1080,
      captured_at: '2026-09-23T10:00:00Z',
      created_at: '2026-09-23T10:00:00Z',
    },
  ];

  it('Gate 1: Strictly enforces camera guard (no camera opened on workspace load)', () => {
    const mockGetUserMedia = vi.fn();
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: mockGetUserMedia },
      configurable: true,
    });

    render(
      <SixSurfaceWorkspace
        inspectionId="insp-phase10"
        surfaces={mockSurfaces}
        onOpenHUD={vi.fn()}
        onUploadFile={vi.fn()}
      />
    );

    // Verify mediaDevices.getUserMedia was NOT called on workspace render
    expect(mockGetUserMedia).not.toHaveBeenCalled();
    // Verify tactile Camera HUD button exists
    expect(screen.getAllByText(/Camera HUD/i).length).toBeGreaterThan(0);
  });

  it('Gate 2: Explicit officer interaction triggers Camera HUD modal', () => {
    const onOpenHUD = vi.fn();
    render(
      <SixSurfaceWorkspace
        inspectionId="insp-phase10"
        surfaces={[]}
        onOpenHUD={onOpenHUD}
        onUploadFile={vi.fn()}
      />
    );

    const hudButtons = screen.getAllByText(/Camera HUD/i);
    fireEvent.click(hudButtons[0]);

    expect(onOpenHUD).toHaveBeenCalledWith('FRONT_PDP');
  });

  it('Gate 3: File upload fallback provides seamless manual evidence ingestion', () => {
    const onUploadFile = vi.fn();
    render(
      <SixSurfaceWorkspace
        inspectionId="insp-phase10"
        surfaces={[]}
        onOpenHUD={vi.fn()}
        onUploadFile={onUploadFile}
      />
    );

    const fileInputs = document.querySelectorAll('input[type="file"]');
    expect(fileInputs.length).toBe(6);

    const dummyFile = new File(['mock_image_bytes'], 'package.jpg', { type: 'image/jpeg' });
    fireEvent.change(fileInputs[0], { target: { files: [dummyFile] } });

    expect(onUploadFile).toHaveBeenCalledWith('FRONT_PDP', dummyFile);
  });

  it('Gate 4: CameraHUD provides immediate fallback when camera is inaccessible', async () => {
    const mockGetUserMedia = vi.fn().mockRejectedValue({
      name: 'NotAllowedError',
      message: 'Permission denied',
    });

    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: mockGetUserMedia },
      configurable: true,
    });

    render(
      <CameraHUD
        surfaceType="FRONT_PDP"
        onCapture={vi.fn()}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Camera Unavailable')).toBeInTheDocument();
      expect(screen.getByText(/Camera permission denied/i)).toBeInTheDocument();
      expect(screen.getByText(/Upload Image Instead/i)).toBeInTheDocument();
    });
  });

  it('Gate 5: Preserves evidence integrity display with SHA-256 preview', () => {
    render(
      <SixSurfaceWorkspace
        inspectionId="insp-phase10"
        surfaces={mockSurfaces}
        onOpenHUD={vi.fn()}
        onUploadFile={vi.fn()}
      />
    );

    expect(screen.getByText(/SHA: 12345678/i)).toBeInTheDocument();
    expect(screen.getByText('PDP')).toBeInTheDocument();
  });
});
