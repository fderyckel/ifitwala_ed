<!-- ui-spa/src/components/calendar/SchoolEventModal.vue -->
<template>
	<TransitionRoot
		as="template"
		:show="open"
		@after-leave="emitAfterLeave"
	>
		<Dialog
			as="div"
			class="if-overlay if-overlay--school"
			:style="overlayStyle"
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
						<div class="meeting-modal__header">
							<div class="meeting-modal__headline">
								<p class="meeting-modal__eyebrow type-overline">School Event</p>
								<DialogTitle as="h3" class="type-h3">
									{{ event?.subject || 'School Event' }}
								</DialogTitle>
								<p class="meeting-modal__time type-meta" v-if="windowLabel">
									{{ windowLabel }}
									<span v-if="event?.timezone" class="meeting-modal__timezone">
										({{ event.timezone }})
									</span>
								</p>
							</div>
							<div class="meeting-modal__header-actions">
								<span
									v-if="event?.event_type"
									class="meeting-modal__badge type-badge-label"
								>
									{{ event.event_type }}
								</span>
								<button
									class="if-overlay__icon-button"
									aria-label="Close event modal"
									@click="emitClose"
								>
									<FeatherIcon name="x" class="h-5 w-5" />
								</button>
							</div>
						</div>

						<div class="if-overlay__body meeting-modal__body">
							<div v-if="loading" class="meeting-modal__loading">
								<div class="meeting-modal__skeleton h-6 w-2/3"></div>
								<div class="meeting-modal__skeleton h-4 w-full"></div>
								<div class="meeting-modal__skeleton h-4 w-5/6"></div>
								<div class="meeting-modal__skeleton h-32 w-full"></div>
							</div>

							<div v-else-if="error" class="meeting-modal__error">
								<p class="type-body">{{ error }}</p>
								<button class="meeting-modal__cta" @click="emitClose">Close</button>
							</div>

							<div v-else-if="event">
								<section class="meeting-modal__meta-grid">
									<div>
										<p class="meeting-modal__label type-label">Location</p>
										<p class="meeting-modal__value type-body">
											{{ event.location || 'To be announced' }}
										</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">School</p>
										<p class="meeting-modal__value type-body">
											{{ event.school || '—' }}
										</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Category</p>
										<p class="meeting-modal__value type-body">
											{{ event.event_category || '—' }}
										</p>
									</div>
								</section>

								<section class="meeting-modal__agenda">
									<header class="meeting-modal__section-heading">
										<div>
											<p class="meeting-modal__label type-label">Description</p>
											<p class="meeting-modal__value type-body">Shared live from Desk</p>
										</div>
									</header>
									<div
										v-if="event.description"
										class="meeting-modal__agenda-content"
										v-html="event.description"
									></div>
									<p v-else class="meeting-modal__empty type-body">
										This event doesn’t have a description yet. Check back soon.
									</p>
								</section>

								<section v-if="referenceLink" class="meeting-modal__participants">
									<div class="meeting-modal__section-heading">
										<div>
											<p class="meeting-modal__label type-label">Reference</p>
											<p class="meeting-modal__value type-body">
												{{ event.reference_type }} · {{ event.reference_name }}
											</p>
										</div>
									</div>
									<a
										class="meeting-modal__link type-caption"
										:href="referenceLink"
										target="_blank"
										rel="noreferrer"
									>
										<FeatherIcon name="external-link" class="h-4 w-4" />
										View referenced document
									</a>
								</section>
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

import type { SchoolEventDetails } from './schoolEventTypes';

const props = defineProps<{
	open: boolean;
	loading: boolean;
	error: string | null;
	event: SchoolEventDetails | null;
	zIndex?: number;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'after-leave'): void;
}>();

const overlayStyle = computed(() => ({
	zIndex: props.zIndex ?? 70,
}));

function emitAfterLeave() {
	emit('after-leave');
}

function emitClose() {
	emit('close');
}

const windowLabel = computed(() => {
	const start = safeDate(props.event?.start);
	if (!start) return '';

	const end = safeDate(props.event?.end);
	const timezone = props.event?.timezone || undefined;
	const dateFormatter = new Intl.DateTimeFormat(undefined, {
		weekday: 'long',
		month: 'long',
		day: 'numeric',
		timeZone: timezone,
	});
	const timeFormatter = new Intl.DateTimeFormat(undefined, {
		hour: 'numeric',
		minute: '2-digit',
		timeZone: timezone,
	});

	const dateLabel = dateFormatter.format(start);
	if (!end || props.event?.all_day) {
		return props.event?.all_day
			? `${dateLabel} · All day`
			: `${dateLabel} · ${timeFormatter.format(start)}`;
	}

	const sameDay = start.toDateString() === end.toDateString();
	if (sameDay) {
		return `${dateLabel} · ${timeFormatter.format(start)} – ${timeFormatter.format(end)}`;
	}

	return `${dateLabel} · ${timeFormatter.format(start)} → ${dateFormatter.format(end)} · ${timeFormatter.format(end)}`;
});

const referenceLink = computed(() => {
	if (!props.event?.reference_type || !props.event.reference_name) {
		return '';
	}
	const doctype = encodeURIComponent(props.event.reference_type);
	const name = encodeURIComponent(props.event.reference_name);
	return `/app/${doctype}/${name}`;
});

function safeDate(value?: string | null) {
	if (!value) return null;
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return null;
	return date;
}
</script>
