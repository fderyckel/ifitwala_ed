// ifitwala_ed/ui-spa/src/lib/client.ts

type HttpMethod = 'POST' | 'GET'

let cachedCsrfToken: string | null = null
let csrfPromise: Promise<string> | null = null
const AUTH_ERROR_PATTERNS = [
	'you need to sign in',
	'you must be logged in',
	'user none not found',
	'session expired',
]

async function resolveCsrfToken(): Promise<string> {
	if (cachedCsrfToken) {
		return cachedCsrfToken
	}

	if (typeof window !== 'undefined' && (window as any)?.csrf_token) {
		cachedCsrfToken = (window as any).csrf_token as string
		return cachedCsrfToken
	}

	if (typeof document !== 'undefined') {
		const meta = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null
		if (meta?.content) {
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
					const token = payload?.message || ''
					if (token && typeof window !== 'undefined') {
						(window as any).csrf_token = token
					}
					cachedCsrfToken = token
					return token
				}
			} catch (error) {
				console.warn('[api] Unable to fetch CSRF token', error)
			}
			return ''
		})()
	}

	const token = await csrfPromise
	csrfPromise = null
	return token || ''
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

function isSessionFailureMessage(message: string): boolean {
	const normalized = (message || '').toLowerCase()
	return AUTH_ERROR_PATTERNS.some((pattern) => normalized.includes(pattern))
}

function redirectToLoginIfNeeded() {
	if (typeof window === 'undefined') {
		return
	}
	if (window.location.pathname.startsWith('/login')) {
		return
	}
	const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
	const loginPath = `/login?redirect-to=${encodeURIComponent(currentPath)}`
	window.location.assign(loginPath)
}

export async function api(method: string, payload?: any, httpMethod: HttpMethod = 'POST') {
	const csrf = await resolveCsrfToken()
	const response = await fetch(`/api/method/${method}`, {
		method: httpMethod,
		credentials: 'same-origin',
		headers: {
			'Content-Type': 'application/json',
			...(csrf ? { 'X-Frappe-CSRF-Token': csrf } : {}),
		},
		body: httpMethod === 'POST' ? JSON.stringify(payload || {}) : undefined,
	})

	const data = await response.json().catch(() => ({}))
	if (!response.ok || data?.exception || data?.exc) {
		const serverMessages = parseServerMessages(data?._server_messages)
		const message = serverMessages.join('\n') || data?.message || response.statusText
		if ((response.status === 401 || response.status === 403) && isSessionFailureMessage(message || '')) {
			redirectToLoginIfNeeded()
		}
		throw new Error(message || 'API request failed')
	}
	return data?.message ?? data
}

export async function apiUpload<T>(method: string, formData: FormData): Promise<T> {
	const csrf = await resolveCsrfToken()
	const response = await fetch(`/api/method/${method}`, {
		method: 'POST',
		credentials: 'same-origin',
		body: formData,
		headers: csrf ? { 'X-Frappe-CSRF-Token': csrf } : undefined,
	})

	const data = await response.json().catch(() => ({}))
	if (!response.ok || data?.exception || data?.exc) {
		const serverMessages = parseServerMessages(data?._server_messages)
		const message = serverMessages.join('\n') || data?.message || response.statusText
		if ((response.status === 401 || response.status === 403) && isSessionFailureMessage(message || '')) {
			redirectToLoginIfNeeded()
		}
		throw new Error(message || 'API request failed')
	}

	return (data?.message ?? data) as T
}

export function setCsrfToken(token: string) {
	cachedCsrfToken = token
	if (typeof window !== 'undefined') {
		(window as any).csrf_token = token
	}
}
