<template>
	<Dialog v-model="show" :options="{ size: 'xl', title: null }">
		<template #body-content>
			<div class="history-dialog flex h-[640px] max-h-[85vh] flex-col gap-4">
				<!-- HEADER -->
				<header class="relative flex items-start justify-between gap-3 overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-white via-[rgb(var(--surface-rgb)/0.96)] to-white px-5 py-4 shadow-soft">
					<div class="absolute -left-14 -top-10 h-36 w-36 rounded-full bg-jacaranda/10 blur-3xl"></div>
					<div class="absolute -right-8 bottom-0 h-28 w-28 rounded-full bg-leaf/10 blur-3xl"></div>

					<div class="relative space-y-1">
						<p class="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-slate-token/70">
							Historical view
						</p>
						<div class="flex flex-wrap items-center gap-2">
							<h3 class="text-xl font-semibold text-ink">
								{{ titleText }}
							</h3>
							<span class="chip">
								{{ selectedRangeLabel }}
							</span>
						</div>
						<p v-if="subtitle" class="text-sm text-slate-token/80">
							{{ subtitle }}
						</p>
					</div>

					<div class="relative flex items-center gap-3">
						<div class="flex items-center gap-1 rounded-full border border-border/85 bg-white/90 px-1 py-1 shadow-inner backdrop-blur">
							<button
								v-for="range in ranges"
								:key="range.value"
								type="button"
								@click="selectedRange = range.value"
								class="rounded-full px-3 py-1.5 text-xs font-semibold transition-all"
								:class="selectedRange === range.value
									? 'bg-ink text-white shadow-sm'
									: 'text-slate-token/70 hover:text-ink hover:bg-surface-soft'"
							>
								{{ range.label }}
							</button>
						</div>

						<button
							type="button"
							@click="show = false"
							class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border/80 bg-white/90 text-slate-token/70 shadow-inner transition hover:border-jacaranda/40 hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-jacaranda/30"
							aria-label="Close history dialog"
						>
							<FeatherIcon name="x" class="h-4 w-4" />
						</button>
					</div>
				</header>

				<!-- MAIN CONTENT -->
				<section class="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
					<!-- Chart panel -->
					<div class="relative flex flex-col overflow-hidden rounded-2xl border border-border/80 bg-white/95 shadow-strong">
						<div class="flex items-center justify-between border-b border-border/70 px-5 py-3">
							<div class="space-y-0.5">
								<p class="text-xs font-semibold uppercase tracking-wide text-slate-token/70">
									Trend line
								</p>
								<p class="text-sm text-slate-token/80">
									{{ hasData ? 'Smooth curve with soft fill to catch shifts quickly.' : 'Waiting for data to render.' }}
								</p>
							</div>
							<span class="inline-flex items-center gap-1 rounded-full bg-surface-soft px-3 py-1 text-[11px] font-semibold text-slate-token/80">
								{{ totalPoints }} point<span v-if="totalPoints !== 1">s</span>
							</span>
						</div>

						<div class="relative flex-1">
							<div v-if="loading" class="absolute inset-0 z-10 flex items-center justify-center bg-white/75 backdrop-blur-sm">
								<FeatherIcon name="loader" class="h-7 w-7 animate-spin text-jacaranda" />
							</div>

							<AnalyticsChart :option="chartOption" class="h-full w-full" />
						</div>

						<div class="flex flex-wrap items-center justify-between gap-3 border-t border-border/70 bg-surface-soft/60 px-5 py-3 text-xs text-slate-token/70">
							<div class="flex items-center gap-2">
								<span class="h-2.5 w-2.5 rounded-full bg-canopy"></span>
								<span>
									Showing data for <span class="font-semibold text-ink">{{ schoolName }}</span>
								</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="h-2.5 w-2.5 rounded-full bg-jacaranda"></span>
								<span class="uppercase tracking-wide">
									{{ selectedRangeLabel }}
								</span>
							</div>
						</div>
					</div>

					<!-- Right column inspired by OrgCommunicationArchive sidebar -->
					<div class="flex h-full flex-col overflow-hidden rounded-2xl border border-border/80 bg-white shadow-soft">
						<div class="flex items-start justify-between gap-3 border-b border-border/70 bg-slate-50/60 px-4 py-3">
							<div class="space-y-1">
								<p class="text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-slate-token/70">
									Context & comments
								</p>
								<p class="text-sm text-slate-token/80">
									Matches the archive sidebar: crisp white shell, subtle borders, sticky composer.
								</p>
							</div>
							<div class="flex items-center gap-2">
								<span class="inline-flex items-center gap-1 rounded-full border border-border/70 bg-white px-3 py-1 text-[11px] font-semibold text-slate-token/80">
									{{ selectedRangeLabel }}
								</span>
								<span class="inline-flex items-center gap-1 rounded-full bg-surface-soft px-3 py-1 text-[11px] font-semibold text-slate-token/80">
									{{ totalPoints }} pts
								</span>
							</div>
						</div>

						<div class="flex-1 space-y-4 overflow-y-auto bg-white/90 p-4">
							<div class="rounded-xl border border-border/70 bg-[rgb(var(--surface-rgb)/0.95)] px-3 py-3 text-sm text-slate-token/80 shadow-inner">
								Use this panel to narrate what changed, pin action items, and keep the thread anchored to the selected slice.
							</div>

							<div class="grid grid-cols-2 gap-3">
								<div class="rounded-xl border border-border/65 bg-white/90 px-3 py-2 shadow-inner">
									<p class="text-[11px] font-semibold uppercase tracking-wide text-slate-token/70">
										Total
									</p>
									<p class="mt-1 text-xl font-semibold text-canopy">
										{{ totalCount.toLocaleString() }}
									</p>
									<p class="text-xs text-slate-token/70">
										Sum across {{ selectedRangeLabel }}
									</p>
								</div>
								<div class="rounded-xl border border-border/65 bg-white/90 px-3 py-2 shadow-inner">
									<p class="text-[11px] font-semibold uppercase tracking-wide text-slate-token/70">
										Average
									</p>
									<p class="mt-1 text-xl font-semibold text-jacaranda">
										{{ averageCount }}
									</p>
									<p class="text-xs text-slate-token/70">
										Per data point
									</p>
								</div>
							</div>

							<div class="space-y-2">
								<div class="flex items-center justify-between gap-2">
									<h4 class="text-sm font-semibold text-ink">
										Comments
									</h4>
									<span class="inline-flex items-center gap-1 rounded-full bg-surface-soft px-3 py-1 text-[11px] font-semibold text-slate-token/80">
										{{ commentCount }} {{ commentCount === 1 ? 'comment' : 'comments' }}
									</span>
								</div>

								<div class="min-h-[180px] rounded-xl border border-border/70 bg-surface-soft/70 p-3 shadow-inner">
									<div
										v-if="commentsLoading"
										class="flex h-full items-center justify-center gap-2 text-sm text-slate-token/70"
									>
										<FeatherIcon name="loader" class="h-4 w-4 animate-spin text-jacaranda" />
										Loading conversation...
									</div>
									<div
										v-else-if="!hasComments"
										class="flex h-full flex-col items-center justify-center gap-1 text-center text-slate-token/70"
									>
										<FeatherIcon name="message-circle" class="h-5 w-5 text-jacaranda" />
										<p class="text-sm">
											No comments yet. Start the thread with context or next steps.
										</p>
									</div>
									<div v-else class="flex max-h-64 flex-col gap-3 overflow-y-auto custom-scrollbar pr-1">
										<article
											v-for="(comment, index) in displayedComments"
											:key="comment.id || comment.name || index"
											class="flex gap-3 rounded-lg border border-border/70 bg-white/95 px-3 py-2 shadow-inner"
										>
											<Avatar
												:label="comment.full_name || comment.author || comment.user || 'User'"
												:image="comment.avatar"
												size="sm"
											/>
											<div class="flex min-w-0 flex-1 flex-col gap-1">
												<div class="flex items-center justify-between gap-2">
													<p class="text-sm font-semibold text-ink">
														{{ comment.full_name || comment.author || comment.user || 'User' }}
													</p>
													<span v-if="comment.timestamp || comment.creation" class="text-[11px] text-slate-token/70">
														{{ comment.timestamp || comment.creation }}
													</span>
												</div>
												<p class="text-xs leading-relaxed text-slate-token/80">
													{{ comment.note || comment.message || '' }}
												</p>
											</div>
										</article>
									</div>
								</div>
							</div>
						</div>

						<div class="sticky bottom-0 border-t border-border/70 bg-white/95 px-4 py-3 shadow-inner">
							<form class="flex flex-col gap-2 sm:flex-row sm:items-end" @submit.prevent="submitComment">
								<label class="sr-only" for="history-comment">Add a comment</label>
								<textarea
									id="history-comment"
									v-model="commentDraft"
									rows="2"
									class="flex-1 rounded-xl border border-border/70 bg-white/90 px-3 py-2 text-sm text-ink shadow-inner focus:border-jacaranda/60 focus:outline-none focus:ring-2 focus:ring-jacaranda/25"
									placeholder="Summarize what changed, tag a teammate, or capture a next step."
								/>
								<button
									type="submit"
									class="inline-flex items-center justify-center gap-2 rounded-full bg-canopy px-4 py-2 text-xs font-semibold text-white shadow-soft transition hover:bg-canopy/90 focus:outline-none focus:ring-2 focus:ring-leaf/40 disabled:cursor-not-allowed disabled:bg-slate-300"
									:disabled="!commentDraft.trim()"
								>
									<FeatherIcon name="send" class="h-4 w-4" />
									Send
								</button>
							</form>
							<p class="mt-2 text-[11px] text-slate-token/70">
								Shared with your team; keep notes concise and actionable.
							</p>
						</div>
					</div>
				</section>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Avatar, Dialog, FeatherIcon, createResource } from 'frappe-ui'
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'

type HistoryComment = {
	id?: string | number
	name?: string
	author?: string
	full_name?: string
	user?: string
	avatar?: string
	timestamp?: string
	creation?: string
	note?: string
	message?: string
	role?: string
}

const props = defineProps<{
	modelValue: boolean
	subtitle?: string
	method: string
	color?: string
	params?: Record<string, any>
	title?: string
	comments?: HistoryComment[]
	loadingComments?: boolean
}>()

const emit = defineEmits<{
	(event: 'update:modelValue', value: boolean): void
	(event: 'submit-comment', value: string): void
}>()

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
})

const titleText = computed(() => props.title || 'History view')

const ranges: Array<{ label: string; value: string }> = [
	{ label: '1M', value: '1M' },
	{ label: '3M', value: '3M' },
	{ label: '6M', value: '6M' },
	{ label: 'YTD', value: 'YTD' },
]

const selectedRange = ref('1M')

// Resource
const resource = createResource({
	url: props.method,
	makeParams() {
		return {
			time_range: selectedRange.value,
			...(props.params || {})
		}
	},
	auto: false
})

const loading = computed(() => resource.loading)
const schoolName = computed(() => resource.data?.school || 'Loading...')
const totalPoints = computed(() => resource.data?.data?.length || 0)
const totalCount = computed(() => {
	const data = resource.data?.data || []
	return data.reduce((sum: number, entry: any) => sum + Number(entry.count || 0), 0)
})
const averageCount = computed(() => {
	if (!totalPoints.value) return 0
	return Number((totalCount.value / totalPoints.value).toFixed(1))
})
const hasData = computed(() => totalPoints.value > 0)
const selectedRangeLabel = computed(
	() => ranges.find((range) => range.value === selectedRange.value)?.label || selectedRange.value
)

const displayedComments = computed<HistoryComment[]>(() => props.comments || [])
const commentCount = computed(() => displayedComments.value.length)
const hasComments = computed(() => commentCount.value > 0)
const commentsLoading = computed(() => props.loadingComments ?? false)
const commentDraft = ref('')

// Watch for open to fetch
watch(show, (isOpen) => {
	if (isOpen) {
		resource.fetch()
	}
})

// Watch for range change to refetch
watch(selectedRange, () => {
	if (show.value) {
		resource.fetch()
	}
})

function submitComment() {
	const note = commentDraft.value.trim()
	if (!note) return
	emit('submit-comment', note)
	commentDraft.value = ''
}

// Chart Option
const chartOption = computed(() => {
	const data = resource.data?.data || []
	const dates = data.map((d: any) => d.date)
	const counts = data.map((d: any) => d.count)

	// Use prop color or default to Jacaranda token
	const baseColor = props.color || '#7e6bd6'

	// Convert hex to rgba for area style
	let r = 0, g = 0, b = 0
	if (baseColor.length === 7) {
		r = parseInt(baseColor.slice(1, 3), 16)
		g = parseInt(baseColor.slice(3, 5), 16)
		b = parseInt(baseColor.slice(5, 7), 16)
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
			containLabel: true
		},
		xAxis: {
			type: 'category',
			data: dates,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: '#475569', fontSize: 11 }
		},
		yAxis: {
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed', color: 'rgba(226, 232, 240, 0.85)' }
			},
			axisLabel: { color: '#475569', fontSize: 11 }
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
						x: 0, y: 0, x2: 0, y2: 1,
						colorStops: [
							{ offset: 0, color: `rgba(${r}, ${g}, ${b}, 0.22)` },
							{ offset: 1, color: `rgba(${r}, ${g}, ${b}, 0)` }
						]
					}
				}
			}
		]
	}
})

</script>
