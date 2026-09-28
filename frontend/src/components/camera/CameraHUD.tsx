import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Camera, 
  FlipHorizontal, 
  AlertCircle, 
  CheckCircle2, 
  XCircle, 
  Sun, 
  Focus, 
  Sparkles, 
  Activity, 
  Maximize, 
  X,
  Upload,
  Timer
} from 'lucide-react';
import { SurfaceType } from '../../types/api';
import { evaluateFrameQuality, FrameQualityMetrics } from '../../utils/heuristics';

interface CameraHUDProps {
  surfaceType: SurfaceType;
  onCapture: (blob: Blob) => Promise<void> | void;
  onClose: () => void;
}

export const CameraHUD: React.FC<CameraHUDProps> = ({
  surfaceType,
  onCapture,
  onClose,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const analysisCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameIdRef = useRef<number | null>(null);
  const prevImageDataRef = useRef<ImageData | null>(null);

  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const [readinessState, setReadinessState] = useState<'NOT_READY' | 'CHECKING' | 'READY' | 'CAPTURING' | 'CAPTURED'>('CHECKING');
  const [qualityMetrics, setQualityMetrics] = useState<FrameQualityMetrics | null>(null);
  
  // Auto-capture configuration: optional HUD auto-capture, user-initiated via HUD mount
  const [autoCaptureEnabled, setAutoCaptureEnabled] = useState<boolean>(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const countdownTimerRef = useRef<any>(null);
  const consecutiveReadyFrames = useRef<number>(0);

  // Initialize camera stream
  const startCamera = useCallback(async (mode: 'environment' | 'user') => {
    setCameraError(null);
    setReadinessState('CHECKING');

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (typeof window !== 'undefined' && window.isSecureContext === false) {
      setCameraError('Camera capture requires a secure context (HTTPS). Please access Metrixa over HTTPS or use the file upload option.');
      setReadinessState('NOT_READY');
      return;
    }

    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraError('Camera API is not supported in this browser. Please use the file upload option.');
      setReadinessState('NOT_READY');
      return;
    }

    try {
      let mediaStream: MediaStream;
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: { ideal: mode },
          width: { ideal: 1920, min: 1280 },
          height: { ideal: 1080, min: 720 },
        },
        audio: false,
      };

      try {
        mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch {
        // Graceful fallback for mobile devices or browsers with non-standard resolutions
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: mode },
          audio: false,
        }).catch(() => navigator.mediaDevices.getUserMedia({ video: true, audio: false }));
      }

      streamRef.current = mediaStream;

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        await videoRef.current.play();
      }
      setReadinessState('NOT_READY');
    } catch (err: any) {
      console.warn('Camera access issue:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraError('Camera permission denied. Please grant permission in your browser bar or use manual upload.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraError('No video camera device detected on this system.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraError('Camera is currently busy or in use by another application.');
      } else {
        setCameraError(`Camera initialization failed: ${err.message || 'Unknown error'}`);
      }
      setReadinessState('NOT_READY');
    }
  }, []);

  useEffect(() => {
    startCamera(facingMode);

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
      if (countdownTimerRef.current) {
        clearInterval(countdownTimerRef.current);
      }
    };
  }, [facingMode, startCamera]);

  // Capture frame function
  const triggerCapture = useCallback(async () => {
    if (!videoRef.current || readinessState === 'CAPTURING') return;
    setReadinessState('CAPTURING');
    if (countdownTimerRef.current) {
      clearInterval(countdownTimerRef.current);
      setCountdown(null);
    }

    const video = videoRef.current;
    const captureCanvas = document.createElement('canvas');
    captureCanvas.width = video.videoWidth || 1920;
    captureCanvas.height = video.videoHeight || 1080;

    const ctx = captureCanvas.getContext('2d');
    if (!ctx) {
      setReadinessState('NOT_READY');
      return;
    }

    ctx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);

    captureCanvas.toBlob(
      async (blob) => {
        if (!blob) {
          setCameraError('Failed to encode captured frame.');
          setReadinessState('NOT_READY');
          return;
        }

        try {
          await onCapture(blob);
          setReadinessState('CAPTURED');
        } catch (err: any) {
          setCameraError(err.message || 'Upload failed');
          setReadinessState('NOT_READY');
        }
      },
      'image/jpeg',
      0.95
    );
  }, [onCapture, readinessState]);

  // Real-time HUD analysis loop (throttled ~15-20fps for performance)
  useEffect(() => {
    let lastAnalysisTime = 0;
    const ANALYSIS_INTERVAL_MS = 65; // ~15 frames per second

    const runAnalysisLoop = (timestamp: number) => {
      if (
        videoRef.current &&
        videoRef.current.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
        timestamp - lastAnalysisTime >= ANALYSIS_INTERVAL_MS &&
        readinessState !== 'CAPTURING' &&
        readinessState !== 'CAPTURED'
      ) {
        lastAnalysisTime = timestamp;

        if (!analysisCanvasRef.current) {
          analysisCanvasRef.current = document.createElement('canvas');
          // Downsample to 320x240 for ultra-fast heuristics calculation
          analysisCanvasRef.current.width = 320;
          analysisCanvasRef.current.height = 240;
        }

        const canvas = analysisCanvasRef.current;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });

        if (ctx) {
          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
          const currentImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

          const metrics = evaluateFrameQuality(currentImageData, prevImageDataRef.current);
          prevImageDataRef.current = currentImageData;
          setQualityMetrics(metrics);

          if (metrics.isReady) {
            consecutiveReadyFrames.current += 1;
            setReadinessState('READY');

            // Auto-capture trigger after 12 consecutive ready frames (~800ms stable)
            if (autoCaptureEnabled && consecutiveReadyFrames.current === 12 && !countdown) {
              setCountdown(2);
              let remaining = 2;
              countdownTimerRef.current = setInterval(() => {
                remaining -= 1;
                if (remaining <= 0) {
                  clearInterval(countdownTimerRef.current!);
                  countdownTimerRef.current = null;
                  setCountdown(null);
                  triggerCapture();
                } else {
                  setCountdown(remaining);
                }
              }, 600);
            }
          } else {
            consecutiveReadyFrames.current = 0;
            setReadinessState('NOT_READY');
            if (countdownTimerRef.current) {
              clearInterval(countdownTimerRef.current);
              countdownTimerRef.current = null;
              setCountdown(null);
            }
          }
        }
      }

      animationFrameIdRef.current = requestAnimationFrame(runAnalysisLoop);
    };

    animationFrameIdRef.current = requestAnimationFrame(runAnalysisLoop);

    return () => {
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
    };
  }, [autoCaptureEnabled, countdown, readinessState, triggerCapture]);

  // Fallback file input change
  const handleFallbackFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      onCapture(file);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(5, 8, 15, 0.88)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: 16,
    }}>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        width: '100%',
        maxWidth: 880,
      }}>
        {/* Main HUD Viewport */}
        <div className="camera-hud-container" style={{ position: 'relative' }}>
          {cameraError ? (
            <div style={{
              padding: 32,
              textAlign: 'center',
              color: '#F9FAFB',
              maxWidth: 540,
            }}>
              <AlertCircle size={48} color="var(--accent-amber)" style={{ margin: '0 auto 16px' }} />
              <h3 style={{ fontSize: '1.25rem', marginBottom: 10 }}>Camera Unavailable</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', marginBottom: 24, lineHeight: 1.5 }}>
                {cameraError}
              </p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                <button 
                  onClick={() => startCamera(facingMode)}
                  className="btn btn-secondary"
                >
                  Retry Camera
                </button>
                <label className="btn btn-cyan" style={{ cursor: 'pointer' }}>
                  <Upload size={16} />
                  Upload Image Instead
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    style={{ display: 'none' }}
                    onChange={handleFallbackFile}
                  />
                </label>
              </div>
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                className="camera-video"
                playsInline
                muted
                autoPlay
              />

              {/* HUD Target Alignment Reticle */}
              <div className={`hud-reticle ${readinessState === 'READY' ? 'hud-reticle-ready' : 'hud-reticle-not-ready'}`}>
                <div className="reticle-corner reticle-tl" />
                <div className="reticle-corner reticle-tr" />
                <div className="reticle-corner reticle-bl" />
                <div className="reticle-corner reticle-br" />

                {/* Reticle Center Crosshair */}
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: 20,
                  height: 20,
                  pointerEvents: 'none',
                  opacity: 0.35,
                }}>
                  <div style={{ position: 'absolute', top: 9, left: 0, right: 0, height: 2, background: 'var(--accent-cyan)' }} />
                  <div style={{ position: 'absolute', left: 9, top: 0, bottom: 0, width: 2, background: 'var(--accent-cyan)' }} />
                </div>
              </div>

              {/* Auto-Capture Countdown Overlay */}
              {countdown !== null && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  backgroundColor: 'rgba(99, 102, 241, 0.85)',
                  color: '#FFFFFF',
                  width: 100,
                  height: 100,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '3.5rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  boxShadow: 'var(--shadow-indigo-glow)',
                  zIndex: 20,
                  animation: 'pulse-ring 0.6s infinite',
                }}>
                  {countdown}
                </div>
              )}

              {/* Interactive HUD Overlay Elements */}
              <div className="hud-overlay">
                {/* Header Bar */}
                <div className="hud-header">
                  <div className="hud-surface-badge">
                    <Camera size={16} />
                    <span>SURFACE: {surfaceType}</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: '0.78rem',
                      fontFamily: 'var(--font-mono)',
                      color: readinessState === 'READY' ? 'var(--verdict-pass)' : 'var(--text-secondary)',
                      backgroundColor: 'rgba(0,0,0,0.5)',
                      padding: '4px 10px',
                      borderRadius: 4,
                      border: `1px solid ${readinessState === 'READY' ? 'var(--verdict-pass-border)' : 'var(--border-muted)'}`
                    }}>
                      {readinessState === 'READY' ? (
                        <>
                          <CheckCircle2 size={13} color="var(--verdict-pass)" />
                          <span>READY FOR CAPTURE</span>
                        </>
                      ) : readinessState === 'CAPTURING' ? (
                        <>
                          <Activity size={13} color="var(--primary-500)" />
                          <span>CAPTURING...</span>
                        </>
                      ) : (
                        <>
                          <Focus size={13} color="var(--text-muted)" />
                          <span>ADJUSTING FRAMING</span>
                        </>
                      )}
                    </div>

                    <button
                      onClick={onClose}
                      className="btn btn-outline btn-sm"
                      style={{ padding: 4, borderRadius: '50%' }}
                      title="Close HUD"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>

                {/* Left Telemetry Panel */}
                <div className="hud-telemetry-panel">
                  {/* Focus / Sharpness */}
                  <div className={`telemetry-item ${qualityMetrics?.isSharp ? 'status-ok' : 'status-bad'}`}>
                    <Focus size={14} />
                    <span>{qualityMetrics?.sharpnessLabel || 'Checking focus...'}</span>
                  </div>

                  {/* Lighting */}
                  <div className={`telemetry-item ${qualityMetrics?.lightingStatus === 'optimal' ? 'status-ok' : 'status-warn'}`}>
                    <Sun size={14} />
                    <span>{qualityMetrics?.lightingLabel || 'Evaluating lighting...'}</span>
                  </div>

                  {/* Glare */}
                  <div className={`telemetry-item ${qualityMetrics?.hasGlare ? 'status-bad' : 'status-ok'}`}>
                    <Sparkles size={14} />
                    <span>{qualityMetrics?.glareLabel || 'Scanning reflections...'}</span>
                  </div>

                  {/* Stability */}
                  <div className={`telemetry-item ${qualityMetrics?.isStable ? 'status-ok' : 'status-warn'}`}>
                    <Activity size={14} />
                    <span>{qualityMetrics?.stabilityLabel || 'Detecting motion...'}</span>
                  </div>

                  {/* Framing */}
                  <div className={`telemetry-item ${qualityMetrics?.framingStatus === 'good' ? 'status-ok' : 'status-warn'}`}>
                    <Maximize size={14} />
                    <span>{qualityMetrics?.framingLabel || 'Center package...'}</span>
                  </div>
                </div>

                {/* Bottom HUD Controls */}
                <div className="hud-footer">
                  {/* Switch Camera */}
                  <button
                    onClick={() => setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))}
                    className="btn btn-secondary btn-sm"
                    style={{ gap: 6 }}
                    title="Flip Camera"
                  >
                    <FlipHorizontal size={16} />
                    <span>Flip</span>
                  </button>

                  {/* Shutter Button */}
                  <button
                    onClick={triggerCapture}
                    className="hud-shutter-btn"
                    disabled={readinessState === 'CAPTURING'}
                    title="Capture Now"
                  >
                    <div className="hud-shutter-inner" />
                  </button>

                  {/* Auto-Capture Toggle */}
                  <button
                    onClick={() => setAutoCaptureEnabled((prev) => !prev)}
                    className="btn btn-secondary btn-sm"
                    style={{
                      gap: 6,
                      borderColor: autoCaptureEnabled ? 'var(--primary-500)' : 'var(--border-muted)',
                      color: autoCaptureEnabled ? 'var(--accent-cyan)' : 'var(--text-muted)'
                    }}
                    title="Toggle Automatic Capture"
                  >
                    <Timer size={16} />
                    <span>Auto: {autoCaptureEnabled ? 'ON' : 'OFF'}</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Guidance disclaimer footer */}
        <div style={{
          marginTop: 12,
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          textAlign: 'center',
          maxWidth: 600,
        }}>
          Capture HUD provides image-quality and framing guidance only. 
          Deterministic legal compliance evaluation is performed exclusively by the backend statutory rule engine.
        </div>
      </div>
    </div>
  );
};
