// ui-spa/src/lib/services/student/studentHomeService.ts

import { createResource } from 'frappe-ui'

export type StudentPortalIdentity = {
	user: string
	student?: string | null
	display_name?: string | null
	preferred_name?: string | null
	first_name?: string | null
	full_name?: string | null
	image_url?: string | null
}

const studentPortalIdentityResource = createResource<StudentPortalIdentity>({
	url: 'ifitwala_ed.api.portal.get_student_portal_identity',
	method: 'POST',
	auto: false,
})

export async function getStudentPortalIdentity(): Promise<StudentPortalIdentity> {
	return studentPortalIdentityResource.submit({})
}
