import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { SixSurfaceWorkspace } from '../components/inspection/SixSurfaceWorkspace';
import { SurfaceRead } from '../types/api';

describe('Six-Surface Capture Workspace Suite', () => {
  const mockSurfaces: SurfaceRead[] = [
    {
      id: 'surf-1',
      inspection_id: 'insp-1',
      surface_type: 'FRONT_PDP',
      image_storage_path: 'surfaces/surf-1.jpg',
      sha256_hash: 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
      image_width: 1920,
      image_height: 1080,
      captured_at: '2026-09-22T10:00:00Z',
      created_at: '2026-09-22T10:00:00Z',
    },
  ];

  it('renders all six canonical packaging surfaces', () => {
    render(
      <SixSurfaceWorkspace
        inspectionId="insp-1"
        surfaces={mockSurfaces}
        onOpenHUD={vi.fn()}
        onUploadFile={vi.fn()}
      />
    );

    expect(screen.getByText(/Front \(Principal Display Panel\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Back Surface/i)).toBeInTheDocument();
    expect(screen.getByText(/Left Lateral Surface/i)).toBeInTheDocument();
    expect(screen.getByText(/Right Lateral Surface/i)).toBeInTheDocument();
    expect(screen.getByText(/Top Surface/i)).toBeInTheDocument();
    expect(screen.getByText(/Bottom Surface/i)).toBeInTheDocument();
  });

  it('displays PDP highlight badge and SHA-256 preview for captured front panel', () => {
    render(
      <SixSurfaceWorkspace
        inspectionId="insp-1"
        surfaces={mockSurfaces}
        onOpenHUD={vi.fn()}
        onUploadFile={vi.fn()}
      />
    );

    expect(screen.getByText('PDP')).toBeInTheDocument();
    expect(screen.getByText(/SHA: abcdef12/i)).toBeInTheDocument();
    expect(screen.getByText('1 Image')).toBeInTheDocument();
  });

  it('triggers Camera HUD callback when officer clicks Camera HUD button', () => {
    const onOpenHUD = vi.fn();
    render(
      <SixSurfaceWorkspace
        inspectionId="insp-1"
        surfaces={[]}
        onOpenHUD={onOpenHUD}
        onUploadFile={vi.fn()}
      />
    );

    const hudButtons = screen.getAllByRole('button', { name: /Camera HUD/i });
    fireEvent.click(hudButtons[0]);
    expect(onOpenHUD).toHaveBeenCalledWith('FRONT_PDP');
  });
});
