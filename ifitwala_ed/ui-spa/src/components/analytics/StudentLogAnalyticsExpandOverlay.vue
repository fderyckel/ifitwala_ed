<!-- ui-spa/src/components/analytics/StudentLogAnalyticsExpandOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog as="div" class="if-overlay if-overlay--student-log-analytics" @close="emitClose">
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" />
			</TransitionChild>

			<div class="if-overlay__wrap" :style="overlayStyle">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel">
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose"
						>
							Close
						</button>

						<div class="flex items-start justify-between gap-3 px-5 pt-5">
							<div class="min-w-0">
								<p class="type-overline">Analytics</p>
								<DialogTitle class="type-h2 text-ink mt-1">
									{{ title }}
								</DialogTitle>
								<p v-if="subtitle" class="type-caption mt-1">
									{{ subtitle }}
								</p>
							</div>

							<button
								type="button"
								class="if-overlay__icon-button"
								aria-label="Close"
								@click="emitClose"
							>
								<FeatherIcon name="x" class="h-4 w-4" />
							</button>
						</div>

						<div class="if-overlay__body">
							<div v-if="kind === 'chart'">
								<AnalyticsChart
									v-if="hasChartSeries"
									:option="chartOption"
									class="analytics-chart--expanded"
								/>
								<div v-else class="type-empty">
									No data to display.
								</div>
							</div>

							<div v-else class="space-y-3">
								<div v-if="!rows.length" class="type-empty">
									No rows to display.
								</div>

								<div v-else class="overflow-auto rounded-xl border border-slate-200">
									<table class="min-w-full border-collapse type-caption text-ink/80">
										<thead class="bg-slate-50">
											<tr v-if="isRecentRows" class="border-b border-slate-200">
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Date</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Student</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Program</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Type</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Log</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Author</th>
												<th class="px-3 py-2 text-center type-label text-slate-token/70">FU</th>
											</tr>
											<tr v-else class="border-b border-slate-200">
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Date</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Type</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Log</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Author</th>
											</tr>
										</thead>
										<tbody>
											<tr
												v-for="row in rows"
												:key="rowKey(row)"
												class="border-b border-slate-100"
											>
												<template v-if="isRecentRow(row)">
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ formatDate(row.date) }}
													</td>
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ row.student_full_name || row.student }}
													</td>
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ row.program || '-' }}
													</td>
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ row.log_type }}
													</td>
													<td class="px-3 py-2 align-top" :title="stripHtml(row.content || '')">
														{{ truncate(stripHtml(row.content || ''), 180) }}
													</td>
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ row.author }}
													</td>
													<td class="px-3 py-2 align-top text-center">
														<span
															v-if="row.requires_follow_up"
															class="inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-100 type-badge-label text-amber-700"
														>
															Y
														</span>
													</td>
												</template>
												<template v-else>
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ formatDate(row.date) }}
													</td>
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ row.log_type }}
													</td>
													<td class="px-3 py-2 align-top" :title="stripHtml(row.content || '')">
														{{ truncate(stripHtml(row.content || ''), 200) }}
													</td>
													<td class="px-3 py-2 align-top whitespace-nowrap">
														{{ row.author }}
													</td>
												</template>
											</tr>
										</tbody>
									</table>
								</div>
							</div>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { FeatherIcon } from 'frappe-ui'

import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'
import type { StudentLogRecentRow, StudentLogStudentRow } from '@/types/studentLogDashboard'

type ChartOption = Record<string, unknown>
type TableRow = StudentLogRecentRow | StudentLogStudentRow

const props = defineProps<{
	open: boolean
	zIndex?: number
	overlayId?: string | null
	title: string
	chartOption: ChartOption
	kind: 'chart' | 'table'
	rows?: TableRow[]
	subtitle?: string | null
}>()

const emit = defineEmits<{
	(e: 'close'): void
	(e: 'after-leave'): void
}>()

const initialFocus = ref<HTMLElement | null>(null)
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }))
const rows = computed(() => props.rows ?? [])
const hasChartSeries = computed(() => {
	const option = props.chartOption
	const series = option && typeof option === 'object' ? (option as { series?: unknown }).series : null
	return Array.isArray(series) && series.length > 0
})

const isRecentRows = computed(() => {
	const first = rows.value[0]
	return !!first && isRecentRow(first)
})

function emitClose() {
	emit('close')
}

function emitAfterLeave() {
	emit('after-leave')
}

function isRecentRow(row: TableRow): row is StudentLogRecentRow {
	return 'student' in row
}

function rowKey(row: TableRow) {
	if (isRecentRow(row)) {
		return `${row.date}-${row.student}-${row.log_type}-${row.author}`
	}
	return `${row.date}-${row.log_type}-${row.author}`
}

function formatDate(value: string | null | undefined) {
	return value || ''
}

function stripHtml(html: string) {
	if (!html) return ''
	return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

function truncate(text: string, max = 140) {
	if (!text) return ''
	return text.length > max ? `${text.slice(0, max)}...` : text
}
</script>
