// ui-spa/src/types/client.ts

type HttpMethod = 'POST' | 'GET'

let cachedCsrfToken: string | null = null
let csrfPromise: Promise<string> | null = null

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
		const message = data?._server_messages
			? JSON.parse(data._server_messages).join('\n')
			: data?.message || response.statusText
		throw new Error(message || 'API request failed')
	}
	return data?.message ?? data
}

export function setCsrfToken(token: string) {
	cachedCsrfToken = token
	if (typeof window !== 'undefined') {
		(window as any).csrf_token = token
	}
}
