// ui-spa/src/types/contracts/organization_chart/get_org_chart_children.ts

type OrgChartNode = {
	id: string
	name: string
	first_name: string | null
	title: string | null
	school: string | null
	organization: string | null
	image: string | null
	connections: number
	expandable: boolean
	parent_id: string | null
}

export type Request = {
	parent?: string | null
	organization?: string | null
}

export type Response = OrgChartNode[]
