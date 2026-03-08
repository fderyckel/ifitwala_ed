// ifitwala_ed/ui-spa/src/lib/frappe.ts

import { setConfig, frappeRequest } from 'frappe-ui'

const AUTH_ERROR_PATTERNS = [
	'you need to sign in',
	'you must be logged in',
	'user none not found',
	'session expired',
]

async function resolveCsrfToken(): Promise<string> {
	if (typeof window !== 'undefined' && (window as any)?.csrf_token) {
		return (window as any).csrf_token as string
	}

	if (typeof document !== 'undefined') {
		const meta = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null
		if (meta?.content) {
			if (typeof window !== 'undefined') {
				;(window as any).csrf_token = meta.content
			}
			return meta.content
		}
	}

	return ''
}

function extractErrorStatus(error: unknown): number | null {
	if (!error || typeof error !== 'object') return null
	const status = (error as any)?.response?.status ?? (error as any)?.status
	return typeof status === 'number' ? status : null
}

function extractErrorMessage(error: unknown): string {
	if (!error || typeof error !== 'object') {
		return String(error || '')
	}
	const rawMessage =
		(error as any)?.response?._server_messages ||
		(error as any)?.response?.message ||
		(error as any)?.message ||
		(error as any)?.response?.statusText ||
		''
	if (typeof rawMessage === 'string') return rawMessage
	return String(rawMessage || '')
}

function isSessionFailureMessage(message: string): boolean {
	const normalized = (message || '').toLowerCase()
	return AUTH_ERROR_PATTERNS.some((pattern) => normalized.includes(pattern))
}

function redirectToLoginIfNeeded() {
	if (typeof window === 'undefined') return
	if (window.location.pathname.startsWith('/login')) return
	const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
	const loginPath = `/login?redirect-to=${encodeURIComponent(currentPath)}`
	window.location.assign(loginPath)
}

/**
 * Transport Contract (LOCKED)
 * ------------------------------------------------------------
 * Internal SPA contract:
 * - All callers above this layer receive domain payloads ONLY (T).
 * - No component/page/service may unwrap transport envelopes.
 *
 * Backend baseline:
 * - Frappe /api/method returns: { message: T }
 *
 * Client variance (real-world):
 * - Some stacks wrap: { data: { message: T } }
 * - frappe-ui's frappeRequest may already return T (message-unwrapped)
 *
 * This boundary:
 * - Normalizes exactly once.
 * - Returns ONLY T.
 * - Throws loudly on null/undefined and obvious server error shapes.
 */
function unwrapTransport<T>(res: unknown): T {
	let root: unknown = res

	// Allow axios-ish wrapper if present
	if (root && typeof root === 'object' && 'data' in root) {
		root = (root as { data: unknown }).data
	}

	// Hard fail on null-ish
	if (root === null || root === undefined) {
		throw new Error('[frappe] Invalid response shape: expected { message: T } or T (got null/undefined)')
	}

	// Standard Frappe envelope
	if (typeof root === 'object' && 'message' in root) {
		return (root as { message: T }).message
	}

	// If server returned an error-ish object without message, fail fast.
	// (We keep this minimal and deterministic — no clever inference.)
	if (typeof root === 'object') {
		if ('exc' in root || 'exception' in root) {
			throw new Error('[frappe] Server exception response (missing message envelope)')
		}
	}

	// Already-unwrapped payload (T) — acceptable at the boundary
	return root as T
}

/**
 * Proposal F (LOCKED): Only this module may call frappeRequest.
 * Everyone else must call apiRequest()/apiMethod() exported from here.
 */
async function _frappeRequestRaw(opts: unknown): Promise<unknown> {
	return (frappeRequest as (o: unknown) => Promise<unknown>)(opts)
}

/**
 * Canonical request wrapper used by services (domain payload only).
 * - returns T (never {message:T})
 * - throws on invalid shapes
 */
export async function apiRequest<T>(opts: unknown): Promise<T> {
	try {
		const res = await _frappeRequestRaw(opts)
		return unwrapTransport<T>(res)
	} catch (error) {
		const status = extractErrorStatus(error)
		const message = extractErrorMessage(error)
		if ((status === 401 || status === 403) && isSessionFailureMessage(message)) {
			redirectToLoginIfNeeded()
		}
		throw error
	}
}

/**
 * Convenience wrapper for /api/method calls.
 * NOTE: Keep usage centralized; do not sprinkle ad-hoc request shapes.
 */
export async function apiMethod<T>(method: string, params?: Record<string, unknown>): Promise<T> {
	const opts = {
		url: `/api/method/${method}`,
		method: 'POST',
		params: params || {},
	}
	return apiRequest<T>(opts)
}

export async function setupFrappeUI() {
	// Enforce “domain payload only” for all frappe-ui resources.
	setConfig('resourceFetcher', async (opts: unknown) => {
		return apiRequest(opts)
	})

	// Ensure CSRF token accompanies every request (required for POST)
	const csrfToken = await resolveCsrfToken()

	setConfig('fetchOptions', {
		credentials: 'same-origin',
		headers: csrfToken ? { 'X-Frappe-CSRF-Token': csrfToken } : undefined,
	})
}
