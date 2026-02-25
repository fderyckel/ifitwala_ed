<!-- ui-spa/src/components/calendar/SchoolEventModal.vue -->
<!--
  SchoolEventModal.vue
  A dialog displaying details for a general school event (e.g. assembly, holiday).

  Used by:
  - ScheduleCalendar.vue
-->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--school"
			:style="overlayStyle"
			:initialFocus="initialFocus"
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
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
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
							@click="emitClose('programmatic')"
						>
							Close
						</button>
						<div class="meeting-modal__header">
							<div class="meeting-modal__headline">
								<p class="meeting-modal__eyebrow type-overline">School Event</p>
								<DialogTitle as="h3" class="type-h3">
									{{ resolvedEvent?.subject || 'School Event' }}
								</DialogTitle>
								<p class="meeting-modal__time type-meta" v-if="windowLabel">
									{{ windowLabel }}
									<span v-if="resolvedEvent?.timezone" class="meeting-modal__timezone">
										({{ resolvedEvent.timezone }})
									</span>
								</p>
							</div>
							<div class="meeting-modal__header-actions">
								<span
									v-if="resolvedEvent?.event_type"
									class="meeting-modal__badge type-badge-label"
								>
									{{ resolvedEvent.event_type }}
								</span>
								<button
									class="if-overlay__icon-button"
									aria-label="Close event modal"
									@click="emitClose('programmatic')"
								>
									<FeatherIcon name="x" class="h-5 w-5" />
								</button>
							</div>
						</div>

						<div class="if-overlay__body meeting-modal__body">
							<div v-if="resolvedLoading" class="meeting-modal__loading">
								<div class="meeting-modal__skeleton h-6 w-2/3"></div>
								<div class="meeting-modal__skeleton h-4 w-full"></div>
								<div class="meeting-modal__skeleton h-4 w-5/6"></div>
								<div class="meeting-modal__skeleton h-32 w-full"></div>
							</div>

							<div v-else-if="resolvedError" class="meeting-modal__error">
								<p class="type-body">{{ resolvedError }}</p>
								<button class="meeting-modal__cta" @click="emitClose('programmatic')">
									Close
								</button>
							</div>

							<div v-else-if="resolvedEvent">
								<section class="meeting-modal__meta-grid">
									<div>
										<p class="meeting-modal__label type-label">Location</p>
										<p class="meeting-modal__value type-body">
											{{ resolvedEvent.location || 'To be announced' }}
										</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">School</p>
										<p class="meeting-modal__value type-body">
											{{ resolvedEvent.school || '—' }}
										</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Category</p>
										<p class="meeting-modal__value type-body">
											{{ resolvedEvent.event_category || '—' }}
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
										v-if="resolvedEvent.description"
										class="meeting-modal__agenda-content"
										v-html="resolvedEvent.description"
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
												{{ resolvedEvent.reference_type }} · {{ resolvedEvent.reference_name }}
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
import { computed, onBeforeUnmount, ref, watch } from 'vue';

import { api } from '@/lib/client';
import type { SchoolEventDetails } from './schoolEventTypes';

const props = defineProps<{
	open: boolean;
	loading?: boolean;
	error?: string | null;
	event?: SchoolEventDetails | string | null;
	zIndex?: number;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlayStyle = computed(() => ({
	zIndex: props.zIndex ?? 70,
}));

function emitAfterLeave() {
	emit('after-leave');
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

const resolvedEvent = ref<SchoolEventDetails | null>(null);
const localLoading = ref(false);
const localError = ref<string | null>(null);

let reqSeq = 0;

function isEventPayload(value: unknown): value is SchoolEventDetails {
	return Boolean(
		value && typeof value === 'object' && 'subject' in (value as Record<string, unknown>)
	);
}

async function fetchSchoolEventDetails(eventName: string) {
	const seq = ++reqSeq;
	localLoading.value = true;
	localError.value = null;
	resolvedEvent.value = null;

	try {
		const payload = (await api('ifitwala_ed.api.calendar.get_school_event_details', {
			event: eventName,
		})) as SchoolEventDetails;

		if (seq === reqSeq) {
			resolvedEvent.value = payload;
		}
	} catch (err) {
		if (seq === reqSeq) {
			localError.value =
				err instanceof Error ? err.message : 'Unable to load school event details right now.';
		}
	} finally {
		if (seq === reqSeq) {
			localLoading.value = false;
		}
	}
}

const resolvedLoading = computed(() => Boolean(props.loading) || localLoading.value);
const resolvedError = computed(() => props.error || localError.value);

watch(
	() => [props.open, props.event] as const,
	([isOpen, eventInput]) => {
		if (!isOpen) return;

		if (isEventPayload(eventInput)) {
			reqSeq += 1;
			localLoading.value = false;
			localError.value = null;
			resolvedEvent.value = eventInput;
			return;
		}

		if (typeof eventInput === 'string' && eventInput) {
			void fetchSchoolEventDetails(eventInput);
			return;
		}

		reqSeq += 1;
		localLoading.value = false;
		localError.value =
			'Could not determine which school event was clicked. Please refresh and try again.';
		resolvedEvent.value = null;
	},
	{ immediate: true }
);

const windowLabel = computed(() => {
	const start = safeDate(resolvedEvent.value?.start);
	if (!start) return '';

	const end = safeDate(resolvedEvent.value?.end);
	const timezone = resolvedEvent.value?.timezone || undefined;
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
	if (!end || resolvedEvent.value?.all_day) {
		return resolvedEvent.value?.all_day
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
	if (!resolvedEvent.value?.reference_type || !resolvedEvent.value.reference_name) {
		return '';
	}
	const doctype = String(resolvedEvent.value.reference_type || '')
		.trim()
		.toLowerCase()
		.replace(/_/g, ' ')
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
	if (!doctype) return '';
	const name = encodeURIComponent(resolvedEvent.value.reference_name);
	return `/desk/${encodeURIComponent(doctype)}/${name}`;
});

function safeDate(value?: string | null) {
	if (!value) return null;
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return null;
	return date;
}

const initialFocus = ref<HTMLElement | null>(null);

/**
 * HeadlessUI Dialog @close payload is ambiguous (boolean/undefined).
 * Under A+, ignore it and close only via explicit backdrop/esc/button paths.
 */
function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	v => {
		if (v) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>
