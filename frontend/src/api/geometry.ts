import { request } from './client';
import { PDPGeometryResponse, PDPGeometryListResponse } from '../types/api';

export interface CalibrationParams {
  scale_px_per_mm?: number;
  reference_dimension_mm?: number;
  reference_dimension_px?: number;
  calibration_source?: string;
}

export async function analyzePDPGeometry(
  inspectionId: string,
  imageId: string,
  params?: CalibrationParams
): Promise<PDPGeometryResponse> {
  return request<PDPGeometryResponse>(
    `/inspections/${inspectionId}/images/${imageId}/geometry`,
    {
      method: 'POST',
      body: params ? JSON.stringify(params) : undefined,
    }
  );
}

export async function getPDPGeometryHistory(
  inspectionId: string,
  imageId: string
): Promise<PDPGeometryListResponse> {
  return request<PDPGeometryListResponse>(
    `/inspections/${inspectionId}/images/${imageId}/geometry`
  );
}
