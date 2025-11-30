<template>
	<TransitionRoot as="template" :show="open">
		<Dialog as="div" class="meeting-modal meeting-modal--meeting" @close="emitClose"></Dialog>
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
								<p class="meeting-modal__eyebrow">Meeting</p>
								<DialogTitle as="h3">{{ meeting?.title || 'Meeting details' }}</DialogTitle>
								<p class="meeting-modal__time" v-if="windowLabel">
									{{ windowLabel }}
									<span v-if="meeting?.timezone" class="meeting-modal__timezone">({{ meeting.timezone }})</span>
								</p>
							</div>
							<div class="meeting-modal__header-actions">
								<span v-if="meeting?.status" class="meeting-modal__badge">{{ meeting.status }}</span>
								<a
									v-if="meeting"
									class="meeting-modal__desk-link"
									:href="`/app/meeting/${meeting.name}`"
									target="_blank"
									rel="noreferrer"
								>
									<FeatherIcon name="external-link" class="h-4 w-4" />
									View in Desk
								</a>
								<button class="meeting-modal__icon-button" aria-label="Close meeting modal" @click="emitClose">
									<FeatherIcon name="x" class="h-5 w-5" />
								</button>
							</div>
						</div>

						<div v-if="loading" class="meeting-modal__loading">
							<div class="meeting-modal__skeleton h-6 w-2/3"></div>
							<div class="meeting-modal__skeleton h-4 w-full"></div>
							<div class="meeting-modal__skeleton h-4 w-5/6"></div>
							<div class="meeting-modal__skeleton h-32 w-full"></div>
						</div>

						<div v-else-if="error" class="meeting-modal__error">
							<p>{{ error }}</p>
							<button class="meeting-modal__cta" @click="emitClose">Close</button>
						</div>

						<div v-else-if="meeting" class="meeting-modal__body">
							<section class="meeting-modal__meta-grid">
								<div>
									<p class="meeting-modal__label">Location</p>
									<p class="meeting-modal__value">
										{{ meeting.location || 'To be announced' }}
									</p>
									<a
										v-if="meeting.virtual_link"
										:href="meeting.virtual_link"
										target="_blank"
										rel="noreferrer"
										class="meeting-modal__link"
									>
										<FeatherIcon name="external-link" class="h-4 w-4" />
										Join online
									</a>
								</div>
								<div>
									<p class="meeting-modal__label">Team</p>
									<p class="meeting-modal__value">
										{{ meeting.team_name || meeting.team || '—' }}
									</p>
								</div>
								<div>
									<p class="meeting-modal__label">Category</p>
									<p class="meeting-modal__value">
										{{ meeting.meeting_category || '—' }}
									</p>
								</div>
							</section>

							<section class="meeting-modal__agenda">
								<header class="meeting-modal__section-heading">
									<div>
										<p class="meeting-modal__label">Agenda</p>
										<p class="meeting-modal__value">Shared live from Desk</p>
									</div>
								</header>
								<div
									v-if="meeting.agenda"
									class="meeting-modal__agenda-content"
									v-html="meeting.agenda"
								></div>
								<p v-else class="meeting-modal__empty">
									This meeting doesn’t have an agenda yet. Check back soon.
								</p>
							</section>

							<section class="meeting-modal__participants">
								<div class="meeting-modal__section-heading">
									<div>
										<p class="meeting-modal__label">Participants</p>
										<p class="meeting-modal__value">
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

import type { MeetingDetails, MeetingParticipantSummary } from './meetingTypes';

const MAX_PARTICIPANTS = 10;

const props = defineProps<{
	open: boolean;
	loading: boolean;
	error: string | null;
	meeting: MeetingDetails | null;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
}>();

const windowLabel = computed(() => {
	const start = safeDate(props.meeting?.start);
	if (!start) return '';

	const end = safeDate(props.meeting?.end);
	const timezone = props.meeting?.timezone || undefined;
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
	if (!end) {
		return `${dateLabel} · ${timeFormatter.format(start)}`;
	}

	const sameDay = start.toDateString() === end.toDateString();
	if (sameDay) {
		return `${dateLabel} · ${timeFormatter.format(start)} – ${timeFormatter.format(end)}`;
	}

	return `${dateLabel} · ${timeFormatter.format(start)} → ${dateFormatter.format(end)} · ${timeFormatter.format(
		end
	)}`;
});

const visibleParticipants = computed<MeetingParticipantSummary[]>(() => {
	const list = props.meeting?.participants || [];
	return list.slice(0, MAX_PARTICIPANTS);
});

const overflowCount = computed(() => {
	const total = props.meeting?.participant_count || 0;
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
