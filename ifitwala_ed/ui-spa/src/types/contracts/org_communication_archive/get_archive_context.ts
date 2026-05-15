// ui-spa/src/types/contracts/org_communication_archive/get_archive_context.ts

type TeamOption = {
  value: string
  label: string
}

type GroupOption = {
  value: string
  label: string
  school?: string | null
}

type SchoolOption = {
  name: string
  school_name?: string | null
  abbr?: string | null
  organization?: string | null
}

type OrganizationOption = {
  name: string
  organization_name?: string | null
  abbr?: string | null
}

type Defaults = {
  school: string | null
  organization: string | null
  team: string | null
}

export type Request = Record<string, never>

export type Response = {
  my_teams: TeamOption[]
  my_groups: GroupOption[]
  schools: SchoolOption[]
  organizations: OrganizationOption[]
  defaults: Defaults
  base_org: string | null
  base_school: string | null
}
