import { request } from './client';
import { OCRRunResponse, OCRRunListResponse } from '../types/api';

export async function runImageOCR(
  inspectionId: string,
  imageId: string,
  options?: {
    provider?: string;
    provider_name?: string;
    preprocessing_variant?: string;
    run_all_variants?: boolean;
  }
): Promise<OCRRunResponse> {
  const payload = options
    ? {
        ...options,
        provider_name: options.provider_name || options.provider,
      }
    : undefined;

  return request<OCRRunResponse>(
    `/inspections/${inspectionId}/images/${imageId}/ocr`,
    {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    }
  );
}

export async function getImageOCRHistory(
  inspectionId: string,
  imageId: string
): Promise<OCRRunListResponse> {
  return request<OCRRunListResponse>(
    `/inspections/${inspectionId}/images/${imageId}/ocr`
  );
}
