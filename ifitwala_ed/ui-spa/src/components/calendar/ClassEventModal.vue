<!-- ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue -->
<template>
	<TransitionRoot
		as="template"
		:show="open"
		@after-leave="emitAfterLeave"
	>
		<Dialog
			as="div"
			class="if-overlay if-overlay--class"
			:style="overlayStyle"
			:initialFocus="initialFocus"
			@close="emitClose"
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
				<div class="if-overlay__backdrop" />
			</TransitionChild>

			<div class="if-overlay__wrap">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel if-overlay__panel--compact">
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
						<div class="meeting-modal__header">
							<div class="meeting-modal__headline">
								<p class="meeting-modal__eyebrow type-overline">Class</p>
								<DialogTitle as="h3" class="type-h3">
									{{ data?.title || 'Class' }}
								</DialogTitle>
								<p v-if="data?.course_name" class="meeting-modal__time type-meta">
									{{ data.course_name }}
								</p>
							</div>
							<button class="if-overlay__icon-button" aria-label="Close class modal" @click="emitClose">
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body meeting-modal__body">
							<div v-if="loading" class="meeting-modal__loading">
								<div class="meeting-modal__skeleton h-6 w-3/5"></div>
								<div class="meeting-modal__skeleton h-4 w-4/5"></div>
								<div class="meeting-modal__skeleton h-4 w-2/3"></div>
								<div class="meeting-modal__skeleton h-24 w-full"></div>
							</div>

							<div v-else-if="error" class="meeting-modal__error">
								<p class="type-body">{{ error }}</p>
								<button class="meeting-modal__cta" @click="emitClose">Close</button>
							</div>

							<div v-else-if="data">
								<section class="meeting-modal__meta-grid">
									<div>
										<p class="meeting-modal__label type-label">Type</p>
										<p class="meeting-modal__value type-body">{{ data.class_type || 'Course' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Program</p>
										<p class="meeting-modal__value type-body">{{ data.program || '—' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Course</p>
										<p class="meeting-modal__value type-body">{{ courseLabel }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Cohort</p>
										<p class="meeting-modal__value type-body">{{ data.cohort || '—' }}</p>
									</div>
								</section>

								<section class="meeting-modal__meta-grid">
									<div>
										<p class="meeting-modal__label type-label">Rotation Day</p>
										<p class="meeting-modal__value type-body">
											{{ data.rotation_day !== null && data.rotation_day !== undefined ? `Day ${data.rotation_day}` : '—' }}
										</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Block</p>
										<p class="meeting-modal__value type-body">{{ data.block_label || '—' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Location</p>
										<p class="meeting-modal__value type-body">{{ data.location || 'To be announced' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">School</p>
										<p class="meeting-modal__value type-body">{{ data.school || '—' }}</p>
									</div>
								</section>

								<section class="meeting-modal__agenda">
									<header class="meeting-modal__section-heading">
										<div>
											<p class="meeting-modal__label type-label">Schedule</p>
											<p class="meeting-modal__value type-body" v-if="sessionDateLabel">{{ sessionDateLabel }}</p>
										</div>
									</header>
									<p class="meeting-modal__value type-body">
										{{ timeLabel }}
										<span v-if="data?.timezone" class="meeting-modal__timezone">({{ data.timezone }})</span>
									</p>
								</section>

								<div class="meeting-modal__actions">
									<RouterLink
										class="meeting-modal__action-button"
										:to="attendanceLink"
										target="_blank"
										rel="noreferrer"
									>
										<FeatherIcon name="check-square" class="h-4 w-4" />
										Take Attendance
									</RouterLink>

									<RouterLink
										class="meeting-modal__action-button meeting-modal__action-button--secondary"
										:to="gradebookLink"
										target="_blank"
										rel="noreferrer"
									>
										<FeatherIcon name="book-open" class="h-4 w-4" />
										Open Gradebook
									</RouterLink>

									<button
										type="button"
										class="meeting-modal__action-button meeting-modal__action-button--secondary"
										@click="emitCreateAnnouncement"
									>
										<FeatherIcon name="message-square" class="h-4 w-4" />
										Create Announcement
									</button>

									<button
										type="button"
										class="meeting-modal__action-button meeting-modal__action-button--secondary"
										@click="emitCreateTask"
									>
										<FeatherIcon name="clipboard" class="h-4 w-4" />
										Create Task
									</button>
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
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue'
import { FeatherIcon } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useOverlayStack } from '@/composables/useOverlayStack'
import { api } from '@/lib/client'
import type { ClassEventDetails } from './classEventTypes'

const props = defineProps<{
	open: boolean
	zIndex?: number
	eventId?: string | null
}>()

const overlay = useOverlayStack()


const emit = defineEmits<{
	(e: 'close'): void
	(e: 'create-announcement', event: ClassEventDetails): void
	(e: 'create-task', payload: { studentGroup: string; dueDate: string | null }): void
	(e: 'after-leave'): void
}>()

const overlayStyle = computed(() => {
	return props.zIndex ? ({ zIndex: props.zIndex } as Record<string, any>) : undefined
})

const loading = ref(false)
const error = ref<string | null>(null)
const data = ref<ClassEventDetails | null>(null)

let requestSeq = 0

watch(
	() => [props.open, props.eventId] as const,
	async ([isOpen, eventId]) => {
		if (!isOpen) return
		if (!eventId) {
			loading.value = false
			error.value = 'Could not determine which class was clicked. Please refresh and try again.'
			data.value = null
			return
		}

		loading.value = true
		error.value = null
		data.value = null

		const seq = ++requestSeq
		try {
			const payload = (await api('ifitwala_ed.api.calendar.get_student_group_event_details', {
				event_id: eventId,
			})) as ClassEventDetails

			if (seq === requestSeq) {
				data.value = payload
			}
		} catch (err) {
			if (seq === requestSeq) {
				error.value = err instanceof Error ? err.message : 'Unable to load class details right now.'
			}
		} finally {
			if (seq === requestSeq) {
				loading.value = false
			}
		}
	},
	{ immediate: true }
)

const courseLabel = computed(() => data.value?.course_name || data.value?.course || '—')

const sessionDateLabel = computed(() => {
	if (!data.value?.session_date) return ''
	try {
		const date = new Date(data.value.session_date)
		return new Intl.DateTimeFormat(undefined, {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
			year: 'numeric',
		}).format(date)
	} catch {
		return data.value.session_date ?? ''
	}
})

function safeDate(value?: string | null) {
	if (!value) return null
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return null
	return date
}

const timeLabel = computed(() => {
	const start = safeDate(data.value?.start)
	if (!start) return 'Time to be confirmed'
	const end = safeDate(data.value?.end)
	const timezone = data.value?.timezone || undefined
	const formatter = new Intl.DateTimeFormat(undefined, {
		hour: 'numeric',
		minute: '2-digit',
		timeZone: timezone,
	})
	if (!end) return formatter.format(start)
	return `${formatter.format(start)} – ${formatter.format(end)}`
})

const attendanceLink = computed(() => {
	if (!data.value?.student_group) return { name: 'staff-attendance' }
	return { name: 'staff-attendance', query: { student_group: data.value.student_group } }
})

const gradebookLink = computed(() => {
	if (!data.value?.student_group) return { name: 'staff-gradebook' }
	return { name: 'staff-gradebook', query: { student_group: data.value.student_group } }
})

function emitClose() {
	emit('close')
}

function emitCreateAnnouncement() {
	if (!data.value) return

	// Replace current modal with announcement quick-create overlay
	// (You must have this overlay type + component registered in OverlayHost)
	overlay.replaceTop('org-communication-quick-create', {
		// keep it minimal: pass what the quick-create needs
		studentGroup: data.value.student_group || null,
		title: data.value.title || '',
	})
}

function emitCreateTask() {
	if (!data.value?.student_group) return

	// Clean handoff: class modal disappears, create-task appears as top
	overlay.replaceTop('create-task', {
		prefillStudentGroup: data.value.student_group,
		prefillDueDate: data.value.end || data.value.start || null,
	})
}



function emitAfterLeave() {
	emit('after-leave')
}

const initialFocus = ref<HTMLElement | null>(null)
</script>
