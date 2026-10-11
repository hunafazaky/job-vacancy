import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface ExtractionFields {
	job_title: string | null;
	company: string | null;
	description: string | null;
	skills_required: string[] | null;
	location: string | null;
	employment_type: string | null;
	salary_range: string | null;
}

export interface ExtractionResponse extends ExtractionFields {
	id: string | null;
	saved: boolean;
	image_url: string | null;
	llm_provider: string;
	created_at: string | null;
}

export interface RateLimitStatus {
	limit: number;
	used: number;
	remaining: number;
}

class ApiError extends Error {
	status: number;
	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

function authHeaders(): HeadersInit {
	const { accessToken } = get(auth);
	return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

// Only one refresh should ever be in flight at a time — if several requests
// 401 at once, they all await the same refresh call instead of each firing
// their own POST /auth/refresh.
let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
	const { refreshToken } = get(auth);
	if (!refreshToken) return null;

	if (!refreshInFlight) {
		refreshInFlight = (async () => {
			try {
				const res = await fetch(`${API_BASE}/auth/refresh`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ refresh_token: refreshToken })
				});
				if (!res.ok) {
					auth.logout();
					return null;
				}
				const data = await res.json();
				auth.login(data.access_token, data.refresh_token);
				return data.access_token as string;
			} catch {
				auth.logout();
				return null;
			} finally {
				refreshInFlight = null;
			}
		})();
	}
	return refreshInFlight;
}

async function handle<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		throw new ApiError(res.status, body.detail ?? `Request failed (${res.status})`);
	}
	if (res.status === 204) return undefined as T;
	return res.json();
}

/**
 * Fetch wrapper for authenticated requests. On a 401, transparently
 * refreshes the access token once and retries the original request. If
 * refresh fails (no refresh token, or it's expired/invalid), the user is
 * logged out and the original 401 is surfaced to the caller.
 */
async function authorizedFetch(url: string, init: RequestInit = {}): Promise<Response> {
	const firstAttempt = await fetch(url, {
		...init,
		headers: { ...init.headers, ...authHeaders() }
	});

	if (firstAttempt.status !== 401) return firstAttempt;

	const newAccessToken = await refreshAccessToken();
	if (!newAccessToken) return firstAttempt; // no valid refresh token — surface the original 401

	return fetch(url, {
		...init,
		headers: { ...init.headers, Authorization: `Bearer ${newAccessToken}` }
	});
}

export async function signup(email: string, password: string) {
	const res = await fetch(`${API_BASE}/auth/signup`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password })
	});
	return handle<{ access_token: string; refresh_token: string }>(res);
}

export async function login(email: string, password: string) {
	const res = await fetch(`${API_BASE}/auth/login`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password })
	});
	return handle<{ access_token: string; refresh_token: string }>(res);
}

export async function extractJobImage(file: File): Promise<ExtractionResponse> {
	const formData = new FormData();
	formData.append('file', file);

	// Not every caller is signed in, so a 401 here just means "no/expired
	// token" rather than an error — authorizedFetch still handles the
	// refresh-and-retry transparently when a refresh token is available.
	const res = await authorizedFetch(`${API_BASE}/extract`, {
		method: 'POST',
		body: formData // no Content-Type — browser sets multipart boundary
	});
	return handle<ExtractionResponse>(res);
}

export async function getRateLimitStatus(): Promise<RateLimitStatus> {
	const res = await authorizedFetch(`${API_BASE}/rate-limit-status`);
	return handle<RateLimitStatus>(res);
}

export async function getHistory() {
	const res = await authorizedFetch(`${API_BASE}/history`);
	return handle<ExtractionResponse[]>(res);
}

export async function deleteExtraction(id: string) {
	const res = await authorizedFetch(`${API_BASE}/history/${id}`, { method: 'DELETE' });
	return handle<void>(res);
}

export { ApiError };
