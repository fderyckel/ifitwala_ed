<template>
	<div class="flex h-full flex-col">
		<div
			class="hidden border-b border-slate-200 bg-slate-50 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 lg:grid lg:grid-cols-[minmax(240px,1.2fr)_minmax(0,2fr)_88px]"
		>
			<span>{{ __('Student') }}</span>
			<span>{{ __('Attendance') }}</span>
			<span class="text-right">{{ __('Remark') }}</span>
		</div>

		<div v-for="student in students" :key="student.student" class="border-b border-slate-100 px-5 py-4 last:border-b-0">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:gap-6">
				<!-- Identity -->
				<div class="flex min-w-[240px] flex-1 items-center gap-3">
					<a
						:href="studentLink(student.student)"
						target="_blank"
						rel="noopener"
						class="relative inline-flex h-16 w-16 flex-shrink-0 overflow-hidden rounded-xl ring-1 ring-slate-200"
					>
						<img
							:src="student.student_image || DEFAULT_AVATAR"
							:alt="student.student_name"
							class="h-full w-full object-cover"
							loading="lazy"
							@error="onImageError"
						/>
					</a>

					<div class="min-w-0 space-y-1">
						<div class="flex flex-wrap items-center gap-2">
							<a
								:href="studentLink(student.student)"
								target="_blank"
								rel="noopener"
								class="truncate text-base font-semibold text-slate-900 hover:text-blue-600"
							>
								{{ displayName(student) }}
							</a>
							<span v-if="student.preferred_name" class="truncate text-sm text-slate-500">
								({{ student.student_name }})
							</span>
						</div>

						<!-- Alerts -->
						<div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
							<button
								v-if="hasMedicalInfo(student)"
								type="button"
								class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 font-medium text-red-600 transition hover:bg-red-100"
								@click="openPopover('health', student, $event)"
							>
								<FeatherIcon name="stethoscope" class="h-3.5 w-3.5" />
								<span>{{ __('Health note') }}</span>
							</button>

							<button
								v-if="isBirthdaySoon(student.birth_date)"
								type="button"
								class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 font-medium text-amber-700 transition hover:bg-amber-100"
								@click="openPopover('birthday', student, $event)"
							>
								<span role="img" aria-hidden="true">🎂</span>
								{{ __('Birthday') }}
							</button>
						</div>
					</div>
				</div>

				<!-- Attendance controls -->
				<div class="flex flex-1 flex-col gap-4">
					<div
						v-for="block in blocks"
						:key="`${student.student}-${block}`"
						class="flex flex-col gap-3 rounded-xl border border-slate-100 bg-slate-50/70 p-3 shadow-inner sm:flex-row sm:items-center sm:justify-between"
					>
						<div class="flex flex-wrap items-center gap-2">
							<span class="text-xs font-medium uppercase tracking-wide text-slate-500">
								{{ blockLabel(block) }}
							</span>
						</div>

						<div class="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<div class="flex flex-wrap items-center gap-2">
								<button
									v-for="code in codes"
									:key="code.name"
									type="button"
									class="inline-flex items-center justify-center rounded-full border px-3 py-1 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed"
									:class="chipClass(student.attendance[block] === code.name)"
									:style="chipStyle(code, student.attendance[block] === code.name)"
									:disabled="disabled"
									@click="$emit('change-code', { studentId: student.student, block, code: code.name })"
									:aria-pressed="student.attendance[block] === code.name"
								>
									{{ code.attendance_code || (code.attendance_code_name || code.name)?.charAt(0) }}
								</button>
							</div>

							<div class="flex items-center gap-2">
								<Button
									appearance="minimal"
									icon="message-circle"
									class="!h-9 !w-9 rounded-full border border-transparent text-slate-500 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
									:class="student.remarks?.[block] ? '!border-blue-200 !bg-blue-50 !text-blue-600' : ''"
									:title="student.remarks?.[block] ? __('Edit remark') : __('Add remark')"
									:disabled="disabled"
									@click="$emit('open-remark', { student, block })"
								/>
								<p v-if="student.remarks?.[block]" class="hidden text-xs text-slate-500 sm:inline">
									{{ truncate(student.remarks?.[block]) }}
								</p>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Mobile remark block -->
			<div
				v-if="studentHasRemark(student)"
				class="mt-3 rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3 text-sm text-slate-600 lg:hidden"
			>
				<strong class="block text-xs font-semibold uppercase tracking-wide text-blue-500">
					{{ __('Remark') }}
				</strong>
				{{ firstRemark(student) }}
			</div>
		</div>
	</div>

	<!-- POPOVER (anchored white card) -->
	<div
		v-if="popover.open"
		ref="popEl"
		:style="popoverInlineStyle"
		class="fixed z-50 max-w-[32rem] rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-xl ring-1 ring-black/5"
		role="dialog"
		aria-modal="true"
	>
		<div class="mb-2 flex items-center gap-2">
			<span class="inline-block h-2.5 w-2.5 rounded-full" :class="popover.type === 'health' ? 'bg-red-500' : 'bg-amber-500'" />
			<h3 class="text-sm font-semibold text-slate-900">
				{{ popoverTitle }}
			</h3>
			<button
				type="button"
				class="ml-auto inline-flex h-7 w-7 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-600"
				@click="closePopover"
				aria-label="Close"
			>
				<FeatherIcon name="x" class="h-4 w-4" />
			</button>
		</div>

		<p class="leading-relaxed whitespace-pre-line">
			{{ popoverBody }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
import { __ } from '@/lib/i18n'
import type { AttendanceCode, StudentRosterEntry, BlockKey } from '../types'

const DEFAULT_AVATAR = '/assets/ifitwala_ed/images/default_student_image.png'

const props = defineProps<{
	students: StudentRosterEntry[]
	blocks: BlockKey[]
	codes: AttendanceCode[]
	disabled?: boolean
	codeColors?: Record<string, string>
}>()

defineEmits<{
	(event: 'change-code', payload: { studentId: string; block: BlockKey; code: string }): void
	(event: 'open-remark', payload: { student: StudentRosterEntry; block: BlockKey }): void
}>()

/* ------------------- Popover state & behavior ------------------- */
const popEl = ref<HTMLElement | null>(null)

type PopType = 'health' | 'birthday'
const popover = ref<{
	open: boolean
	type: PopType | null
	student: StudentRosterEntry | null
	anchorEl: HTMLElement | null
	left: number
	top: number
}>({
	open: false,
	type: null,
	student: null,
	anchorEl: null,
	left: 0,
	top: 0,
})

async function openPopover(type: PopType, student: StudentRosterEntry, evt: MouseEvent) {
	const target = evt.currentTarget as HTMLElement
	popover.value.open = true
	popover.value.type = type
	popover.value.student = student
	popover.value.anchorEl = target
	await nextTick()
	positionPopover() // measure and place after DOM paints
}

function closePopover() {
	popover.value.open = false
	popover.value.anchorEl = null
}

/* Smart positioning: center over anchor, flip above if needed, clamp to viewport */
function positionPopover() {
	if (!popover.value.open || !popover.value.anchorEl) return
	const el = popEl.value
	if (!el) return

	const anchor = popover.value.anchorEl.getBoundingClientRect()
	const tip = el.getBoundingClientRect()

	const margin = 12 // min viewport margin
	const gap = 8 // space from anchor

	const vw = window.innerWidth
	const vh = window.innerHeight

	// Desired centered position (viewport coords; popover is position: fixed)
	let left = anchor.left + anchor.width / 2 - tip.width / 2
	left = Math.max(margin, Math.min(left, vw - tip.width - margin))

	// Default below
	let top = anchor.bottom + gap

	// If bottom clips, flip above
	if (top + tip.height > vh - margin) {
		top = anchor.top - gap - tip.height
	}

	// If flipping still clips top, clamp
	if (top < margin) top = margin

	popover.value.left = Math.round(left)
	popover.value.top = Math.round(top)
}

/* Keep it positioned on scroll/resize */
function onScrollOrResize() {
	if (!popover.value.open) return
	positionPopover()
}

/* Close on outside click / Esc */
function onDocClick(e: MouseEvent) {
	if (!popover.value.open) return
	const el = popEl.value
	if (!el) return
	if (e.target instanceof Node && !el.contains(e.target)) {
		// allow clicking the anchor without closing before open handler
		if (popover.value.anchorEl && popover.value.anchorEl.contains(e.target as Node)) return
		closePopover()
	}
}
function onEsc(e: KeyboardEvent) {
	if (e.key === 'Escape') closePopover()
}

onMounted(() => {
	document.addEventListener('click', onDocClick, true) // capture so initial click doesn’t close
	document.addEventListener('keydown', onEsc)
	window.addEventListener('scroll', onScrollOrResize, { passive: true })
	window.addEventListener('resize', onScrollOrResize, { passive: true })
})
onBeforeUnmount(() => {
	document.removeEventListener('click', onDocClick, true)
	document.removeEventListener('keydown', onEsc)
	window.removeEventListener('scroll', onScrollOrResize)
	window.removeEventListener('resize', onScrollOrResize)
})

const popoverInlineStyle = computed(() => ({
	left: `${popover.value.left}px`,
	top: `${popover.value.top}px`,
}))

/* ------------------- Titles & body ------------------- */
const popoverTitle = computed(() => {
	const s = popover.value.student
	if (!s) return ''
	return popover.value.type === 'health'
		? __('Health Note for {0}', [displayName(s)])
		: __('Birthday for {0}', [displayName(s)])
})

const popoverBody = computed(() => {
	const s = popover.value.student
	if (!s) return ''
	if (popover.value.type === 'health') {
		const txt = stripHtml(s.medical_info || '').replace(/&nbsp;/gi, ' ').replace(/\s+/g, ' ').trim()
		return txt || __('No details provided.')
	}
	const dob = formatDOB(s.birth_date)
	const age = s.birth_date ? ' · ' + formatAge(s.birth_date) : ''
	return (dob || '') + age
})

/* ------------------- Helpers ------------------- */
const fallbackColor = '#2563eb'

function studentLink(studentId: string) {
	return `/app/student/${studentId}`
}

function displayName(student: StudentRosterEntry) {
	return student.preferred_name || student.student_name || student.student
}

function blockLabel(block: BlockKey) {
	return block === -1 ? __('All day') : __('Block {0}', [block])
}

function hasMedicalInfo(student: StudentRosterEntry) {
	const html = student.medical_info || ''
	const text = stripHtml(html).replace(/&nbsp;/gi, '').trim()
	return text.length > 0
}

function stripHtml(input: string) {
	return String(input || '').replace(/<[^>]*>/g, ' ')
}

function formatDOB(birthDate?: string | null) {
	if (!birthDate) return ''
	try {
		return new Intl.DateTimeFormat(undefined, { dateStyle: 'long' }).format(new Date(birthDate + 'T00:00:00'))
	} catch {
		return birthDate
	}
}

function formatAge(birthDate?: string | null) {
	if (!birthDate) return ''
	try {
		const b = new Date(birthDate + 'T00:00:00')
		const t = new Date()
		let age = t.getFullYear() - b.getFullYear()
		const m = t.getMonth() - b.getMonth()
		if (m < 0 || (m === 0 && t.getDate() < b.getDate())) age--
		return `${age} ${age === 1 ? 'year' : 'years'} old`
	} catch {
		return ''
	}
}

function chipClass(isSelected: boolean) {
	return isSelected ? 'text-white shadow-sm' : 'bg-white text-slate-600 hover:bg-blue-50 hover:text-blue-600'
}

function chipStyle(code: AttendanceCode, isSelected: boolean) {
	const color = props.codeColors?.[code.name] || code.color || fallbackColor
	if (isSelected) {
		return { backgroundColor: color, borderColor: color }
	}
	return { borderColor: color, color }
}

function onImageError(event: Event) {
	const target = event.target as HTMLImageElement
	if (!target) return
	target.src = DEFAULT_AVATAR
}

function isBirthdaySoon(birthDate?: string | null) {
	if (!birthDate) return false
	try {
		const today = new Date()
		const date = new Date(birthDate)
		const thisYear = new Date(today.getFullYear(), date.getMonth(), date.getDate())
		const diff = Math.floor((thisYear.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
		return Math.abs(diff) <= 5
	} catch {
		console.warn('Failed to parse birth date', birthDate)
		return false
	}
}

function studentHasRemark(student: StudentRosterEntry) {
	return props.blocks.some((block) => !!(student.remarks?.[block]))
}

function firstRemark(student: StudentRosterEntry) {
	for (const block of props.blocks) {
		const text = student.remarks?.[block]
		if (text) return text
	}
	return ''
}

function truncate(text?: string, limit = 60) {
	if (!text) return ''
	return text.length > limit ? `${text.slice(0, limit)}…` : text
}
</script>
