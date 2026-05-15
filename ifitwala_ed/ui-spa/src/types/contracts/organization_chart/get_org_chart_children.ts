// ui-spa/src/types/contracts/organization_chart/get_org_chart_children.ts

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

export type Request = {
	parent?: string | null
	organization?: string | null
}

export type Response = OrgChartNode[]
