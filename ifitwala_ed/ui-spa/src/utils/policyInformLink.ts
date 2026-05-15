// ui-spa/src/utils/policyInformLink.ts

export type PolicyInformLinkPayload = {
	policyVersion: string;
	orgCommunication?: string | null;
};

function normalize(value: unknown): string {
	return typeof value === 'string' ? value.trim() : '';
}

function parseHashPolicyVersion(href: string): string {
	const raw = normalize(href);
	if (!raw.startsWith('#policy-inform')) return '';
	const [_, query = ''] = raw.split('?', 2);
	const params = new URLSearchParams(query);
	return normalize(params.get('policy_version'));
}

function parseDeskOrAppPolicyVersion(href: string): string {
	const raw = normalize(href);
	if (!raw) return '';
	const match = raw.match(/\/(?:app|desk)\/policy-version\/([^/?#]+)/i);
	if (!match || !match[1]) return '';
	try {
		return normalize(decodeURIComponent(match[1]));
	} catch {
		return normalize(match[1]);
	}
}

function parseAnchorPayload(anchor: HTMLAnchorElement): PolicyInformLinkPayload | null {
	const marker = normalize(anchor.getAttribute('data-policy-inform'));
	const dataPolicyVersion = normalize(anchor.getAttribute('data-policy-version'));
	const dataOrgCommunication = normalize(anchor.getAttribute('data-org-communication'));
	const href = normalize(anchor.getAttribute('href'));

	const policyVersion = dataPolicyVersion || parseHashPolicyVersion(href) || parseDeskOrAppPolicyVersion(href);
	if (!policyVersion) return null;
	if (marker && marker !== '1') return null;

	return {
		policyVersion,
		orgCommunication: dataOrgCommunication || null,
	};
}

export function extractPolicyInformLinkFromClickEvent(
	event: MouseEvent
): PolicyInformLinkPayload | null {
	const target = event.target;
	if (!(target instanceof Element)) return null;
	const anchor = target.closest('a');
	if (!(anchor instanceof HTMLAnchorElement)) return null;
	return parseAnchorPayload(anchor);
}
