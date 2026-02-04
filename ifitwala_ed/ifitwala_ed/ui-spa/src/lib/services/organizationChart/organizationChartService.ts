// ui-spa/src/lib/services/organizationChart/organizationChartService.ts

import { apiMethod } from '@/lib/frappe'

import type {
	Request as OrgChartChildrenRequest,
	Response as OrgChartChildrenResponse,
} from '@/types/contracts/organization_chart/get_org_chart_children'

import type { Response as OrgChartContextResponse } from '@/types/contracts/organization_chart/get_org_chart_context'

import type {
	Request as OrgChartTreeRequest,
	Response as OrgChartTreeResponse,
} from '@/types/contracts/organization_chart/get_org_chart_tree'

export async function getOrganizationChartContext() {
	return apiMethod<OrgChartContextResponse>(
		'ifitwala_ed.api.organization_chart.get_org_chart_context'
	)
}

export async function getOrganizationChartChildren(payload: OrgChartChildrenRequest) {
	return apiMethod<OrgChartChildrenResponse>(
		'ifitwala_ed.api.organization_chart.get_org_chart_children',
		payload as Record<string, unknown>
	)
}

export async function getOrganizationChartTree(payload: OrgChartTreeRequest) {
	return apiMethod<OrgChartTreeResponse>(
		'ifitwala_ed.api.organization_chart.get_org_chart_tree',
		payload as Record<string, unknown>
	)
}
