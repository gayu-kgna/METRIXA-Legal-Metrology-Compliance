import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  PlusCircle,
  Tag,
  Eye,
  EyeOff,
  Percent,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Crosshair,
} from 'lucide-react';
import { AdjudicatedOCRRegion, BoundingBoxNormalized } from '../../types/api';

interface BoundingBoxCanvasProps {
  imageUrl: string;
  regions: AdjudicatedOCRRegion[];
  selectedRegionId: string | null;
  onSelectRegion: (region: AdjudicatedOCRRegion | null) => void;
  onUpdateRegionBbox: (regionId: string, newBbox: BoundingBoxNormalized) => void;
  onCreateRegionBox: (newBbox: BoundingBoxNormalized) => void;
  isDrawingMode: boolean;
  setIsDrawingMode: (val: boolean) => void;
  showLabels: boolean;
  setShowLabels: (val: boolean) => void;
  showConfidence: boolean;
  setShowConfidence: (val: boolean) => void;
  hideRejected: boolean;
  setHideRejected: (val: boolean) => void;
  surfaceName?: string;
}

export function normalizeBox(b: any): {
  x: number;
  y: number;
  width: number;
  height: number;
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
} {
  if (!b) return { x: 0, y: 0, width: 0, height: 0, xmin: 0, ymin: 0, xmax: 0, ymax: 0 };
  const x = b.x ?? b.xmin ?? 0;
  const y = b.y ?? b.ymin ?? 0;
  const width = b.width ?? (b.xmax !== undefined ? Math.max(0, b.xmax - (b.xmin ?? 0)) : 0);
  const height = b.height ?? (b.ymax !== undefined ? Math.max(0, b.ymax - (b.ymin ?? 0)) : 0);
  const xmin = b.xmin ?? x;
  const ymin = b.ymin ?? y;
  const xmax = b.xmax ?? Math.min(1, x + width);
  const ymax = b.ymax ?? Math.min(1, y + height);
  return { x, y, width, height, xmin, ymin, xmax, ymax };
}

type DragHandle = 'move' | 'nw' | 'ne' | 'se' | 'sw' | 'n' | 's' | 'e' | 'w';

export const BoundingBoxCanvas: React.FC<BoundingBoxCanvasProps> = ({
  imageUrl,
  regions,
  selectedRegionId,
  onSelectRegion,
  onUpdateRegionBbox,
  onCreateRegionBox,
  isDrawingMode,
  setIsDrawingMode,
  showLabels,
  setShowLabels,
  showConfidence,
  setShowConfidence,
  hideRejected,
  setHideRejected,
  surfaceName = 'Front (PDP)',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [zoom, setZoom] = useState<number>(1.0);
  const [imageSize, setImageSize] = useState<{ width: number; height: number }>({ width: 800, height: 600 });
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number }>({ width: 800, height: 600 });
  const [cursorPos, setCursorPos] = useState<{ x: number; y: number; normX: number; normY: number }>({
    x: 0,
    y: 0,
    normX: 0,
    normY: 0,
  });

  // Interactive drawing state
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);

  // Dragging/resizing existing box state
  const [dragAction, setDragAction] = useState<{
    handle: DragHandle;
    regionId: string;
    startNorm: { x: number; y: number };
    initialBbox: BoundingBoxNormalized;
  } | null>(null);

  // Handle image load to capture actual rendered and natural dimensions
  const onImageLoad = () => {
    if (imageRef.current) {
      const { naturalWidth, naturalHeight, clientWidth, clientHeight } = imageRef.current;
      setNaturalSize({ width: naturalWidth || 800, height: naturalHeight || 600 });
      setImageSize({ width: clientWidth || 800, height: clientHeight || 600 });
    }
  };

  useEffect(() => {
    const handleResize = () => {
      if (imageRef.current) {
        setImageSize({
          width: imageRef.current.clientWidth,
          height: imageRef.current.clientHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Calculate normalized coordinate from mouse event
  const getNormalizedPoint = useCallback((e: React.MouseEvent): { normX: number; normY: number; pxX: number; pxY: number } => {
    if (!imageRef.current) return { normX: 0, normY: 0, pxX: 0, pxY: 0 };
    const rect = imageRef.current.getBoundingClientRect();
    const pxX = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const pxY = Math.max(0, Math.min(e.clientY - rect.top, rect.height));
    const normX = Math.max(0, Math.min(pxX / rect.width, 1));
    const normY = Math.max(0, Math.min(pxY / rect.height, 1));
    return { normX, normY, pxX, pxY };
  }, []);

  // Track cursor position
  const handleMouseMove = (e: React.MouseEvent) => {
    const { normX, normY, pxX, pxY } = getNormalizedPoint(e);
    setCursorPos({
      x: Math.round(normX * naturalSize.width),
      y: Math.round(normY * naturalSize.height),
      normX: parseFloat(normX.toFixed(4)),
      normY: parseFloat(normY.toFixed(4)),
    });

    if (isDrawingMode && isDrawing && drawStart) {
      setDrawCurrent({ x: normX, y: normY });
    } else if (dragAction) {
      handleDragMove(normX, normY);
    }
  };

  // Drawing new bounding box
  const handleMouseDown = (e: React.MouseEvent) => {
    if (isDrawingMode) {
      e.preventDefault();
      const { normX, normY } = getNormalizedPoint(e);
      setIsDrawing(true);
      setDrawStart({ x: normX, y: normY });
      setDrawCurrent({ x: normX, y: normY });
    }
  };

  const handleMouseUp = () => {
    if (isDrawingMode && isDrawing && drawStart && drawCurrent) {
      setIsDrawing(false);
      const xmin = Math.max(0, Math.min(drawStart.x, drawCurrent.x));
      const xmax = Math.min(1, Math.max(drawStart.x, drawCurrent.x));
      const ymin = Math.max(0, Math.min(drawStart.y, drawCurrent.y));
      const ymax = Math.min(1, Math.max(drawStart.y, drawCurrent.y));

      // Minimum threshold check (prevent accidental clicks)
      if (xmax - xmin > 0.01 && ymax - ymin > 0.01) {
        onCreateRegionBox({ xmin, xmax, ymin, ymax });
      }
      setDrawStart(null);
      setDrawCurrent(null);
      setIsDrawingMode(false);
    }

    if (dragAction) {
      setDragAction(null);
    }
  };

  // Start dragging or resizing a region
  const startDrag = (
    e: React.MouseEvent,
    regionId: string,
    handle: DragHandle,
    initialBbox: BoundingBoxNormalized
  ) => {
    e.stopPropagation();
    if (isDrawingMode) return;
    const { normX, normY } = getNormalizedPoint(e);
    setDragAction({
      handle,
      regionId,
      startNorm: { x: normX, y: normY },
      initialBbox: { ...initialBbox },
    });
  };

  // Compute new bbox during drag/resize
  const handleDragMove = (currentNormX: number, currentNormY: number) => {
    if (!dragAction) return;
    const { handle, regionId, startNorm, initialBbox } = dragAction;
    const dx = currentNormX - startNorm.x;
    const dy = currentNormY - startNorm.y;

    let { xmin, ymin, xmax, ymax } = initialBbox;

    if (handle === 'move') {
      const width = xmax - xmin;
      const height = ymax - ymin;
      xmin = Math.max(0, Math.min(1 - width, initialBbox.xmin + dx));
      xmax = xmin + width;
      ymin = Math.max(0, Math.min(1 - height, initialBbox.ymin + dy));
      ymax = ymin + height;
    } else if (handle === 'nw') {
      xmin = Math.max(0, Math.min(initialBbox.xmax - 0.01, initialBbox.xmin + dx));
      ymin = Math.max(0, Math.min(initialBbox.ymax - 0.01, initialBbox.ymin + dy));
    } else if (handle === 'ne') {
      xmax = Math.min(1, Math.max(initialBbox.xmin + 0.01, initialBbox.xmax + dx));
      ymin = Math.max(0, Math.min(initialBbox.ymax - 0.01, initialBbox.ymin + dy));
    } else if (handle === 'se') {
      xmax = Math.min(1, Math.max(initialBbox.xmin + 0.01, initialBbox.xmax + dx));
      ymax = Math.min(1, Math.max(initialBbox.ymin + 0.01, initialBbox.ymax + dy));
    } else if (handle === 'sw') {
      xmin = Math.max(0, Math.min(initialBbox.xmax - 0.01, initialBbox.xmin + dx));
      ymax = Math.min(1, Math.max(initialBbox.ymin + 0.01, initialBbox.ymax + dy));
    } else if (handle === 'n') {
      ymin = Math.max(0, Math.min(initialBbox.ymax - 0.01, initialBbox.ymin + dy));
    } else if (handle === 's') {
      ymax = Math.min(1, Math.max(initialBbox.ymin + 0.01, initialBbox.ymax + dy));
    } else if (handle === 'w') {
      xmin = Math.max(0, Math.min(initialBbox.xmax - 0.01, initialBbox.xmin + dx));
    } else if (handle === 'e') {
      xmax = Math.min(1, Math.max(initialBbox.xmin + 0.01, initialBbox.xmax + dx));
    }

    onUpdateRegionBbox(regionId, {
      xmin: parseFloat(xmin.toFixed(4)),
      ymin: parseFloat(ymin.toFixed(4)),
      xmax: parseFloat(xmax.toFixed(4)),
      ymax: parseFloat(ymax.toFixed(4)),
    });
  };

  const selectedRegion = regions.find((r) => r.id === selectedRegionId);
  const visibleRegions = hideRejected
    ? regions.filter((r) => !(r.is_rejected ?? (r.status === 'REJECTED')))
    : regions;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-canvas)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* HUD Header Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          backgroundColor: 'var(--bg-surface-primary)',
          borderBottom: '1px solid var(--border-subtle)',
          flexWrap: 'wrap',
          gap: '8px',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              fontSize: '13px',
              fontWeight: 600,
              letterSpacing: '0.05em',
              color: 'var(--accent-cyan)',
              textTransform: 'uppercase',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Crosshair size={15} />
            {surfaceName}
          </span>
          <span
            style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-secondary)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {visibleRegions.length} Regions
          </span>
        </div>

        {/* Action controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          {/* Draw region toggle */}
          <button
            id="btn-draw-box-mode"
            onClick={() => setIsDrawingMode(!isDrawingMode)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 600,
              border: isDrawingMode ? '1px solid var(--accent-cyan)' : '1px solid var(--border-muted)',
              backgroundColor: isDrawingMode ? 'var(--accent-cyan-glow)' : 'var(--bg-surface-secondary)',
              color: isDrawingMode ? 'var(--accent-cyan)' : 'var(--text-main)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            title="Click and drag on the image to draw a new bounding region"
          >
            <PlusCircle size={14} />
            {isDrawingMode ? 'Drawing Active...' : 'Draw Region'}
          </button>

          <div style={{ height: '18px', width: '1px', backgroundColor: 'var(--border-muted)', margin: '0 4px' }} />

          {/* Toggle Labels */}
          <button
            onClick={() => setShowLabels(!showLabels)}
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              border: '1px solid var(--border-muted)',
              backgroundColor: showLabels ? 'var(--primary-glow)' : 'var(--bg-surface-secondary)',
              color: showLabels ? 'var(--primary-500)' : 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Toggle OCR Text Labels"
          >
            <Tag size={14} />
            Labels
          </button>

          {/* Toggle Confidence */}
          <button
            onClick={() => setShowConfidence(!showConfidence)}
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              border: '1px solid var(--border-muted)',
              backgroundColor: showConfidence ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-surface-secondary)',
              color: showConfidence ? 'var(--verdict-pass)' : 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Toggle OCR Confidence Scores"
          >
            <Percent size={14} />
            Conf.
          </button>

          {/* Toggle Hide Rejected */}
          <button
            onClick={() => setHideRejected(!hideRejected)}
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              border: '1px solid var(--border-muted)',
              backgroundColor: hideRejected ? 'rgba(239, 68, 68, 0.15)' : 'var(--bg-surface-secondary)',
              color: hideRejected ? 'var(--verdict-fail)' : 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Hide noise or rejected bounding boxes"
          >
            {hideRejected ? <EyeOff size={14} /> : <Eye size={14} />}
            {hideRejected ? 'Rejected Hidden' : 'Show All'}
          </button>

          <div style={{ height: '18px', width: '1px', backgroundColor: 'var(--border-muted)', margin: '0 4px' }} />

          {/* Zoom controls */}
          <button
            onClick={() => setZoom((z) => Math.max(0.5, parseFloat((z - 0.25).toFixed(2))))}
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-muted)',
              backgroundColor: 'var(--bg-surface-secondary)',
              color: 'var(--text-main)',
              cursor: 'pointer',
            }}
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>

          <span
            style={{
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              minWidth: '42px',
              textAlign: 'center',
              color: 'var(--text-secondary)',
            }}
          >
            {Math.round(zoom * 100)}%
          </span>

          <button
            onClick={() => setZoom((z) => Math.min(3.0, parseFloat((z + 0.25).toFixed(2))))}
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-muted)',
              backgroundColor: 'var(--bg-surface-secondary)',
              color: 'var(--text-main)',
              cursor: 'pointer',
            }}
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>

          <button
            onClick={() => setZoom(1.0)}
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-muted)',
              backgroundColor: 'var(--bg-surface-secondary)',
              color: 'var(--text-main)',
              cursor: 'pointer',
            }}
            title="Reset Zoom (100%)"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      {/* Main Canvas Scroll Area */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflow: 'auto',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '24px',
          backgroundColor: '#070A10',
          position: 'relative',
          cursor: isDrawingMode ? 'crosshair' : 'default',
          userSelect: 'none',
        }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        <div
          style={{
            position: 'relative',
            transform: `scale(${zoom})`,
            transformOrigin: 'top center',
            transition: dragAction ? 'none' : 'transform 0.1s ease',
            boxShadow: 'var(--shadow-lg)',
            border: '1px solid var(--border-highlight)',
            borderRadius: 'var(--radius-sm)',
            overflow: 'hidden',
            backgroundColor: '#000',
          }}
          onMouseDown={handleMouseDown}
        >
          {/* Surface Image */}
          <img
            ref={imageRef}
            src={imageUrl}
            alt={surfaceName}
            onLoad={onImageLoad}
            style={{
              display: 'block',
              maxWidth: '850px',
              maxHeight: '70vh',
              width: 'auto',
              height: 'auto',
              pointerEvents: 'none',
            }}
          />

          {/* SVG Overlay for Bounding Boxes */}
          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: isDrawingMode ? 'none' : 'auto',
            }}
            viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
          >
            {visibleRegions.map((region) => {
              const rawBbox = region.effective_bounding_box || region.bounding_box;
              const normBbox = normalizeBox(rawBbox);
              const isSelected = region.id === selectedRegionId;
              const x = normBbox.xmin * imageSize.width;
              const y = normBbox.ymin * imageSize.height;
              const width = Math.max(4, (normBbox.xmax - normBbox.xmin) * imageSize.width);
              const height = Math.max(4, (normBbox.ymax - normBbox.ymin) * imageSize.height);

              const text = region.effective_text || region.raw_text || '';
              const isRejected = region.is_rejected ?? (region.status === 'REJECTED');
              const isManuallyCreated = region.is_manually_created ?? (region.status === 'MANUAL');

              // Palette determination
              let strokeColor = '#3B82F6'; // Default Blue
              let fillColor = 'rgba(59, 130, 246, 0.12)';
              let strokeDasharray = 'none';

              if (isRejected) {
                strokeColor = '#EF4444';
                fillColor = 'rgba(239, 68, 68, 0.15)';
                strokeDasharray = '4 3';
              } else if (isManuallyCreated) {
                strokeColor = '#A855F7';
                fillColor = 'rgba(168, 85, 247, 0.15)';
              } else if (region.is_adjudicated) {
                strokeColor = '#06B6D4';
                fillColor = 'rgba(6, 182, 212, 0.15)';
              }

              if (isSelected) {
                strokeColor = '#F59E0B';
                fillColor = 'rgba(245, 158, 11, 0.25)';
              }

              const bboxForDrag = {
                xmin: normBbox.xmin,
                ymin: normBbox.ymin,
                xmax: normBbox.xmax,
                ymax: normBbox.ymax,
              };

              return (
                <g key={region.id} id={`region-group-${region.id}`}>
                  {/* Bounding box rect */}
                  <rect
                    id={`bbox-${region.id}`}
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    strokeDasharray={strokeDasharray}
                    style={{
                      cursor: isSelected ? 'move' : 'pointer',
                      transition: 'stroke 0.15s ease',
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectRegion(region);
                    }}
                    onMouseDown={(e) => isSelected && startDrag(e, region.id, 'move', bboxForDrag)}
                  />

                  {/* Text Label & Confidence Tag */}
                  {showLabels && (
                    <g transform={`translate(${x}, ${Math.max(14, y - 4)})`}>
                      <rect
                        x={0}
                        y={-14}
                        width={Math.min(220, (text.length * 6.5) + (showConfidence ? 36 : 8))}
                        height={16}
                        rx={3}
                        fill="rgba(17, 24, 39, 0.9)"
                        stroke={strokeColor}
                        strokeWidth={0.75}
                      />
                      <text
                        x={4}
                        y={-3}
                        fill={isRejected ? '#EF4444' : '#F9FAFB'}
                        fontSize="9.5px"
                        fontFamily="var(--font-mono)"
                        fontWeight="600"
                        style={{
                          textDecoration: isRejected ? 'line-through' : 'none',
                        }}
                      >
                        {text.length > 22
                          ? text.substring(0, 20) + '...'
                          : text}
                        {showConfidence && (
                          <tspan fill="#10B981" dx="4">
                            {(region.confidence * 100).toFixed(0)}%
                          </tspan>
                        )}
                      </text>
                    </g>
                  )}

                  {/* Resize Handles (rendered only when region is selected) */}
                  {isSelected && (
                    <g>
                      {/* NW */}
                      <circle
                        cx={x}
                        cy={y}
                        r={4.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1.5}
                        style={{ cursor: 'nw-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 'nw', bboxForDrag)}
                      />
                      {/* NE */}
                      <circle
                        cx={x + width}
                        cy={y}
                        r={4.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1.5}
                        style={{ cursor: 'ne-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 'ne', bboxForDrag)}
                      />
                      {/* SE */}
                      <circle
                        cx={x + width}
                        cy={y + height}
                        r={4.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1.5}
                        style={{ cursor: 'se-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 'se', bboxForDrag)}
                      />
                      {/* SW */}
                      <circle
                        cx={x}
                        cy={y + height}
                        r={4.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1.5}
                        style={{ cursor: 'sw-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 'sw', bboxForDrag)}
                      />

                      {/* North center */}
                      <circle
                        cx={x + width / 2}
                        cy={y}
                        r={3.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1}
                        style={{ cursor: 'n-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 'n', bboxForDrag)}
                      />
                      {/* South center */}
                      <circle
                        cx={x + width / 2}
                        cy={y + height}
                        r={3.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1}
                        style={{ cursor: 's-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 's', bboxForDrag)}
                      />
                      {/* West center */}
                      <circle
                        cx={x}
                        cy={y + height / 2}
                        r={3.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1}
                        style={{ cursor: 'w-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 'w', bboxForDrag)}
                      />
                      {/* East center */}
                      <circle
                        cx={x + width}
                        cy={y + height / 2}
                        r={3.5}
                        fill="#F59E0B"
                        stroke="#111827"
                        strokeWidth={1}
                        style={{ cursor: 'e-resize' }}
                        onMouseDown={(e) => startDrag(e, region.id, 'e', bboxForDrag)}
                      />
                    </g>
                  )}
                </g>
              );
            })}

            {/* Drawing Preview Rect */}
            {isDrawing && drawStart && drawCurrent && (
              <rect
                x={Math.min(drawStart.x, drawCurrent.x) * imageSize.width}
                y={Math.min(drawStart.y, drawCurrent.y) * imageSize.height}
                width={Math.abs(drawCurrent.x - drawStart.x) * imageSize.width}
                height={Math.abs(drawCurrent.y - drawStart.y) * imageSize.height}
                fill="rgba(6, 182, 212, 0.2)"
                stroke="var(--accent-cyan)"
                strokeWidth={2}
                strokeDasharray="4 4"
              />
            )}
          </svg>
        </div>
      </div>

      {/* HUD Coordinate & Status Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 16px',
          backgroundColor: 'var(--bg-surface-primary)',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-secondary)',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span>
            Cursor: <strong style={{ color: 'var(--text-main)' }}>X:{cursorPos.x} Y:{cursorPos.y}</strong> ({cursorPos.normX}, {cursorPos.normY})
          </span>
          <span>
            Source Res: <strong style={{ color: 'var(--text-main)' }}>{naturalSize.width}x{naturalSize.height} px</strong>
          </span>
        </div>

        <div>
          {selectedRegion ? (
            (() => {
              const nb = normalizeBox(selectedRegion.effective_bounding_box || selectedRegion.bounding_box);
              return (
                <span style={{ color: 'var(--accent-amber)' }}>
                  Selected: [{nb.xmin.toFixed(3)},{' '}
                  {nb.ymin.toFixed(3)},{' '}
                  {nb.xmax.toFixed(3)},{' '}
                  {nb.ymax.toFixed(3)}]
                </span>
              );
            })()
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>Click a box to select & edit</span>
          )}
        </div>
      </div>
    </div>
  );
};
