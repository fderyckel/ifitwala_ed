// ui-spa/src/lib/services/organizationChart/organizationChartService.ts

import { createResource } from 'frappe-ui'

import type {
	Request as OrgChartChildrenRequest,
	Response as OrgChartChildrenResponse,
} from '@/types/contracts/organization_chart/get_org_chart_children'

import type { Response as OrgChartContextResponse } from '@/types/contracts/organization_chart/get_org_chart_context'

import type {
	Request as OrgChartTreeRequest,
	Response as OrgChartTreeResponse,
} from '@/types/contracts/organization_chart/get_org_chart_tree'

const contextResource = createResource<OrgChartContextResponse>({
	url: 'ifitwala_ed.api.organization_chart.get_org_chart_context',
	method: 'GET',
	auto: false,
})

const childrenResource = createResource<OrgChartChildrenResponse>({
	url: 'ifitwala_ed.api.organization_chart.get_org_chart_children',
	method: 'POST',
	auto: false,
})

const treeResource = createResource<OrgChartTreeResponse>({
	url: 'ifitwala_ed.api.organization_chart.get_org_chart_tree',
	method: 'POST',
	auto: false,
})

export async function getOrganizationChartContext() {
	return contextResource.fetch()
}

export async function getOrganizationChartChildren(payload: OrgChartChildrenRequest) {
	return childrenResource.submit(payload)
}

export async function getOrganizationChartTree(payload: OrgChartTreeRequest) {
	return treeResource.submit(payload)
}
