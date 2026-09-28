import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  Play, 
  Cpu, 
  Eye, 
  FileText, 
  Ruler, 
  Scale, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ArrowRight,
  RefreshCw,
  Layers
} from 'lucide-react';
import { getInspection } from '../api/inspections';
import { runImageOCR, getImageOCRHistory } from '../api/ocr';
import { runEntityParsing, getEntityParsingHistory } from '../api/entities';
import { analyzePDPGeometry, getPDPGeometryHistory } from '../api/geometry';
import { evaluateInspectionRules } from '../api/rules';
import { generateInspectionReport } from '../api/reports';
import { Inspection, SurfaceRead, OCRRunResponse, EntityRunResponse, PDPGeometryResponse } from '../types/api';
import { PipelineStepper, PipelineStage } from '../components/inspection/PipelineStepper';

export const ReviewPipelinePage: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId: string }>();
  const navigate = useNavigate();

  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active step & statuses
  const [currentStage, setCurrentStage] = useState<PipelineStage>('OCR');
  const [stageStatuses, setStageStatuses] = useState<Record<PipelineStage, 'idle' | 'running' | 'completed' | 'failed'>>({
    INGESTION: 'completed',
    OCR: 'idle',
    ENTITIES: 'idle',
    GEOMETRY: 'idle',
    RULES: 'idle',
    DOSSIER: 'idle',
  });

  // Pipeline execution log
  const [executionLogs, setExecutionLogs] = useState<string[]>([]);
  const [isExecutingAll, setIsExecutingAll] = useState<boolean>(false);

  // Execution Results
  const [ocrRuns, setOcrRuns] = useState<OCRRunResponse[]>([]);
  const [entityRuns, setEntityRuns] = useState<EntityRunResponse[]>([]);
  const [geometryRuns, setGeometryRuns] = useState<PDPGeometryResponse[]>([]);

  const addLog = (msg: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setExecutionLogs((prev) => [...prev, `[${timestamp}] ${msg}`]);
  };

  const loadData = useCallback(async () => {
    if (!inspectionId) return;
    try {
      setLoading(true);
      const data = await getInspection(inspectionId);
      setInspection(data);

      const surfaces = data.surfaces || [];
      if (surfaces.length === 0) {
        setStageStatuses((prev) => ({ ...prev, INGESTION: 'idle' }));
        addLog('Warning: No surface images ingested yet. Please capture surfaces first.');
      } else {
        setStageStatuses((prev) => ({ ...prev, INGESTION: 'completed' }));
        addLog(`Loaded inspection ${data.inspection_number} with ${surfaces.length} surface image(s).`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to initialize pipeline inspection');
      addLog(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [inspectionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Execute Step 2: OCR
  const handleExecuteOCR = async () => {
    if (!inspection || !inspection.surfaces || inspection.surfaces.length === 0) {
      addLog('Cannot execute OCR: No images captured.');
      return;
    }

    setStageStatuses((prev) => ({ ...prev, OCR: 'running' }));
    setCurrentStage('OCR');
    addLog('Starting Optical Character Recognition on captured surfaces...');

    try {
      const results: OCRRunResponse[] = [];
      for (const surface of inspection.surfaces) {
        addLog(`Running modular OCR on ${surface.surface_type} [SHA: ${surface.sha256_hash.substring(0, 8)}...]`);
        const ocrRes = await runImageOCR(inspection.id, surface.id, {
          provider: 'TESSERACT_OCR', // Real Tesseract OCR provider
          run_all_variants: true,
        });

        // 1. Check if OCR provider was unavailable
        if (ocrRes.status === 'PROVIDER_UNAVAILABLE') {
          addLog(`OCR provider unavailable on ${surface.surface_type} — configure Tesseract OCR.`);
          throw new Error(`OCR provider unavailable on ${surface.surface_type} — configure Tesseract OCR.`);
        }

        // 2. Check if OCR provider failed
        if (ocrRes.status === 'FAILED') {
          const errMsg = ocrRes.error_message || 'Recognition error';
          addLog(`OCR failed on ${surface.surface_type}: ${errMsg}`);
          throw new Error(`OCR failed on ${surface.surface_type}: ${errMsg}`);
        }

        // 3. Validate canonical contract and region count
        const count = ocrRes.region_count ?? ocrRes.total_regions ?? ocrRes.total_regions_detected ?? (Array.isArray(ocrRes.regions) ? ocrRes.regions.length : undefined);
        const isCountValid = typeof count === 'number' && Number.isInteger(count) && count >= 0;
        const hasRegions = Array.isArray(ocrRes.regions);
        const hasRunId = Boolean(ocrRes.ocr_run_id || ocrRes.id);

        if (ocrRes.status !== 'COMPLETED' || !isCountValid || !hasRegions || !hasRunId) {
          const countDisplay = typeof count === 'number' ? count : 'N/A';
          addLog(`OCR stage failed on ${surface.surface_type}: Invalid response contract (status: ${ocrRes.status || 'UNKNOWN'}, regions: ${countDisplay})`);
          throw new Error(`Invalid OCR response contract on ${surface.surface_type}`);
        }

        if (count !== ocrRes.regions.length) {
          addLog(`OCR stage failed on ${surface.surface_type}: region count mismatch (${count} reported vs ${ocrRes.regions.length} items)`);
          throw new Error(`OCR region count mismatch on ${surface.surface_type}`);
        }

        results.push(ocrRes);
        addLog(`Extracted ${count} bounding regions from ${surface.surface_type}`);
        if (ocrRes.regions && ocrRes.regions.length > 0) {
          const sampleText = ocrRes.regions
            .slice(0, 10)
            .map((r) => r.text || r.raw_text)
            .filter(Boolean)
            .join(' ');
          if (sampleText) {
            addLog(`[OCR Raw Text Sample] "${sampleText}${ocrRes.regions.length > 10 ? '...' : ''}"`);
          }
        }
      }

      setOcrRuns(results);
      setStageStatuses((prev) => ({ ...prev, OCR: 'completed' }));
      addLog('OCR Perception successfully completed across all package surfaces.');
      return results;
    } catch (err: any) {
      setStageStatuses((prev) => ({ ...prev, OCR: 'failed' }));
      addLog(`OCR Execution Failed: ${err.message}`);
      throw err;
    }
  };

  // Execute Step 3: Entity Parsing
  const handleExecuteEntities = async () => {
    if (!inspection || !inspection.surfaces || inspection.surfaces.length === 0) return;

    setStageStatuses((prev) => ({ ...prev, ENTITIES: 'running' }));
    setCurrentStage('ENTITIES');
    addLog('Executing semantic entity parsing and normalization...');

    try {
      const results: EntityRunResponse[] = [];
      for (const surface of inspection.surfaces) {
        addLog(`Parsing statutory declarations on ${surface.surface_type}...`);
        const matchedOcrRun = ocrRuns.find((r) => r.surface_id === surface.id);
        const ocrRunId = matchedOcrRun?.ocr_run_id || matchedOcrRun?.id;
        const entityRes = await runEntityParsing(inspection.id, surface.id, ocrRunId);
        results.push(entityRes);
        const entityCount = entityRes.entity_count ?? entityRes.observations?.length ?? 0;
        addLog(`Identified ${entityCount} statutory observations on ${surface.surface_type}`);
        if (entityRes.observations && entityRes.observations.length > 0) {
          for (const obs of entityRes.observations) {
            // Determine canonical entity type label
            let fieldType = obs.field_type || obs.field_name || 'UNKNOWN';
            if (obs.normalized_value?.entity_type) {
              fieldType = obs.normalized_value.entity_type; // e.g. "MARKETED_BY"
            } else if (fieldType === 'BRAND_NAME') {
              fieldType = 'BRAND';
            }

            // Determine human-readable extracted/raw value
            let displayVal = obs.raw_value || obs.raw_text_extracted || '';
            if (obs.normalized_value?.entity_type === 'MARKETED_BY' && obs.normalized_value?.name) {
              displayVal = obs.normalized_value.name;
            } else if (fieldType === 'BRAND' && obs.normalized_value?.brand_name) {
              displayVal = obs.normalized_value.brand_name;
            } else if (fieldType === 'GENERIC_NAME' && obs.normalized_value?.generic_name) {
              displayVal = obs.normalized_value.generic_name;
            } else if (!displayVal && obs.normalized_value) {
              displayVal = typeof obs.normalized_value === 'string'
                ? obs.normalized_value
                : (obs.normalized_value.name || obs.normalized_value.value || obs.normalized_value.formatted || '');
            }

            // Format confidence accurately: show actual percentage or 'N/A' if null/undefined
            const conf = obs.confidence ?? obs.confidence_score;
            const confStr = (conf !== undefined && conf !== null)
              ? `${Math.round(conf * 100)}%`
              : 'N/A';

            addLog(`  • [${fieldType}] "${displayVal}" (Confidence: ${confStr})`);
          }
        }
      }

      setEntityRuns(results);
      setStageStatuses((prev) => ({ ...prev, ENTITIES: 'completed' }));
      addLog('Entity parsing and value normalization completed.');
      return results;
    } catch (err: any) {
      setStageStatuses((prev) => ({ ...prev, ENTITIES: 'failed' }));
      addLog(`Entity Parsing Failed: ${err.message}`);
      throw err;
    }
  };

  // Execute Step 4: PDP Geometry
  const handleExecuteGeometry = async () => {
    if (!inspection || !inspection.surfaces || inspection.surfaces.length === 0) return;

    setStageStatuses((prev) => ({ ...prev, GEOMETRY: 'running' }));
    setCurrentStage('GEOMETRY');
    addLog('Analyzing Principal Display Panel geometry and font height...');

    try {
      const results: PDPGeometryResponse[] = [];
      for (const surface of inspection.surfaces) {
        const geomRes = await analyzePDPGeometry(inspection.id, surface.id);
        results.push(geomRes);
        const isFrontPdp = surface.surface_type === 'FRONT_PDP' || geomRes.is_pdp_candidate;
        if (isFrontPdp) {
          const areaPx = geomRes.pdp_area_px2 ?? geomRes.pdp_pixel_area ?? 0;
          const calibStatus = geomRes.has_calibration || geomRes.is_calibrated ? 'CALIBRATED' : 'UNCALIBRATED';
          const physArea = geomRes.estimated_physical_area_sq_cm ? `${geomRes.estimated_physical_area_sq_cm} cm²` : 'N/A';
          addLog(`FRONT_PDP → ${areaPx}px² (Pixel Geometry) | Calibration: ${calibStatus} | Physical Area: ${physArea}`);
        } else {
          addLog(`${surface.surface_type} → NON-PDP (Display Panel Analysis: NOT_APPLICABLE)`);
        }
      }

      setGeometryRuns(results);
      setStageStatuses((prev) => ({ ...prev, GEOMETRY: 'completed' }));
      addLog('PDP geometry and declaration placement analysis completed.');
      return results;
    } catch (err: any) {
      setStageStatuses((prev) => ({ ...prev, GEOMETRY: 'failed' }));
      addLog(`Geometry Analysis Failed: ${err.message}`);
      throw err;
    }
  };

  // Execute Step 5: Rule Engine
  const handleExecuteRules = async () => {
    if (!inspection) return;

    setStageStatuses((prev) => ({ ...prev, RULES: 'running' }));
    setCurrentStage('RULES');
    addLog('Invoking backend deterministic Legal Metrology rule engine...');

    try {
      const summary = await evaluateInspectionRules(inspection.id, {
        include_test_rules: false,
      });

      setStageStatuses((prev) => ({ ...prev, RULES: 'completed' }));
      const pass = summary.pass_count ?? 0;
      const fail = summary.fail_count ?? 0;
      const review = summary.review_count ?? 0;
      const indet = summary.indeterminate_count ?? 0;
      const na = summary.not_applicable_count ?? 0;
      addLog(`Statutory Evaluation Complete: ${pass} PASS, ${fail} FAIL, ${review} REVIEW, ${indet} INDETERMINATE, ${na} NOT_APPLICABLE.`);
      const canonicalVerdict = summary.overall_verdict || (
        fail > 0 ? 'NON_COMPLIANT' :
        review > 0 ? 'REVIEW_REQUIRED' :
        indet > 0 ? 'INDETERMINATE' :
        'COMPLIANT'
      );
      addLog(`Overall Statutory Verdict: ${canonicalVerdict}`);
      return summary;
    } catch (err: any) {
      setStageStatuses((prev) => ({ ...prev, RULES: 'failed' }));
      addLog(`Rule Engine Evaluation Failed: ${err.message}`);
      throw err;
    }
  };

  // Execute Step 6: Dossier Generation
  const handleExecuteDossier = async () => {
    if (!inspection) return;

    setStageStatuses((prev) => ({ ...prev, DOSSIER: 'running' }));
    setCurrentStage('DOSSIER');
    addLog('Assembling immutable evidence snapshot and compiling PDF dossier...');

    try {
      const report = await generateInspectionReport(inspection.id, {
        report_type: 'FULL_INSPECTION_DOSSIER',
      });

      setStageStatuses((prev) => ({ ...prev, DOSSIER: 'completed' }));
      const filename = report.pdf_filename || (report.storage_path ? report.storage_path.split('/').pop() : `dossier_v${report.report_version || 1}.pdf`);
      addLog(`Dossier Generated: ${filename} [Version ${report.report_version || 1}]`);
      addLog(`Dossier ID: ${report.id} | Size: ${report.file_size_bytes ?? 0} bytes`);
      addLog(`Cryptographic SHA-256 Digest: ${report.sha256_hash ? report.sha256_hash.substring(0, 16) + '...' : 'N/A'}`);
      return report;
    } catch (err: any) {
      setStageStatuses((prev) => ({ ...prev, DOSSIER: 'failed' }));
      addLog(`Dossier Generation Failed: ${err.message}`);
      throw err;
    }
  };

  // Execute All Steps Sequentially
  const handleExecuteAll = async () => {
    setIsExecutingAll(true);
    addLog('==================================================');
    addLog('STARTING AUTOMATED END-TO-END INSPECTION PIPELINE');
    addLog('==================================================');

    try {
      await handleExecuteOCR();
      await handleExecuteEntities();
      await handleExecuteGeometry();
      await handleExecuteRules();
      await handleExecuteDossier();
      addLog('Inspection pipeline completed successfully! Ready for compliance review.');
    } catch (err: any) {
      addLog(`❌ Pipeline execution HALTED due to error: ${err?.message || err}`);
      addLog('Downstream stages aborted to prevent execution with partial or stale data. Fix the root cause and retry the failed stage.');
    } finally {
      setIsExecutingAll(false);
    }
  };

  if (loading && !inspection) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 60 }}>
        <Clock size={32} className="animate-spin" style={{ margin: '0 auto 16px', color: 'var(--accent-cyan)' }} />
        <div>Loading inspection pipeline...</div>
      </div>
    );
  }

  const hasFailedStage = Object.values(stageStatuses).some((st) => st === 'failed');

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', marginBottom: 4 }}>
            Inspection Processing Pipeline
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Orchestrates OCR perception, entity extraction, geometry analysis, statutory rules, and dossier generation
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={handleExecuteAll}
            className="btn btn-cyan btn-lg"
            disabled={isExecutingAll || !inspection?.surfaces?.length}
            style={{ gap: 8 }}
          >
            {isExecutingAll ? (
              <>
                <Clock size={16} className="animate-spin" />
                <span>Running Pipeline...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Run Complete Pipeline</span>
              </>
            )}
          </button>

          <Link to={`/inspections/${inspection?.id}/results`} className="btn btn-primary btn-lg" style={{ gap: 6 }}>
            <span>View Results</span>
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      {/* Failure Alert Banner */}
      {hasFailedStage && (
        <div style={{
          backgroundColor: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 18px',
          marginBottom: 24,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
          color: '#FCA5A5',
          fontSize: '0.88rem',
          lineHeight: 1.5,
        }}>
          <AlertCircle size={20} color="#F87171" style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <strong style={{ color: '#F87171', display: 'block', marginBottom: 2 }}>
              Pipeline Execution Halted Due to Stage Failure
            </strong>
            A required inspection pipeline stage encountered an error. Downstream stages have been blocked to prevent evaluating stale or partial observations. Please review the telemetry log below, resolve the root cause, and retry the failed stage.
          </div>
        </div>
      )}

      {/* Visual Pipeline Stepper */}
      <PipelineStepper
        currentStage={currentStage}
        stageStatuses={stageStatuses}
        onSelectStage={(st) => setCurrentStage(st)}
      />

      {/* Main Grid: Control Stage Cards & Console Log */}
      <div className="grid-2" style={{ gap: 24 }}>
        {/* Stage Execution Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Step 2: OCR */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Eye size={17} color="var(--accent-cyan)" />
                  <span>Step 2: Modular OCR Perception</span>
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Generates preprocessed variants and extracts text bounding boxes in [0, 1] space.
                </p>
              </div>
              <button
                onClick={handleExecuteOCR}
                className="btn btn-secondary btn-sm"
                disabled={stageStatuses.OCR === 'running' || !inspection?.surfaces?.length}
              >
                {stageStatuses.OCR === 'completed' ? 'Re-Run OCR' : 'Run OCR'}
              </button>
            </div>
          </div>

          {/* Step 3: Entity Parsing */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileText size={17} color="var(--primary-500)" />
                  <span>Step 3: Semantic Entity Parsing</span>
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Normalizes mandatory Legal Metrology declarations (MRP, net quantity, manufacturer, dates).
                </p>
              </div>
              <button
                onClick={handleExecuteEntities}
                className="btn btn-secondary btn-sm"
                disabled={stageStatuses.ENTITIES === 'running' || !inspection?.surfaces?.length || stageStatuses.OCR !== 'completed'}
                title={stageStatuses.OCR !== 'completed' ? 'Requires Step 2 (OCR) to complete first' : ''}
              >
                {stageStatuses.ENTITIES === 'completed' ? 'Re-Parse' : 'Parse Entities'}
              </button>
            </div>
          </div>

          {/* Step 4: Geometry */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Ruler size={17} color="var(--accent-amber)" />
                  <span>Step 4: PDP Geometry & Font Height</span>
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Calculates PDP surface area, text height ratio, and declaration spatial placement.
                </p>
              </div>
              <button
                onClick={handleExecuteGeometry}
                className="btn btn-secondary btn-sm"
                disabled={stageStatuses.GEOMETRY === 'running' || !inspection?.surfaces?.length || stageStatuses.OCR !== 'completed'}
                title={stageStatuses.OCR !== 'completed' ? 'Requires Step 2 (OCR) to complete first' : ''}
              >
                {stageStatuses.GEOMETRY === 'completed' ? 'Re-Analyze' : 'Analyze Geometry'}
              </button>
            </div>
          </div>

          {/* Step 5: Rules */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Scale size={17} color="var(--verdict-pass)" />
                  <span>Step 5: Deterministic Legal Rules</span>
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Evaluates versioned statutory rules deterministically (backend authority only).
                </p>
              </div>
              <button
                onClick={handleExecuteRules}
                className="btn btn-secondary btn-sm"
                disabled={stageStatuses.RULES === 'running' || stageStatuses.ENTITIES !== 'completed'}
                title={stageStatuses.ENTITIES !== 'completed' ? 'Requires Step 3 (Entities) to complete first' : ''}
              >
                {stageStatuses.RULES === 'completed' ? 'Re-Evaluate' : 'Evaluate Rules'}
              </button>
            </div>
          </div>

          {/* Step 6: Dossier */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircle2 size={17} color="var(--verdict-pass)" />
                  <span>Step 6: PDF Inspection Dossier</span>
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  Freezes immutable Evidence Snapshot and compiles explainable Report PDF.
                </p>
              </div>
              <button
                onClick={handleExecuteDossier}
                className="btn btn-secondary btn-sm"
                disabled={stageStatuses.DOSSIER === 'running' || stageStatuses.RULES !== 'completed'}
                title={stageStatuses.RULES !== 'completed' ? 'Requires Step 5 (Rules) to complete first' : ''}
              >
                {stageStatuses.DOSSIER === 'completed' ? 'Generate New Version' : 'Compile Dossier'}
              </button>
            </div>
          </div>
        </div>

        {/* Live Execution Console Log */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div className="card-header" style={{ marginBottom: 12 }}>
            <div className="card-title" style={{ fontSize: '0.95rem' }}>
              <Cpu size={16} color="var(--accent-cyan)" />
              <span>Inspection Engine Telemetry Log</span>
            </div>
            <button
              onClick={() => setExecutionLogs([])}
              className="btn btn-outline btn-sm"
              style={{ fontSize: '0.75rem' }}
            >
              Clear Log
            </button>
          </div>

          <div style={{
            flex: 1,
            minHeight: 380,
            maxHeight: 480,
            backgroundColor: '#070A12',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: 14,
            overflowY: 'auto',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
            color: '#E2E8F0',
            lineHeight: 1.6,
          }}>
            {executionLogs.length === 0 ? (
              <div style={{ color: 'var(--text-muted)' }}>
                System initialized. Waiting for pipeline execution triggers...
              </div>
            ) : (
              executionLogs.map((log, idx) => (
                <div
                  key={idx}
                  style={{
                    color: log.includes('Error') || log.includes('Failed')
                      ? '#F87171'
                      : log.includes('PASS') || log.includes('successfully') || log.includes('Complete')
                      ? '#34D399'
                      : log.includes('Warning')
                      ? '#FBBF24'
                      : '#E2E8F0',
                  }}
                >
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
