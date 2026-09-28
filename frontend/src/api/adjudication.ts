import { request } from './client';
import {
  AdjudicationWorkspaceState,
  AdjudicatedOCRRegion,
  OCRRegionCreateRequest,
  OCRRegionPatchRequest,
  AdjudicatedObservation,
  ManualObservationCreateRequest,
  ObservationCorrectRequest,
  ObservationStatus,
  OCRAdjudication,
  RuleReevaluationResponse,
} from '../types/api';

/**
 * Fetch full workspace state for the adjudication console.
 */
export async function getWorkspaceState(inspectionId: string): Promise<AdjudicationWorkspaceState> {
  return request<AdjudicationWorkspaceState>(`/inspections/${inspectionId}/adjudication`);
}

/**
 * Fetch OCR regions with active adjudications for a specific surface image.
 */
export async function getOCRRegionsForImage(
  inspectionId: string,
  imageId: string
): Promise<AdjudicatedOCRRegion[]> {
  return request<AdjudicatedOCRRegion[]>(`/inspections/${inspectionId}/images/${imageId}/ocr-regions`);
}

/**
 * Create a new officer-drawn bounding box region.
 */
export async function createOCRRegion(
  inspectionId: string,
  data: OCRRegionCreateRequest
): Promise<AdjudicatedOCRRegion> {
  return request<AdjudicatedOCRRegion>(`/inspections/${inspectionId}/ocr-regions`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Patch an existing OCR region with text or bounding box correction.
 */
export async function patchOCRRegion(
  inspectionId: string,
  regionId: string,
  data: OCRRegionPatchRequest
): Promise<AdjudicatedOCRRegion> {
  return request<AdjudicatedOCRRegion>(`/inspections/${inspectionId}/ocr-regions/${regionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Mark an OCR region as rejected (noise / hallucination).
 */
export async function rejectOCRRegion(
  inspectionId: string,
  regionId: string,
  reason?: string
): Promise<AdjudicatedOCRRegion> {
  return request<AdjudicatedOCRRegion>(`/inspections/${inspectionId}/ocr-regions/${regionId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

/**
 * Get all latest observations for an inspection.
 */
export async function getObservations(inspectionId: string): Promise<AdjudicatedObservation[]> {
  return request<AdjudicatedObservation[]>(`/inspections/${inspectionId}/observations`);
}

/**
 * Create a manual statutory observation directly by officer input.
 */
export async function createManualObservation(
  inspectionId: string,
  data: ManualObservationCreateRequest
): Promise<AdjudicatedObservation> {
  return request<AdjudicatedObservation>(`/inspections/${inspectionId}/observations/manual`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Verify an observation as legally accurate.
 */
export async function verifyObservation(
  inspectionId: string,
  observationId: string,
  notes?: string
): Promise<AdjudicatedObservation> {
  return request<AdjudicatedObservation>(`/inspections/${inspectionId}/observations/${observationId}/verify`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

/**
 * Correct an observation value with revision tracking.
 */
export async function correctObservation(
  inspectionId: string,
  observationId: string,
  data: ObservationCorrectRequest
): Promise<AdjudicatedObservation> {
  return request<AdjudicatedObservation>(`/inspections/${inspectionId}/observations/${observationId}/correct`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Mark an observation as rejected.
 */
export async function rejectObservation(
  inspectionId: string,
  observationId: string,
  reason?: string
): Promise<AdjudicatedObservation> {
  return request<AdjudicatedObservation>(`/inspections/${inspectionId}/observations/${observationId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

/**
 * Update an observation's status (e.g. UNCERTAIN, OBSERVED).
 */
export async function updateObservationStatus(
  inspectionId: string,
  observationId: string,
  status: ObservationStatus,
  notes?: string
): Promise<AdjudicatedObservation> {
  return request<AdjudicatedObservation>(`/inspections/${inspectionId}/observations/${observationId}/status`, {
    method: 'POST',
    body: JSON.stringify({ status, notes }),
  });
}

/**
 * Get the immutable audit history of all adjudications for an inspection.
 */
export async function getAdjudicationsHistory(inspectionId: string): Promise<OCRAdjudication[]> {
  return request<OCRAdjudication[]>(`/inspections/${inspectionId}/adjudications`);
}

/**
 * Re-evaluate deterministic compliance rules based on updated observations.
 */
export async function reevaluateRules(
  inspectionId: string,
  justification?: string
): Promise<RuleReevaluationResponse> {
  return request<RuleReevaluationResponse>(`/inspections/${inspectionId}/rules/re-evaluate`, {
    method: 'POST',
    body: JSON.stringify({ justification }),
  });
}
