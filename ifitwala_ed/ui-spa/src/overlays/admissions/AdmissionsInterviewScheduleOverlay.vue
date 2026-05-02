<!-- ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsInterviewScheduleOverlay.vue -->

<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--admissions"
			:style="overlayStyle"
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
					<DialogPanel class="if-overlay__panel max-w-4xl">
						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">{{ __('Schedule interview') }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{ applicantTitle }}
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								@click="emitClose('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body px-6 pb-6">
							<div
								v-if="errorMessage"
								class="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">
									{{ __('Unable to schedule interview') }}
								</p>
								<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">
									{{ errorMessage }}
								</p>
							</div>

							<div v-if="loadingOptions" class="flex items-center gap-2 type-caption text-ink/60">
								<Spinner class="h-4 w-4" />
								<span>{{ __('Loading schedule options...') }}</span>
							</div>

							<div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(280px,0.95fr)]">
								<section class="space-y-4">
									<div class="grid gap-3 sm:grid-cols-3">
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Date') }}</span>
											<input
												v-model="form.date"
												type="date"
												class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
											/>
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Start') }}</span>
											<input
												v-model="form.startTime"
												type="time"
												class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
											/>
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Minutes') }}</span>
											<input
												v-model.number="form.durationMinutes"
												type="number"
												min="5"
												step="5"
												class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
											/>
										</label>
									</div>

									<div class="grid gap-3 sm:grid-cols-2">
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Interview type') }}</span>
											<select
												v-model="form.interviewType"
												class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
											>
												<option v-for="item in interviewTypes" :key="item" :value="item">
													{{ item }}
												</option>
											</select>
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Mode') }}</span>
											<select
												v-model="form.mode"
												class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
											>
												<option v-for="item in modes" :key="item" :value="item">{{ item }}</option>
											</select>
										</label>
									</div>

									<div v-if="isInPerson" class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_160px]">
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Room') }}</span>
											<select
												v-model="form.location"
												class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
											>
												<option value="">{{ __('Select room') }}</option>
												<option v-for="room in rooms" :key="room.value" :value="room.value">
													{{ room.label }}
												</option>
											</select>
										</label>
										<div class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
											<p class="type-caption text-slate-token/70">{{ __('Available rooms') }}</p>
											<p class="mt-1 text-lg font-semibold text-ink">{{ rooms.length }}</p>
										</div>
									</div>

									<label class="block">
										<span class="type-caption text-ink/70">{{ __('Confidentiality') }}</span>
										<select
											v-model="form.confidentialityLevel"
											class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
										>
											<option value="">{{ __('Default') }}</option>
											<option v-for="item in confidentialityLevels" :key="item" :value="item">
												{{ item }}
											</option>
										</select>
									</label>

									<label class="block">
										<span class="type-caption text-ink/70">{{ __('Operational notes') }}</span>
										<textarea
											v-model="form.notes"
											rows="3"
											class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
										/>
									</label>
								</section>

								<section class="space-y-4">
									<div class="rounded-lg border border-slate-200 bg-white p-4">
										<div class="flex items-center justify-between gap-3">
											<div>
												<p class="type-body-strong text-ink">{{ __('Interviewers') }}</p>
												<p class="type-caption text-ink/60">
													{{ __('Employee calendars are checked before save.') }}
												</p>
											</div>
										</div>
										<div class="mt-3 flex gap-2">
											<input
												v-model="attendeeQuery"
												type="search"
												class="min-w-0 flex-1 rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
												:placeholder="__('Search employees')"
												@keydown.enter.prevent="searchEmployees"
											/>
											<button
												type="button"
												class="if-button if-button--secondary"
												:disabled="searchingEmployees"
												@click="searchEmployees"
											>
												<Spinner v-if="searchingEmployees" class="h-4 w-4" />
												<span v-else>{{ __('Search') }}</span>
											</button>
										</div>

										<div
											v-if="employeeResults.length"
											class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200"
										>
											<button
												v-for="employee in employeeResults"
												:key="employee.value"
												type="button"
												class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-slate-50"
												@click="addInterviewer(employee.value, employee.label)"
											>
												<span class="min-w-0">
													<span class="block truncate type-caption text-ink">{{
														employee.label
													}}</span>
													<span
														v-if="employee.meta"
														class="block truncate text-[11px] text-slate-500"
														>{{ employee.meta }}</span
													>
												</span>
												<FeatherIcon name="plus" class="h-4 w-4 text-canopy" />
											</button>
										</div>

										<div class="mt-3 flex flex-wrap gap-2">
											<span
												v-for="person in selectedInterviewers"
												:key="person.user"
												class="inline-flex max-w-full items-center gap-2 rounded-full border border-canopy/25 bg-canopy/5 px-3 py-1 text-xs font-semibold text-canopy"
											>
												<span class="truncate">{{ person.label || person.user }}</span>
												<button
													type="button"
													class="text-canopy/70 hover:text-canopy"
													@click="removeInterviewer(person.user)"
												>
													<FeatherIcon name="x" class="h-3.5 w-3.5" />
												</button>
											</span>
											<span v-if="!selectedInterviewers.length" class="type-caption text-rose-700">
												{{ __('Select at least one interviewer.') }}
											</span>
										</div>
									</div>

									<div class="rounded-lg border border-slate-200 bg-white p-4">
										<p class="type-body-strong text-ink">{{ __('Free time search') }}</p>
										<div class="mt-3 grid grid-cols-2 gap-3">
											<label class="block">
												<span class="type-caption text-ink/70">{{ __('From') }}</span>
												<input
													v-model="form.windowStartTime"
													type="time"
													class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
												/>
											</label>
											<label class="block">
												<span class="type-caption text-ink/70">{{ __('To') }}</span>
												<input
													v-model="form.windowEndTime"
													type="time"
													class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink"
												/>
											</label>
										</div>
										<button
											type="button"
											class="if-button if-button--secondary mt-3 w-full justify-center"
											:disabled="submitting"
											@click="loadSuggestions"
										>
											{{ __('Suggest free times') }}
										</button>

										<ol v-if="suggestions.length" class="mt-3 space-y-2">
											<li v-for="slot in suggestions" :key="slot.start">
												<button
													type="button"
													class="w-full rounded-lg border border-slate-200 px-3 py-2 text-left type-caption text-ink hover:border-canopy"
													@click="applySuggestion(slot.start)"
												>
													{{ slot.label }}
												</button>
											</li>
										</ol>
									</div>

									<div
										v-if="conflicts.length"
										class="rounded-lg border border-amber-200 bg-amber-50 p-4"
									>
										<p class="type-body-strong text-amber-900">{{ __('Conflict details') }}</p>
										<ul class="mt-2 space-y-1 type-caption text-amber-900/80">
											<li
												v-for="(conflict, index) in conflicts"
												:key="`${conflict.kind || 'conflict'}-${index}`"
											>
												{{ conflictLabel(conflict) }}
											</li>
										</ul>
									</div>
								</section>
							</div>
						</div>

						<div
							class="if-overlay__footer flex flex-wrap items-center justify-between gap-3 px-6 pb-6"
						>
							<p class="type-caption text-ink/55">
								{{
									__(
										'Feedback is entered from the calendar event or interview workspace after scheduling.'
									)
								}}
							</p>
							<div class="flex items-center gap-3">
								<button
									type="button"
									class="if-button if-button--secondary"
									@click="emitClose('programmatic')"
								>
									{{ __('Cancel') }}
								</button>
								<button
									type="button"
									class="if-button if-button--primary"
									:disabled="loadingOptions || submitting"
									@click="submit"
								>
									<span v-if="submitting" class="inline-flex items-center gap-2">
										<Spinner class="h-4 w-4" /> {{ __('Scheduling...') }}
									</span>
									<span v-else>{{ __('Schedule') }}</span>
								</button>
							</div>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon, Spinner } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { __ } from '@/lib/i18n';
import { searchMeetingAttendees } from '@/lib/services/calendar/eventQuickCreateService';
import {
	getInterviewScheduleOptions,
	scheduleApplicantInterview,
	suggestInterviewSlots,
} from '@/lib/services/admissions/admissionsWorkspaceService';

import type { MeetingAttendee } from '@/types/contracts/calendar/meeting_quick_create_shared';
import type {
	InterviewScheduleConflict,
	InterviewScheduleOptionsResponse,
	InterviewScheduleSuggestion,
} from '@/types/contracts/admissions/applicant_interview_schedule';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	studentApplicant?: string | null;
	applicantName?: string | null;
	school?: string | null;
}>();
const emit = defineEmits(['close', 'after-leave']);

const overlay = useOverlayStack();

const loadingOptions = ref(false);
const submitting = ref(false);
const searchingEmployees = ref(false);
const errorMessage = ref('');
const optionsPayload = ref<InterviewScheduleOptionsResponse | null>(null);
const attendeeQuery = ref('');
const employeeResults = ref<MeetingAttendee[]>([]);
const selectedInterviewers = ref<Array<{ user: string; label: string }>>([]);
const suggestions = ref<InterviewScheduleSuggestion[]>([]);
const conflicts = ref<InterviewScheduleConflict[]>([]);

const form = reactive({
	date: '',
	startTime: '',
	durationMinutes: 30,
	interviewType: 'Student',
	mode: 'In Person',
	location: '',
	confidentialityLevel: '',
	notes: '',
	windowStartTime: '07:00',
	windowEndTime: '17:00',
});

const overlayStyle = computed(() => ({
	zIndex: props.zIndex || 0,
}));

const applicantTitle = computed(() => {
	const label = (
		props.applicantName ||
		optionsPayload.value?.applicant?.display_name ||
		props.studentApplicant ||
		''
	).trim();
	const school = (props.school || optionsPayload.value?.applicant?.school || '').trim();
	return [label, school].filter(Boolean).join(' - ') || __('Admission interview');
});

const interviewTypes = computed(() =>
	optionsPayload.value?.interview_types?.length
		? optionsPayload.value.interview_types
		: ['Family', 'Student', 'Joint']
);
const modes = computed(() =>
	optionsPayload.value?.modes?.length
		? optionsPayload.value.modes
		: ['In Person', 'Online', 'Phone']
);
const confidentialityLevels = computed(() => optionsPayload.value?.confidentiality_levels || []);
const rooms = computed(() => optionsPayload.value?.rooms || []);
const isInPerson = computed(() => form.mode === 'In Person');

function resetForm() {
	errorMessage.value = '';
	optionsPayload.value = null;
	attendeeQuery.value = '';
	employeeResults.value = [];
	selectedInterviewers.value = [];
	suggestions.value = [];
	conflicts.value = [];
	form.date = '';
	form.startTime = '';
	form.durationMinutes = 30;
	form.interviewType = 'Student';
	form.mode = 'In Person';
	form.location = '';
	form.confidentialityLevel = '';
	form.notes = '';
	form.windowStartTime = '07:00';
	form.windowEndTime = '17:00';
}

function emitClose(reason: CloseReason) {
	const overlayId = props.overlayId || null;
	if (overlayId) {
		try {
			overlay.close(overlayId);
			return;
		} catch {
			// fall through
		}
	}
	emit('close', reason);
}

function emitAfterLeave() {
	resetForm();
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op; OverlayHost owns close reasons.
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	val => {
		if (val) {
			document.addEventListener('keydown', onKeydown, true);
			void loadOptions();
		} else {
			document.removeEventListener('keydown', onKeydown, true);
		}
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});

async function loadOptions() {
	const applicant = String(props.studentApplicant || '').trim();
	if (!applicant) {
		errorMessage.value = __('Applicant reference is missing.');
		return;
	}

	resetForm();
	loadingOptions.value = true;
	try {
		const payload = await getInterviewScheduleOptions(applicant);
		optionsPayload.value = payload;
		const defaults = payload.defaults;
		form.date = defaults.date || '';
		form.startTime = (defaults.start_time || '09:00:00').slice(0, 5);
		form.durationMinutes = Number(defaults.duration_minutes || 30);
		form.windowStartTime = (defaults.window_start_time || '07:00:00').slice(0, 5);
		form.windowEndTime = (defaults.window_end_time || '17:00:00').slice(0, 5);
		form.interviewType = payload.interview_types?.includes('Student')
			? 'Student'
			: payload.interview_types?.[0] || 'Student';
		form.mode = payload.modes?.includes('In Person')
			? 'In Person'
			: payload.modes?.[0] || 'In Person';
		form.location = payload.rooms?.length === 1 ? payload.rooms[0].value : '';
		form.confidentialityLevel = payload.confidentiality_levels?.[0] || '';
		const currentUser = String(defaults.current_user || '').trim();
		if (currentUser) {
			selectedInterviewers.value = [{ user: currentUser, label: currentUser }];
		}
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not load schedule options.');
	} finally {
		loadingOptions.value = false;
	}
}

async function searchEmployees() {
	const query = attendeeQuery.value.trim();
	if (!query) {
		employeeResults.value = [];
		return;
	}
	searchingEmployees.value = true;
	errorMessage.value = '';
	try {
		const payload = await searchMeetingAttendees({
			query,
			attendee_kinds: ['employee'],
			limit: 8,
		});
		const selected = new Set(selectedInterviewers.value.map(row => row.user));
		employeeResults.value = (payload.results || []).filter(
			row => row.kind === 'employee' && !selected.has(row.value)
		);
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not search employees.');
	} finally {
		searchingEmployees.value = false;
	}
}

function addInterviewer(user: string, label: string) {
	const resolvedUser = String(user || '').trim();
	if (!resolvedUser || selectedInterviewers.value.some(row => row.user === resolvedUser)) {
		return;
	}
	selectedInterviewers.value = [
		...selectedInterviewers.value,
		{ user: resolvedUser, label: String(label || resolvedUser).trim() || resolvedUser },
	];
	employeeResults.value = employeeResults.value.filter(row => row.value !== resolvedUser);
}

function removeInterviewer(user: string) {
	selectedInterviewers.value = selectedInterviewers.value.filter(row => row.user !== user);
}

function validateScheduleForm(): string {
	if (!form.date || !form.startTime) {
		return __('Date and start time are required.');
	}
	if (!form.durationMinutes || Number(form.durationMinutes) <= 0) {
		return __('Duration must be greater than zero.');
	}
	if (!selectedInterviewers.value.length) {
		return __('Select at least one interviewer.');
	}
	if (isInPerson.value && !form.location) {
		return __('Select a room for an in-person interview.');
	}
	return '';
}

function suggestionPayload() {
	const users = selectedInterviewers.value.map(row => row.user).filter(Boolean);
	return {
		student_applicant: String(props.studentApplicant || '').trim(),
		interview_date: form.date,
		primary_interviewer: users[0] || null,
		interviewer_users: users,
		mode: form.mode,
		location: isInPerson.value ? form.location : null,
		duration_minutes: form.durationMinutes,
		window_start_time: form.windowStartTime,
		window_end_time: form.windowEndTime,
	};
}

async function loadSuggestions() {
	const problem = validateScheduleForm();
	if (problem) {
		errorMessage.value = problem;
		return;
	}
	errorMessage.value = '';
	try {
		const payload = await suggestInterviewSlots(suggestionPayload());
		suggestions.value = payload.slots || [];
		if (suggestions.value.length) {
			applySuggestion(suggestions.value[0].start);
		} else {
			errorMessage.value = __('No common free time was found in the selected search window.');
		}
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not fetch suggested times.');
	}
}

function applySuggestion(start: string) {
	const normalized = String(start || '').replace('T', ' ');
	if (normalized.length < 16) return;
	form.date = normalized.slice(0, 10);
	form.startTime = normalized.slice(11, 16);
}

async function submit() {
	const applicant = String(props.studentApplicant || '').trim();
	const problem = validateScheduleForm();
	if (!applicant) {
		errorMessage.value = __('Applicant reference is missing.');
		return;
	}
	if (problem) {
		errorMessage.value = problem;
		return;
	}

	submitting.value = true;
	errorMessage.value = '';
	conflicts.value = [];
	try {
		const users = selectedInterviewers.value.map(row => row.user).filter(Boolean);
		const payload = await scheduleApplicantInterview({
			student_applicant: applicant,
			interview_start: `${form.date} ${form.startTime}`,
			duration_minutes: form.durationMinutes,
			interview_type: form.interviewType,
			mode: form.mode,
			location: isInPerson.value ? form.location : null,
			confidentiality_level: form.confidentialityLevel || null,
			notes: form.notes,
			primary_interviewer: users[0] || null,
			interviewer_users: users,
			suggestion_window_start_time: form.windowStartTime,
			suggestion_window_end_time: form.windowEndTime,
		});

		if (payload.ok) {
			emitClose('programmatic');
			return;
		}

		conflicts.value = payload.conflicts || [];
		suggestions.value = payload.suggestions || [];
		if (suggestions.value.length) {
			applySuggestion(suggestions.value[0].start);
		}
		errorMessage.value = payload.message || __('The selected time is not available.');
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not schedule interview.');
	} finally {
		submitting.value = false;
	}
}

function conflictLabel(conflict: InterviewScheduleConflict) {
	const source = [conflict.source_doctype, conflict.source_name].filter(Boolean).join(' ');
	const windowLabel = [conflict.start_label, conflict.end_label].filter(Boolean).join(' - ');
	if (conflict.kind === 'room') {
		return [
			conflict.location_label || conflict.location || __('Room'),
			conflict.occupancy_type,
			source,
			windowLabel,
		]
			.filter(Boolean)
			.join(' - ');
	}
	return [
		conflict.employee_name || conflict.employee || __('Employee'),
		conflict.booking_type,
		source,
		windowLabel,
	]
		.filter(Boolean)
		.join(' - ');
}
</script>
