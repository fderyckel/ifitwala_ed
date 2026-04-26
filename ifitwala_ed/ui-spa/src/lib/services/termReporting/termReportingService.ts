import { apiMethod } from '@/resources/frappe'

import type {
	QueueReviewActionRequest,
	QueueReviewActionResponse,
	Request as GetTermReportingReviewSurfaceRequest,
	Response as GetTermReportingReviewSurfaceResponse,
} from '@/types/contracts/term_reporting/get_term_reporting_review_surface'

const REVIEW_SURFACE_METHOD = 'ifitwala_ed.api.term_reporting.get_review_surface'
const QUEUE_REVIEW_ACTION_METHOD = 'ifitwala_ed.api.term_reporting.queue_review_action'

export function getTermReportingReviewSurface(
	payload: GetTermReportingReviewSurfaceRequest = {}
): Promise<GetTermReportingReviewSurfaceResponse> {
	return apiMethod<GetTermReportingReviewSurfaceResponse>(
		REVIEW_SURFACE_METHOD,
		payload as Record<string, unknown>
	)
}

export function queueTermReportingReviewAction(
	payload: QueueReviewActionRequest
): Promise<QueueReviewActionResponse> {
	return apiMethod<QueueReviewActionResponse>(
		QUEUE_REVIEW_ACTION_METHOD,
		payload as unknown as Record<string, unknown>
	)
}
