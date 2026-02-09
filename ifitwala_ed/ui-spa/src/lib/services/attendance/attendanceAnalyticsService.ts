// ui-spa/src/lib/services/attendance/attendanceAnalyticsService.ts

import { createResource } from 'frappe-ui'

import type {
	AttendanceCodeUsageParams,
	AttendanceCodeUsageResponse,
	AttendanceHeatmapParams,
	AttendanceHeatmapResponse,
	AttendanceMyGroupsParams,
	AttendanceMyGroupsResponse,
	AttendanceOverviewParams,
	AttendanceOverviewResponse,
	AttendanceRiskParams,
	AttendanceRiskResponse,
} from '@/types/contracts/attendance'

const METHOD = 'ifitwala_ed.api.attendance.get'

/**
 * Attendance Analytics Service (A+)
 * ------------------------------------------------------------
 * - Single backend endpoint with strict modes.
 * - POST only.
 * - Flat payload via submit(payload).
 * - No UI side effects (no toast, no signals).
 */
export function createAttendanceAnalyticsService() {
	const overviewResource = createResource<AttendanceOverviewResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const heatmapResource = createResource<AttendanceHeatmapResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const riskResource = createResource<AttendanceRiskResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const codeUsageResource = createResource<AttendanceCodeUsageResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	const myGroupsResource = createResource<AttendanceMyGroupsResponse>({
		url: METHOD,
		method: 'POST',
		auto: false,
	})

	async function getOverview(payload: AttendanceOverviewParams): Promise<AttendanceOverviewResponse> {
		return overviewResource.submit(payload)
	}

	async function getHeatmap(payload: AttendanceHeatmapParams): Promise<AttendanceHeatmapResponse> {
		return heatmapResource.submit(payload)
	}

	async function getRisk(payload: AttendanceRiskParams): Promise<AttendanceRiskResponse> {
		return riskResource.submit(payload)
	}

	async function getCodeUsage(payload: AttendanceCodeUsageParams): Promise<AttendanceCodeUsageResponse> {
		return codeUsageResource.submit(payload)
	}

	async function getMyGroups(payload: AttendanceMyGroupsParams): Promise<AttendanceMyGroupsResponse> {
		return myGroupsResource.submit(payload)
	}

	return {
		getOverview,
		getHeatmap,
		getRisk,
		getCodeUsage,
		getMyGroups,
	}
}
