/**
 * Real-Time Client-Side Image-Quality Heuristics for Metrixa Camera Capture HUD
 * 
 * IMPORTANT ARCHITECTURAL SAFEGUARD:
 * This heuristics engine serves solely as an image-quality and capture-guidance instrument.
 * It strictly evaluates photographic suitability (sharpness, lighting, glare, stability, framing)
 * to ensure clear evidence capture. It NEVER determines legal compliance or statutory outcomes.
 */

export interface FrameQualityMetrics {
  sharpnessScore: number;
  isSharp: boolean;
  sharpnessLabel: string;

  luminance: number;
  lightingStatus: 'optimal' | 'too_dark' | 'too_bright';
  lightingLabel: string;

  glareFraction: number;
  hasGlare: boolean;
  glareLabel: string;

  stabilityScore: number;
  isStable: boolean;
  stabilityLabel: string;

  framingStatus: 'good' | 'move_closer' | 'move_farther';
  framingLabel: string;

  isReady: boolean;
  readinessReason: string;
}

/**
 * Computes average luminance across all pixels
 * Y = 0.299R + 0.587G + 0.114B
 */
export function computeLuminance(imageData: ImageData): number {
  const data = imageData.data;
  let totalLuminance = 0;
  const totalPixels = data.length / 4;

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    totalLuminance += 0.299 * r + 0.587 * g + 0.114 * b;
  }

  return totalPixels > 0 ? totalLuminance / totalPixels : 0;
}

/**
 * Detects glare regions where pixels approach maximum saturation
 */
export function detectGlare(imageData: ImageData, threshold = 248, maxAllowedFraction = 0.035): {
  glareFraction: number;
  hasGlare: boolean;
} {
  const data = imageData.data;
  let blownPixels = 0;
  const totalPixels = data.length / 4;

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    if (r >= threshold && g >= threshold && b >= threshold) {
      blownPixels++;
    }
  }

  const glareFraction = totalPixels > 0 ? blownPixels / totalPixels : 0;
  return {
    glareFraction,
    hasGlare: glareFraction > maxAllowedFraction,
  };
}

/**
 * Computes discrete Laplacian variance to evaluate focus sharpness
 * Higher variance indicates sharp, high-frequency edge transitions
 */
export function computeLaplacianVariance(imageData: ImageData): number {
  const width = imageData.width;
  const height = imageData.height;
  const data = imageData.data;

  // Convert to grayscale grid
  const gray = new Float32Array(width * height);
  for (let i = 0, j = 0; i < data.length; i += 4, j++) {
    gray[j] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
  }

  // Apply discrete 3x3 Laplacian operator:
  // [ 0  1  0 ]
  // [ 1 -4  1 ]
  // [ 0  1  0 ]
  let sum = 0;
  let sumSq = 0;
  let count = 0;

  // Sample with step to maintain high performance in HUD loop
  const step = 2;
  for (let y = 1; y < height - 1; y += step) {
    for (let x = 1; x < width - 1; x += step) {
      const idx = y * width + x;
      const laplacian =
        gray[idx - width] + // top
        gray[idx + width] + // bottom
        gray[idx - 1] +     // left
        gray[idx + 1] -     // right
        4 * gray[idx];

      sum += laplacian;
      sumSq += laplacian * laplacian;
      count++;
    }
  }

  if (count === 0) return 0;
  const mean = sum / count;
  const variance = sumSq / count - mean * mean;
  return Math.max(0, variance);
}

/**
 * Evaluates frame stability by computing mean absolute difference
 * between consecutive video frames
 */
export function computeFrameStability(
  prevImageData: ImageData | null,
  currImageData: ImageData,
  motionThreshold = 14
): {
  stabilityScore: number;
  isStable: boolean;
} {
  if (!prevImageData || prevImageData.data.length !== currImageData.data.length) {
    return { stabilityScore: 0, isStable: true };
  }

  const prev = prevImageData.data;
  const curr = currImageData.data;
  let diffSum = 0;
  let samples = 0;

  // Subsample every 8th pixel for fast differencing
  for (let i = 0; i < curr.length; i += 32) {
    const prevY = 0.299 * prev[i] + 0.587 * prev[i + 1] + 0.114 * prev[i + 2];
    const currY = 0.299 * curr[i] + 0.587 * curr[i + 1] + 0.114 * curr[i + 2];
    diffSum += Math.abs(currY - prevY);
    samples++;
  }

  const meanDiff = samples > 0 ? diffSum / samples : 0;
  return {
    stabilityScore: Math.round(meanDiff * 10) / 10,
    isStable: meanDiff < motionThreshold,
  };
}

/**
 * Estimates package framing and coverage relative to central reticle
 */
export function estimateFraming(imageData: ImageData): {
  framingStatus: 'good' | 'move_closer' | 'move_farther';
  framingLabel: string;
} {
  const width = imageData.width;
  const height = imageData.height;
  const data = imageData.data;

  // Check brightness variance in central region (25% to 75%) vs outer borders
  const startX = Math.floor(width * 0.25);
  const endX = Math.floor(width * 0.75);
  const startY = Math.floor(height * 0.25);
  const endY = Math.floor(height * 0.75);

  let centerEnergy = 0;
  let centerCount = 0;

  for (let y = startY; y < endY; y += 4) {
    for (let x = startX; x < endX; x += 4) {
      const idx = (y * width + x) * 4;
      const yVal = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
      centerEnergy += yVal;
      centerCount++;
    }
  }

  const avgCenter = centerCount > 0 ? centerEnergy / centerCount : 0;

  // Relative framing heuristic based on center energy and contrast
  if (avgCenter < 35) {
    return { framingStatus: 'move_closer', framingLabel: 'Move closer — package underexposed or small' };
  } else if (avgCenter > 230) {
    return { framingStatus: 'move_farther', framingLabel: 'Move farther — package fills frame with washout' };
  }

  return { framingStatus: 'good', framingLabel: 'Package positioned well' };
}

/**
 * Aggregates all heuristics into an explainable capture quality assessment
 */
export function evaluateFrameQuality(
  currImageData: ImageData,
  prevImageData: ImageData | null
): FrameQualityMetrics {
  // 1. Luminance & Lighting
  const luminance = Math.round(computeLuminance(currImageData));
  let lightingStatus: 'optimal' | 'too_dark' | 'too_bright' = 'optimal';
  let lightingLabel = 'Lighting looks good';

  if (luminance < 45) {
    lightingStatus = 'too_dark';
    lightingLabel = 'Too dark — improve lighting';
  } else if (luminance > 220) {
    lightingStatus = 'too_bright';
    lightingLabel = 'Too bright — reduce direct light';
  }

  // 2. Glare Detection
  const { glareFraction, hasGlare } = detectGlare(currImageData);
  const glareLabel = hasGlare
    ? 'Glare detected — tilt package slightly'
    : 'Minimal glare reflection';

  // 3. Sharpness / Blur Detection (Laplacian Variance)
  const sharpnessScore = Math.round(computeLaplacianVariance(currImageData));
  const isSharp = sharpnessScore >= 80;
  const sharpnessLabel = isSharp
    ? 'Sharp focus'
    : 'Move/hold steady — image appears blurry';

  // 4. Stability
  const { stabilityScore, isStable } = computeFrameStability(prevImageData, currImageData);
  const stabilityLabel = isStable ? 'Camera stable' : 'Hold steady';

  // 5. Framing
  const { framingStatus, framingLabel } = estimateFraming(currImageData);

  // 6. Capture Readiness
  let isReady = false;
  let readinessReason = '';

  if (lightingStatus === 'too_dark') {
    readinessReason = 'Lighting too low for statutory text capture';
  } else if (lightingStatus === 'too_bright') {
    readinessReason = 'Overexposed lighting washed out declaration area';
  } else if (hasGlare) {
    readinessReason = 'High specular glare over label area';
  } else if (!isSharp) {
    readinessReason = 'Blur detected — stabilize camera';
  } else if (!isStable) {
    readinessReason = 'Camera movement detected';
  } else {
    isReady = true;
    readinessReason = 'Optimal conditions for high-quality evidence';
  }

  return {
    sharpnessScore,
    isSharp,
    sharpnessLabel,
    luminance,
    lightingStatus,
    lightingLabel,
    glareFraction,
    hasGlare,
    glareLabel,
    stabilityScore,
    isStable,
    stabilityLabel,
    framingStatus,
    framingLabel,
    isReady,
    readinessReason,
  };
}
