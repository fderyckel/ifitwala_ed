// ui-spa/src/types/contracts/organization_chart/get_org_chart_context.ts

type OrganizationOption = {
	name: string
	organization_name: string
}

export type Request = Record<string, never>

export type Response = {
	organizations: OrganizationOption[]
	default_organization: string | null
	expand_limits: {
		max_nodes: number
		max_depth: number
	}
}
