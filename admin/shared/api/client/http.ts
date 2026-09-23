import { API_BASE_URL } from '@/shared/config';

import { emitUnauthorized } from './authEvents';
import { ApiError } from './errors';
import { getAuthToken } from './token';

type QueryValue = string | number | boolean | undefined | null;

interface RequestOptions {
  query?: Record<string, QueryValue>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(path.replace(/^\//, ''), `${window.location.origin}${API_BASE_URL}/`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
    }
  }
  return url.href;
}

async function extractErrorMessage(response: Response): Promise<{ message: string; detail: unknown }> {
  try {
    const body = (await response.clone().json()) as { detail?: unknown; message?: unknown };
    const message =
      (typeof body.detail === 'string' && body.detail) ||
      (typeof body.message === 'string' && body.message) ||
      response.statusText;
    return { message, detail: body };
  } catch {
    return { message: response.statusText || `HTTP ${response.status}`, detail: undefined };
  }
}

async function request<T>(method: string, path: string, body?: unknown, options?: RequestOptions): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const isFormData = body instanceof FormData;
  if (body !== undefined && !isFormData) headers['Content-Type'] = 'application/json';

  const response = await fetch(buildUrl(path, options?.query), {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
    signal: options?.signal,
  });

  if (response.status === 401) emitUnauthorized();

  if (!response.ok) {
    const { message, detail } = await extractErrorMessage(response);
    throw new ApiError(response.status, message, detail);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const http = {
  get: <T>(path: string, options?: RequestOptions) => request<T>('GET', path, undefined, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>('POST', path, body, options),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>('PATCH', path, body, options),
  delete: <T>(path: string, options?: RequestOptions) => request<T>('DELETE', path, undefined, options),
};
