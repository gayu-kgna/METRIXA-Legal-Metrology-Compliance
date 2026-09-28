import { request } from './client';
import {
  AnalyticsOverview,
  TrendDataPoint,
  OutcomeDistribution,
  CategoryDistributionItem,
  LocationDistributionItem,
  AdjudicationActivityItem,
} from '../types/api';

export async function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  return request<AnalyticsOverview>('/analytics/overview');
}

export async function getInspectionsTrend(days: number = 30): Promise<TrendDataPoint[]> {
  return request<TrendDataPoint[]>(`/analytics/inspections?days=${days}`);
}

export async function getOutcomesBreakdown(): Promise<OutcomeDistribution> {
  return request<OutcomeDistribution>('/analytics/outcomes');
}

export async function getCategoriesBreakdown(): Promise<CategoryDistributionItem[]> {
  return request<CategoryDistributionItem[]>('/analytics/categories');
}

export async function getLocationsBreakdown(): Promise<LocationDistributionItem[]> {
  return request<LocationDistributionItem[]>('/analytics/locations');
}

export async function getAdjudicationActivity(): Promise<AdjudicationActivityItem[]> {
  return request<AdjudicationActivityItem[]>('/analytics/adjudications');
}
