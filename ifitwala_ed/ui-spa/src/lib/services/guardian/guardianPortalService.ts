import { createResource } from 'frappe-ui'

export type GuardianPortalIdentity = {
	user: string
	guardian?: string | null
	display_name?: string | null
	full_name?: string | null
	email?: string | null
	image_url?: string | null
}

const guardianPortalIdentityResource = createResource<GuardianPortalIdentity>({
	url: 'ifitwala_ed.api.portal.get_guardian_portal_identity',
	method: 'POST',
	auto: false,
})

export async function getGuardianPortalIdentity(): Promise<GuardianPortalIdentity> {
	return guardianPortalIdentityResource.submit({})
}
