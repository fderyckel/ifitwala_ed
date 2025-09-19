// ifitwala_ed/ifitwala_ed/ui-spa/src/resources/frappe.ts
import { setConfig, frappeRequest } from 'frappe-ui';

export function setupFrappeUI() {
	// Use the official frappe-ui fetcher everywhere
	setConfig('resourceFetcher', frappeRequest);

	// Optional: send cookies for auth (needed if subdomains differ)
	// setConfig('fetchOptions', { credentials: 'include' });

	// Optional: central error toaster (we can wire later)
	// setConfig('onError', (err: any) => {
	// 	console.error(err);
	// });
}
