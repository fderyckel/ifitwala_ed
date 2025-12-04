<template>
	<Dialog
		v-model="isOpen"
		:options="{ size: 'xl', title: null }"
		class="heatmap-dialog"
	>
		<template #body-content>
			<div class="heatmap-surface flex h-[90vh] flex-col gap-4 p-5 text-ink">
				<header class="flex flex-wrap items-center gap-4 border-b border-border/70 pb-3">
					<div class="min-w-0">
						<p class="text-sm uppercase tracking-[0.08em] text-ink/70">
							Attendance signal view
						</p>
						<h2 class="text-2xl font-semibold text-ink">
							Student heatmap
						</h2>
						<p class="mt-1 text-sm text-ink/70">
							Toggle between whole-day and per-block to see when attendance slips.
						</p>
					</div>

					<div class="ml-auto flex flex-wrap items-center gap-2">
						<div class="flex rounded-full border border-border bg-white/80 p-1 shadow-sm backdrop-blur">
							<button
								v-for="option in modeOptions"
								:key="option.value"
								@click="mode = option.value"
								class="rounded-full px-3 py-1.5 text-sm font-semibold transition"
								:class="mode === option.value
									? 'bg-ink text-white shadow-sm'
									: 'text-ink/70 hover:text-ink'"
							>
								{{ option.label }}
							</button>
						</div>

						<Button
							appearance="minimal"
							icon="x"
							@click="isOpen = false"
							class="text-ink/60"
						/>
					</div>
				</header>

				<section class="flex flex-col gap-3 rounded-xl border border-border/80 bg-white/90 p-4 shadow-sm backdrop-blur">
					<div class="grid w-full grid-cols-1 gap-3 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
						<FormControl
							type="select"
							size="md"
							:options="studentOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.student"
							placeholder="Student"
							:disabled="!studentOptions.length"
							@update:modelValue="updateFilter('student', $event)"
						/>

						<FormControl
							type="select"
							size="md"
							:options="academicYearOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.academicYear"
							placeholder="Academic year"
							:disabled="!academicYearOptions.length"
							@update:modelValue="updateFilter('academicYear', $event)"
						/>

						<div class="flex flex-col gap-2">
							<div class="flex items-center justify-between">
								<p class="text-xs font-semibold uppercase tracking-wide text-ink/70">
									Attendance codes
								</p>
								<button
									v-if="filters.codes.length"
									class="text-xs font-semibold text-jacaranda hover:underline"
									@click="filters.codes = []"
								>
									Clear
								</button>
							</div>

							<div class="flex flex-wrap gap-2">
								<button
									v-for="code in attendanceCodeOptions"
									:key="code.value || code.code"
									type="button"
									@click="toggleCode(code.value || code.code)"
									class="flex items-center gap-2 rounded-full border border-border/80 bg-slate-50/60 px-3 py-1 text-xs font-semibold transition hover:border-ink/30"
									:class="filters.codes.includes(code.value || code.code)
										? 'border-ink/60 bg-ink text-white shadow-sm'
										: 'text-ink/75'"
								>
									<span>{{ code.label || code.value || code.code }}</span>
									<span
										v-if="code.description"
										class="text-[10px] uppercase tracking-wide"
									>
										{{ code.description }}
									</span>
								</button>

								<p v-if="!attendanceCodeOptions.length" class="text-xs text-ink/60">
									Load School Attendance Codes to filter by status.
								</p>
							</div>
						</div>

						<div class="flex items-center justify-end gap-2">
							<Button
								appearance="secondary"
								icon="sliders"
								@click="advancedOpen = !advancedOpen"
								class="whitespace-nowrap"
							>
								{{ advancedOpen ? 'Hide advanced filters' : 'Advanced filters' }}
							</Button>
						</div>
					</div>

					<Transition name="fade">
						<div
							v-if="advancedOpen"
							class="grid grid-cols-1 gap-3 border-t border-border/70 pt-3 sm:grid-cols-2 lg:grid-cols-4"
						>
							<FormControl
								type="text"
								size="md"
								:model-value="filters.course"
								placeholder="Course"
								@update:modelValue="updateFilter('course', $event)"
							/>
							<FormControl
								type="text"
								size="md"
								:model-value="filters.instructor"
								placeholder="Instructor"
								@update:modelValue="updateFilter('instructor', $event)"
							/>
							<FormControl
								type="text"
								size="md"
								:model-value="filters.term"
								placeholder="Term"
								@update:modelValue="updateFilter('term', $event)"
							/>
							<FormControl
								type="text"
								size="md"
								:model-value="filters.rotationDay"
								placeholder="Rotation day"
								@update:modelValue="updateFilter('rotationDay', $event)"
							/>
						</div>
					</Transition>
				</section>

				<section class="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(280px,1fr)]">
					<div class="relative flex h-full flex-col overflow-hidden rounded-xl border border-border/80 bg-white/90 shadow-md backdrop-blur">
						<div class="flex items-center justify-between border-b border-border/70 px-4 py-3">
							<div class="flex flex-col">
								<p class="text-xs font-semibold uppercase tracking-wide text-ink/70">
									{{ mode === 'whole-day' ? 'Whole-day view' : 'Per-block view' }}
								</p>
								<p class="text-sm text-ink/75">
									{{ chartSubtitle }}
								</p>
							</div>

							<div class="flex items-center gap-2">
								<Badge
									v-if="filters.codes.length"
									variant="subtle"
									class="text-xs font-semibold text-ink"
								>
									{{ filters.codes.length }} code filter
									<span v-if="filters.codes.length > 1">s</span>
								</Badge>
								<Badge
									v-if="filters.course || filters.instructor || filters.term || filters.rotationDay"
									variant="subtle"
									class="text-xs font-semibold text-ink"
								>
									Advanced filters on
								</Badge>
							</div>
						</div>

						<div class="relative flex flex-1 flex-col">
							<div
								v-if="loading"
								class="absolute inset-0 z-10 flex items-center justify-center bg-white/70 backdrop-blur-sm"
							>
								<Spinner class="h-8 w-8 text-jacaranda" />
							</div>

							<div v-if="!hasData" class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center text-ink/70">
								<FeatherIcon name="grid" class="h-10 w-10 text-ink/30" />
								<p class="text-base font-semibold">No heatmap data to display</p>
								<p class="max-w-md text-sm">
									Adjust filters or load attendance data for this student and academic year to see signal patterns.
								</p>
							</div>

							<VChart
								v-else
								class="h-full w-full"
								:option="chartOption"
								:autoresize="{ throttle: 120 }"
							/>
						</div>
					</div>

					<aside class="flex h-full flex-col gap-4 rounded-xl border border-border/80 bg-white/95 p-4 shadow-md backdrop-blur">
						<div>
							<p class="text-xs font-semibold uppercase tracking-wide text-ink/70">
								Status legend
							</p>
							<div class="mt-3 flex flex-col gap-2">
								<div
									v-for="entry in legendEntries"
									:key="entry.key + entry.score"
									class="flex items-start gap-3 rounded-lg border border-border/70 bg-slate-50/60 px-3 py-2"
								>
									<span
										class="mt-1 h-4 w-4 rounded-full border border-ink/10"
										:style="{ backgroundColor: entry.color }"
									/>
									<div class="flex-1">
										<p class="text-sm font-semibold text-ink">
											{{ entry.label }}
										</p>
										<p class="text-xs text-ink/70">
											{{ entry.description }}
										</p>
									</div>
								</div>
							</div>
						</div>

						<div class="rounded-lg border border-border/80 bg-slate-50/60 p-3">
							<p class="text-xs font-semibold uppercase tracking-wide text-ink/70">
								What you’re seeing
							</p>
							<ul class="mt-2 space-y-1 text-sm leading-relaxed text-ink/80">
								<li v-if="mode === 'whole-day'">
									Whole-day squares aggregate all attendance codes per calendar date. Greyed cells are weekends/holidays from the school calendar; dark cells are missing records on school days.
								</li>
								<li v-else>
									Per-block squares track the student’s scheduled courses. Light grey indicates no class in that block; dark cells flag missing attendance in a scheduled class.
								</li>
								<li>
									Tooltip shows the date, status, and recorded course-level detail.
								</li>
								<li>
									Use attendance code filters to spotlight unexcused patterns or late streaks quickly.
								</li>
							</ul>
						</div>
					</aside>
				</section>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Badge, Button, Dialog, FeatherIcon, FormControl, Spinner } from 'frappe-ui'
import { VChart, type ComposeOption, type HeatmapSeriesOption } from '@/lib/echarts'

type HeatmapMode = 'whole-day' | 'per-block'
type SeverityKey = 'present' | 'unexcused' | 'excused' | 'late' | 'no_school' | 'missing' | 'neutral'

type SeverityEntry = {
	key: SeverityKey
	label: string
	description: string
	score: number
	color: string
}

type SelectOption = { label: string; value: string }

type AttendanceCodeOption = {
	label?: string
	value?: string
	code?: string
	description?: string
	severity?: SeverityKey
	severityScore?: number
}

type WholeDayPoint = {
	date: string
	week_index?: number
	weekday_index?: number
	academic_year?: string
	student?: string
	status_code?: string
	severity_score?: number
	blocks_scheduled?: number
	blocks_recorded?: number
	blocks_absent?: number
	courses_missed?: string[]
	term?: string
	rotation_day?: string
	instructor?: string
	source?: string
}

type BlockPoint = {
	date: string
	week_index?: number
	weekday_index?: number
	block_number: number
	block_label?: string
	academic_year?: string
	student?: string
	course?: string
	instructor?: string
	location?: string
	code?: string
	severity_score?: number
	status_code?: string
	minutes_late?: number
	term?: string
	rotation_day?: string
	source?: string
}

type StatusLegendEntry = { severity?: SeverityKey; label?: string; score?: number }

type ChartOption = ComposeOption<HeatmapSeriesOption>

const props = withDefaults(
	defineProps<{
		modelValue: boolean
		studentOptions?: SelectOption[]
		academicYearOptions?: SelectOption[]
		attendanceCodeOptions?: AttendanceCodeOption[]
		wholeDayPoints?: WholeDayPoint[]
		blockPoints?: BlockPoint[]
		weekdayLabels?: string[]
		blockLabels?: Record<number, string>
		selectedStudent?: string
		selectedAcademicYear?: string
		initialMode?: HeatmapMode
		loading?: boolean
		statusLegend?: Record<string, SeverityKey | StatusLegendEntry>
	}>(),
	{
		studentOptions: () => [],
		academicYearOptions: () => [],
		attendanceCodeOptions: () => [],
		wholeDayPoints: () => [],
		blockPoints: () => [],
		weekdayLabels: () => ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
		blockLabels: () => ({}),
		selectedStudent: '',
		selectedAcademicYear: '',
		initialMode: 'whole-day',
		loading: false,
		statusLegend: () => ({})
	}
)

const emit = defineEmits<{
	(event: 'update:modelValue', value: boolean): void
	(event: 'filters-change', payload: Record<string, unknown>): void
	(event: 'mode-change', mode: HeatmapMode): void
}>()

const isOpen = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
})

const modeOptions: { label: string; value: HeatmapMode }[] = [
	{ label: 'Whole-day', value: 'whole-day' },
	{ label: 'Per-block', value: 'per-block' }
]
const mode = ref<HeatmapMode>(props.initialMode)

const filters = reactive({
	student: props.selectedStudent || '',
	academicYear: props.selectedAcademicYear || '',
	codes: [] as string[],
	course: '',
	instructor: '',
	term: '',
	rotationDay: ''
})

const advancedOpen = ref(false)
const palette = ref({
	leaf: '#1f7a45',
	flame: '#f25b32',
	clay: '#b6522b',
	sand: '#f4ecdd',
	border: '#e2e8f0',
	ink: '#071019'
})

const baseSeverityScale = ref<SeverityEntry[]>([
	{
		key: 'no_school',
		label: 'No school / holiday',
		description: 'Weekend or holiday from the school calendar.',
		score: 0,
		color: '#e2e8f0'
	},
	{
		key: 'missing',
		label: 'Missing attendance',
		description: 'School day without a recorded code.',
		score: 1,
		color: 'rgba(7, 16, 25, 0.45)'
	},
	{
		key: 'present',
		label: 'Present',
		description: 'Present or no significant issue recorded.',
		score: 2,
		color: '#1f7a45'
	},
	{
		key: 'late',
		label: 'Late',
		description: 'Marked late for the day or block.',
		score: 3,
		color: '#f2a044'
	},
	{
		key: 'excused',
		label: 'Excused / mixed',
		description: 'Excused absence or mixed attendance.',
		score: 4,
		color: '#d79f42'
	},
	{
		key: 'unexcused',
		label: 'Absent (Unexcused)',
		description: 'Unexcused absence.',
		score: 5,
		color: '#f25b32'
	}
])

const severityScale = computed<SeverityEntry[]>(() => baseSeverityScale.value)
const severityByKey = computed(() => {
	return severityScale.value.reduce<Record<string, SeverityEntry>>((acc, entry) => {
		acc[entry.key] = entry
		return acc
	}, {})
})

const weekdayAxis = computed(() => props.weekdayLabels)

const normalizedWholeDayPoints = computed(() =>
	filteredWholeDayPoints.value.map((point) => {
		const severity = resolveSeverity(point.status_code, point.severity_score)
		return {
			...point,
			week_index: resolveWeekIndex(point.week_index, point.date),
			weekday_index: resolveWeekdayIndex(point.weekday_index, point.date),
			severity
		}
	})
)

const normalizedBlockPoints = computed(() =>
	filteredBlockPoints.value.map((point) => {
		const severity = resolveSeverity(point.status_code || point.code, point.severity_score)
		return {
			...point,
			week_index: resolveWeekIndex(point.week_index, point.date),
			weekday_index: resolveWeekdayIndex(point.weekday_index, point.date),
			severity
		}
	})
)

const weekAxis = computed(() => {
	const weeks = new Set<number>()
	if (mode.value === 'whole-day') {
		normalizedWholeDayPoints.value.forEach((point) => weeks.add(point.week_index || 0))
	} else {
		normalizedBlockPoints.value.forEach((point) => weeks.add(point.week_index || 0))
	}
	return Array.from(weeks).sort((a, b) => a - b)
})

const weekIndexLookup = computed(() => {
	const map = new Map<number, number>()
	weekAxis.value.forEach((week, idx) => map.set(week, idx))
	return map
})

const blockAxis = computed(() => {
	const blocks = new Set<number>()
	normalizedBlockPoints.value.forEach((point) => blocks.add(point.block_number))
	return Array.from(blocks).sort((a, b) => a - b)
})

const blockIndexLookup = computed(() => {
	const map = new Map<number, number>()
	blockAxis.value.forEach((block, idx) => map.set(block, idx))
	return map
})

const blockXAxis = computed(() => {
	const combos = new Map<string, { label: string; week: number; weekday: number }>()

	normalizedBlockPoints.value.forEach((point) => {
		const week = point.week_index || 0
		const weekday = point.weekday_index || 0
		const key = `${week}-${weekday}`
		if (!combos.has(key)) {
			const weekLabel = `W${week || '–'}`
			const dayLabel = weekdayAxis.value[weekday] || `D${weekday + 1}`
			combos.set(key, { label: `${weekLabel} · ${dayLabel}`, week, weekday })
		}
	})

	return Array.from(combos.values()).sort((a, b) => {
		if (a.week === b.week) return a.weekday - b.weekday
		return a.week - b.week
	})
})

const blockXAxisLookup = computed(() => {
	const map = new Map<string, number>()
	blockXAxis.value.forEach((item, idx) => map.set(`${item.week}-${item.weekday}`, idx))
	return map
})

const visualPieces = computed(() => {
	const used = new Map<number, SeverityEntry>()
	const addSeverity = (entry: SeverityEntry) => {
		if (!used.has(entry.score)) {
			used.set(entry.score, entry)
		}
	}

	const dataSource = mode.value === 'whole-day' ? normalizedWholeDayPoints.value : normalizedBlockPoints.value
	dataSource.forEach((point) => addSeverity(point.severity))

	severityScale.value.forEach((entry) => addSeverity(entry))

	return Array.from(used.values()).sort((a, b) => a.score - b.score).map((entry) => ({
		value: entry.score,
		label: entry.label,
		color: entry.color
	}))
})

const chartSubtitle = computed(() => {
	if (mode.value === 'whole-day') {
		return 'Calendar days stacked by week and weekday (GitHub-style).'
	}
	return 'Blocks on the Y-axis, week × day along the X-axis.'
})

const chartOption = computed<ChartOption>(() => {
	if (mode.value === 'whole-day') {
		return buildWholeDayOption()
	}
	return buildBlockOption()
})

const legendEntries = computed(() =>
	severityScale.value
		.slice()
		.sort((a, b) => a.score - b.score)
)

const hasData = computed(() =>
	mode.value === 'whole-day' ? !!normalizedWholeDayPoints.value.length : !!normalizedBlockPoints.value.length
)

const filteredWholeDayPoints = computed(() => {
	return (props.wholeDayPoints || []).filter((point) => {
		if (filters.student && point.student && point.student !== filters.student) return false
		if (filters.academicYear && point.academic_year && point.academic_year !== filters.academicYear) return false
		if (filters.codes.length && point.status_code && !filters.codes.includes(point.status_code)) return false
		if (filters.term && point.term && point.term !== filters.term) return false
		if (filters.rotationDay && point.rotation_day && point.rotation_day !== filters.rotationDay) return false
		if (filters.course && Array.isArray(point.courses_missed)) {
			const match = point.courses_missed.some((course) =>
				course.toLowerCase().includes(filters.course.toLowerCase())
			)
			if (!match) return false
		}
		if (filters.instructor && point.instructor && !point.instructor.toLowerCase().includes(filters.instructor.toLowerCase())) {
			return false
		}
		return true
	})
})

const filteredBlockPoints = computed(() => {
	return (props.blockPoints || []).filter((point) => {
		if (filters.student && point.student && point.student !== filters.student) return false
		if (filters.academicYear && point.academic_year && point.academic_year !== filters.academicYear) return false
		const statusCode = point.status_code || point.code
		if (filters.codes.length && statusCode && !filters.codes.includes(statusCode)) return false
		if (filters.course && point.course && !point.course.toLowerCase().includes(filters.course.toLowerCase())) {
			return false
		}
		if (filters.instructor && point.instructor && !point.instructor.toLowerCase().includes(filters.instructor.toLowerCase())) {
			return false
		}
		if (filters.rotationDay && point.rotation_day && point.rotation_day !== filters.rotationDay) {
			return false
		}
		if (filters.term && point.term && point.term !== filters.term) {
			return false
		}
		return true
	})
})

watch(
	() => ({ ...filters }),
	(updated) => {
		emit('filters-change', { ...updated, mode: mode.value })
	},
	{ deep: true }
)

watch(
	() => mode.value,
	(value) => emit('mode-change', value)
)

watch(
	() => props.selectedStudent,
	(value) => {
		if (value !== undefined) {
			filters.student = value
		}
	}
)

watch(
	() => props.selectedAcademicYear,
	(value) => {
		if (value !== undefined) {
			filters.academicYear = value
		}
	}
)

onMounted(() => {
	// Keep the palette in sync with design tokens so the chart respects CSS vars
	const rootStyle = getComputedStyle(document.documentElement)
	const readToken = (name: string, fallback: string) => rootStyle.getPropertyValue(name).trim() || fallback
	palette.value = {
		leaf: readToken('--leaf', palette.value.leaf),
		flame: readToken('--flame', palette.value.flame),
		clay: readToken('--clay', palette.value.clay),
		sand: readToken('--sand', palette.value.sand),
		border: readToken('--border', palette.value.border),
		ink: readToken('--ink', palette.value.ink)
	}

	// Rebuild severity scale with resolved token colors
	baseSeverityScale.value = [
		{ ...baseSeverityScale.value[0], color: palette.value.border },
		{ ...baseSeverityScale.value[1], color: toRgba(palette.value.ink, 0.45) },
		{ ...baseSeverityScale.value[2], color: palette.value.leaf },
		{ ...baseSeverityScale.value[3], color: mixColors(palette.value.flame, palette.value.sand, 0.55) },
		{ ...baseSeverityScale.value[4], color: mixColors(palette.value.clay, palette.value.sand, 0.6) },
		{ ...baseSeverityScale.value[5], color: palette.value.flame }
	]
})

function updateFilter(key: keyof typeof filters, value: any) {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	;(filters as any)[key] = value
}

function toggleCode(code?: string) {
	if (!code) return
	if (filters.codes.includes(code)) {
		filters.codes = filters.codes.filter((c) => c !== code)
	} else {
		filters.codes = [...filters.codes, code]
	}
}

function resolveWeekIndex(weekIndex: number | undefined, date: string) {
	if (Number.isFinite(weekIndex)) return Number(weekIndex)
	const parsed = new Date(date)
	if (Number.isNaN(parsed.getTime())) return 0
	const start = new Date(parsed.getFullYear(), 0, 1)
	const diff = parsed.getTime() - start.getTime()
	const day = (start.getDay() + 6) % 7
	return Math.ceil((diff / 86400000 + day + 1) / 7)
}

function resolveWeekdayIndex(weekdayIndex: number | undefined, date: string) {
	if (Number.isFinite(weekdayIndex)) return Number(weekdayIndex)
	const parsed = new Date(date)
	if (Number.isNaN(parsed.getTime())) return 0
	const jsDay = parsed.getDay() // 0 = Sunday
	return (jsDay + 6) % 7 // convert to Mon-first
}

function resolveSeverity(code?: string, severityScore?: number): SeverityEntry {
	const legendValue = code ? props.statusLegend[code] : undefined
	const mappedSeverity = typeof legendValue === 'string' ? legendValue : legendValue?.severity
	const mappedScore = typeof legendValue === 'object' ? legendValue?.score : undefined
	const mappedLabel = typeof legendValue === 'object' ? legendValue?.label : undefined
	const codeMeta = code
		? props.attendanceCodeOptions.find((option) => option.value === code || option.code === code)
		: undefined
	const optionSeverity = codeMeta?.severity
	const optionScore = codeMeta?.severityScore

	let severityKey: SeverityKey = mappedSeverity || optionSeverity || inferSeverityKey(code)
	let base = severityByKey.value[severityKey] || severityScale.value[0]

	const score = Number.isFinite(severityScore)
		? Number(severityScore)
		: mappedScore ?? optionScore ?? base.score
	if (base.score !== score) {
		base = { ...base, score }
	}

	if (mappedLabel) {
		base = { ...base, label: mappedLabel }
	}

	return base
}

function inferSeverityKey(code?: string): SeverityKey {
	if (!code) return 'missing'
	const normalized = code.toUpperCase()
	if (normalized === 'P') return 'present'
	if (normalized === 'A' || normalized === 'UA' || normalized === 'UNX') return 'unexcused'
	if (normalized === 'E' || normalized === 'EXC') return 'excused'
	if (normalized === 'L') return 'late'
	if (normalized === 'HOL' || normalized === 'NA' || normalized === 'OFF') return 'no_school'
	return 'missing'
}

function buildWholeDayOption(): ChartOption {
	const data = normalizedWholeDayPoints.value.map((point) => ({
		value: [
			weekIndexLookup.value.get(point.week_index || 0) ?? 0,
			point.weekday_index || 0,
			point.severity.score
		],
		date: point.date,
		status: point.severity.label,
		code: point.status_code,
		blocks_scheduled: point.blocks_scheduled,
		blocks_absent: point.blocks_absent,
		courses_missed: point.courses_missed,
		source: point.source
	}))

	const weeks = weekAxis.value.map((week) => `W${week || '–'}`)

	return {
		tooltip: {
			trigger: 'item',
			className: 'chart-tooltip',
			confine: true,
			formatter: (params: any) => formatWholeDayTooltip(params.data)
		},
		grid: {
			top: 30,
			left: 80,
			right: 16,
			bottom: 80,
			containLabel: true
		},
		xAxis: {
			type: 'category',
			data: weeks,
			axisLine: { lineStyle: { color: palette.value.border } },
			axisLabel: { color: 'rgba(7,16,25,0.7)' },
			splitArea: { show: true }
		},
		yAxis: {
			type: 'category',
			data: weekdayAxis.value,
			axisLine: { lineStyle: { color: palette.value.border } },
			axisLabel: { color: 'rgba(7,16,25,0.7)' },
			splitArea: { show: true }
		},
		visualMap: {
			type: 'piecewise',
			orient: 'horizontal',
			left: 'center',
			bottom: 20,
			dimension: 2,
			itemSymbol: 'rect',
			itemWidth: 14,
			itemHeight: 12,
			textStyle: { color: 'rgba(7,16,25,0.8)', fontSize: 11 },
			pieces: visualPieces.value
		},
		series: [
			{
				type: 'heatmap',
				data,
				label: { show: false },
				emphasis: {
					itemStyle: {
						shadowBlur: 12,
						shadowColor: 'rgba(7,16,25,0.22)'
					}
				}
			}
		]
	}
}

function buildBlockOption(): ChartOption {
	const data = normalizedBlockPoints.value.map((point) => {
		const axisX = blockXAxisLookup.value.get(`${point.week_index || 0}-${point.weekday_index || 0}`) ?? 0
		const axisY = blockIndexLookup.value.get(point.block_number) ?? 0
		return {
			value: [axisX, axisY, point.severity.score],
			date: point.date,
			block: point.block_number,
			block_label: point.block_label || props.blockLabels[point.block_number] || `Block ${point.block_number}`,
			code: point.code || point.status_code,
			status: point.severity.label,
			course: point.course,
			instructor: point.instructor,
			location: point.location,
			minutes_late: point.minutes_late,
			source: point.source
		}
	})

	return {
		tooltip: {
			trigger: 'item',
			className: 'chart-tooltip',
			confine: true,
			formatter: (params: any) => formatBlockTooltip(params.data)
		},
		grid: {
			top: 30,
			left: 90,
			right: 16,
			bottom: 90,
			containLabel: true
		},
		xAxis: {
			type: 'category',
			data: blockXAxis.value.map((item) => item.label),
			axisLabel: {
				color: 'rgba(7,16,25,0.7)',
				formatter: (value: string) => value,
				rotate: 35
			},
			axisLine: { lineStyle: { color: palette.value.border } },
			splitArea: { show: true }
		},
		yAxis: {
			type: 'category',
			data: blockAxis.value.map((block) => props.blockLabels[block] || `Block ${block}`),
			axisLine: { lineStyle: { color: palette.value.border } },
			axisLabel: { color: 'rgba(7,16,25,0.7)' },
			splitArea: { show: true }
		},
		visualMap: {
			type: 'piecewise',
			orient: 'horizontal',
			left: 'center',
			bottom: 30,
			dimension: 2,
			itemSymbol: 'rect',
			itemWidth: 14,
			itemHeight: 12,
			textStyle: { color: 'rgba(7,16,25,0.8)', fontSize: 11 },
			pieces: visualPieces.value
		},
		series: [
			{
				type: 'heatmap',
				data,
				label: { show: false },
				emphasis: {
					itemStyle: {
						shadowBlur: 12,
						shadowColor: 'rgba(7,16,25,0.22)'
					}
				}
			}
		]
	}
}

function formatWholeDayTooltip(data: any) {
	if (!data) return ''
	const lines: string[] = []
	lines.push(`<strong>${data.date || 'Date unknown'}</strong>`)
	const statusLine = data.status || 'Status unavailable'
	const code = data.code ? ` (${data.code})` : ''
	lines.push(`Whole-day status: ${statusLine}${code}`)

	if (Number.isFinite(data.blocks_scheduled)) {
		lines.push(`Blocks: ${data.blocks_scheduled} scheduled${Number.isFinite(data.blocks_absent) ? ` / ${data.blocks_absent} absent` : ''}`)
	}

	if (Array.isArray(data.courses_missed) && data.courses_missed.length) {
		lines.push(`Courses missed: ${data.courses_missed.join(', ')}`)
	}

	if (data.source) {
		lines.push(`Source: ${data.source}`)
	}
	return lines.join('<br/>')
}

function formatBlockTooltip(data: any) {
	if (!data) return ''
	const lines: string[] = []
	const blockLabel = data.block_label || `Block ${data.block}`
	lines.push(`<strong>${data.date || 'Date unknown'} – ${blockLabel}</strong>`)
	const statusLine = data.status || 'Status unavailable'
	const code = data.code ? ` (Code: ${data.code})` : ''
	lines.push(`Attendance: ${statusLine}${code}`)
	if (data.course) lines.push(`Course: ${data.course}`)
	if (data.instructor) lines.push(`Instructor: ${data.instructor}`)
	if (data.location) lines.push(`Location: ${data.location}`)
	if (Number.isFinite(data.minutes_late)) lines.push(`Minutes late: ${data.minutes_late}`)
	if (data.source) lines.push(`Source: ${data.source}`)
	return lines.join('<br/>')
}

function toRgba(hex: string, alpha: number) {
	const normalized = hex.replace('#', '')
	if (normalized.length !== 6) return hex
	const r = parseInt(normalized.substring(0, 2), 16)
	const g = parseInt(normalized.substring(2, 4), 16)
	const b = parseInt(normalized.substring(4, 6), 16)
	return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function mixColors(hexA: string, hexB: string, weight = 0.5) {
	const normalize = (hex: string) => hex.replace('#', '')
	const a = normalize(hexA)
	const b = normalize(hexB)
	if (a.length !== 6 || b.length !== 6) return hexA

	const mixChannel = (start: number, end: number) =>
		Math.round(start + (end - start) * weight)

	const r = mixChannel(parseInt(a.substring(0, 2), 16), parseInt(b.substring(0, 2), 16))
	const g = mixChannel(parseInt(a.substring(2, 4), 16), parseInt(b.substring(2, 4), 16))
	const h = mixChannel(parseInt(a.substring(4, 6), 16), parseInt(b.substring(4, 6), 16))

	return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${h.toString(16).padStart(2, '0')}`
}
</script>

<style scoped>
.heatmap-dialog {
	color: var(--ink);
}

.heatmap-surface {
	background: var(--modal-panel-gradient-bg);
}

.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
