import type { Location, TripPlan, TripRequest } from './types';

function describeError(payload: unknown): string {
  if (typeof payload === 'string') return payload;
  if (Array.isArray(payload)) return payload.map(describeError).join(' ');
  if (payload && typeof payload === 'object') {
    return Object.entries(payload)
      .map(
        ([field, message]) =>
          `${field === 'error' || field === 'detail' ? '' : field.replaceAll('_', ' ') + ': '}${describeError(message)}`,
      )
      .join(' ');
  }
  return 'Something went wrong. Please try again.';
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 150_000);
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(describeError(payload));
    return payload as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw new Error(
        'The server took too long. Please retry; a free hosted server may need time to wake up.',
      );
    if (error instanceof TypeError || error instanceof SyntaxError)
      throw new Error('Could not reach the planning server. Check your connection and try again.');
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const findLocations = (query: string) =>
  request<{ results: Location[] }>(`/api/locations?q=${encodeURIComponent(query)}`);
export const createTripPlan = (trip: TripRequest) =>
  request<TripPlan>('/api/trips/plan', { method: 'POST', body: JSON.stringify(trip) });
