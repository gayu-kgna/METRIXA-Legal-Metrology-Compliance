import { request } from './client';
import { ReportRead } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function generateInspectionReport(
  inspectionId: string,
  payload?: {
    report_type?: string;
    evidence_snapshot_id?: string;
    evaluation_run_id?: string;
  }
): Promise<ReportRead> {
  return request<ReportRead>(
    `/inspections/${inspectionId}/reports`,
    {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    }
  );
}

export async function listInspectionReports(
  inspectionId: string
): Promise<ReportRead[]> {
  return request<ReportRead[]>(
    `/inspections/${inspectionId}/reports`
  );
}

export async function getInspectionReport(
  inspectionId: string,
  reportId: string
): Promise<ReportRead> {
  return request<ReportRead>(
    `/inspections/${inspectionId}/reports/${reportId}`
  );
}

export async function downloadReportPdfBlob(
  inspectionId: string,
  reportId: string
): Promise<Blob> {
  return request<Blob>(
    `/inspections/${inspectionId}/reports/${reportId}/content`
  );
}

export function getReportPdfUrl(inspectionId: string, reportId: string): string {
  const token = localStorage.getItem('metrixa_token');
  const base = `${API_BASE_URL}/inspections/${inspectionId}/reports/${reportId}/content`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}
