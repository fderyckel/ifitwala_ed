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

/**
 * A++ Transport Contract (LOCKED)
 * ------------------------------------------------------------
 * Services must NEVER unwrap transport responses.
 * Therefore, the resourceFetcher MUST return domain payloads only.
 *
 * Backend contract:
 * - Frappe /api/method returns: { message: T }
 *
 * Client variance:
 * - Some request stacks may wrap: { data: { message: T } }
 *
 * This adapter:
 * - accepts unknown
 * - enforces { message: T }
 * - returns ONLY T
 * - throws loudly when the backend breaks the envelope contract
 */
function unwrapFrappeEnvelope<T>(res: unknown): T {
	let root: unknown = res;

	// Defensive: allow axios-ish wrappers if present
	if (root && typeof root === 'object' && 'data' in root) {
		root = (root as { data: unknown }).data;
	}

	if (root && typeof root === 'object' && 'message' in root) {
		return (root as { message: T }).message;
	}

	throw new Error(
		'[frappe] Invalid response shape: expected { message: T } envelope'
	);
}

export async function setupFrappeUI() {
	// Use the official frappe-ui fetcher everywhere,
	// but enforce domain-only payloads (A++).
	setConfig('resourceFetcher', async (opts: unknown) => {
		const res = await (frappeRequest as (o: unknown) => Promise<unknown>)(opts);
		return unwrapFrappeEnvelope(res);
	});

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
