import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CameraHUD } from '../components/camera/CameraHUD';

describe('Intelligent Camera HUD & Guidance Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders fallback UI when navigator.mediaDevices is unsupported', async () => {
    // Mock navigator.mediaDevices = undefined
    const originalMediaDevices = navigator.mediaDevices;
    Object.defineProperty(navigator, 'mediaDevices', {
      value: undefined,
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
      expect(screen.getByText(/Camera API is not supported in this browser/i)).toBeInTheDocument();
      expect(screen.getByText(/Upload Image Instead/i)).toBeInTheDocument();
    });

    Object.defineProperty(navigator, 'mediaDevices', {
      value: originalMediaDevices,
      configurable: true,
    });
  });

  it('handles camera permission denied with helpful officer instructions', async () => {
    const mockGetUserMedia = vi.fn().mockRejectedValue({
      name: 'NotAllowedError',
      message: 'Permission denied by user',
    });

    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: mockGetUserMedia },
      configurable: true,
    });

    render(
      <CameraHUD
        surfaceType="BACK"
        onCapture={vi.fn()}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Camera Unavailable')).toBeInTheDocument();
      expect(screen.getByText(/Camera permission denied/i)).toBeInTheDocument();
    });
  });

  it('renders live telemetry guidance and auto-capture toggle when stream initializes', async () => {
    const mockStream = {
      getTracks: () => [{ stop: vi.fn() }],
    };

    const mockGetUserMedia = vi.fn().mockResolvedValue(mockStream);

    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: mockGetUserMedia },
      configurable: true,
    });

    // Mock HTMLMediaElement play
    window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);

    render(
      <CameraHUD
        surfaceType="FRONT_PDP"
        onCapture={vi.fn()}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/SURFACE: FRONT_PDP/i)).toBeInTheDocument();
      expect(screen.getByText(/Auto: OFF/i)).toBeInTheDocument();
      expect(screen.getByTitle('Capture Now')).toBeInTheDocument();
    });

    // Toggle Auto-Capture ON
    const autoToggle = screen.getByTitle('Toggle Automatic Capture');
    fireEvent.click(autoToggle);
    expect(screen.getByText(/Auto: ON/i)).toBeInTheDocument();
  });
});
