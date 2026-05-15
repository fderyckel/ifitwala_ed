// ui-spa/src/lib/services/policyInform/policyInformService.ts

import { createResource } from 'frappe-ui';

import type {
	Request as GetPolicyInformPayloadRequest,
	Response as GetPolicyInformPayloadResponse,
} from '@/types/contracts/policy_communication/get_policy_inform_payload';

export function createPolicyInformService() {
	const getPolicyInformPayloadResource = createResource<GetPolicyInformPayloadResponse>({
		url: 'ifitwala_ed.api.policy_communication.get_policy_inform_payload',
		method: 'POST',
		auto: false,
	});

	async function getPolicyInformPayload(
		payload: GetPolicyInformPayloadRequest
	): Promise<GetPolicyInformPayloadResponse> {
		return getPolicyInformPayloadResource.submit(payload);
	}

	return {
		getPolicyInformPayload,
	};
}
