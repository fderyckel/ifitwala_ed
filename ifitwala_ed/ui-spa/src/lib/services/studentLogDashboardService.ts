// ui-spa/src/lib/services/studentLogDashboardService.ts

import { computed, ref, type Ref } from 'vue'
import { createResource } from 'frappe-ui'

import type {
	StudentLogDashboardData,
	StudentLogDashboardFilters,
	StudentLogFilterMeta,
	StudentLogRecentRow,
	StudentSearchResult,
} from '@/types/studentLogDashboard'

type ResourceResponse<T> = T | { message: T }

function unwrapMessage<T>(res: ResourceResponse<T>): T {
	if (res && typeof res === 'object' && 'message' in res) {
		return (res as { message: T }).message
	}
	return res as T
}

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
	const resource = createResource<StudentLogFilterMeta>({
		url: 'ifitwala_ed.api.student_log_dashboard.get_filter_meta',
		method: 'GET',
		auto: false,
		transform: unwrapMessage,
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
	const resource = createResource<StudentLogDashboardData>({
		url: 'ifitwala_ed.api.student_log_dashboard.get_dashboard_data',
		method: 'POST',
		auto: false,
		transform: unwrapMessage,
	})

	const dashboard = computed(() => resource.data ?? emptyDashboard)
	const loading = computed(() => resource.loading)

	async function reload() {
		return resource.submit({ filters: filtersRef.value })
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

	const resource = createResource<StudentLogRecentRow[]>({
		url: 'ifitwala_ed.api.student_log_dashboard.get_recent_logs',
		method: 'POST',
		auto: false,
		transform: unwrapMessage,
	})

	const loading = computed(() => resource.loading)

	async function reload(options?: { reset?: boolean }) {
		if (options?.reset) {
			rows.value = []
			hasMore.value = true
			pagingRef.value.start = 0
		}

		if (!hasMore.value) return []

		const payload = {
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

const studentSearchResource = createResource<StudentSearchResult[]>({
	url: 'ifitwala_ed.api.student_log_dashboard.get_distinct_students',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
})

export async function searchDistinctStudents(
	filters: StudentLogDashboardFilters,
	searchText: string
) {
	return studentSearchResource.submit({
		filters,
		search_text: searchText,
	})
}
