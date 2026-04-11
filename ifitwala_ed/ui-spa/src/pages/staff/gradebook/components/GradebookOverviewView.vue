<template>
	<section
		class="flex h-fit flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
	>
		<div class="border-b border-border/50 bg-gray-50/50 px-6 py-4">
			<div class="flex flex-wrap items-center justify-between gap-4">
				<div class="space-y-1">
					<h2 class="text-lg font-semibold text-ink">Class Overview</h2>
					<p class="max-w-2xl text-sm text-ink/60">
						Rows are students and columns are recent deliveries for this group. Open any cell to jump back
						into quick grading.
					</p>
				</div>
				<div class="flex items-center gap-3">
					<div class="hidden text-xs uppercase tracking-wide text-ink/45 sm:block">Recent deliveries</div>
					<FormControl
						type="select"
						size="sm"
						:options="limitOptions"
						option-label="label"
						option-value="value"
						:model-value="deliveryLimit"
						@update:modelValue="onLimitChanged"
					/>
				</div>
			</div>
		</div>

		<div class="min-h-[400px] flex-1 bg-white p-6">
			<div v-if="!group" class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60">
				<div class="rounded-full bg-gray-100 p-4">
					<FeatherIcon name="layout" class="h-8 w-8 text-ink/30" />
				</div>
				<p class="text-lg font-medium text-ink">No Group Selected</p>
				<p class="max-w-xs text-sm">Choose a student group first to open the overall gradebook view.</p>
			</div>

			<div v-else-if="loading" class="flex h-full flex-col items-center justify-center gap-3 pt-20">
				<Spinner class="h-8 w-8 text-canopy" />
				<p class="text-sm text-ink/50">Loading overview...</p>
			</div>

			<div
				v-else-if="errorMessage"
				class="rounded-xl border border-flame/20 bg-flame/5 p-5 text-sm text-ink/70"
			>
				<p class="font-semibold text-ink">Overview unavailable</p>
				<p class="mt-1">{{ errorMessage }}</p>
			</div>

			<div
				v-else-if="!deliveries.length || !students.length"
				class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
			>
				<p class="text-lg font-medium text-ink">Nothing to show yet</p>
				<p class="max-w-md text-sm">
					This overview only shows deliveries that match the current group and filters. Try a different group
					or widen the task filters.
				</p>
			</div>

			<div v-else class="space-y-4">
				<div class="flex flex-wrap gap-2">
					<Badge variant="subtle">Students {{ students.length }}</Badge>
					<Badge variant="subtle">Deliveries {{ deliveries.length }}</Badge>
					<Badge v-if="deliveryType" variant="subtle">{{ deliveryType }}</Badge>
					<Badge v-if="taskType" variant="subtle">{{ taskType }}</Badge>
				</div>

				<div class="overflow-x-auto rounded-xl border border-border/70">
					<table class="min-w-[920px] border-collapse">
						<thead class="bg-gray-50/80">
							<tr class="align-top">
								<th
									class="sticky left-0 z-20 min-w-[220px] border-b border-r border-border/70 bg-gray-50/95 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-ink/50"
								>
									Student
								</th>
								<th
									v-for="delivery in deliveries"
									:key="delivery.delivery_id"
									class="min-w-[170px] border-b border-border/70 px-4 py-3 text-left align-top"
									:class="delivery.delivery_id === selectedTaskName ? 'bg-sky/10' : ''"
								>
									<div class="space-y-1">
										<p class="text-sm font-semibold text-ink">{{ delivery.task_title }}</p>
										<div class="flex flex-wrap gap-1 text-xs text-ink/55">
											<span>Due {{ formatDate(delivery.due_date) || '—' }}</span>
											<Badge v-if="taskModeBadge(delivery)" variant="subtle">
												{{ taskModeBadge(delivery) }}
											</Badge>
										</div>
									</div>
								</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="student in students" :key="student.student" class="align-top">
								<th
									class="sticky left-0 z-10 border-b border-r border-border/60 bg-white px-4 py-3 text-left"
								>
									<div class="flex items-center gap-3">
										<img
											:src="student.student_image || DEFAULT_STUDENT_IMAGE"
											alt=""
											class="h-10 w-10 rounded-full border border-white bg-white object-cover shadow-sm"
										/>
										<div class="min-w-0">
											<p class="truncate text-sm font-semibold text-ink">{{ student.student_name }}</p>
											<p v-if="student.student_id" class="text-xs text-ink/50">{{ student.student_id }}</p>
										</div>
									</div>
								</th>
								<td
									v-for="delivery in deliveries"
									:key="`${student.student}-${delivery.delivery_id}`"
									class="border-b border-border/60 p-2 align-top"
								>
									<button
										type="button"
										class="flex min-h-[104px] w-full flex-col items-start justify-between rounded-lg border px-3 py-3 text-left transition-all"
										:class="
											cellClass(student.student, delivery.delivery_id)
										"
										@click="openCell(student.student, delivery.delivery_id)"
									>
										<div class="space-y-1">
											<p class="text-sm font-semibold text-ink">
												{{ primaryLabel(student.student, delivery) }}
											</p>
											<p class="text-xs text-ink/55">
												{{ secondaryLabel(student.student, delivery) }}
											</p>
										</div>
										<div class="flex flex-wrap gap-1">
											<Badge v-for="badge in cellBadges(student.student, delivery)" :key="badge" variant="subtle">
												{{ badge }}
											</Badge>
										</div>
									</button>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Badge, FeatherIcon, FormControl, Spinner, toast } from 'frappe-ui'
import { createGradebookService } from '@/lib/services/gradebook/gradebookService'
import type { GroupSummary } from '@/types/contracts/gradebook/fetch_groups'
import type { Delivery, Response as GetGridResponse } from '@/types/contracts/gradebook/get_grid'
import { DEFAULT_STUDENT_IMAGE, formatDate, formatPoints, isBinaryTask, isCompletionTask, isCriteriaTask, isPointsTask, taskModeBadge } from '../gradebookUtils'

const props = defineProps<{
	group: GroupSummary | null
	school: string | null
	academicYear: string | null
	course: string | null
	taskType: string | null
	deliveryType: string | null
	selectedTaskName?: string | null
}>()

const emit = defineEmits<{
	openTask: [payload: { taskName: string; student: string }]
}>()

const gradebookService = createGradebookService()
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const deliveryLimit = ref(10)
const response = reactive<GetGridResponse>({
	deliveries: [],
	students: [],
	cells: [],
})
const loadVersion = ref(0)

const limitOptions = [
	{ label: '8 columns', value: 8 },
	{ label: '10 columns', value: 10 },
	{ label: '14 columns', value: 14 },
]

const deliveries = computed(() => response.deliveries || [])
const students = computed(() => response.students || [])
const cellMap = computed(() => {
	const entries = new Map<string, GetGridResponse['cells'][number]>()
	for (const cell of response.cells || []) {
		entries.set(`${cell.student}::${cell.delivery_id}`, cell)
	}
	return entries
})

function showToast(title: string, appearance: 'danger' | 'success' | 'warning' = 'danger') {
	const toastApi = toast as unknown as
		| ((payload: { title: string; appearance?: string }) => void)
		| {
				error?: (message: string) => void
				create?: (payload: { title: string; appearance?: string }) => void
		  }
	if (typeof toastApi === 'function') {
		toastApi({ title, appearance })
		return
	}
	if (appearance === 'danger' && toastApi && typeof toastApi.error === 'function') {
		toastApi.error(title)
		return
	}
	if (toastApi && typeof toastApi.create === 'function') {
		toastApi.create({ title, appearance })
	}
}

function clearResponse() {
	response.deliveries = []
	response.students = []
	response.cells = []
}

async function loadGrid() {
	if (!props.group || !props.school || !props.academicYear) {
		clearResponse()
		errorMessage.value = null
		return
	}

	const version = loadVersion.value + 1
	loadVersion.value = version
	loading.value = true
	errorMessage.value = null

	try {
		const payload = await gradebookService.getGrid({
			school: props.school,
			academic_year: props.academicYear,
			student_group: props.group.name,
			course: props.course,
			task_type: props.taskType,
			delivery_mode: props.deliveryType,
			limit: deliveryLimit.value,
		})
		if (loadVersion.value !== version) {
			return
		}
		response.deliveries = payload.deliveries || []
		response.students = payload.students || []
		response.cells = payload.cells || []
	} catch (error) {
		console.error('Failed to load overview grid', error)
		if (loadVersion.value === version) {
			clearResponse()
			errorMessage.value = 'The overview could not be loaded right now.'
			showToast('Could not load the gradebook overview')
		}
	} finally {
		if (loadVersion.value === version) {
			loading.value = false
		}
	}
}

function onLimitChanged(value: number | string | null) {
	const parsed = typeof value === 'number' ? value : Number.parseInt(String(value || ''), 10)
	if (!Number.isFinite(parsed)) return
	deliveryLimit.value = parsed
}

function findCell(student: string, deliveryId: string) {
	return cellMap.value.get(`${student}::${deliveryId}`) || null
}

function primaryLabel(student: string, delivery: Delivery) {
	const cell = findCell(student, delivery.delivery_id)
	if (!cell) return '—'

	if (isPointsTask(delivery)) {
		return String(cell.official.score ?? cell.official.grade ?? '—')
	}
	if (isCriteriaTask(delivery)) {
		if (delivery.rubric_scoring_strategy === 'Separate Criteria') {
			return cell.official.criteria?.length ? `${cell.official.criteria.length} criteria` : '—'
		}
		return String(cell.official.score ?? cell.official.grade ?? '—')
	}
	if (isBinaryTask(delivery)) {
		return cell.flags.is_complete ? 'Yes' : 'No'
	}
	if (isCompletionTask(delivery)) {
		return cell.flags.is_complete ? 'Complete' : 'Not complete'
	}
	if (delivery.delivery_mode === 'Collect Work') {
		return cell.flags.has_submission ? 'Submitted' : 'Awaiting'
	}
	return cell.flags.grading_status || cell.flags.procedural_status || '—'
}

function secondaryLabel(student: string, delivery: Delivery) {
	const cell = findCell(student, delivery.delivery_id)
	if (!cell) return 'No outcome yet'

	if (isCriteriaTask(delivery) && cell.official.criteria?.length) {
		const levels = cell.official.criteria
			.map(item => item.level)
			.filter(Boolean)
			.slice(0, 2)
			.join(' · ')
		if (levels) return levels
	}

	if (delivery.delivery_mode === 'Collect Work') {
		return cell.flags.procedural_status || cell.flags.grading_status || 'No submission'
	}

	return cell.flags.grading_status || cell.flags.procedural_status || 'Open task'
}

function cellBadges(student: string, delivery: Delivery) {
	const cell = findCell(student, delivery.delivery_id)
	if (!cell) return []

	const badges: string[] = []
	if (cell.flags.has_new_submission) {
		badges.push('New Evidence')
	}
	if (cell.flags.is_published) {
		badges.push('Released')
	}
	if (delivery.allow_feedback && cell.official.feedback) {
		badges.push('Comment')
	}
	if (isPointsTask(delivery) && delivery.max_points !== null && delivery.max_points !== undefined) {
		badges.push(`${formatPoints(delivery.max_points)} max`)
	}
	return badges
}

function cellClass(student: string, deliveryId: string) {
	const cell = findCell(student, deliveryId)
	if (!cell) {
		return 'border-border/70 bg-gray-50/50 hover:border-leaf/40 hover:bg-white'
	}
	if (cell.flags.has_new_submission) {
		return 'border-sand/70 bg-sand/10 hover:border-sand hover:bg-white'
	}
	if (cell.flags.is_published) {
		return 'border-leaf/40 bg-leaf/5 hover:border-leaf hover:bg-white'
	}
	if (props.selectedTaskName === deliveryId) {
		return 'border-leaf/40 bg-sky/10 hover:border-leaf hover:bg-white'
	}
	return 'border-border/70 bg-white hover:border-leaf/40 hover:bg-white'
}

function openCell(student: string, deliveryId: string) {
	emit('openTask', { taskName: deliveryId, student })
}

watch(
	() => [
		props.group?.name,
		props.school,
		props.academicYear,
		props.course,
		props.taskType,
		props.deliveryType,
		deliveryLimit.value,
	],
	() => {
		void loadGrid()
	},
	{ immediate: true }
)
</script>
