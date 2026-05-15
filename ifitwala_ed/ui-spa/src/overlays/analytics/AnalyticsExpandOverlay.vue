<!-- ifitwala_ed/ui-spa/src/overlays/analytics/AnalyticsExpandOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog as="div" class="if-overlay if-overlay--analytics-expand" @close="onDialogClose">
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap" :style="overlayStyle" @click.self="emitClose('backdrop')">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel
						class="if-overlay__panel analytics-expand__panel"
						:class="{ 'analytics-expand__panel--table': kind === 'table' }"
					>
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose('programmatic')"
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
								@click="emitClose('programmatic')"
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
								<div v-else class="type-empty">No data to display.</div>
							</div>

							<div v-else class="space-y-3">
								<div v-if="!rows.length" class="type-empty">No rows to display.</div>

								<div v-else class="overflow-auto rounded-xl border border-slate-200">
									<!-- Expanded/zoom view: body text should NOT be caption-sized -->
									<table
										class="border-collapse text-ink/90"
										:class="
											isRecentRows
												? 'w-full min-w-[1260px] table-fixed analytics-expand__table--recent'
												: 'min-w-full'
										"
									>
										<colgroup v-if="isRecentRows">
											<col style="width: 10%" />
											<col style="width: 14%" />
											<col style="width: 11%" />
											<col style="width: 11%" />
											<col style="width: 22%" />
											<col style="width: 10%" />
											<col style="width: 22%" />
										</colgroup>
										<thead class="bg-slate-50">
											<tr v-if="isRecentRows" class="border-b border-slate-200">
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Date</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Student</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Program</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Type</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Log</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Author</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">
													Follow-ups
												</th>
											</tr>
											<tr v-else class="border-b border-slate-200">
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Date</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Type</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Log</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">Author</th>
												<th class="px-3 py-2 text-left type-label text-slate-token/70">
													Follow-ups
												</th>
											</tr>
										</thead>

										<tbody class="type-body">
											<tr
												v-for="row in rows"
												:key="rowKey(row)"
												class="border-b border-slate-100 hover:bg-slate-50"
											>
												<template v-if="isRecentRow(row)">
													<td class="px-3 py-3 align-top whitespace-nowrap">
														{{ formatDate(row.date) }}
													</td>
													<td class="px-3 py-3 align-top font-medium">
														<div
															class="analytics-expand__cell-truncate"
															:title="row.student_full_name || row.student"
														>
															{{ row.student_full_name || row.student }}
														</div>
													</td>
													<td class="px-3 py-3 align-top">
														<div
															class="analytics-expand__cell-truncate"
															:title="row.program || '-'"
														>
															{{ row.program || '-' }}
														</div>
													</td>
													<td class="px-3 py-3 align-top">
														<div class="analytics-expand__cell-truncate" :title="row.log_type">
															{{ row.log_type }}
														</div>
													</td>
													<td class="px-3 py-3 align-top">
														<AnalyticsTextPreview
															class="analytics-expand__log-snippet"
															:text="stripHtml(row.content || '')"
															:lines="3"
														/>
													</td>
													<td class="px-3 py-3 align-top font-medium">
														<div class="analytics-expand__cell-truncate" :title="row.author">
															{{ row.author }}
														</div>
													</td>
													<td class="px-3 py-3 align-top">
														<div v-if="row.follow_ups.length" class="analytics-expand__followups">
															<div
																v-for="followUp in row.follow_ups"
																:key="followUp.name"
																class="analytics-expand__followup-card"
															>
																<div class="analytics-expand__followup-meta">
																	<span class="analytics-expand__followup-chip">
																		{{ followUp.doctype }}
																	</span>
																	<span v-if="followUp.next_step">
																		Next step: {{ followUp.next_step }}
																	</span>
																	<span v-if="responseMetric(followUp)">
																		{{ responseMetric(followUp) }}
																	</span>
																</div>
																<div class="analytics-expand__followup-submeta">
																	<span v-if="followUp.follow_up_author">
																		{{ followUp.follow_up_author }}
																	</span>
																	<span v-if="formatRespondedAt(followUp.responded_at)">
																		{{ formatRespondedAt(followUp.responded_at) }}
																	</span>
																</div>
																<AnalyticsTextPreview
																	v-if="followUp.comment_text"
																	class="analytics-expand__followup-comment"
																	:text="followUp.comment_text"
																	:lines="2"
																	:preview-width="520"
																/>
															</div>
														</div>
														<div v-else class="analytics-expand__followup-empty">
															{{ followUpEmptyLabel(row) }}
														</div>
													</td>
												</template>

												<template v-else>
													<td class="px-3 py-3 align-top whitespace-nowrap">
														{{ formatDate(row.date) }}
													</td>
													<td class="px-3 py-3 align-top whitespace-nowrap">
														{{ row.log_type }}
													</td>
													<td class="px-3 py-3 align-top">
														<AnalyticsTextPreview
															class="analytics-expand__log-snippet analytics-expand__log-snippet--selected"
															:text="stripHtml(row.content || '')"
															:lines="3"
														/>
													</td>
													<td class="px-3 py-3 align-top whitespace-nowrap font-medium">
														{{ row.author }}
													</td>
													<td class="px-3 py-3 align-top">
														<div v-if="row.follow_ups.length" class="analytics-expand__followups">
															<div
																v-for="followUp in row.follow_ups"
																:key="followUp.name"
																class="analytics-expand__followup-card"
															>
																<div class="analytics-expand__followup-meta">
																	<span class="analytics-expand__followup-chip">
																		{{ followUp.doctype }}
																	</span>
																	<span v-if="followUp.next_step">
																		Next step: {{ followUp.next_step }}
																	</span>
																	<span v-if="responseMetric(followUp)">
																		{{ responseMetric(followUp) }}
																	</span>
																</div>
																<div class="analytics-expand__followup-submeta">
																	<span v-if="followUp.follow_up_author">
																		{{ followUp.follow_up_author }}
																	</span>
																	<span v-if="formatRespondedAt(followUp.responded_at)">
																		{{ formatRespondedAt(followUp.responded_at) }}
																	</span>
																</div>
																<AnalyticsTextPreview
																	v-if="followUp.comment_text"
																	class="analytics-expand__followup-comment"
																	:text="followUp.comment_text"
																	:lines="2"
																	:preview-width="520"
																/>
															</div>
														</div>
														<div v-else class="analytics-expand__followup-empty">
															{{ followUpEmptyLabel(row) }}
														</div>
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
import { computed, ref } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';
import AnalyticsTextPreview from '@/components/analytics/AnalyticsTextPreview.vue';
import { formatLocalizedDateTime } from '@/lib/datetime';
import type {
	StudentLogFollowUpSummary,
	StudentLogRecentRow,
	StudentLogStudentRow,
} from '@/types/studentLogDashboard';

type ChartOption = Record<string, unknown>;
type TableRow = StudentLogRecentRow | StudentLogStudentRow;

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	title: string;
	chartOption: ChartOption;
	kind: 'chart' | 'table';
	rows?: TableRow[];
	subtitle?: string | null;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const initialFocus = ref<HTMLElement | null>(null);
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));
const rows = computed(() => props.rows ?? []);
const hasChartSeries = computed(() => {
	const option = props.chartOption;
	const series =
		option && typeof option === 'object' ? (option as { series?: unknown }).series : null;
	return Array.isArray(series) && series.length > 0;
});

const isRecentRows = computed(() => {
	const first = rows.value[0];
	return !!first && isRecentRow(first);
});

function onDialogClose(_payload: unknown) {
	// no-op by design (A+)
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

function isRecentRow(row: TableRow): row is StudentLogRecentRow {
	return 'student' in row;
}

function rowKey(row: TableRow) {
	return row.name;
}

function formatDate(value: string | null | undefined) {
	return value || '';
}

function stripHtml(html: string) {
	if (!html) return '';
	return html
		.replace(/<[^>]+>/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}

function followUpEmptyLabel(row: TableRow) {
	return row.requires_follow_up ? 'Awaiting submitted follow-up' : 'No follow-up recorded';
}

function formatRespondedAt(value: string | null | undefined) {
	return value ? formatLocalizedDateTime(value, { includeWeekday: false, month: 'short' }) : '';
}

function responseMetric(followUp: StudentLogFollowUpSummary) {
	return followUp.responded_in_label ? `Responded in ${followUp.responded_in_label}` : '';
}
</script>

<style scoped>
.analytics-expand__panel--table {
	max-width: min(96rem, calc(100vw - 3rem));
}

.analytics-expand__cell-truncate {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.analytics-expand__log-snippet {
	font-size: 1rem;
	line-height: 1.7rem;
	color: rgb(30 41 59);
}

.analytics-expand__log-snippet--selected {
	word-break: break-word;
}

.analytics-expand__followups {
	display: flex;
	flex-direction: column;
	gap: 0.65rem;
}

.analytics-expand__followup-card {
	border: 1px solid rgba(148, 163, 184, 0.22);
	border-radius: 1rem;
	padding: 0.7rem 0.8rem;
	background: linear-gradient(135deg, rgba(255, 251, 235, 0.82), rgba(255, 255, 255, 0.98)), #fff;
}

.analytics-expand__followup-meta,
.analytics-expand__followup-submeta {
	display: flex;
	flex-wrap: wrap;
	gap: 0.35rem 0.6rem;
	align-items: center;
}

.analytics-expand__followup-meta {
	font-size: 0.78rem;
	line-height: 1.1rem;
	font-weight: 600;
	color: rgb(146 64 14);
}

.analytics-expand__followup-submeta {
	margin-top: 0.28rem;
	font-size: 0.76rem;
	line-height: 1.05rem;
	color: rgb(71 85 105);
}

.analytics-expand__followup-chip {
	display: inline-flex;
	align-items: center;
	border-radius: 9999px;
	padding: 0.1rem 0.52rem;
	background: rgba(251, 191, 36, 0.18);
	color: rgb(120 53 15);
}

.analytics-expand__followup-comment {
	margin-top: 0.5rem;
	font-size: 0.84rem;
	line-height: 1.35rem;
	color: rgb(30 41 59);
}

.analytics-expand__followup-empty {
	font-size: 0.78rem;
	line-height: 1.1rem;
	color: rgb(100 116 139);
}
</style>
