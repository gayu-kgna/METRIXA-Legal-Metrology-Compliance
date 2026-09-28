import { request } from './client';
import { 
  Inspection, 
  CreateInspectionPayload, 
  InspectionOverallStatus 
} from '../types/api';

export async function listInspections(statusFilter?: InspectionOverallStatus, retailer?: string): Promise<Inspection[]> {
  const params = new URLSearchParams();
  if (statusFilter) params.set('status', statusFilter);
  if (retailer) params.set('retailer', retailer);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request<Inspection[]>(`/inspections${qs}`);
}

export async function getInspection(id: string): Promise<Inspection> {
  return request<Inspection>(`/inspections/${id}`);
}

export async function createInspection(payload: CreateInspectionPayload): Promise<Inspection> {
  return request<Inspection>('/inspections', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateInspection(
  id: string, 
  updates: { overall_status?: InspectionOverallStatus; notes?: string }
): Promise<Inspection> {
  return request<Inspection>(`/inspections/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}
