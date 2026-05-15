import { createResource } from 'frappe-ui'

import type {
	Request as GetDashboardContextRequest,
	Response as GetDashboardContextResponse,
} from '@/types/contracts/family_consent/get_family_consent_dashboard_context'
import type {
	Request as GetDashboardRequest,
	Response as GetDashboardResponse,
} from '@/types/contracts/family_consent/get_family_consent_dashboard'

export function createFamilyConsentService() {
	const getDashboardContextResource = createResource<GetDashboardContextResponse>({
		url: 'ifitwala_ed.api.family_consent_staff.get_family_consent_dashboard_context',
		method: 'POST',
		auto: false,
	})

	const getDashboardResource = createResource<GetDashboardResponse>({
		url: 'ifitwala_ed.api.family_consent_staff.get_family_consent_dashboard',
		method: 'POST',
		auto: false,
	})

	async function getDashboardContext(
		payload: GetDashboardContextRequest = {}
	): Promise<GetDashboardContextResponse> {
		return getDashboardContextResource.submit(payload)
	}

	async function getDashboard(payload: GetDashboardRequest = {}): Promise<GetDashboardResponse> {
		return getDashboardResource.submit(payload)
	}

	return {
		getDashboardContext,
		getDashboard,
	}
}
