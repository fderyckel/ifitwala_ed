import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianPortalChromeRequest,
	Response as GetGuardianPortalChromeResponse,
} from '@/types/contracts/portal/get_guardian_portal_chrome'
import type {
	Request as GetStudentPortalChromeRequest,
	Response as GetStudentPortalChromeResponse,
} from '@/types/contracts/portal/get_student_portal_chrome'

const STUDENT_PORTAL_CHROME_METHOD = 'ifitwala_ed.api.portal.get_student_portal_chrome'
const GUARDIAN_PORTAL_CHROME_METHOD = 'ifitwala_ed.api.portal.get_guardian_portal_chrome'

export async function getStudentPortalChrome(
	payload: GetStudentPortalChromeRequest = {}
): Promise<GetStudentPortalChromeResponse> {
	return apiMethod<GetStudentPortalChromeResponse>(STUDENT_PORTAL_CHROME_METHOD, payload)
}

export async function getGuardianPortalChrome(
	payload: GetGuardianPortalChromeRequest = {}
): Promise<GetGuardianPortalChromeResponse> {
	return apiMethod<GetGuardianPortalChromeResponse>(GUARDIAN_PORTAL_CHROME_METHOD, payload)
}
