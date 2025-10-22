// ifitwala_ed/ifitwala_ed/ui-spa/src/resources/frappe.ts
import { setConfig, frappeRequest } from 'frappe-ui';

export function setupFrappeUI() {
	// Use the official frappe-ui fetcher everywhere
	setConfig('resourceFetcher', frappeRequest);

	// Ensure CSRF token accompanies every request (required for POST)
	const csrfToken =
		typeof window !== 'undefined' && (window as any)?.csrf_token
			? (window as any).csrf_token
			: '';

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
