// ifitwala_ed/ui-spa/src/lib/frappe.ts

import { setConfig } from 'frappe-ui'

const AUTH_ERROR_PATTERNS = [
	'you need to sign in',
	'you must be logged in',
	'user none not found',
	'session expired',
]

const FRAPPE_TRANSPORT_KEYS = new Set([
	'message',
	'docs',
	'docinfo',
	'exc',
	'exception',
	'_server_messages',
	'_debug_messages',
	'_error_message',
	'_exc_source',
	'home_page',
	'full_name',
	'freeze',
	'freeze_message',
])

let cachedCsrfToken: string | null = null
let csrfPromise: Promise<string> | null = null

export function setCsrfToken(token: string | null) {
	cachedCsrfToken = token?.trim() || null
	if (typeof window !== 'undefined') {
		if (cachedCsrfToken) {
			;(window as Window & { csrf_token?: string }).csrf_token = cachedCsrfToken
		} else {
			delete (window as Window & { csrf_token?: string }).csrf_token
		}
	}
}

async function resolveCsrfToken(): Promise<string> {
	if (cachedCsrfToken) {
		return cachedCsrfToken
	}

	if (typeof window !== 'undefined') {
		const browserWindow = window as Window & { csrf_token?: string }
		if (browserWindow.csrf_token) {
			cachedCsrfToken = browserWindow.csrf_token
			return cachedCsrfToken
		}
	}

	if (typeof document !== 'undefined') {
		const meta = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null
		if (meta?.content) {
			if (typeof window !== 'undefined') {
				;(window as Window & { csrf_token?: string }).csrf_token = meta.content
			}
			cachedCsrfToken = meta.content
			return cachedCsrfToken
		}
	}

	if (!csrfPromise) {
		csrfPromise = (async () => {
			try {
				const response = await fetch('/api/method/frappe.client.get_csrf_token', {
					method: 'GET',
					credentials: 'same-origin',
					headers: { Accept: 'application/json' },
				})
				if (response.ok) {
					const payload = await response.json()
					const token = typeof payload?.message === 'string' ? payload.message : ''
					if (token && typeof window !== 'undefined') {
						;(window as Window & { csrf_token?: string }).csrf_token = token
					}
					cachedCsrfToken = token
					return token
				}
			} catch (error) {
				console.warn('[frappe] Unable to fetch CSRF token', error)
			}
			return ''
		})()
	}

	const token = await csrfPromise
	csrfPromise = null
	return token || ''
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

function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== 'string' || !raw.trim()) {
		return []
	}

	try {
		const entries = JSON.parse(raw)
		if (!Array.isArray(entries)) {
			return []
		}
		return entries
			.map((entry) => {
				if (typeof entry !== 'string') {
					return String(entry || '')
				}
				try {
					const payload = JSON.parse(entry)
					return typeof payload?.message === 'string' ? payload.message : entry
				} catch {
					return entry
				}
			})
			.filter((message) => Boolean((message || '').trim()))
	} catch {
		return []
	}
}

function normalizeRequestUrl(url: string): string {
	if (!url) {
		throw new Error('[frappe] Request url is required')
	}
	if (url.startsWith('/') || url.startsWith('http')) {
		return url
	}
	return `/api/method/${url}`
}

function mergeHeaders(headers: HeadersInit | undefined, csrfToken: string): Headers {
	const merged = new Headers(headers || {})

	if (!merged.has('Accept')) {
		merged.set('Accept', 'application/json')
	}

	if (typeof window !== 'undefined' && window.location?.hostname && !merged.has('X-Frappe-Site-Name')) {
		merged.set('X-Frappe-Site-Name', window.location.hostname)
	}

	if (csrfToken && !merged.has('X-Frappe-CSRF-Token')) {
		merged.set('X-Frappe-CSRF-Token', csrfToken)
	}

	return merged
}

async function parseResponseBody(response: Response): Promise<unknown> {
	if (typeof response.text !== 'function') {
		if (typeof (response as Response & { json?: () => Promise<unknown> }).json === 'function') {
			return (response as Response & { json: () => Promise<unknown> }).json()
		}
		return null
	}

	const text = await response.text()
	if (!text) {
		return null
	}

	try {
		return JSON.parse(text)
	} catch {
		return text
	}
}

function extractMessagesFromPayload(payload: unknown): string[] {
	if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
		if (typeof payload === 'string' && payload.trim() && !payload.trim().startsWith('<')) {
			return [payload.trim()]
		}
		return []
	}

	const maybe = payload as Record<string, unknown>
	const messages = [
		...parseServerMessages(maybe._server_messages),
		typeof maybe.message === 'string' && maybe.message.trim() ? maybe.message.trim() : '',
		typeof maybe._error_message === 'string' && maybe._error_message.trim() ? maybe._error_message.trim() : '',
	]

	return messages.filter(Boolean)
}

function buildApiError(response: Response, payload: unknown): Error & Record<string, any> {
	const messages = extractMessagesFromPayload(payload)
	const message = messages[0] || response.statusText || 'Request failed.'
	const error = new Error(message) as Error & Record<string, any>

	error.status = response.status
	error.response = response
	error.messages = messages

	if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
		const maybe = payload as Record<string, unknown>
		error.data = payload
		error.exc = maybe.exc
		error.exc_type = maybe.exc_type
		error._server_messages = maybe._server_messages
	}

	return error
}

async function requestRaw(options: Record<string, any>): Promise<unknown> {
	const url = normalizeRequestUrl(String(options.url || ''))
	const method = String(options.method || 'POST').toUpperCase()
	const csrfToken = await resolveCsrfToken()
	const headers = mergeHeaders(options.headers, csrfToken)

	const init: RequestInit = {
		method,
		headers,
		credentials: 'same-origin',
	}

	if (options.params !== undefined) {
		if (method === 'GET') {
			const params = new URLSearchParams()
			for (const [key, value] of Object.entries(options.params || {})) {
				if (Array.isArray(value)) {
					for (const item of value) {
						params.append(key, String(item))
					}
					continue
				}
				if (value !== undefined && value !== null) {
					params.append(key, String(value))
				}
			}
			const query = params.toString()
			const response = await fetch(query ? `${url}?${query}` : url, init)
			const payload = await parseResponseBody(response)
			if (!response.ok) {
				throw buildApiError(response, payload)
			}
			return payload
		}

		const isFormData = typeof FormData !== 'undefined' && options.params instanceof FormData
		if (isFormData) {
			headers.delete('Content-Type')
			init.body = options.params
		} else {
			if (!headers.has('Content-Type')) {
				headers.set('Content-Type', 'application/json; charset=utf-8')
			}
			init.body = JSON.stringify(options.params)
		}
	} else if (!headers.has('Content-Type') && method !== 'GET') {
		headers.set('Content-Type', 'application/json; charset=utf-8')
	}

	const response = await fetch(url, init)
	const payload = await parseResponseBody(response)

	if (!response.ok) {
		throw buildApiError(response, payload)
	}

	if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
		const maybe = payload as Record<string, unknown>
		if (maybe._server_messages) {
			const handler = options.onServerMessages || null
			if (handler) {
				handler(parseServerMessages(maybe._server_messages))
			}
		}
	}

	return payload
}

function redirectToLoginIfNeeded() {
	if (typeof window === 'undefined') return
	if (window.location.pathname.startsWith('/login')) return
	const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
	const loginPath = `/login?redirect-to=${encodeURIComponent(currentPath)}`
	window.location.assign(loginPath)
}

function isCanonicalFrappeEnvelope(value: unknown): value is { message: unknown } {
	if (!value || typeof value !== 'object' || Array.isArray(value) || !('message' in value)) {
		return false
	}

	const keys = Object.keys(value as Record<string, unknown>)
	if (!keys.length || keys.some((key) => !FRAPPE_TRANSPORT_KEYS.has(key))) {
		return false
	}

	if (keys.some((key) => key !== 'message')) {
		return true
	}

	const message = (value as { message: unknown }).message
	return message !== null && typeof message === 'object'
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
 * - some domain payloads legitimately include a top-level `message` field
 *
 * This boundary:
 * - Normalizes exactly once.
 * - Returns ONLY T.
 * - Treats only transport-only objects as Frappe envelopes.
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
	if (isCanonicalFrappeEnvelope(root)) {
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
 * Canonical request wrapper used by services (domain payload only).
 * - returns T (never {message:T})
 * - throws on invalid shapes
 */
export async function apiRequest<T>(opts: unknown): Promise<T> {
	try {
		const res = await requestRaw((opts || {}) as Record<string, any>)
		return unwrapTransport<T>(res)
	} catch (error) {
		if (opts && typeof opts === 'object') {
			;(opts as Record<string, any>).onError?.(error)
		}
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
