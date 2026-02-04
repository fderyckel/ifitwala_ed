// ui-spa/src/types/contracts/student_log_dashboard.ts

import type {
	StudentLogDashboardData,
	StudentLogDashboardFilters,
	StudentLogFilterMeta,
	StudentLogRecentRow,
	StudentSearchResult,
} from '@/types/studentLogDashboard'

/**
 * Student Log Dashboard — API Contracts
 * ------------------------------------------------------------
 * Purpose:
 * - Describe request/response shapes per backend method.
 * - Keep API contracts separate from UI/domain types.
 * - Services should use these types at the boundary.
 *
 * Notes:
 * - Responses currently match domain types 1:1, so we alias them.
 * - If backend shapes diverge later, update contracts here first.
 */

/* get_filter_meta (GET) */
export type StudentLogDashboardGetFilterMetaRequest = Record<string, never>
export type StudentLogDashboardGetFilterMetaResponse = StudentLogFilterMeta

/* get_dashboard_data (POST) */
export type StudentLogDashboardGetDashboardDataRequest = {
	filters: StudentLogDashboardFilters
}
export type StudentLogDashboardGetDashboardDataResponse = StudentLogDashboardData

/* get_recent_logs (POST) */
export type StudentLogDashboardGetRecentLogsRequest = {
	filters: StudentLogDashboardFilters
	start: number
	page_length: number
}
export type StudentLogDashboardGetRecentLogsResponse = StudentLogRecentRow[]

/* get_distinct_students (POST) */
export type StudentLogDashboardGetDistinctStudentsRequest = {
	filters: StudentLogDashboardFilters
	search_text: string
}
export type StudentLogDashboardGetDistinctStudentsResponse = StudentSearchResult[]
