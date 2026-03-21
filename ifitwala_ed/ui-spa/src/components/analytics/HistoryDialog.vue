<!-- ifitwala_ed/ui-spa/src/components/analytics/HistoryDialog.vue -->
<template>
	<Teleport to="body">
		<TransitionRoot as="template" :show="show">
			<Dialog
				as="div"
				class="if-overlay if-overlay--morning-brief-history"
				:initialFocus="closeButtonRef"
				@close="onDialogClose"
			>
				<TransitionChild
					as="template"
					enter="if-overlay__fade-enter"
					enter-from="if-overlay__fade-from"
					enter-to="if-overlay__fade-to"
					leave="if-overlay__fade-leave"
					leave-from="if-overlay__fade-to"
					leave-to="if-overlay__fade-from"
				>
					<div class="if-overlay__backdrop" @click="closeDialog" />
				</TransitionChild>

				<div class="if-overlay__wrap history-dialog__wrap" @click.self="closeDialog">
					<TransitionChild
						as="template"
						enter="if-overlay__panel-enter"
						enter-from="if-overlay__panel-from"
						enter-to="if-overlay__panel-to"
						leave="if-overlay__panel-leave"
						leave-from="if-overlay__panel-to"
						leave-to="if-overlay__panel-from"
					>
						<DialogPanel class="if-overlay__panel history-dialog__panel">
							<header class="history-dialog__header">
								<div class="history-dialog__headline">
									<p class="type-overline history-dialog__eyebrow">
										{{ __('Historical view') }}
									</p>
									<DialogTitle class="type-h2 text-ink mt-2">
										{{ titleText }}
									</DialogTitle>
									<p v-if="subtitle" class="type-caption mt-2 text-ink/65">
										{{ subtitle }}
									</p>
								</div>

								<div class="history-dialog__header-actions">
									<DateRangePills
										v-model="selectedRange"
										:items="ranges"
										size="sm"
										wrap-class="history-dialog__range-group"
									/>

									<button
										ref="closeButtonRef"
										type="button"
										class="if-overlay__icon-button"
										aria-label="Close history dialog"
										@click="closeDialog"
									>
										<FeatherIcon name="x" class="h-4 w-4" />
									</button>
								</div>
							</header>

							<section class="if-overlay__body history-dialog__body">
								<section class="history-dialog__summary-grid">
									<div class="history-dialog__stat-card">
										<p class="history-dialog__stat-label">{{ __('School') }}</p>
										<p class="history-dialog__stat-value text-canopy">{{ schoolName }}</p>
									</div>
									<div class="history-dialog__stat-card">
										<p class="history-dialog__stat-label">{{ __('Points') }}</p>
										<p class="history-dialog__stat-value text-jacaranda">{{ totalPoints }}</p>
									</div>
									<div class="history-dialog__stat-card">
										<p class="history-dialog__stat-label">{{ __('Total') }}</p>
										<p class="history-dialog__stat-value">{{ totalCount.toLocaleString() }}</p>
									</div>
									<div class="history-dialog__stat-card">
										<p class="history-dialog__stat-label">{{ __('Average') }}</p>
										<p class="history-dialog__stat-value">{{ averageCount }}</p>
									</div>
								</section>

								<section class="history-dialog__content-grid">
									<div class="history-dialog__chart-card">
										<div class="history-dialog__card-head">
											<div>
												<p
													class="text-xs font-semibold uppercase tracking-wide text-slate-token/70"
												>
													{{ __('Trend line') }}
												</p>
												<p class="mt-1 text-sm text-slate-token/80">
													{{
														errorMessage
															? __('The history request failed. Review the message below.')
															: hasData
																? __('Read the recent movement at a glance.')
																: __('Waiting for enough data to draw the trend.')
													}}
												</p>
											</div>
											<span class="history-dialog__card-pill">
												{{ selectedRangeLabel }}
											</span>
										</div>

										<div class="history-dialog__chart-frame">
											<div v-if="loading" class="history-dialog__chart-loading">
												<FeatherIcon name="loader" class="h-7 w-7 animate-spin text-jacaranda" />
											</div>
											<div v-else-if="errorMessage" class="history-dialog__chart-empty">
												<FeatherIcon name="alert-circle" class="h-5 w-5 text-flame" />
												<span>{{ errorMessage }}</span>
											</div>
											<div v-else-if="isEmpty" class="history-dialog__chart-empty">
												<FeatherIcon name="bar-chart-2" class="h-5 w-5 text-jacaranda" />
												<span>{{
													__('No business-day clinic data is available for this range yet.')
												}}</span>
											</div>
											<AnalyticsChart v-else :option="chartOption" class="h-full w-full" />
										</div>
									</div>

									<div class="history-dialog__context-card">
										<div class="history-dialog__card-head">
											<div>
												<p
													class="text-xs font-semibold uppercase tracking-wide text-slate-token/70"
												>
													{{ __('Context & comments') }}
												</p>
												<p class="mt-1 text-sm text-slate-token/80">
													{{ __('Capture shifts, explanations, and next steps for this metric.') }}
												</p>
											</div>
											<span class="history-dialog__card-pill">
												{{ commentCount }}
												{{ commentCount === 1 ? __('comment') : __('comments') }}
											</span>
										</div>

										<div class="history-dialog__comment-stream custom-scrollbar">
											<div class="history-dialog__context-note">
												{{
													__(
														'Shared with your team. Keep notes concise, specific, and actionable.'
													)
												}}
											</div>

											<div v-if="commentsLoading" class="history-dialog__comments-empty">
												<FeatherIcon name="loader" class="h-4 w-4 animate-spin text-jacaranda" />
												<span>{{ __('Loading conversation...') }}</span>
											</div>
											<div v-else-if="!hasComments" class="history-dialog__comments-empty">
												<FeatherIcon name="message-circle" class="h-5 w-5 text-jacaranda" />
												<span>{{
													__('No comments yet. Start the thread with context or a next step.')
												}}</span>
											</div>
											<div v-else class="space-y-3">
												<article
													v-for="(comment, index) in displayedComments"
													:key="comment.id || comment.name || index"
													class="history-dialog__comment-card"
												>
													<Avatar
														:label="comment.full_name || comment.author || comment.user || 'User'"
														:image="comment.avatar"
														size="sm"
													/>
													<div class="min-w-0 flex-1">
														<div class="flex items-center justify-between gap-2">
															<p class="text-sm font-semibold text-ink">
																{{ comment.full_name || comment.author || comment.user || 'User' }}
															</p>
															<span
																v-if="comment.timestamp || comment.creation"
																class="text-[11px] text-slate-token/70"
															>
																{{ comment.timestamp || comment.creation }}
															</span>
														</div>
														<p class="mt-1 text-xs leading-relaxed text-slate-token/82">
															{{ comment.note || comment.message || '' }}
														</p>
													</div>
												</article>
											</div>
										</div>

										<form class="history-dialog__composer" @submit.prevent="submitComment">
											<label class="sr-only" for="history-comment">{{
												__('Add a comment')
											}}</label>
											<textarea
												id="history-comment"
												v-model="commentDraft"
												rows="2"
												class="history-dialog__textarea"
												:placeholder="
													__('Summarize what changed, tag a teammate, or capture a next step.')
												"
											/>
											<div class="flex justify-end">
												<button
													type="submit"
													class="history-dialog__submit-button"
													:disabled="!commentDraft.trim()"
												>
													<FeatherIcon name="send" class="h-4 w-4" />
													{{ __('Send') }}
												</button>
											</div>
										</form>
									</div>
								</section>
							</section>
						</DialogPanel>
					</TransitionChild>
				</div>
			</Dialog>
		</TransitionRoot>
	</Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { Avatar, FeatherIcon, createResource } from 'frappe-ui';
import { __ } from '@/lib/i18n';
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';
import DateRangePills from '@/components/filters/DateRangePills.vue';

type HistoryComment = {
	id?: string | number;
	name?: string;
	author?: string;
	full_name?: string;
	user?: string;
	avatar?: string;
	timestamp?: string;
	creation?: string;
	note?: string;
	message?: string;
	role?: string;
};

const props = defineProps<{
	modelValue: boolean;
	subtitle?: string;
	method: string;
	color?: string;
	params?: Record<string, any>;
	title?: string;
	comments?: HistoryComment[];
	loadingComments?: boolean;
	rangeOptions?: ReadonlyArray<{ label: string; value: string }>;
	defaultRange?: string;
}>();

const emit = defineEmits<{
	(event: 'update:modelValue', value: boolean): void;
	(event: 'submit-comment', value: string): void;
}>();

const closeButtonRef = ref<HTMLButtonElement | null>(null);

const show = computed({
	get: () => props.modelValue,
	set: value => emit('update:modelValue', value),
});

const titleText = computed(() => props.title || __('History view'));

const defaultRanges: ReadonlyArray<{ label: string; value: string }> = [
	{ label: '1M', value: '1M' },
	{ label: '3M', value: '3M' },
	{ label: '6M', value: '6M' },
	{ label: 'YTD', value: 'YTD' },
];

const ranges = computed(() => (props.rangeOptions?.length ? props.rangeOptions : defaultRanges));
const selectedRange = ref(props.defaultRange || ranges.value[0]?.value || '1M');
const commentDraft = ref('');

const resource = createResource({
	url: props.method,
	makeParams() {
		return {
			time_range: selectedRange.value,
			...(props.params || {}),
		};
	},
	auto: false,
});

const loading = computed(() => resource.loading);
const errorMessage = computed(() => {
	const err = resource.error;
	if (!err) return '';
	if (typeof err === 'string') return err;
	if (err instanceof Error) return err.message || __('Unable to load history.');
	if (err && typeof err === 'object' && 'message' in err) {
		const message = typeof err.message === 'string' ? err.message : '';
		return message || __('Unable to load history.');
	}
	return __('Unable to load history.');
});
const schoolName = computed(() => {
	if (errorMessage.value) return __('Unavailable');
	return resource.data?.school || __('Loading...');
});
const totalPoints = computed(() => resource.data?.data?.length || 0);
const totalCount = computed(() => {
	const data = resource.data?.data || [];
	return data.reduce((sum: number, entry: any) => sum + Number(entry.count || 0), 0);
});
const averageCount = computed(() => {
	if (!totalPoints.value) return 0;
	return Number((totalCount.value / totalPoints.value).toFixed(1));
});
const hasData = computed(() => totalPoints.value > 0);
const isEmpty = computed(() => !loading.value && !errorMessage.value && !hasData.value);
const selectedRangeLabel = computed(
	() =>
		ranges.value.find(range => range.value === selectedRange.value)?.label || selectedRange.value
);

const displayedComments = computed<HistoryComment[]>(() => props.comments || []);
const commentCount = computed(() => displayedComments.value.length);
const hasComments = computed(() => commentCount.value > 0);
const commentsLoading = computed(() => props.loadingComments ?? false);

function closeDialog() {
	show.value = false;
}

function onDialogClose(_payload: unknown) {
	// Explicit close paths only.
}

watch(show, isOpen => {
	if (isOpen) {
		resource.fetch();
	}
});

watch(selectedRange, () => {
	if (show.value) {
		resource.fetch();
	}
});

watch(
	() => props.defaultRange,
	value => {
		if (typeof value === 'string' && value && value !== selectedRange.value) {
			selectedRange.value = value;
		}
	}
);

function submitComment() {
	const note = commentDraft.value.trim();
	if (!note) return;
	emit('submit-comment', note);
	commentDraft.value = '';
}

function onKeydown(event: KeyboardEvent) {
	if (!show.value) return;
	if (event.key === 'Escape') closeDialog();
}

onMounted(() => {
	document.addEventListener('keydown', onKeydown, true);
});

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});

const chartOption = computed(() => {
	const data = resource.data?.data || [];
	const dates = data.map((d: any) => d.date);
	const counts = data.map((d: any) => d.count);

	const baseColor = props.color || '#7e6bd6';

	let r = 0;
	let g = 0;
	let b = 0;
	if (baseColor.length === 7) {
		r = parseInt(baseColor.slice(1, 3), 16);
		g = parseInt(baseColor.slice(3, 5), 16);
		b = parseInt(baseColor.slice(5, 7), 16);
	}

	return {
		tooltip: {
			trigger: 'axis',
			className: 'chart-tooltip',
		},
		grid: {
			top: 30,
			right: 20,
			bottom: 30,
			left: 40,
			containLabel: true,
		},
		xAxis: {
			type: 'category',
			data: dates,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: '#475569', fontSize: 11 },
		},
		yAxis: {
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed', color: 'rgba(226, 232, 240, 0.85)' },
			},
			axisLabel: { color: '#475569', fontSize: 11 },
		},
		series: [
			{
				data: counts,
				type: 'line',
				smooth: true,
				symbol: 'circle',
				symbolSize: 6,
				itemStyle: { color: baseColor },
				lineStyle: { width: 3, color: baseColor },
				areaStyle: {
					color: {
						type: 'linear',
						x: 0,
						y: 0,
						x2: 0,
						y2: 1,
						colorStops: [
							{ offset: 0, color: `rgba(${r}, ${g}, ${b}, 0.22)` },
							{ offset: 1, color: `rgba(${r}, ${g}, ${b}, 0)` },
						],
					},
				},
			},
		],
	};
});
</script>

<style scoped>
.history-dialog__wrap {
	align-items: center;
}

.history-dialog__panel {
	max-width: min(82rem, calc(100vw - 1.5rem));
}

.history-dialog__header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	padding: 1.4rem 1.5rem;
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.65);
	background:
		radial-gradient(circle at top left, rgb(var(--jacaranda-rgb) / 0.12), transparent 34%),
		radial-gradient(circle at top right, rgb(var(--leaf-rgb) / 0.14), transparent 36%),
		linear-gradient(180deg, rgb(var(--surface-rgb) / 0.98), rgb(var(--surface-strong-rgb) / 1));
}

.history-dialog__headline {
	min-width: 0;
}

.history-dialog__eyebrow {
	color: rgb(var(--slate-rgb) / 0.74);
}

.history-dialog__header-actions {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.history-dialog__range-group {
	display: flex;
	flex-wrap: wrap;
	gap: 0.4rem;
	justify-content: flex-end;
}

.history-dialog__range-chip {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border-radius: 9999px;
	border: 1px solid rgb(var(--border-rgb) / 0.8);
	background: rgb(var(--surface-strong-rgb) / 0.95);
	padding: 0.48rem 0.8rem;
	font-size: 0.76rem;
	font-weight: 700;
	color: rgb(var(--slate-rgb) / 0.82);
	transition:
		border-color 120ms ease,
		background 120ms ease,
		color 120ms ease;
}

.history-dialog__range-chip--active {
	border-color: rgb(var(--ink-rgb) / 0.15);
	background: rgb(var(--ink-rgb) / 0.96);
	color: white;
}

.history-dialog__body {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	padding: 1.25rem;
	background: linear-gradient(
		180deg,
		rgb(var(--surface-rgb) / 0.76),
		rgb(var(--surface-strong-rgb) / 0.95)
	);
}

.history-dialog__summary-grid {
	display: grid;
	gap: 0.85rem;
	grid-template-columns: repeat(4, minmax(0, 1fr));
}

.history-dialog__stat-card {
	border-radius: 1.15rem;
	border: 1px solid rgb(var(--border-rgb) / 0.72);
	background: rgb(var(--surface-strong-rgb) / 0.96);
	padding: 0.95rem 1rem;
	box-shadow: var(--shadow-soft);
}

.history-dialog__stat-label {
	font-size: 0.72rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: rgb(var(--slate-rgb) / 0.72);
}

.history-dialog__stat-value {
	margin-top: 0.45rem;
	font-size: 1.15rem;
	font-weight: 700;
	color: rgb(var(--ink-rgb) / 0.94);
}

.history-dialog__content-grid {
	display: grid;
	gap: 1rem;
	grid-template-columns: minmax(0, 1.65fr) minmax(22rem, 1fr);
	min-height: 0;
}

.history-dialog__chart-card,
.history-dialog__context-card {
	display: flex;
	flex-direction: column;
	min-height: 0;
	border-radius: 1.5rem;
	border: 1px solid rgb(var(--border-rgb) / 0.72);
	background: rgb(var(--surface-strong-rgb) / 0.96);
	box-shadow: var(--shadow-soft);
}

.history-dialog__card-head {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 1rem 1.1rem;
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.62);
}

.history-dialog__card-pill {
	display: inline-flex;
	align-items: center;
	border-radius: 9999px;
	background: rgb(var(--surface-rgb) / 0.92);
	padding: 0.45rem 0.8rem;
	font-size: 0.72rem;
	font-weight: 700;
	color: rgb(var(--slate-rgb) / 0.78);
}

.history-dialog__chart-frame {
	position: relative;
	flex: 1;
	min-height: 22rem;
	padding: 0.75rem 1rem 1rem;
}

.history-dialog__chart-loading {
	position: absolute;
	inset: 0;
	z-index: 10;
	display: flex;
	align-items: center;
	justify-content: center;
	background: rgb(var(--surface-strong-rgb) / 0.7);
	backdrop-filter: blur(4px);
}

.history-dialog__chart-empty {
	display: flex;
	height: 100%;
	min-height: 14rem;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 0.65rem;
	border: 1px dashed rgb(var(--border-rgb) / 0.78);
	border-radius: 1.15rem;
	background: rgb(var(--surface-rgb) / 0.72);
	padding: 1rem;
	text-align: center;
	font-size: 0.86rem;
	color: rgb(var(--slate-rgb) / 0.82);
}

.history-dialog__comment-stream {
	flex: 1;
	min-height: 0;
	overflow-y: auto;
	padding: 1rem;
}

.history-dialog__context-note {
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.65);
	background: rgb(var(--surface-rgb) / 0.86);
	padding: 0.85rem 0.95rem;
	font-size: 0.82rem;
	color: rgb(var(--slate-rgb) / 0.8);
}

.history-dialog__comments-empty {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 0.5rem;
	min-height: 12rem;
	border-radius: 1rem;
	border: 1px dashed rgb(var(--border-rgb) / 0.8);
	background: rgb(var(--surface-rgb) / 0.72);
	padding: 1rem;
	text-align: center;
	font-size: 0.85rem;
	color: rgb(var(--slate-rgb) / 0.78);
}

.history-dialog__comment-card {
	display: flex;
	gap: 0.75rem;
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.68);
	background: rgb(var(--surface-rgb) / 0.92);
	padding: 0.85rem;
}

.history-dialog__composer {
	border-top: 1px solid rgb(var(--border-rgb) / 0.65);
	padding: 1rem;
	background: rgb(var(--surface-rgb) / 0.76);
}

.history-dialog__textarea {
	width: 100%;
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.82);
	background: rgb(var(--surface-strong-rgb) / 0.98);
	padding: 0.75rem 0.9rem;
	font-size: 0.88rem;
	color: rgb(var(--ink-rgb) / 0.95);
	box-shadow: var(--shadow-soft);
	outline: none;
	resize: vertical;
}

.history-dialog__textarea:focus {
	border-color: rgb(var(--jacaranda-rgb) / 0.45);
	box-shadow: 0 0 0 3px rgb(var(--jacaranda-rgb) / 0.16);
}

.history-dialog__submit-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 0.45rem;
	margin-top: 0.75rem;
	border-radius: 9999px;
	border: 1px solid rgb(var(--canopy-rgb) / 0.9);
	background: rgb(var(--canopy-rgb) / 0.96);
	padding: 0.6rem 1rem;
	font-size: 0.8rem;
	font-weight: 700;
	color: white;
	transition:
		transform 120ms ease,
		opacity 120ms ease;
}

.history-dialog__submit-button:hover:not(:disabled) {
	transform: translateY(-1px);
}

.history-dialog__submit-button:disabled {
	cursor: not-allowed;
	opacity: 0.45;
}

@media (max-width: 1023px) {
	.history-dialog__summary-grid,
	.history-dialog__content-grid {
		grid-template-columns: 1fr;
	}

	.history-dialog__chart-frame {
		min-height: 18rem;
	}
}

@media (max-width: 767px) {
	.history-dialog__panel {
		max-width: calc(100vw - 1rem);
		max-height: calc(100vh - 1rem);
	}

	.history-dialog__header {
		flex-direction: column;
		padding: 1rem;
	}

	.history-dialog__header-actions {
		width: 100%;
		justify-content: space-between;
	}

	.history-dialog__range-group {
		justify-content: flex-start;
	}

	.history-dialog__body {
		padding: 1rem;
	}
}
</style>
