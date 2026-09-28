import { request } from './client';
import { EvidenceBundleResponse, EvidenceSnapshotRead } from '../types/api';

export async function getInspectionEvidenceBundle(
  inspectionId: string,
  snapshotId?: string,
  evaluationRunId?: string
): Promise<EvidenceBundleResponse> {
  const params = new URLSearchParams();
  if (snapshotId) params.set('snapshot_id', snapshotId);
  if (evaluationRunId) params.set('evaluation_run_id', evaluationRunId);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request<EvidenceBundleResponse>(
    `/inspections/${inspectionId}/evidence${qs}`
  );
}

export async function getEvidenceSnapshot(
  inspectionId: string,
  snapshotId: string
): Promise<EvidenceSnapshotRead> {
  return request<EvidenceSnapshotRead>(
    `/inspections/${inspectionId}/evidence/${snapshotId}`
  );
}
