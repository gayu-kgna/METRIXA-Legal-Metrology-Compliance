import { request } from './client';
import { EntityRunResponse, EntityRunListResponse } from '../types/api';

export async function runEntityParsing(
  inspectionId: string,
  imageId: string,
  ocrRunId?: string
): Promise<EntityRunResponse> {
  return request<EntityRunResponse>(
    `/inspections/${inspectionId}/images/${imageId}/entities`,
    {
      method: 'POST',
      body: ocrRunId ? JSON.stringify({ ocr_run_id: ocrRunId }) : undefined,
    }
  );
}

export async function getEntityParsingHistory(
  inspectionId: string,
  imageId: string
): Promise<EntityRunListResponse> {
  return request<EntityRunListResponse>(
    `/inspections/${inspectionId}/images/${imageId}/entities`
  );
}
