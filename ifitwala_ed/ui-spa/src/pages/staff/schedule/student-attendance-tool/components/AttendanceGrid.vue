<template>
	<div class="space-y-4">
		<div
			v-for="student in students"
			:key="student.student"
			class="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300"
		>
			<div class="flex items-start gap-3">
				<img
					:src="student.student_image || DEFAULT_AVATAR"
					:alt="student.student_name"
					class="h-14 w-14 flex-shrink-0 rounded-xl object-cover ring-1 ring-slate-200"
					loading="lazy"
					@error="onImageError"
				/>

				<div class="flex w-full flex-col gap-1">
					<div class="flex flex-wrap items-center gap-2">
						<p class="text-base font-semibold text-slate-900">
							{{ student.preferred_name || student.student_name }}
						</p>
						<p v-if="student.preferred_name" class="text-sm text-slate-500">
							({{ student.student_name }})
						</p>
						<a
							:href="`/app/student/${student.student}`"
							target="_blank"
							rel="noopener"
							class="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600 hover:bg-slate-200"
						>
							{{ student.student }}
						</a>

                        <button
                            v-if="student.medical_info"
                            type="button"
                            class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 text-xs text-red-600 hover:bg-red-100"
                            @click="$emit('show-medical', student)"
                        >
                            <FeatherIcon name="stethoscope" class="h-3.5 w-3.5" />
                            <span>{{ __('Health note') }}</span>
                        </button>

                        <span
                            v-if="isBirthdaySoon(student.birth_date)"
                            class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-700"
                        >
                            <FeatherIcon name="cake" class="h-3.5 w-3.5" />
                            {{ __('Birthday soon') }}
                        </span>
					</div>

					<div class="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
						<div
							v-for="block in blocks"
							:key="`${student.student}-${block}`"
							class="rounded-xl border border-slate-100 bg-slate-50/70 p-3"
						>
							<div class="flex items-center justify-between gap-2">
								<span class="text-xs font-medium uppercase tracking-wide text-slate-500">
									{{ blockLabel(block) }}
								</span>

								<span
									v-if="student.attendance[block]"
									class="inline-flex h-2 w-2 rounded-full"
									:style="dotStyle(student.attendance[block])"
								/>
							</div>

							<div class="mt-2 flex items-center gap-2">
								<FormControl
									type="select"
									:modelValue="student.attendance[block]"
									:options="codeOptions"
									:disabled="disabled"
									@update:modelValue="(value) => $emit('change-code', { studentId: student.student, block, code: value })"
								/>

								<Button
									appearance="minimal"
									:title="remarkTooltip(student.remarks[block])"
									class="!h-9 !w-9 rounded-lg border border-transparent text-slate-500 hover:border-slate-200 hover:bg-slate-100"
									:class="student.remarks[block] ? '!text-blue-600 hover:!text-blue-600' : ''"
									icon="message-circle"
									:disabled="disabled"
									@click="$emit('open-remark', { student, block })"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, FormControl, FeatherIcon } from 'frappe-ui'
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

const codeOptions = computed(() =>
	props.codes.map((code) => ({
		label: code.attendance_code_name || code.name,
		value: code.name,
	}))
)

function blockLabel(block: BlockKey) {
	return block === -1 ? __('All day') : __('Block {0}', [block])
}

function remarkTooltip(current: string | undefined) {
	return current ? __('Edit remark') : __('Add remark')
}

function dotStyle(codeName: string) {
	const color = props.codeColors?.[codeName]
	return color ? { backgroundColor: color } : { backgroundColor: '#2563eb' }
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
	} catch (e) {
		console.warn('Failed to parse birth date', birthDate, e)
		return false
	}
}
</script>
