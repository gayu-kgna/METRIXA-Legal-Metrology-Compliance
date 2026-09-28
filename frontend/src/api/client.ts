import { ResponseEnvelope } from '../types/api';

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: any;

  constructor(message: string, status: number, code?: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('metrixa_token');
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Set default JSON Content-Type if body is not FormData
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${cleanEndpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      localStorage.removeItem('metrixa_token');
      localStorage.removeItem('metrixa_user');
      // Trigger navigation event or state update if in browser window
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.dispatchEvent(new CustomEvent('auth:expired'));
      }
      throw new ApiError('Session expired. Please log in again.', 401, 'UNAUTHORIZED');
    }

    // Handle file downloads (blob responses)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/pdf')) {
      if (!response.ok) {
        throw new ApiError(`Download failed with status ${response.status}`, response.status);
      }
      return (await response.blob()) as unknown as T;
    }

    const json = await response.json();

    if (!response.ok) {
      const errorMsg = json?.error?.message || json?.detail || `HTTP Error ${response.status}`;
      const errorCode = json?.error?.code || 'REQUEST_FAILED';
      const details = json?.error?.details || json?.detail;
      throw new ApiError(errorMsg, response.status, errorCode, details);
    }

    // If backend wrapped in ResponseEnvelope, return data
    if (json && typeof json === 'object' && 'success' in json) {
      const envelope = json as ResponseEnvelope<T>;
      if (!envelope.success) {
        throw new ApiError(envelope.message || 'Operation failed', response.status, envelope.error?.code);
      }
      if ('pagination' in json && (options as any)?.includePagination) {
        return json as T;
      }
      return (envelope.data !== undefined && envelope.data !== null ? envelope.data : envelope) as T;
    }

    return json as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(err?.message || 'Network connection error', 0, 'NETWORK_ERROR');
  }
}
