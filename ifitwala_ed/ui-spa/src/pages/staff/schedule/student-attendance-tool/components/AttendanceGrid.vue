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

						<div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
							<span class="rounded-full bg-slate-100 px-2 py-1 font-medium text-slate-600">
								{{ student.student }}
							</span>

							<button
								v-if="student.medical_info"
								type="button"
								class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 font-medium text-red-600 hover:bg-red-100"
								@click="$emit('show-medical', student)"
							>
								<FeatherIcon name="stethoscope" class="h-3.5 w-3.5" />
								<span>{{ __('Health note') }}</span>
							</button>

							<span
								v-if="isBirthdaySoon(student.birth_date)"
								class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 font-medium text-amber-700"
							>
								<FeatherIcon name="gift" class="h-3.5 w-3.5" />
								{{ __('Birthday soon') }}
							</span>
						</div>
					</div>
				</div>

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
									:title="code.attendance_code_name || code.name"
									class="inline-flex items-center justify-center rounded-full border px-3 py-1 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed"
									:class="chipClass(student.attendance[block] === code.name)"
									:style="chipStyle(code, student.attendance[block] === code.name)"
									:disabled="disabled"
									@click="$emit('change-code', { studentId: student.student, block, code: code.name })"
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
</template>

<script setup lang="ts">
import { Button, FeatherIcon } from 'frappe-ui'
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
	(event: 'show-medical', student: StudentRosterEntry): void
}>()

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

function chipClass(isSelected: boolean) {
	return isSelected
		? 'text-white shadow-sm'
		: 'bg-white text-slate-600 hover:bg-blue-50 hover:text-blue-600'
}

function chipStyle(code: AttendanceCode, isSelected: boolean) {
	const color = props.codeColors?.[code.name] || code.color || fallbackColor
	if (isSelected) {
		return {
			backgroundColor: color,
			borderColor: color,
		}
	}
	return {
		borderColor: color,
		color,
	}
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
	} catch (error) {
		console.warn('Failed to parse birth date', birthDate, error)
		return false
	}
}

function studentHasRemark(student: StudentRosterEntry) {
	return props.blocks.some((block) => !!(student.remarks?.[block]))
}

function firstRemark(student: StudentRosterEntry) {
	for (const block of props.blocks) {
		const text = student.remarks?.[block]
		if (text) {
			return text
		}
	}
	return ''
}

function truncate(text?: string, limit = 60) {
	if (!text) return ''
	return text.length > limit ? `${text.slice(0, limit)}…` : text
}
</script>
