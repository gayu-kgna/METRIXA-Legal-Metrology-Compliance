import { request } from './client';
import { ImageUploadResponse, SurfaceType } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function uploadSurfaceImage(
  inspectionId: string,
  surfaceType: SurfaceType,
  file: File | Blob,
  filename?: string
): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append('file', file, filename || (file instanceof File ? file.name : 'capture.jpg'));

  return request<ImageUploadResponse>(
    `/inspections/${inspectionId}/surfaces/${surfaceType}/images`,
    {
      method: 'POST',
      body: formData,
    }
  );
}

export async function listSurfaceImages(
  inspectionId: string,
  surfaceType: SurfaceType
): Promise<ImageUploadResponse[]> {
  return request<ImageUploadResponse[]>(
    `/inspections/${inspectionId}/surfaces/${surfaceType}/images`
  );
}

export async function getImageMetadata(
  inspectionId: string,
  imageId: string
): Promise<ImageUploadResponse> {
  return request<ImageUploadResponse>(
    `/inspections/${inspectionId}/images/${imageId}`
  );
}

export function getImageContentUrl(inspectionId: string, imageId: string): string {
  const token = localStorage.getItem('metrixa_token');
  const base = `${API_BASE_URL}/inspections/${inspectionId}/images/${imageId}/content`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

export async function fetchImageBlob(inspectionId: string, imageId: string): Promise<Blob> {
  const token = localStorage.getItem('metrixa_token');
  const headers: HeadersInit = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}/inspections/${inspectionId}/images/${imageId}/content`, {
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to load image: ${res.statusText}`);
  }
  return res.blob();
}
