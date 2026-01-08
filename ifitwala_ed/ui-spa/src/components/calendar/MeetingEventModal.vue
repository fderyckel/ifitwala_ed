<template>
	<TransitionRoot as="template" :show="open">
		<Dialog
			as="div"
			class="if-overlay if-overlay--meeting"
			:style="{ zIndex: zIndex }"
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
								<p class="meeting-modal__eyebrow type-overline">Meeting</p>
								<DialogTitle as="h3" class="type-h3">
									{{ meeting?.title || 'Meeting details' }}
								</DialogTitle>
								<p class="meeting-modal__time type-meta" v-if="windowLabel">
									{{ windowLabel }}
									<span v-if="meeting?.timezone" class="meeting-modal__timezone">({{ meeting.timezone }})</span>
								</p>
							</div>
							<div class="meeting-modal__header-actions">
								<span v-if="meeting?.status" class="meeting-modal__badge type-badge-label">
									{{ meeting.status }}
								</span>
								<a
									v-if="meeting"
									class="meeting-modal__desk-link type-caption"
									:href="`/app/meeting/${meeting.name}`"
									target="_blank"
									rel="noreferrer"
								>
									<FeatherIcon name="external-link" class="h-4 w-4" />
									View in Desk
								</a>
								<button class="if-overlay__icon-button" aria-label="Close meeting modal" @click="emitClose">
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

							<div v-else-if="meeting">
								<section class="meeting-modal__meta-grid">
									<div>
										<p class="meeting-modal__label type-label">Location</p>
										<p class="meeting-modal__value type-body">
											{{ meeting.location || 'To be announced' }}
										</p>
										<a
											v-if="meeting.virtual_link"
											:href="meeting.virtual_link"
											target="_blank"
											rel="noreferrer"
											class="meeting-modal__link type-caption"
										>
											<FeatherIcon name="external-link" class="h-4 w-4" />
											Join online
										</a>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Team</p>
										<p class="meeting-modal__value type-body">
											{{ meeting.team_name || meeting.team || '—' }}
										</p>
									</div>
									<div>
										<p class="meeting-modal__label type-label">Category</p>
										<p class="meeting-modal__value type-body">
											{{ meeting.meeting_category || '—' }}
										</p>
									</div>
								</section>

								<section class="meeting-modal__agenda">
									<header class="meeting-modal__section-heading">
										<div>
											<p class="meeting-modal__label type-label">Agenda</p>
											<p class="meeting-modal__value type-body">Shared live from Desk</p>
										</div>
									</header>
									<div
										v-if="meeting.agenda"
										class="meeting-modal__agenda-content"
										v-html="meeting.agenda"
									></div>
									<p v-else class="meeting-modal__empty type-body">
										This meeting doesn’t have an agenda yet. Check back soon.
									</p>
								</section>

								<section class="meeting-modal__participants">
									<div class="meeting-modal__section-heading">
										<div>
											<p class="meeting-modal__label type-label">Participants</p>
											<p class="meeting-modal__value type-body">
												{{ meeting.participant_count }} invited
											</p>
										</div>
									</div>
									<ul class="meeting-modal__chip-list">
										<li v-for="row in visibleParticipants" :key="row.participant + row.participant_name">
											<span class="meeting-modal__chip">
												{{ row.participant_name || row.participant || 'Participant' }}
												<span v-if="row.role_in_meeting" class="meeting-modal__chip-role">
													{{ row.role_in_meeting }}
												</span>
											</span>
										</li>
										<li v-if="overflowCount > 0">
											<span class="meeting-modal__chip meeting-modal__chip--muted">
												+{{ overflowCount }} more
											</span>
										</li>
									</ul>
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
import { computed, onMounted, ref, watch } from 'vue';

import { api } from '@/lib/client';
import type { MeetingDetails, MeetingParticipantSummary } from './meetingTypes';

const MAX_PARTICIPANTS = 10;

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	meeting: string; // meeting name/id from ScheduleCalendar extractMeetingName()
}>();

const emit = defineEmits<{
	(e: 'close'): void;
}>();

const zIndex = computed(() => props.zIndex ?? 60);

const loading = ref(false);
const error = ref<string | null>(null);
const meeting = ref<MeetingDetails | null>(null);

let reqSeq = 0;

async function fetchMeetingDetails() {
	if (!props.meeting) return;
	const seq = ++reqSeq;

	loading.value = true;
	error.value = null;
	meeting.value = null;

	try {
		const payload = (await api('ifitwala_ed.api.calendar.get_meeting_details', {
			meeting: props.meeting,
		})) as MeetingDetails;

		if (seq === reqSeq) {
			meeting.value = payload;
		}
	} catch (err) {
		if (seq === reqSeq) {
			error.value = err instanceof Error ? err.message : 'Unable to load meeting details right now.';
		}
	} finally {
		if (seq === reqSeq) {
			loading.value = false;
		}
	}
}

onMounted(() => {
	if (props.open) fetchMeetingDetails();
});

watch(
	() => props.meeting,
	() => {
		if (props.open) fetchMeetingDetails();
	}
);

const windowLabel = computed(() => {
	const start = safeDate(meeting.value?.start);
	if (!start) return '';

	const end = safeDate(meeting.value?.end);
	const timezone = meeting.value?.timezone || undefined;

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
	if (!end) return `${dateLabel} · ${timeFormatter.format(start)}`;

	const sameDay = start.toDateString() === end.toDateString();
	if (sameDay) return `${dateLabel} · ${timeFormatter.format(start)} – ${timeFormatter.format(end)}`;

	return `${dateLabel} · ${timeFormatter.format(start)} → ${dateFormatter.format(end)} · ${timeFormatter.format(end)}`;
});

const visibleParticipants = computed<MeetingParticipantSummary[]>(() => {
	const list = meeting.value?.participants || [];
	return list.slice(0, MAX_PARTICIPANTS);
});

const overflowCount = computed(() => {
	const total = meeting.value?.participant_count || 0;
	return Math.max(0, total - MAX_PARTICIPANTS);
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
