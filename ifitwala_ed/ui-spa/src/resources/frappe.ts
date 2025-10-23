// ifitwala_ed/ifitwala_ed/ui-spa/src/resources/frappe.ts
import { setConfig, frappeRequest } from 'frappe-ui';

async function resolveCsrfToken(): Promise<string> {
	if (typeof window !== 'undefined' && (window as any)?.csrf_token) {
		return (window as any).csrf_token as string;
	}

	if (typeof document !== 'undefined') {
		const meta = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null;
		if (meta?.content) {
			if (typeof window !== 'undefined') {
				(window as any).csrf_token = meta.content;
			}
			return meta.content;
		}
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
