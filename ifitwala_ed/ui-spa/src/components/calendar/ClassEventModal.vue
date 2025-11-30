<!-- ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue -->
<template>
	<TransitionRoot as="template" :show="open">
		<Dialog as="div" class="meeting-modal meeting-modal--class" @close="emitClose">
			<TransitionChild
				as="template"
				enter="meeting-modal__fade-enter"
				enter-from="meeting-modal__fade-from"
				enter-to="meeting-modal__fade-to"
				leave="meeting-modal__fade-leave"
				leave-from="meeting-modal__fade-to"
				leave-to="meeting-modal__fade-from"
			>
				<div class="meeting-modal__backdrop" />
			</TransitionChild>

			<div class="meeting-modal__wrapper">
				<TransitionChild
					as="template"
					enter="meeting-modal__panel-enter"
					enter-from="meeting-modal__panel-from"
					enter-to="meeting-modal__panel-to"
					leave="meeting-modal__panel-leave"
					leave-from="meeting-modal__panel-to"
					leave-to="meeting-modal__panel-from"
				>
					<DialogPanel class="meeting-modal__panel">
						<div class="meeting-modal__header">
							<div class="meeting-modal__headline">
								<p class="meeting-modal__eyebrow">Class</p>
								<DialogTitle as="h3">{{ event?.title || 'Class' }}</DialogTitle>
								<p v-if="event?.course_name" class="meeting-modal__time">
									{{ event.course_name }}
								</p>
							</div>
							<button class="meeting-modal__icon-button" aria-label="Close class modal" @click="emitClose">
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div v-if="loading" class="meeting-modal__loading">
							<div class="meeting-modal__skeleton h-6 w-3/5"></div>
							<div class="meeting-modal__skeleton h-4 w-4/5"></div>
							<div class="meeting-modal__skeleton h-4 w-2/3"></div>
							<div class="meeting-modal__skeleton h-24 w-full"></div>
						</div>

						<div v-else-if="error" class="meeting-modal__error">
							<p>{{ error }}</p>
							<button class="meeting-modal__cta" @click="emitClose">Close</button>
						</div>

						<div v-else-if="event" class="meeting-modal__body space-y-6">
							<section class="meeting-modal__meta-grid">
								<div>
									<p class="meeting-modal__label">Type</p>
									<p class="meeting-modal__value">{{ event.class_type || 'Course' }}</p>
								</div>
								<div>
									<p class="meeting-modal__label">Program</p>
									<p class="meeting-modal__value">{{ event.program || '—' }}</p>
								</div>
								<div>
									<p class="meeting-modal__label">Course</p>
									<p class="meeting-modal__value">{{ courseLabel }}</p>
								</div>
								<div>
									<p class="meeting-modal__label">Cohort</p>
									<p class="meeting-modal__value">{{ event.cohort || '—' }}</p>
								</div>
							</section>

							<section class="meeting-modal__meta-grid">
								<div>
									<p class="meeting-modal__label">Rotation Day</p>
									<p class="meeting-modal__value">
										{{ event.rotation_day !== null && event.rotation_day !== undefined ? `Day ${event.rotation_day}` : '—' }}
									</p>
								</div>
								<div>
									<p class="meeting-modal__label">Block</p>
									<p class="meeting-modal__value">{{ event.block_label || '—' }}</p>
								</div>
								<div>
									<p class="meeting-modal__label">Location</p>
									<p class="meeting-modal__value">{{ event.location || 'To be announced' }}</p>
								</div>
								<div>
									<p class="meeting-modal__label">School</p>
									<p class="meeting-modal__value">{{ event.school || '—' }}</p>
								</div>
							</section>

							<section class="meeting-modal__agenda">
								<header class="meeting-modal__section-heading">
									<div>
										<p class="meeting-modal__label">Schedule</p>
										<p class="meeting-modal__value" v-if="sessionDateLabel">{{ sessionDateLabel }}</p>
									</div>
								</header>
								<p class="meeting-modal__value">
									{{ timeLabel }}
									<span v-if="event?.timezone" class="meeting-modal__timezone">({{ event.timezone }})</span>
								</p>
							</section>

							<div class="meeting-modal__actions">
								<a
									class="meeting-modal__action-button"
									:href="attendanceLink"
									target="_blank"
									rel="noreferrer"
								>
									<FeatherIcon name="check-square" class="h-4 w-4" />
									Take Attendance
								</a>
								<a
									class="meeting-modal__action-button meeting-modal__action-button--secondary"
									:href="gradebookLink"
									target="_blank"
									rel="noreferrer"
								>
									<FeatherIcon name="book-open" class="h-4 w-4" />
									Open Gradebook
								</a>
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
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';
import { computed } from 'vue';

import type { ClassEventDetails } from './classEventTypes';

const props = defineProps<{
	open: boolean;
	loading: boolean;
	error: string | null;
	event: ClassEventDetails | null;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
}>();

const courseLabel = computed(() => props.event?.course_name || props.event?.course || '—');

const sessionDateLabel = computed(() => {
	if (!props.event?.session_date) return '';
	try {
		const date = new Date(props.event.session_date);
		return new Intl.DateTimeFormat(undefined, {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
			year: 'numeric',
		}).format(date);
	} catch {
		return props.event.session_date;
	}
});

const timeLabel = computed(() => {
	const start = safeDate(props.event?.start);
	if (!start) return 'Time to be confirmed';
	const end = safeDate(props.event?.end);
	const timezone = props.event?.timezone || undefined;
	const formatter = new Intl.DateTimeFormat(undefined, {
		hour: 'numeric',
		minute: '2-digit',
		timeZone: timezone,
	});
	if (!end) {
		return formatter.format(start);
	}
	return `${formatter.format(start)} – ${formatter.format(end)}`;
});

const attendanceLink = computed(() => {
	if (!props.event?.student_group) return '/portal/staff/attendance';
	return `/portal/staff/attendance?student_group=${encodeURIComponent(props.event.student_group)}`;
});

const gradebookLink = computed(() => {
	if (!props.event?.student_group) return '/portal/staff/gradebook';
	return `/portal/staff/gradebook?student_group=${encodeURIComponent(props.event.student_group)}`;
});

function safeDate(value?: string | null) {
	if (!value) return null;
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return null;
	return date;
}

function emitClose() {
	emit('close');
}
</script>
