// ifitwala_ed/ifitwala_ed/ui-spa/src/resources/frappe.ts
import { setConfig, frappeRequest } from 'frappe-ui';

async function resolveCsrfToken(): Promise<string> {
	if (typeof window !== 'undefined' && (window as any)?.csrf_token) {
		return (window as any).csrf_token as string;
	}

	if (typeof document !== 'undefined') {
		const meta = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null;
		if (meta?.content) {
			return meta.content;
		}
	}

	try {
		const response = await fetch('/api/method/frappe.client.get_csrf_token', {
			method: 'GET',
			credentials: 'same-origin',
			headers: { Accept: 'application/json' },
		});
		if (response.ok) {
			const payload = await response.json();
			const token = payload?.message || '';
			if (token && typeof window !== 'undefined') {
				(window as any).csrf_token = token;
			}
			return token;
		}
	} catch (err) {
		console.warn('[setupFrappeUI] Unable to fetch CSRF token', err);
	}

	return '';
}

export async function setupFrappeUI() {
	// Use the official frappe-ui fetcher everywhere
	setConfig('resourceFetcher', frappeRequest);

	// Ensure CSRF token accompanies every request (required for POST)
	const csrfToken = await resolveCsrfToken();

	setConfig('fetchOptions', {
		credentials: 'same-origin',
		headers: csrfToken
			? { 'X-Frappe-CSRF-Token': csrfToken }
			: undefined,
	});

	// Optional: central error toaster (we can wire later)
	// setConfig('onError', (err: any) => {
	// 	console.error(err);
	// });
}
