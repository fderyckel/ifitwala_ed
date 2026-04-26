import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetTermReportingReviewSurfaceRequest,
	Response as GetTermReportingReviewSurfaceResponse,
} from '@/types/contracts/term_reporting/get_term_reporting_review_surface'

const REVIEW_SURFACE_METHOD = 'ifitwala_ed.api.term_reporting.get_review_surface'

export function getTermReportingReviewSurface(
	payload: GetTermReportingReviewSurfaceRequest = {}
): Promise<GetTermReportingReviewSurfaceResponse> {
	return apiMethod<GetTermReportingReviewSurfaceResponse>(
		REVIEW_SURFACE_METHOD,
		payload as Record<string, unknown>
	)
}
