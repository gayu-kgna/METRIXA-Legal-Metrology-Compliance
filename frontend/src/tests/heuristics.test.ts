import { describe, it, expect } from 'vitest';
import {
  computeLuminance,
  detectGlare,
  computeLaplacianVariance,
  computeFrameStability,
  estimateFraming,
  evaluateFrameQuality,
} from '../utils/heuristics';

function createMockImageData(width: number, height: number, fillFn: (x: number, y: number) => [number, number, number, number]): ImageData {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;
      const [r, g, b, a] = fillFn(x, y);
      data[idx] = r;
      data[idx + 1] = g;
      data[idx + 2] = b;
      data[idx + 3] = a;
    }
  }
  return new ImageData(data, width, height);
}

describe('Metrixa Image-Quality Heuristics Suite', () => {
  describe('Luminance / Brightness Heuristic', () => {
    it('accurately computes 0 luminance for pure black frame', () => {
      const black = createMockImageData(10, 10, () => [0, 0, 0, 255]);
      expect(computeLuminance(black)).toBe(0);
    });

    it('accurately computes 255 luminance for pure white frame', () => {
      const white = createMockImageData(10, 10, () => [255, 255, 255, 255]);
      expect(Math.round(computeLuminance(white))).toBe(255);
    });

    it('accurately computes mid-level luminance', () => {
      const gray = createMockImageData(10, 10, () => [128, 128, 128, 255]);
      expect(Math.round(computeLuminance(gray))).toBe(128);
    });
  });

  describe('Glare Reflection Heuristic', () => {
    it('detects minimal glare on well-diffused packaging', () => {
      const normal = createMockImageData(20, 20, () => [120, 130, 140, 255]);
      const res = detectGlare(normal);
      expect(res.hasGlare).toBe(false);
      expect(res.glareFraction).toBe(0);
    });

    it('detects specular reflection glare when hot spots exceed threshold', () => {
      // 10% of pixels completely saturated
      const glary = createMockImageData(20, 20, (x, y) => {
        if (x < 6 && y < 6) return [255, 255, 255, 255];
        return [100, 100, 100, 255];
      });
      const res = detectGlare(glary);
      expect(res.hasGlare).toBe(true);
      expect(res.glareFraction).toBeGreaterThan(0.04);
    });
  });

  describe('Laplacian Focus & Sharpness Heuristic', () => {
    it('calculates near-zero variance on flat, out-of-focus surfaces', () => {
      const flat = createMockImageData(40, 40, () => [120, 120, 120, 255]);
      const variance = computeLaplacianVariance(flat);
      expect(variance).toBe(0);
    });

    it('calculates elevated variance on sharp edge transitions', () => {
      // High-frequency checkerboard pattern
      const sharp = createMockImageData(40, 40, (x, y) => {
        const isWhite = (Math.floor(x / 4) + Math.floor(y / 4)) % 2 === 0;
        return isWhite ? [255, 255, 255, 255] : [0, 0, 0, 255];
      });
      const variance = computeLaplacianVariance(sharp);
      expect(variance).toBeGreaterThan(150);
    });
  });

  describe('Frame Stability Differencing', () => {
    it('reports perfect stability when consecutive frames are identical', () => {
      const frame1 = createMockImageData(30, 30, () => [120, 120, 120, 255]);
      const frame2 = createMockImageData(30, 30, () => [120, 120, 120, 255]);
      const res = computeFrameStability(frame1, frame2);
      expect(res.isStable).toBe(true);
      expect(res.stabilityScore).toBe(0);
    });

    it('detects camera shake motion when consecutive frames differ significantly', () => {
      const frame1 = createMockImageData(30, 30, () => [50, 50, 50, 255]);
      const frame2 = createMockImageData(30, 30, () => [200, 200, 200, 255]);
      const res = computeFrameStability(frame1, frame2);
      expect(res.isStable).toBe(false);
      expect(res.stabilityScore).toBeGreaterThan(20);
    });
  });

  describe('Relative Package Framing & Distance Heuristic', () => {
    it('flags underexposed or absent package in reticle', () => {
      const darkCenter = createMockImageData(40, 40, () => [20, 20, 20, 255]);
      const res = estimateFraming(darkCenter);
      expect(res.framingStatus).toBe('move_closer');
    });

    it('flags washed-out package occupying frame', () => {
      const brightCenter = createMockImageData(40, 40, () => [240, 240, 240, 255]);
      const res = estimateFraming(brightCenter);
      expect(res.framingStatus).toBe('move_farther');
    });

    it('recognizes well-positioned package with good central energy', () => {
      const wellFramed = createMockImageData(40, 40, () => [140, 140, 140, 255]);
      const res = estimateFraming(wellFramed);
      expect(res.framingStatus).toBe('good');
    });
  });

  describe('Aggregate Capture Readiness Decision', () => {
    it('returns READY when frame is sharp, well-lit, stable, and glare-free', () => {
      const optimalFrame = createMockImageData(40, 40, (x, y) => {
        const isWhite = (Math.floor(x / 4) + Math.floor(y / 4)) % 2 === 0;
        return isWhite ? [200, 200, 200, 255] : [60, 60, 60, 255];
      });
      const metrics = evaluateFrameQuality(optimalFrame, optimalFrame);
      expect(metrics.lightingStatus).toBe('optimal');
      expect(metrics.hasGlare).toBe(false);
      expect(metrics.isSharp).toBe(true);
      expect(metrics.isStable).toBe(true);
      expect(metrics.isReady).toBe(true);
    });

    it('returns NOT_READY with clear statutory rationale when frame is blurry', () => {
      const blurryFrame = createMockImageData(40, 40, () => [120, 120, 120, 255]);
      const metrics = evaluateFrameQuality(blurryFrame, blurryFrame);
      expect(metrics.isSharp).toBe(false);
      expect(metrics.isReady).toBe(false);
      expect(metrics.readinessReason).toContain('Blur detected');
    });
  });
});
