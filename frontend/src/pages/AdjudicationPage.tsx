import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  RotateCcw,
  Layers,
  ArrowLeft,
  FileText,
  AlertCircle,
  CheckCircle,
  Eye,
  Crosshair,
} from 'lucide-react';
import {
  AdjudicationWorkspaceState,
  AdjudicatedOCRRegion,
  AdjudicatedObservation,
  BoundingBoxNormalized,
  OCRRegionPatchRequest,
  ManualObservationCreateRequest,
  ObservationCorrectRequest,
  ObservationStatus,
  RuleReevaluationResponse,
  SurfaceRead,
} from '../types/api';
import {
  getWorkspaceState,
  createOCRRegion,
  patchOCRRegion,
  rejectOCRRegion,
  verifyObservation,
  correctObservation,
  rejectObservation,
  updateObservationStatus,
  createManualObservation,
  reevaluateRules,
} from '../api/adjudication';
import { getImageContentUrl } from '../api/images';
import { BoundingBoxCanvas } from '../components/adjudication/BoundingBoxCanvas';
import { OCRRegionEditor } from '../components/adjudication/OCRRegionEditor';
import { ObservationPanel } from '../components/adjudication/ObservationPanel';
import { ManualObservationDialog } from '../components/adjudication/ManualObservationDialog';
import { ConflictResolutionPanel } from '../components/adjudication/ConflictResolutionPanel';
import { RuleReevaluationPanel } from '../components/adjudication/RuleReevaluationPanel';

export const AdjudicationPage: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId: string }>();

  const [workspace, setWorkspace] = useState<AdjudicationWorkspaceState | null>(null);
  const [selectedSurfaceId, setSelectedSurfaceId] = useState<string | null>(null);
  const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);
  const [pendingNewBox, setPendingNewBox] = useState<BoundingBoxNormalized | null>(null);
  const [isDrawingMode, setIsDrawingMode] = useState<boolean>(false);
  const [showLabels, setShowLabels] = useState<boolean>(true);
  const [showConfidence, setShowConfidence] = useState<boolean>(true);
  const [hideRejected, setHideRejected] = useState<boolean>(false);

  const [isManualModalOpen, setIsManualModalOpen] = useState<boolean>(false);
  const [reevaluationResult, setReevaluationResult] = useState<RuleReevaluationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'declarations' | 'conflicts' | 'reevaluation'>('declarations');

  // Load workspace state
  const loadWorkspace = useCallback(async () => {
    if (!inspectionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await getWorkspaceState(inspectionId);
      setWorkspace(data);

      // Default to front surface if available
      if (!selectedSurfaceId && data.surfaces && data.surfaces.length > 0) {
        const front = data.surfaces.find((s) => s.surface_type === 'FRONT_PDP') || data.surfaces[0];
        setSelectedSurfaceId(front.id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load adjudication workspace state.');
    } finally {
      setIsLoading(false);
    }
  }, [inspectionId, selectedSurfaceId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // Active surface and its regions
  const currentSurface = workspace?.surfaces?.find((s) => s.id === selectedSurfaceId) || workspace?.surfaces?.[0];
  const surfaceRegions = workspace?.regions?.filter((r) => r.surface_id === currentSurface?.id) || [];
  const selectedRegion = surfaceRegions.find((r) => r.id === selectedRegionId) || null;

  // Region actions
  const handleSelectRegion = (region: AdjudicatedOCRRegion | null) => {
    setSelectedRegionId(region ? region.id : null);
    setPendingNewBox(null);
  };

  const handleUpdateRegionBbox = async (regionId: string, newBbox: BoundingBoxNormalized) => {
    if (!inspectionId) return;
    try {
      const updated = await patchOCRRegion(inspectionId, regionId, {
        corrected_bounding_box: newBbox,
        reason: 'Officer adjusted bounding box coordinates on visual canvas',
      });
      // Optimistic update
      setWorkspace((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          regions: prev.regions.map((r) => (r.id === regionId ? updated : r)),
        };
      });
    } catch (err: any) {
      console.error('Error updating region bbox:', err);
    }
  };

  const handleCreateRegionBox = (newBbox: BoundingBoxNormalized) => {
    setPendingNewBox(newBbox);
    setSelectedRegionId(null);
  };

  const handleSaveCorrection = async (regionId: string, patch: OCRRegionPatchRequest) => {
    if (!inspectionId) return;
    const updated = await patchOCRRegion(inspectionId, regionId, patch);
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        adjudicated_regions_count: prev.adjudicated_regions_count + 1,
        regions: prev.regions.map((r) => (r.id === regionId ? updated : r)),
      };
    });
    setSelectedRegionId(null);
  };

  const handleRejectRegion = async (regionId: string, reason: string) => {
    if (!inspectionId) return;
    const updated = await rejectOCRRegion(inspectionId, regionId, reason);
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        rejected_regions_count: prev.rejected_regions_count + 1,
        regions: prev.regions.map((r) => (r.id === regionId ? updated : r)),
      };
    });
    setSelectedRegionId(null);
  };

  const handleCreateRegion = async (rawText: string, reason: string) => {
    if (!inspectionId || !currentSurface || !pendingNewBox) return;
    const created = await createOCRRegion(inspectionId, {
      surface_id: currentSurface.id,
      raw_text: rawText,
      bounding_box: pendingNewBox,
      reason,
    });
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        total_regions: prev.total_regions + 1,
        adjudicated_regions_count: prev.adjudicated_regions_count + 1,
        regions: [...prev.regions, created],
      };
    });
    setPendingNewBox(null);
  };

  // Observation actions
  const handleVerifyObservation = async (obsId: string) => {
    if (!inspectionId) return;
    const updated = await verifyObservation(inspectionId, obsId, 'Officer verified statutory compliance');
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        verified_observations_count: prev.verified_observations_count + 1,
        observations: prev.observations.map((o) => (o.id === obsId ? updated : o)),
      };
    });
  };

  const handleCorrectObservation = async (obsId: string, data: ObservationCorrectRequest) => {
    if (!inspectionId) return;
    const updated = await correctObservation(inspectionId, obsId, data);
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        observations: prev.observations.map((o) => (o.id === obsId ? updated : o)),
      };
    });
  };

  const handleRejectObservation = async (obsId: string, reason: string) => {
    if (!inspectionId) return;
    const updated = await rejectObservation(inspectionId, obsId, reason);
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        observations: prev.observations.map((o) => (o.id === obsId ? updated : o)),
      };
    });
  };

  const handleUpdateObsStatus = async (obsId: string, status: ObservationStatus) => {
    if (!inspectionId) return;
    const updated = await updateObservationStatus(inspectionId, obsId, status);
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        observations: prev.observations.map((o) => (o.id === obsId ? updated : o)),
      };
    });
  };

  const handleCreateManualObservation = async (data: ManualObservationCreateRequest) => {
    if (!inspectionId) return;
    const created = await createManualObservation(inspectionId, data);
    setWorkspace((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        total_observations: prev.total_observations + 1,
        observations: [...prev.observations, created],
      };
    });
  };

  // Conflict resolution
  const handleSelectAuthoritative = async (fieldType: string, winningObsId: string) => {
    if (!workspace) return;
    // Verify winning observation
    await handleVerifyObservation(winningObsId);
    // Reject other conflicting observations in group
    const group = workspace.conflicts.find((c) => c.field_type === fieldType);
    if (group) {
      for (const obs of group.observations) {
        if (obs.id !== winningObsId && obs.status !== 'REJECTED') {
          await handleRejectObservation(obs.id, `Superseded by authoritative observation ${winningObsId}`);
        }
      }
    }
    // Reload state
    await loadWorkspace();
  };

  // Rule re-evaluation
  const handleReevaluateRules = async (justification?: string) => {
    if (!inspectionId) throw new Error('No inspection ID');
    const result = await reevaluateRules(inspectionId, justification);
    setReevaluationResult(result);
    return result;
  };

  if (isLoading && !workspace) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Loading inspection adjudication console...
      </div>
    );
  }

  if (error && !workspace) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--verdict-fail)' }}>
        <AlertCircle size={28} style={{ margin: '0 auto 12px' }} />
        <p>{error}</p>
        <button onClick={loadWorkspace} style={{ marginTop: '16px', padding: '8px 16px' }}>
          Retry
        </button>
      </div>
    );
  }

  const activeConflictsCount = workspace?.conflicts?.filter((c) => c.has_conflict).length || 0;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - var(--navbar-height))',
        backgroundColor: 'var(--bg-canvas)',
        overflow: 'hidden',
      }}
    >
      {/* Top Console Navigation & Summary Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 24px',
          backgroundColor: 'var(--bg-surface-primary)',
          borderBottom: '1px solid var(--border-subtle)',
          flexWrap: 'wrap',
          gap: '12px',
          zIndex: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Link
            to={`/inspections/${inspectionId}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: 'var(--text-secondary)',
              textDecoration: 'none',
              fontSize: '13px',
            }}
          >
            <ArrowLeft size={16} /> Inspection Detail
          </Link>

          <div style={{ height: '18px', width: '1px', backgroundColor: 'var(--border-muted)' }} />

          <div>
            <h1 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Crosshair size={18} style={{ color: 'var(--accent-cyan)' }} />
              Adjudication Console & Bounding Box Workspace
            </h1>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Inspection {workspace?.inspection_number} | Authorized Legal Metrology Officer Console
            </p>
          </div>
        </div>

        {/* Stats Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <div
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-secondary)',
              border: '1px solid var(--border-subtle)',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span style={{ color: 'var(--text-muted)' }}>Regions: </span>
            <strong style={{ color: 'var(--text-main)' }}>{workspace?.total_regions ?? workspace?.regions?.length ?? 0}</strong>{' '}
            <span style={{ color: 'var(--accent-cyan)' }}>({workspace?.adjudicated_regions_count ?? workspace?.regions?.filter(r => r.is_adjudicated).length ?? 0} adj)</span>
          </div>

          <div
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-secondary)',
              border: '1px solid var(--border-subtle)',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span style={{ color: 'var(--text-muted)' }}>Observations: </span>
            <strong style={{ color: 'var(--text-main)' }}>{workspace?.total_observations ?? workspace?.observations?.length ?? 0}</strong>{' '}
            <span style={{ color: 'var(--verdict-pass)' }}>({workspace?.verified_observations_count ?? workspace?.observations?.filter(o => o.status === 'VERIFIED').length ?? 0} verified)</span>
          </div>

          {activeConflictsCount > 0 && (
            <div
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--verdict-review-bg)',
                border: '1px solid var(--verdict-review-border)',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                color: 'var(--verdict-review)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <AlertCircle size={13} />
              {activeConflictsCount} Conflict{activeConflictsCount > 1 ? 's' : ''}
            </div>
          )}

          {/* Quick link to Evidence Browser */}
          <Link
            to={`/inspections/${inspectionId}/evidence`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--primary-glow)',
              color: 'var(--primary-500)',
              fontSize: '12px',
              fontWeight: 600,
              textDecoration: 'none',
              border: '1px solid var(--border-glow)',
            }}
          >
            <ShieldCheck size={14} /> Evidence Trace
          </Link>
        </div>
      </div>

      {/* Surface Selector Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          padding: '8px 24px',
          backgroundColor: 'var(--bg-canvas)',
          borderBottom: '1px solid var(--border-subtle)',
          overflowX: 'auto',
        }}
      >
        {workspace?.surfaces?.map((surf) => {
          const isSelected = surf.id === currentSurface?.id;
          const count = workspace.regions.filter((r) => r.surface_id === surf.id).length;

          return (
            <button
              key={surf.id}
              id={`tab-surface-${surf.surface_type}`}
              onClick={() => {
                setSelectedSurfaceId(surf.id);
                setSelectedRegionId(null);
                setPendingNewBox(null);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '12px',
                fontWeight: isSelected ? 700 : 500,
                border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                backgroundColor: isSelected ? 'var(--accent-cyan-glow)' : 'var(--bg-surface-secondary)',
                color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              <span>{surf.surface_type}</span>
              <span
                style={{
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  padding: '1px 5px',
                  borderRadius: 'var(--radius-full)',
                  backgroundColor: isSelected ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.1)',
                  color: isSelected ? '#000' : 'var(--text-muted)',
                }}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Main Split Body */}
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'minmax(450px, 1.4fr) minmax(380px, 1fr)',
          overflow: 'hidden',
          gap: '1px',
          backgroundColor: 'var(--border-subtle)',
        }}
      >
        {/* Left Column: Bounding Box Canvas and Region Editor */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'var(--bg-canvas)',
            overflow: 'hidden',
          }}
        >
          {currentSurface && inspectionId ? (
            <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
              <BoundingBoxCanvas
                imageUrl={getImageContentUrl(inspectionId, currentSurface.id)}
                regions={surfaceRegions}
                selectedRegionId={selectedRegionId}
                onSelectRegion={handleSelectRegion}
                onUpdateRegionBbox={handleUpdateRegionBbox}
                onCreateRegionBox={handleCreateRegionBox}
                isDrawingMode={isDrawingMode}
                setIsDrawingMode={setIsDrawingMode}
                showLabels={showLabels}
                setShowLabels={setShowLabels}
                showConfidence={showConfidence}
                setShowConfidence={setShowConfidence}
                hideRejected={hideRejected}
                setHideRejected={setHideRejected}
                surfaceName={currentSurface.surface_type}
              />
            </div>
          ) : (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No captured surface image available for this inspection.
            </div>
          )}

          {/* Region Editor Bottom Dock (visible if region selected or newly drawn) */}
          {(selectedRegion || pendingNewBox) && (
            <div
              style={{
                borderTop: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-surface-primary)',
                maxHeight: '260px',
                overflowY: 'auto',
              }}
            >
              <OCRRegionEditor
                selectedRegion={selectedRegion}
                pendingNewBox={pendingNewBox}
                onClose={() => {
                  setSelectedRegionId(null);
                  setPendingNewBox(null);
                }}
                onSaveCorrection={handleSaveCorrection}
                onRejectRegion={handleRejectRegion}
                onCreateRegion={handleCreateRegion}
              />
            </div>
          )}
        </div>

        {/* Right Column: Statutory Observations, Conflicts & Rule Engine Tabs */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'var(--bg-surface-primary)',
            overflow: 'hidden',
          }}
        >
          {/* Tabs navigation */}
          <div
            style={{
              display: 'flex',
              borderBottom: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--bg-surface-secondary)',
            }}
          >
            <button
              id="tab-btn-declarations"
              onClick={() => setActiveTab('declarations')}
              style={{
                flex: 1,
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                borderBottom: activeTab === 'declarations' ? '2px solid var(--primary-500)' : '2px solid transparent',
                backgroundColor: activeTab === 'declarations' ? 'var(--bg-surface-primary)' : 'transparent',
                color: activeTab === 'declarations' ? 'var(--text-main)' : 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              Declarations ({workspace?.total_observations || 0})
            </button>

            <button
              id="tab-btn-conflicts"
              onClick={() => setActiveTab('conflicts')}
              style={{
                flex: 1,
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                borderBottom: activeTab === 'conflicts' ? '2px solid var(--accent-amber)' : '2px solid transparent',
                backgroundColor: activeTab === 'conflicts' ? 'var(--bg-surface-primary)' : 'transparent',
                color: activeTab === 'conflicts' ? 'var(--text-main)' : 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              Conflicts
              {activeConflictsCount > 0 && (
                <span
                  style={{
                    fontSize: '10px',
                    padding: '1px 6px',
                    borderRadius: 'var(--radius-full)',
                    backgroundColor: 'var(--verdict-review)',
                    color: '#000',
                  }}
                >
                  {activeConflictsCount}
                </span>
              )}
            </button>

            <button
              id="tab-btn-reevaluation"
              onClick={() => setActiveTab('reevaluation')}
              style={{
                flex: 1,
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                borderBottom: activeTab === 'reevaluation' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                backgroundColor: activeTab === 'reevaluation' ? 'var(--bg-surface-primary)' : 'transparent',
                color: activeTab === 'reevaluation' ? 'var(--text-main)' : 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              Rule Re-Evaluation
            </button>
          </div>

          {/* Active Tab Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            {activeTab === 'declarations' && workspace && (
              <ObservationPanel
                observations={workspace.observations}
                onVerify={handleVerifyObservation}
                onCorrect={handleCorrectObservation}
                onReject={handleRejectObservation}
                onUpdateStatus={handleUpdateObsStatus}
                onOpenManualDialog={() => setIsManualModalOpen(true)}
              />
            )}

            {activeTab === 'conflicts' && workspace && (
              <ConflictResolutionPanel
                conflicts={workspace.conflicts}
                onSelectAuthoritative={handleSelectAuthoritative}
                onVerifySingle={handleVerifyObservation}
                onRejectSingle={handleRejectObservation}
              />
            )}

            {activeTab === 'reevaluation' && inspectionId && (
              <RuleReevaluationPanel
                inspectionId={inspectionId}
                onReevaluate={handleReevaluateRules}
                reevaluationResult={reevaluationResult}
                hasUncommittedAdjudications={Boolean(workspace?.adjudicated_regions_count)}
              />
            )}
          </div>
        </div>
      </div>

      {/* Manual Observation Modal Dialog */}
      {workspace && (
        <ManualObservationDialog
          isOpen={isManualModalOpen}
          onClose={() => setIsManualModalOpen(false)}
          onSubmit={handleCreateManualObservation}
          surfaces={workspace.surfaces}
          selectedSurfaceId={currentSurface?.id}
        />
      )}
    </div>
  );
};
