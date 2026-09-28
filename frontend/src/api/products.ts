import { request } from './client';
import {
  ProductLedgerItem,
  ProductDetail,
  LabelVersionDetail,
  LabelDiffResponse,
  TimelineEvent,
  ProductInspectionItem,
} from '../types/api';

export interface ListProductsParams {
  q?: string;
  category?: string;
  manufacturer?: string;
  gtin?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PaginatedProductLedger {
  data: ProductLedgerItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export async function listProducts(params: ListProductsParams = {}): Promise<PaginatedProductLedger> {
  const qp = new URLSearchParams();
  if (params.q) qp.set('q', params.q);
  if (params.category) qp.set('category', params.category);
  if (params.manufacturer) qp.set('manufacturer', params.manufacturer);
  if (params.gtin) qp.set('gtin', params.gtin);
  if (params.page) qp.set('page', params.page.toString());
  if (params.page_size) qp.set('page_size', params.page_size.toString());
  if (params.sort_by) qp.set('sort_by', params.sort_by);
  if (params.sort_order) qp.set('sort_order', params.sort_order);

  const qs = qp.toString() ? `?${qp.toString()}` : '';
  return request<PaginatedProductLedger>(`/products${qs}`, {
    includePagination: true,
  } as any);
}

export async function getProduct(productId: string): Promise<ProductDetail> {
  return request<ProductDetail>(`/products/${productId}`);
}

export interface ListProductInspectionsParams {
  status_filter?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedProductInspections {
  data: ProductInspectionItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export async function getProductInspections(
  productId: string,
  params: ListProductInspectionsParams = {}
): Promise<PaginatedProductInspections> {
  const qp = new URLSearchParams();
  if (params.status_filter) qp.set('status_filter', params.status_filter);
  if (params.from_date) qp.set('from_date', params.from_date);
  if (params.to_date) qp.set('to_date', params.to_date);
  if (params.page) qp.set('page', params.page.toString());
  if (params.page_size) qp.set('page_size', params.page_size.toString());

  const qs = qp.toString() ? `?${qp.toString()}` : '';
  return request<PaginatedProductInspections>(`/products/${productId}/inspections${qs}`, {
    includePagination: true,
  } as any);
}

export async function getProductLabelVersions(productId: string): Promise<LabelVersionDetail[]> {
  return request<LabelVersionDetail[]>(`/products/${productId}/label-versions`);
}

export async function getProductTimeline(productId: string): Promise<TimelineEvent[]> {
  return request<TimelineEvent[]>(`/products/${productId}/timeline`);
}

export async function getLabelVersionChanges(
  productId: string,
  fromVersionId: string,
  toVersionId: string
): Promise<LabelDiffResponse> {
  const qp = new URLSearchParams({
    from_version_id: fromVersionId,
    to_version_id: toVersionId,
  });
  return request<LabelDiffResponse>(`/products/${productId}/changes?${qp.toString()}`);
}
