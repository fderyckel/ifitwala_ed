<!-- ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue -->
<template>
	<TransitionRoot as="template" :show="open">
		<Dialog as="div" class="if-overlay if-overlay--class" @close="emitClose">
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
						<div class="meeting-modal__header">
							<div class="meeting-modal__headline">
								<p class="meeting-modal__eyebrow type-overline">Class</p>
								<DialogTitle as="h3" class="type-h3">
									{{ event?.title || 'Class' }}
								</DialogTitle>
								<p v-if="event?.course_name" class="meeting-modal__time type-meta">
									{{ event.course_name }}
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

							<div v-else-if="event">
								<section class="meeting-modal__meta-grid">
									<div>
										<p class="meeting-modal__label type-label">Type</p>
										<p class="meeting-modal__value type-body">{{ event.class_type || 'Course' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Program</p>
										<p class="meeting-modal__value type-body">{{ event.program || '—' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Course</p>
										<p class="meeting-modal__value type-body">{{ courseLabel }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Cohort</p>
										<p class="meeting-modal__value type-body">{{ event.cohort || '—' }}</p>
									</div>
								</section>

								<section class="meeting-modal__meta-grid">
									<div>
										<p class="meeting-modal__label type-label">Rotation Day</p>
										<p class="meeting-modal__value type-body">
											{{ event.rotation_day !== null && event.rotation_day !== undefined ? `Day ${event.rotation_day}` : '—' }}
										</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Block</p>
										<p class="meeting-modal__value type-body">{{ event.block_label || '—' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Location</p>
										<p class="meeting-modal__value type-body">{{ event.location || 'To be announced' }}</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">School</p>
										<p class="meeting-modal__value type-body">{{ event.school || '—' }}</p>
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
										<span v-if="event?.timezone" class="meeting-modal__timezone">({{ event.timezone }})</span>
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
										@click="emit('create-announcement')"
									>
										<FeatherIcon name="message-square" class="h-4 w-4" />
										Create Announcement
									</button>
									<button
										type="button"
										class="meeting-modal__action-button meeting-modal__action-button--secondary"
										@click="emit('create-task')"
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
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

import type { ClassEventDetails } from './classEventTypes';

const props = defineProps<{
	open: boolean;
	loading: boolean;
	error: string | null;
	event: ClassEventDetails | null;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'create-announcement'): void;
	(e: 'create-task'): void;
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
	if (!props.event?.student_group) return { name: 'staff-attendance' };
	return {
		name: 'staff-attendance',
		query: { student_group: props.event.student_group },
	};
});

const gradebookLink = computed(() => {
	if (!props.event?.student_group) return { name: 'staff-gradebook' };
	return {
		name: 'staff-gradebook',
		query: { student_group: props.event.student_group },
	};
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
