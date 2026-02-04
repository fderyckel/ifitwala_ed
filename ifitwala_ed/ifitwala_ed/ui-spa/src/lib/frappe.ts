// ifitwala_ed/ui-spa/src/lib/frappe.ts

import { setConfig, frappeRequest } from 'frappe-ui'

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
	const res = await _frappeRequestRaw(opts)
	return unwrapTransport<T>(res)
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
