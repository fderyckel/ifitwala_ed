// ifitwala_ed/ui-spa/src/lib/services/policySignature/policySignatureService.ts

import { createResource } from 'frappe-ui';

import { SIGNAL_FOCUS_INVALIDATE, uiSignals } from '@/lib/uiSignals';

import type {
	Request as GetCampaignOptionsRequest,
	Response as GetCampaignOptionsResponse,
} from '@/types/contracts/policy_signature/get_staff_policy_campaign_options';
import type {
	Request as LaunchCampaignRequest,
	Response as LaunchCampaignResponse,
} from '@/types/contracts/policy_signature/launch_staff_policy_campaign';
import type {
	Request as GetDashboardRequest,
	Response as GetDashboardResponse,
} from '@/types/contracts/policy_signature/get_staff_policy_signature_dashboard';

export function createPolicySignatureService() {
	const getCampaignOptionsResource = createResource<GetCampaignOptionsResponse>({
		url: 'ifitwala_ed.api.policy_signature.get_staff_policy_campaign_options',
		method: 'POST',
		auto: false,
	});

	const launchCampaignResource = createResource<LaunchCampaignResponse>({
		url: 'ifitwala_ed.api.policy_signature.launch_staff_policy_campaign',
		method: 'POST',
		auto: false,
	});

	const getDashboardResource = createResource<GetDashboardResponse>({
		url: 'ifitwala_ed.api.policy_signature.get_staff_policy_signature_dashboard',
		method: 'POST',
		auto: false,
	});

	async function getCampaignOptions(
		payload: GetCampaignOptionsRequest = {}
	): Promise<GetCampaignOptionsResponse> {
		return getCampaignOptionsResource.submit(payload);
	}

	async function launchCampaign(payload: LaunchCampaignRequest): Promise<LaunchCampaignResponse> {
		const result = await launchCampaignResource.submit(payload);
		if ((result?.counts?.created || 0) > 0) {
			uiSignals.emit(SIGNAL_FOCUS_INVALIDATE);
		}
		return result;
	}

	async function getDashboard(payload: GetDashboardRequest): Promise<GetDashboardResponse> {
		return getDashboardResource.submit(payload);
	}

	return {
		getCampaignOptions,
		launchCampaign,
		getDashboard,
	};
}
