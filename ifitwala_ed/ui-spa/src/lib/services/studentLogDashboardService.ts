// ui-spa/src/lib/services/studentLogDashboardService.ts

import { computed, ref, type Ref } from 'vue'
import { createResource } from 'frappe-ui'

import type {
	StudentLogDashboardData,
	StudentLogDashboardFilters,
	StudentLogFilterMeta,
	StudentLogRecentRow,
} from '@/types/studentLogDashboard'

import type {
	StudentLogDashboardGetDashboardDataRequest,
	StudentLogDashboardGetDashboardDataResponse,
	StudentLogDashboardGetDistinctStudentsRequest,
	StudentLogDashboardGetDistinctStudentsResponse,
	StudentLogDashboardGetFilterMetaResponse,
	StudentLogDashboardGetRecentLogsRequest,
	StudentLogDashboardGetRecentLogsResponse,
} from '@/types/contracts/student_log_dashboard'

const emptyDashboard: StudentLogDashboardData = {
	openFollowUps: 0,
	logTypeCount: [],
	logsByCohort: [],
	logsByProgram: [],
	logsByAuthor: [],
	nextStepTypes: [],
	incidentsOverTime: [],
	studentLogs: [],
}

const emptyMeta: StudentLogFilterMeta = {
	schools: [],
	academic_years: [],
	programs: [],
	authors: [],
}

export type StudentLogRecentPaging = {
	start: number
	pageLength: number
}

export function createDebouncedRunner(delay = 400) {
	let timer: number | null = null
	return (fn: () => void) => {
		if (timer) window.clearTimeout(timer)
		timer = window.setTimeout(fn, delay)
	}
}

export function useStudentLogFilterMeta() {
	const resource = createResource<StudentLogDashboardGetFilterMetaResponse>({
		url: 'ifitwala_ed.api.student_log_dashboard.get_filter_meta',
		method: 'GET',
		auto: false,
	})

	const meta = computed(() => resource.data ?? emptyMeta)
	const loading = computed(() => resource.loading)

	async function reload() {
		return resource.fetch()
	}

	return {
		meta,
		loading,
		reload,
	}
}

export function useStudentLogDashboard(filtersRef: Ref<StudentLogDashboardFilters>) {
	const resource = createResource<StudentLogDashboardGetDashboardDataResponse>({
		url: 'ifitwala_ed.api.student_log_dashboard.get_dashboard_data',
		method: 'POST',
		auto: false,
	})

	const dashboard = computed(() => resource.data ?? emptyDashboard)
	const loading = computed(() => resource.loading)

	async function reload() {
		const payload: StudentLogDashboardGetDashboardDataRequest = {
			filters: filtersRef.value,
		}
		return resource.submit(payload)
	}

	return {
		dashboard,
		loading,
		reload,
	}
}

export function useStudentLogRecentLogs(
	filtersRef: Ref<StudentLogDashboardFilters>,
	pagingRef: Ref<StudentLogRecentPaging>
) {
	const rows = ref<StudentLogRecentRow[]>([])
	const hasMore = ref(true)

	const resource = createResource<StudentLogDashboardGetRecentLogsResponse>({
		url: 'ifitwala_ed.api.student_log_dashboard.get_recent_logs',
		method: 'POST',
		auto: false,
	})

	const loading = computed(() => resource.loading)

	async function reload(options?: { reset?: boolean }) {
		if (options?.reset) {
			rows.value = []
			hasMore.value = true
			pagingRef.value.start = 0
		}

		if (!hasMore.value) return []

		const payload: StudentLogDashboardGetRecentLogsRequest = {
			filters: filtersRef.value,
			start: pagingRef.value.start,
			page_length: pagingRef.value.pageLength,
		}

		const response = await resource.submit(payload)
		const batch = Array.isArray(response) ? response : []

		if (batch.length) {
			rows.value = options?.reset ? batch : [...rows.value, ...batch]
			pagingRef.value.start += batch.length
		}

		if (batch.length < pagingRef.value.pageLength) {
			hasMore.value = false
		}

		return batch
	}

	return {
		rows,
		loading,
		hasMore,
		reload,
	}
}

const studentSearchResource = createResource<StudentLogDashboardGetDistinctStudentsResponse>({
	url: 'ifitwala_ed.api.student_log_dashboard.get_distinct_students',
	method: 'POST',
	auto: false,
})

export async function searchDistinctStudents(
	filters: StudentLogDashboardFilters,
	searchText: string
) {
	const payload: StudentLogDashboardGetDistinctStudentsRequest = {
		filters,
		search_text: searchText,
	}
	return studentSearchResource.submit(payload)
}
