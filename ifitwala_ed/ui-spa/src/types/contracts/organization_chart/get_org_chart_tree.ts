// ui-spa/src/types/contracts/organization_chart/get_org_chart_tree.ts

type OrgChartNode = {
	id: string
	name: string
	first_name: string | null
	preferred_name: string | null
	title: string | null
	school: string | null
	school_abbr: string | null
	organization: string | null
	organization_abbr: string | null
	image: string | null
	professional_email: string | null
	phone_ext: string | null
	date_of_joining: string | null
	date_of_joining_label: string | null
	connections: number
	expandable: boolean
	parent_id: string | null
}

type BlockedResponse = {
	status: 'blocked'
	reason: 'max_nodes' | 'max_depth'
	total: number
	max_nodes: number
	max_depth: number
	message: string
}

type OkResponse = {
	status: 'ok'
	nodes: OrgChartNode[]
	roots: string[]
	total: number
	max_depth: number
}

export type Request = {
	organization?: string | null
}

export type Response = BlockedResponse | OkResponse
