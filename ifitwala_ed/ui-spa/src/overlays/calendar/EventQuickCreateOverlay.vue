<!-- ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--meeting"
			:style="{ zIndex: zIndex }"
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
					<DialogPanel class="if-overlay__panel">
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

						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">Create event</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									Create a Meeting or School Event using the same server validations and workflows
									as the core DocTypes.
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								aria-label="Close"
								@click="emitClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body px-6 pb-6 space-y-5">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">Action blocked</p>
								<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">
									{{ errorMessage }}
								</p>
							</div>

							<div class="rounded-2xl border border-border/70 bg-white p-3 shadow-soft">
								<div class="flex flex-wrap items-center gap-2">
									<button
										v-for="type in typeOptions"
										:key="type.value"
										type="button"
										class="rounded-full px-3 py-1.5 type-button-label transition"
										:class="
											activeType === type.value
												? 'bg-jacaranda text-white'
												: 'bg-slate-100 text-slate-token hover:bg-slate-200'
										"
										:disabled="!canSwitchType || !type.enabled"
										@click="setActiveType(type.value)"
									>
										{{ type.label }}
									</button>
									<span
										v-if="typeLocked"
										class="rounded-full bg-sky/25 px-2.5 py-1 type-caption text-canopy"
									>
										Mode locked by entry context
									</span>
								</div>
							</div>

							<div
								v-if="optionsLoading"
								class="rounded-2xl border border-border/70 bg-white px-4 py-3 text-ink/70 flex items-center gap-2"
							>
								<Spinner class="h-4 w-4" />
								<span class="type-caption">Loading event options...</span>
							</div>

							<form v-else class="space-y-4" @submit.prevent="submit">
								<section v-if="activeType === 'meeting'" class="space-y-4">
									<div class="space-y-1">
										<label class="type-label">Meeting name</label>
										<FormControl
											type="text"
											:model-value="meetingForm.meeting_name"
											placeholder="Weekly pastoral sync"
											:disabled="submitting"
											@update:modelValue="value => updateMeetingField('meeting_name', value)"
										/>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-3">
										<div class="space-y-1">
											<label class="type-label">Date</label>
											<input
												v-model="meetingForm.date"
												type="date"
												class="if-overlay__input"
												:disabled="submitting"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">Start time</label>
											<input
												v-model="meetingForm.start_time"
												type="time"
												class="if-overlay__input"
												:disabled="submitting"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">End time</label>
											<input
												v-model="meetingForm.end_time"
												type="time"
												class="if-overlay__input"
												:disabled="submitting"
											/>
										</div>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">Team (optional)</label>
											<FormControl
												type="select"
												:options="teamSelectOptions"
												option-label="label"
												option-value="value"
												:model-value="meetingForm.team"
												:disabled="submitting"
												@update:modelValue="value => updateMeetingField('team', value)"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">Location (optional)</label>
											<FormControl
												type="select"
												:options="locationSelectOptions"
												option-label="label"
												option-value="value"
												:model-value="meetingForm.location"
												:disabled="submitting"
												@update:modelValue="value => updateMeetingField('location', value)"
											/>
										</div>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">Meeting category (optional)</label>
											<FormControl
												type="select"
												:options="meetingCategorySelectOptions"
												option-label="label"
												option-value="value"
												:model-value="meetingForm.meeting_category"
												:disabled="submitting"
												@update:modelValue="value => updateMeetingField('meeting_category', value)"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">Virtual link (optional)</label>
											<FormControl
												type="text"
												:model-value="meetingForm.virtual_meeting_link"
												placeholder="https://..."
												:disabled="submitting"
												@update:modelValue="
													value => updateMeetingField('virtual_meeting_link', value)
												"
											/>
										</div>
									</div>

									<div class="space-y-1">
										<label class="type-label">Agenda (optional)</label>
										<FormControl
											type="textarea"
											:rows="5"
											:model-value="meetingForm.agenda"
											:disabled="submitting"
											placeholder="Outline the purpose of this meeting..."
											@update:modelValue="value => updateMeetingField('agenda', value)"
										/>
									</div>

									<p class="type-caption text-ink/65">
										If no Team is selected, you will be added as the first participant
										automatically.
									</p>
								</section>

								<section v-else class="space-y-4">
									<div class="space-y-1">
										<label class="type-label">Event subject</label>
										<FormControl
											type="text"
											:model-value="schoolEventForm.subject"
											placeholder="Parent workshop: assessment reporting"
											:disabled="submitting"
											@update:modelValue="value => updateSchoolEventField('subject', value)"
										/>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">School</label>
											<FormControl
												type="select"
												:options="schoolSelectOptions"
												option-label="label"
												option-value="value"
												:model-value="schoolEventForm.school"
												:disabled="submitting || schoolLocked"
												@update:modelValue="value => updateSchoolEventField('school', value)"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">Event category</label>
											<FormControl
												type="select"
												:options="schoolEventCategorySelectOptions"
												option-label="label"
												option-value="value"
												:model-value="schoolEventForm.event_category"
												:disabled="submitting"
												@update:modelValue="
													value => updateSchoolEventField('event_category', value)
												"
											/>
										</div>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">Starts on</label>
											<input
												v-model="schoolEventForm.starts_on"
												type="datetime-local"
												class="if-overlay__input"
												:disabled="submitting"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">Ends on</label>
											<input
												v-model="schoolEventForm.ends_on"
												type="datetime-local"
												class="if-overlay__input"
												:disabled="submitting"
											/>
										</div>
									</div>

									<div class="space-y-1">
										<label class="type-label">Audience type</label>
										<FormControl
											type="select"
											:options="audienceTypeSelectOptions"
											option-label="label"
											option-value="value"
											:model-value="schoolEventForm.audience_type"
											:disabled="submitting"
											@update:modelValue="value => updateSchoolEventField('audience_type', value)"
										/>
									</div>

									<div
										v-if="schoolEventForm.audience_type === 'Employees in Team'"
										class="space-y-1"
									>
										<label class="type-label">Audience team</label>
										<FormControl
											type="select"
											:options="teamSelectOptions"
											option-label="label"
											option-value="value"
											:model-value="schoolEventForm.audience_team"
											:disabled="submitting"
											@update:modelValue="value => updateSchoolEventField('audience_team', value)"
										/>
									</div>

									<div
										v-if="schoolEventForm.audience_type === 'Students in Student Group'"
										class="space-y-1"
									>
										<label class="type-label">Audience student group</label>
										<FormControl
											type="select"
											:options="studentGroupSelectOptions"
											option-label="label"
											option-value="value"
											:model-value="schoolEventForm.audience_student_group"
											:disabled="submitting"
											@update:modelValue="
												value => updateSchoolEventField('audience_student_group', value)
											"
										/>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">Location (optional)</label>
											<FormControl
												type="select"
												:options="locationSelectOptions"
												option-label="label"
												option-value="value"
												:model-value="schoolEventForm.location"
												:disabled="submitting"
												@update:modelValue="value => updateSchoolEventField('location', value)"
											/>
										</div>
										<div class="space-y-2 pt-6">
											<label class="flex items-center gap-2 type-caption text-ink/80">
												<input
													v-model="schoolEventForm.all_day"
													type="checkbox"
													class="rounded border-border/70"
													:disabled="submitting"
												/>
												All-day event
											</label>
											<label class="flex items-center gap-2 type-caption text-ink/80">
												<input
													v-model="schoolEventForm.include_guardians"
													type="checkbox"
													class="rounded border-border/70"
													:disabled="submitting"
												/>
												Include guardians
											</label>
											<label class="flex items-center gap-2 type-caption text-ink/80">
												<input
													v-model="schoolEventForm.include_students"
													type="checkbox"
													class="rounded border-border/70"
													:disabled="submitting"
												/>
												Include students
											</label>
										</div>
									</div>

									<div class="space-y-1">
										<label class="type-label">Description (optional)</label>
										<FormControl
											type="textarea"
											:rows="5"
											:model-value="schoolEventForm.description"
											:disabled="submitting"
											placeholder="Share event details and expectations..."
											@update:modelValue="value => updateSchoolEventField('description', value)"
										/>
									</div>

									<p
										v-if="schoolEventForm.audience_type === 'Custom Users'"
										class="type-caption text-ink/65"
									>
										Custom Users audience will include you as the initial participant.
									</p>
								</section>
							</form>
						</div>

						<footer
							class="if-overlay__footer flex flex-wrap items-center justify-end gap-2 px-6 pb-6"
						>
							<Button
								appearance="secondary"
								:disabled="submitting"
								@click="emitClose('programmatic')"
							>
								Cancel
							</Button>
							<Button
								appearance="primary"
								:loading="submitting"
								:disabled="submitting"
								@click="submit"
							>
								{{ submitLabel }}
							</Button>
						</footer>
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
import { Button, FeatherIcon, FormControl, Spinner } from 'frappe-ui';

import {
	createMeetingQuick,
	createSchoolEventQuick,
	getEventQuickCreateOptions,
} from '@/lib/services/calendar/eventQuickCreateService';

type EventType = 'meeting' | 'school_event';
type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type SelectOption = { value: string; label: string; enabled?: boolean };

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	eventType?: EventType | null;
	lockEventType?: boolean;
	prefillSchool?: string | null;
	prefillTeam?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
	(e: 'done', payload?: Record<string, unknown>): void;
}>();

const zIndex = computed(() => props.zIndex ?? 60);

const optionsLoading = ref(false);
const submitting = ref(false);
const errorMessage = ref<string | null>(null);

const options = ref<{
	can_create_meeting: boolean;
	can_create_school_event: boolean;
	meeting_categories: string[];
	school_event_categories: string[];
	audience_types: string[];
	schools: SelectOption[];
	teams: SelectOption[];
	student_groups: SelectOption[];
	locations: SelectOption[];
	defaults: { school: string | null };
} | null>(null);

const activeType = ref<EventType>('meeting');

const typeLocked = computed(() => Boolean(props.lockEventType && props.eventType));
const schoolLocked = computed(() => Boolean(typeLocked.value && props.prefillSchool));

const meetingForm = reactive({
	meeting_name: '',
	date: '',
	start_time: '',
	end_time: '',
	team: '',
	location: '',
	meeting_category: '',
	virtual_meeting_link: '',
	agenda: '',
});

const schoolEventForm = reactive({
	subject: '',
	school: '',
	starts_on: '',
	ends_on: '',
	audience_type: '',
	event_category: '',
	all_day: false,
	location: '',
	description: '',
	audience_team: '',
	audience_student_group: '',
	include_guardians: false,
	include_students: false,
});

const hasMeetingAccess = computed(() => Boolean(options.value?.can_create_meeting));
const hasSchoolEventAccess = computed(() => Boolean(options.value?.can_create_school_event));

const canSwitchType = computed(
	() => !typeLocked.value && !submitting.value && !optionsLoading.value
);

const typeOptions = computed<SelectOption[]>(() => [
	{ value: 'meeting', label: 'Meeting', enabled: hasMeetingAccess.value },
	{ value: 'school_event', label: 'School event', enabled: hasSchoolEventAccess.value },
]);

const teamSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: 'No team' },
	...(options.value?.teams || []),
]);

const schoolSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: 'Select school' },
	...(options.value?.schools || []),
]);

const studentGroupSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: 'Select student group' },
	...(options.value?.student_groups || []),
]);

const locationSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: 'No location' },
	...(options.value?.locations || []),
]);

const meetingCategorySelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: 'No category' },
	...((options.value?.meeting_categories || []).map(value => ({
		value,
		label: value,
	})) as SelectOption[]),
]);

const schoolEventCategorySelectOptions = computed<SelectOption[]>(
	() =>
		(options.value?.school_event_categories || []).map(value => ({
			value,
			label: value,
		})) as SelectOption[]
);

const audienceTypeSelectOptions = computed<SelectOption[]>(
	() =>
		(options.value?.audience_types || []).map(value => ({ value, label: value })) as SelectOption[]
);

const submitLabel = computed(() =>
	activeType.value === 'meeting' ? 'Create meeting' : 'Create school event'
);

const initialFocus = ref<HTMLElement | null>(null);

function emitAfterLeave() {
	emit('after-leave');
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

function makeClientRequestId() {
	if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
		return crypto.randomUUID();
	}
	return `evt_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function nowDateInput() {
	return new Date().toISOString().slice(0, 10);
}

function pad2(value: number) {
	return String(value).padStart(2, '0');
}

function timeInputWithOffset(offsetMinutes = 0) {
	const now = new Date();
	const date = new Date(now.getTime() + offsetMinutes * 60_000);
	return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function nowDateTimeInput(offsetMinutes = 0) {
	const now = new Date();
	const date = new Date(now.getTime() + offsetMinutes * 60_000);
	return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function initializeForms() {
	meetingForm.meeting_name = '';
	meetingForm.date = nowDateInput();
	meetingForm.start_time = timeInputWithOffset(0);
	meetingForm.end_time = timeInputWithOffset(60);
	meetingForm.team = props.prefillTeam || '';
	meetingForm.location = '';
	meetingForm.meeting_category = '';
	meetingForm.virtual_meeting_link = '';
	meetingForm.agenda = '';

	schoolEventForm.subject = '';
	schoolEventForm.school = props.prefillSchool || '';
	schoolEventForm.starts_on = nowDateTimeInput(0);
	schoolEventForm.ends_on = nowDateTimeInput(60);
	schoolEventForm.audience_type = '';
	schoolEventForm.event_category = '';
	schoolEventForm.all_day = false;
	schoolEventForm.location = '';
	schoolEventForm.description = '';
	schoolEventForm.audience_team = props.prefillTeam || '';
	schoolEventForm.audience_student_group = '';
	schoolEventForm.include_guardians = false;
	schoolEventForm.include_students = false;
}

function initializeActiveType() {
	const requested = props.eventType || null;
	const canMeeting = hasMeetingAccess.value;
	const canSchool = hasSchoolEventAccess.value;

	if (requested && (requested === 'meeting' ? canMeeting : canSchool)) {
		activeType.value = requested;
		return;
	}
	if (canMeeting) {
		activeType.value = 'meeting';
		return;
	}
	if (canSchool) {
		activeType.value = 'school_event';
	}
}

function applyOptionDefaults() {
	if (!schoolEventForm.school && props.prefillSchool) {
		schoolEventForm.school = props.prefillSchool;
	}
	if (!schoolEventForm.school && options.value?.defaults?.school) {
		schoolEventForm.school = options.value.defaults.school;
	}
	if (!schoolEventForm.audience_type) {
		schoolEventForm.audience_type = options.value?.audience_types?.[0] || '';
	}
	if (!schoolEventForm.event_category) {
		schoolEventForm.event_category = options.value?.school_event_categories?.[0] || '';
	}
}

async function loadOptions() {
	optionsLoading.value = true;
	errorMessage.value = null;
	try {
		options.value = await getEventQuickCreateOptions();
		initializeActiveType();
		applyOptionDefaults();
	} catch (error) {
		errorMessage.value =
			error instanceof Error ? error.message : 'Unable to load create-event options.';
	} finally {
		optionsLoading.value = false;
	}
}

function setActiveType(nextType: string) {
	const safeType = nextType === 'school_event' ? 'school_event' : 'meeting';
	const allowed = safeType === 'meeting' ? hasMeetingAccess.value : hasSchoolEventAccess.value;
	if (!allowed) return;
	if (!canSwitchType.value) return;
	activeType.value = safeType;
	errorMessage.value = null;
}

function updateMeetingField(field: keyof typeof meetingForm, value: unknown) {
	meetingForm[field] = String(value || '').trim();
}

function updateSchoolEventField(field: keyof typeof schoolEventForm, value: unknown) {
	(schoolEventForm as Record<string, unknown>)[field] = String(value || '').trim();
}

function parseDateTime(value: string) {
	const normalized = String(value || '').trim();
	if (!normalized) return null;
	const date = new Date(normalized);
	if (Number.isNaN(date.getTime())) return null;
	return date;
}

function validateMeeting() {
	if (!meetingForm.meeting_name) return 'Meeting name is required.';
	if (!meetingForm.date) return 'Meeting date is required.';
	if (!meetingForm.start_time || !meetingForm.end_time) return 'Start and end times are required.';

	const start = parseDateTime(`${meetingForm.date}T${meetingForm.start_time}`);
	const end = parseDateTime(`${meetingForm.date}T${meetingForm.end_time}`);
	if (!start || !end) return 'Meeting date/time is invalid.';
	if (end <= start) return 'Meeting end time must be later than start time.';
	return null;
}

function validateSchoolEvent() {
	if (!schoolEventForm.subject) return 'Event subject is required.';
	if (!schoolEventForm.school) return 'School is required.';
	if (!schoolEventForm.starts_on || !schoolEventForm.ends_on)
		return 'Start and end datetime are required.';
	if (!schoolEventForm.audience_type) return 'Audience type is required.';

	const start = parseDateTime(schoolEventForm.starts_on);
	const end = parseDateTime(schoolEventForm.ends_on);
	if (!start || !end) return 'School event datetime is invalid.';
	if (end <= start) return 'School event end datetime must be later than start.';

	if (schoolEventForm.audience_type === 'Employees in Team' && !schoolEventForm.audience_team) {
		return "Audience Team is required when audience type is 'Employees in Team'.";
	}
	if (
		schoolEventForm.audience_type === 'Students in Student Group' &&
		!schoolEventForm.audience_student_group
	) {
		return "Audience Student Group is required when audience type is 'Students in Student Group'.";
	}
	return null;
}

async function submit() {
	if (submitting.value) return;

	errorMessage.value = activeType.value === 'meeting' ? validateMeeting() : validateSchoolEvent();
	if (errorMessage.value) return;

	submitting.value = true;
	const clientRequestId = makeClientRequestId();

	try {
		let result: Record<string, unknown>;
		if (activeType.value === 'meeting') {
			result = await createMeetingQuick({
				client_request_id: clientRequestId,
				meeting_name: meetingForm.meeting_name,
				date: meetingForm.date,
				start_time: meetingForm.start_time,
				end_time: meetingForm.end_time,
				team: meetingForm.team || null,
				location: meetingForm.location || null,
				meeting_category: meetingForm.meeting_category || null,
				virtual_meeting_link: meetingForm.virtual_meeting_link || null,
				agenda: meetingForm.agenda || null,
				visibility_scope: null,
				participants: null,
			});
		} else {
			result = await createSchoolEventQuick({
				client_request_id: clientRequestId,
				subject: schoolEventForm.subject,
				school: schoolEventForm.school,
				starts_on: schoolEventForm.starts_on,
				ends_on: schoolEventForm.ends_on,
				audience_type: schoolEventForm.audience_type,
				event_category: schoolEventForm.event_category || null,
				all_day: schoolEventForm.all_day ? 1 : 0,
				location: schoolEventForm.location || null,
				description: schoolEventForm.description || null,
				audience_team: schoolEventForm.audience_team || null,
				audience_student_group: schoolEventForm.audience_student_group || null,
				include_guardians: schoolEventForm.include_guardians ? 1 : 0,
				include_students: schoolEventForm.include_students ? 1 : 0,
				custom_participants: null,
			});
		}

		emitClose('programmatic');
		emit('done', result);
	} catch (error) {
		errorMessage.value = error instanceof Error ? error.message : 'Unable to create event.';
	} finally {
		submitting.value = false;
	}
}

watch(
	() => props.open,
	isOpen => {
		if (isOpen) {
			initializeForms();
			void loadOptions();
			document.addEventListener('keydown', onKeydown, true);
		} else {
			document.removeEventListener('keydown', onKeydown, true);
		}
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>
