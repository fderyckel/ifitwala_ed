<!-- ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsVisitScheduleOverlay.vue -->

<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog as="div" class="if-overlay if-overlay--admissions" :style="overlayStyle" @close="onDialogClose">
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
					<DialogPanel class="if-overlay__panel max-w-5xl">
						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">{{ overlayTitle }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">{{ contextTitle }}</p>
							</div>
							<button type="button" class="if-overlay__close" aria-label="Close" @click="emitClose('programmatic')">
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body px-6 pb-6">
							<div v-if="errorMessage" class="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3" role="alert">
								<p class="type-body-strong text-rose-900">{{ __('Unable to save visit') }}</p>
								<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">{{ errorMessage }}</p>
							</div>

							<div v-if="successMessage" class="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
								<p class="type-caption text-emerald-900">{{ successMessage }}</p>
							</div>

							<div v-if="loadingOptions" class="flex items-center gap-2 type-caption text-ink/60">
								<Spinner class="h-4 w-4" />
								<span>{{ __('Loading visit options...') }}</span>
							</div>

							<div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]">
								<section class="space-y-4">
									<div class="grid gap-3 sm:grid-cols-3">
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Date') }}</span>
											<input v-model="form.date" type="date" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Start') }}</span>
											<input v-model="form.startTime" type="time" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Minutes') }}</span>
											<input v-model.number="form.durationMinutes" type="number" min="5" step="5" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
									</div>

									<div class="grid gap-3 sm:grid-cols-2">
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Visit type') }}</span>
											<select v-model="form.visitType" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink">
												<option v-for="item in visitTypes" :key="item" :value="item">{{ item }}</option>
											</select>
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Mode') }}</span>
											<select v-model="form.visitMode" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink">
												<option v-for="item in visitModes" :key="item" :value="item">{{ item }}</option>
											</select>
										</label>
									</div>

									<div v-if="isInPerson" class="grid gap-3 sm:grid-cols-2">
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Building / Area') }}</span>
											<select v-model="form.building" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink">
												<option value="">{{ __('Select building') }}</option>
												<option v-for="building in buildings" :key="building.value" :value="building.value">
													{{ building.label }}
												</option>
											</select>
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Meeting room') }}</span>
											<select v-model="form.location" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink">
												<option value="">{{ __('Select room') }}</option>
												<option v-for="room in rooms" :key="room.value" :value="room.value">{{ room.label }}</option>
											</select>
										</label>
									</div>

									<div class="grid gap-3 sm:grid-cols-3">
										<label class="block sm:col-span-2">
											<span class="type-caption text-ink/70">{{ __('Visitor name') }}</span>
											<input v-model="form.visitorName" type="text" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Party size') }}</span>
											<input v-model.number="form.partySize" type="number" min="0" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Email') }}</span>
											<input v-model="form.visitorEmail" type="email" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Phone') }}</span>
											<input v-model="form.visitorPhone" type="tel" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Relationship') }}</span>
											<input v-model="form.relationshipToStudent" type="text" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
									</div>

									<div class="grid gap-3 sm:grid-cols-2">
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Requested grade') }}</span>
											<input v-model="form.requestedGradeLevel" type="text" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
										<label class="block">
											<span class="type-caption text-ink/70">{{ __('Program interest') }}</span>
											<input v-model="form.programInterest" type="text" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
										</label>
									</div>

									<label class="block">
										<span class="type-caption text-ink/70">{{ __('Internal notes') }}</span>
										<textarea v-model="form.internalNotes" rows="3" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
									</label>
								</section>

								<section class="space-y-4">
									<div class="rounded-lg border border-slate-200 bg-white p-4">
										<p class="type-body-strong text-ink">{{ __('Visit staff') }}</p>
										<p class="type-caption text-ink/60">{{ __('The first selected staff member leads the visit and receives the calendar event.') }}</p>
										<EmployeePicker
											:query="staffQuery"
											:loading="searchingEmployees"
											:results="staffSearchResults"
											:placeholder="__('Search employees')"
											@update:query="staffQuery = $event"
											@search="searchEmployees('staff')"
											@add="addStaff"
										/>
										<UserChips :users="selectedStaff" empty-label="Select at least one visit lead." @remove="removeStaff" />
									</div>

									<div class="rounded-lg border border-slate-200 bg-white p-4">
										<p class="type-body-strong text-ink">{{ __('Inform only') }}</p>
										<p class="type-caption text-ink/60">{{ __('These users receive a heads-up but are not booked or added to the calendar event.') }}</p>
										<EmployeePicker
											:query="informedQuery"
											:loading="searchingEmployees"
											:results="informedSearchResults"
											:placeholder="__('Search users to inform')"
											@update:query="informedQuery = $event"
											@search="searchEmployees('informed')"
											@add="addInformed"
										/>
										<UserChips :users="selectedInformed" empty-label="No extra users will be informed." @remove="removeInformed" />
									</div>

									<div class="rounded-lg border border-slate-200 bg-white p-4">
										<p class="type-body-strong text-ink">{{ __('Free time search') }}</p>
										<div class="mt-3 grid grid-cols-2 gap-3">
											<label class="block">
												<span class="type-caption text-ink/70">{{ __('From') }}</span>
												<input v-model="form.windowStartTime" type="time" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
											</label>
											<label class="block">
												<span class="type-caption text-ink/70">{{ __('To') }}</span>
												<input v-model="form.windowEndTime" type="time" class="mt-1 block w-full rounded-lg border border-border/70 px-3 py-2 type-caption text-ink" />
											</label>
										</div>
										<button type="button" class="if-button if-button--secondary mt-3 w-full justify-center" :disabled="submitting" @click="loadSuggestions">
											{{ __('Suggest free times') }}
										</button>
										<ol v-if="suggestions.length" class="mt-3 space-y-2">
											<li v-for="slot in suggestions" :key="slot.start">
												<button type="button" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-left type-caption text-ink hover:border-canopy" @click="applySuggestion(slot.start)">
													{{ slot.label }}
												</button>
											</li>
										</ol>
									</div>

									<div v-if="conflicts.length" class="rounded-lg border border-amber-200 bg-amber-50 p-4">
										<p class="type-body-strong text-amber-900">{{ __('Conflict details') }}</p>
										<ul class="mt-2 space-y-1 type-caption text-amber-900/80">
											<li v-for="(conflict, index) in conflicts" :key="`${conflict.kind || 'conflict'}-${index}`">
												{{ conflictLabel(conflict) }}
											</li>
										</ul>
									</div>
								</section>
							</div>
						</div>

						<div class="if-overlay__footer flex flex-wrap items-center justify-between gap-3 px-6 pb-6">
							<div class="flex flex-wrap items-center gap-2">
								<button v-if="isEditMode && canWrite && visitStatus === 'Scheduled'" type="button" class="if-button if-button--quiet" :disabled="submitting" @click="completeVisit">
									{{ __('Mark completed') }}
								</button>
								<button v-if="isEditMode && canWrite && visitStatus === 'Scheduled'" type="button" class="if-button if-button--quiet" :disabled="submitting" @click="markNoShow">
									{{ __('No show') }}
								</button>
								<button v-if="isEditMode && canWrite && selectedInformed.length" type="button" class="if-button if-button--quiet" :disabled="submitting" @click="notifyInformed">
									{{ __('Inform') }}
								</button>
							</div>
							<div class="flex items-center gap-3">
								<button v-if="isEditMode && canWrite && visitStatus !== 'Cancelled'" type="button" class="if-button if-button--secondary" :disabled="submitting" @click="cancelVisit">
									{{ __('Cancel Visit') }}
								</button>
								<button type="button" class="if-button if-button--secondary" @click="emitClose('programmatic')">
									{{ __('Close') }}
								</button>
								<button type="button" class="if-button if-button--primary" :disabled="loadingOptions || submitting || !canWrite" @click="submit">
									<span v-if="submitting" class="inline-flex items-center gap-2">
										<Spinner class="h-4 w-4" /> {{ submitBusyLabel }}
									</span>
									<span v-else>{{ submitLabel }}</span>
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
import { computed, defineComponent, h, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue';
import { FeatherIcon, Spinner } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { __ } from '@/lib/i18n';
import { searchMeetingAttendees } from '@/lib/services/calendar/eventQuickCreateService';
import {
	cancelAdmissionVisit,
	getAdmissionVisitDetail,
	getAdmissionVisitScheduleOptions,
	markAdmissionVisitCompleted,
	markAdmissionVisitNoShow,
	notifyAdmissionVisitInformedUsers,
	rescheduleAdmissionVisit,
	scheduleAdmissionVisit,
	suggestAdmissionVisitSlots,
} from '@/lib/services/admissions/admissionsWorkspaceService';

import type { MeetingAttendee } from '@/types/contracts/calendar/meeting_quick_create_shared';
import type {
	AdmissionVisitDetailResponse,
	AdmissionVisitScheduleConflict,
	AdmissionVisitScheduleOptionsResponse,
	AdmissionVisitScheduleSuggestion,
} from '@/types/contracts/admissions/admission_visit_schedule';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type UserChip = { user: string; label: string };
type SearchTarget = 'staff' | 'informed';

const EmployeePicker = defineComponent({
	props: {
		query: { type: String, required: true },
		loading: { type: Boolean, required: true },
		results: { type: Array as () => MeetingAttendee[], required: true },
		placeholder: { type: String, required: true },
	},
	emits: ['update:query', 'search', 'add'],
	setup(props, { emit }) {
		return () =>
			h('div', { class: 'mt-3' }, [
				h('div', { class: 'flex gap-2' }, [
					h('input', {
						value: props.query,
						type: 'search',
						class: 'min-w-0 flex-1 rounded-lg border border-border/70 px-3 py-2 type-caption text-ink',
						placeholder: props.placeholder,
						onInput: (event: Event) => emit('update:query', (event.target as HTMLInputElement).value),
						onKeydown: (event: KeyboardEvent) => {
							if (event.key === 'Enter') {
								event.preventDefault();
								emit('search');
							}
						},
					}),
					h(
						'button',
						{
							type: 'button',
							class: 'if-button if-button--secondary',
							disabled: props.loading,
							onClick: () => emit('search'),
						},
						props.loading ? __('Searching') : __('Search')
					),
				]),
				props.results.length
					? h(
							'div',
							{ class: 'mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200' },
							props.results.map(employee =>
								h(
									'button',
									{
										key: employee.value,
										type: 'button',
										class: 'flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-slate-50',
										onClick: () => emit('add', employee),
									},
									[
										h('span', { class: 'min-w-0' }, [
											h('span', { class: 'block truncate type-caption text-ink' }, employee.label),
											employee.meta
												? h('span', { class: 'block truncate text-[11px] text-slate-500' }, employee.meta)
												: null,
										]),
										h(FeatherIcon, { name: 'plus', class: 'h-4 w-4 text-canopy' }),
									]
								)
							)
						)
					: null,
			]);
	},
});

const UserChips = defineComponent({
	props: {
		users: { type: Array as () => UserChip[], required: true },
		emptyLabel: { type: String, required: true },
	},
	emits: ['remove'],
	setup(props, { emit }) {
		return () =>
			h('div', { class: 'mt-3 flex flex-wrap gap-2' }, [
				...props.users.map(user =>
					h(
						'span',
						{
							key: user.user,
							class: 'inline-flex max-w-full items-center gap-2 rounded-full border border-canopy/25 bg-canopy/5 px-3 py-1 text-xs font-semibold text-canopy',
						},
						[
							h('span', { class: 'truncate' }, user.label || user.user),
							h(
								'button',
								{
									type: 'button',
									class: 'text-canopy/70 hover:text-canopy',
									onClick: () => emit('remove', user.user),
								},
								[h(FeatherIcon, { name: 'x', class: 'h-3.5 w-3.5' })]
							),
						]
					)
				),
				!props.users.length ? h('span', { class: 'type-caption text-slate-token/70' }, props.emptyLabel) : null,
			]);
	},
});

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	admissionVisit?: string | null;
	conversation?: string | null;
	inquiry?: string | null;
	studentApplicant?: string | null;
	organization?: string | null;
	school?: string | null;
	visitorName?: string | null;
}>();
const emit = defineEmits(['close', 'after-leave']);

const overlay = useOverlayStack();

const loadingOptions = ref(false);
const submitting = ref(false);
const searchingEmployees = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const optionsPayload = ref<AdmissionVisitScheduleOptionsResponse | null>(null);
const detailPayload = ref<AdmissionVisitDetailResponse | null>(null);
const staffQuery = ref('');
const informedQuery = ref('');
const staffSearchResults = ref<MeetingAttendee[]>([]);
const informedSearchResults = ref<MeetingAttendee[]>([]);
const selectedStaff = ref<UserChip[]>([]);
const selectedInformed = ref<UserChip[]>([]);
const suggestions = ref<AdmissionVisitScheduleSuggestion[]>([]);
const conflicts = ref<AdmissionVisitScheduleConflict[]>([]);

const form = reactive({
	date: '',
	startTime: '',
	durationMinutes: 60,
	visitType: 'Family Tour',
	visitMode: 'In Person',
	building: '',
	location: '',
	partySize: null as number | null,
	visitorName: '',
	visitorEmail: '',
	visitorPhone: '',
	relationshipToStudent: '',
	requestedGradeLevel: '',
	programInterest: '',
	internalNotes: '',
	windowStartTime: '07:00',
	windowEndTime: '17:00',
	cancelReason: '',
});

const overlayStyle = computed(() => ({ zIndex: props.zIndex || 0 }));
const isEditMode = computed(() => Boolean(String(props.admissionVisit || '').trim()));
const canWrite = computed(() => !isEditMode.value || Boolean(detailPayload.value?.can_write));
const visitStatus = computed(() => detailPayload.value?.visit?.status || 'Scheduled');
const overlayTitle = computed(() => (isEditMode.value ? __('Admission visit') : __('Schedule visit')));
const submitLabel = computed(() => (isEditMode.value ? __('Update Visit') : __('Schedule Visit')));
const submitBusyLabel = computed(() => (isEditMode.value ? __('Updating...') : __('Scheduling...')));
const contextTitle = computed(() => {
	const context = optionsPayload.value?.context;
	const label = form.visitorName || props.visitorName || context?.visitor_name || props.inquiry || props.studentApplicant || props.conversation || '';
	const school = context?.school || props.school || '';
	return [label, school].filter(Boolean).join(' - ') || __('Admissions visit');
});
const visitTypes = computed(() => optionsPayload.value?.visit_types?.length ? optionsPayload.value.visit_types : ['Family Tour', 'Student Tour', 'Open Day', 'School Visit', 'College Visit', 'Shadow Day', 'Other']);
const visitModes = computed(() => optionsPayload.value?.visit_modes?.length ? optionsPayload.value.visit_modes : ['In Person', 'Online', 'Phone']);
const rooms = computed(() => optionsPayload.value?.rooms || []);
const buildings = computed(() => optionsPayload.value?.buildings || []);
const isInPerson = computed(() => form.visitMode === 'In Person');

function resetForm() {
	errorMessage.value = '';
	successMessage.value = '';
	optionsPayload.value = null;
	detailPayload.value = null;
	staffQuery.value = '';
	informedQuery.value = '';
	staffSearchResults.value = [];
	informedSearchResults.value = [];
	selectedStaff.value = [];
	selectedInformed.value = [];
	suggestions.value = [];
	conflicts.value = [];
	form.date = '';
	form.startTime = '';
	form.durationMinutes = 60;
	form.visitType = 'Family Tour';
	form.visitMode = 'In Person';
	form.building = '';
	form.location = '';
	form.partySize = null;
	form.visitorName = '';
	form.visitorEmail = '';
	form.visitorPhone = '';
	form.relationshipToStudent = '';
	form.requestedGradeLevel = '';
	form.programInterest = '';
	form.internalNotes = '';
	form.windowStartTime = '07:00';
	form.windowEndTime = '17:00';
	form.cancelReason = '';
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
	resetForm();
	loadingOptions.value = true;
	try {
		if (isEditMode.value) {
			const detail = await getAdmissionVisitDetail(String(props.admissionVisit || '').trim());
			detailPayload.value = detail;
			optionsPayload.value = detail.options;
			applyOptions(detail.options);
			applyVisit(detail);
			return;
		}
		const options = await getAdmissionVisitScheduleOptions({
			conversation: props.conversation || null,
			inquiry: props.inquiry || null,
			student_applicant: props.studentApplicant || null,
			organization: props.organization || null,
			school: props.school || null,
		});
		optionsPayload.value = options;
		applyOptions(options);
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not load visit options.');
	} finally {
		loadingOptions.value = false;
	}
}

function applyOptions(options: AdmissionVisitScheduleOptionsResponse) {
	const defaults = options.defaults;
	const context = options.context;
	form.date = defaults.date || '';
	form.startTime = String(defaults.start_time || '09:00:00').slice(0, 5);
	form.durationMinutes = Number(defaults.duration_minutes || 60);
	form.windowStartTime = String(defaults.window_start_time || '07:00:00').slice(0, 5);
	form.windowEndTime = String(defaults.window_end_time || '17:00:00').slice(0, 5);
	form.visitType = defaults.visit_type || options.visit_types?.[0] || 'Family Tour';
	form.visitMode = defaults.visit_mode || options.visit_modes?.[0] || 'In Person';
	form.visitorName = props.visitorName || context.visitor_name || '';
	form.visitorEmail = context.visitor_email || '';
	form.visitorPhone = context.visitor_phone || '';
	form.requestedGradeLevel = context.requested_grade_level || '';
	form.programInterest = context.program_interest || '';
	const leadUser = String(defaults.lead_user || '').trim();
	if (leadUser) selectedStaff.value = [{ user: leadUser, label: leadUser }];
}

function applyVisit(detail: AdmissionVisitDetailResponse) {
	const visit = detail.visit;
	const start = normalizeDateTime(visit.starts_on);
	const end = normalizeDateTime(visit.ends_on);
	if (start) {
		form.date = start.slice(0, 10);
		form.startTime = start.slice(11, 16);
	}
	if (start && end) {
		const minutes = Math.max(5, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000));
		form.durationMinutes = Number.isFinite(minutes) ? minutes : form.durationMinutes;
	}
	form.visitType = visit.visit_type || form.visitType;
	form.visitMode = visit.visit_mode || form.visitMode;
	form.building = visit.building || '';
	form.location = visit.location || '';
	form.partySize = typeof visit.party_size === 'number' ? visit.party_size : null;
	form.visitorName = visit.visitor_name || '';
	form.visitorEmail = visit.visitor_email || '';
	form.visitorPhone = visit.visitor_phone || '';
	form.relationshipToStudent = visit.relationship_to_student || '';
	form.requestedGradeLevel = visit.requested_grade_level || '';
	form.programInterest = visit.program_interest || '';
	form.internalNotes = visit.internal_notes || '';
	form.cancelReason = visit.cancellation_reason || '';
	selectedStaff.value = (visit.staff_users || []).map(user => ({ user, label: user }));
	selectedInformed.value = (visit.informed_users || []).map(user => ({ user, label: user }));
}

async function searchEmployees(target: SearchTarget) {
	const query = (target === 'staff' ? staffQuery.value : informedQuery.value).trim();
	if (!query) {
		if (target === 'staff') staffSearchResults.value = [];
		else informedSearchResults.value = [];
		return;
	}
	searchingEmployees.value = true;
	errorMessage.value = '';
	try {
		const payload = await searchMeetingAttendees({ query, attendee_kinds: ['employee'], limit: 8 });
		const selected = new Set([...selectedStaff.value, ...selectedInformed.value].map(row => row.user));
		const results = (payload.results || []).filter(row => row.kind === 'employee' && !selected.has(row.value));
		if (target === 'staff') staffSearchResults.value = results;
		else informedSearchResults.value = results;
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not search employees.');
	} finally {
		searchingEmployees.value = false;
	}
}

function addStaff(employee: MeetingAttendee) {
	addUserChip(selectedStaff, employee);
	staffSearchResults.value = staffSearchResults.value.filter(row => row.value !== employee.value);
}

function addInformed(employee: MeetingAttendee) {
	if (selectedStaff.value.some(row => row.user === employee.value)) return;
	addUserChip(selectedInformed, employee);
	informedSearchResults.value = informedSearchResults.value.filter(row => row.value !== employee.value);
}

function addUserChip(target: typeof selectedStaff, employee: MeetingAttendee) {
	const user = String(employee.value || '').trim();
	if (!user || target.value.some(row => row.user === user)) return;
	target.value = [...target.value, { user, label: String(employee.label || user).trim() || user }];
}

function removeStaff(user: string) {
	selectedStaff.value = selectedStaff.value.filter(row => row.user !== user);
}

function removeInformed(user: string) {
	selectedInformed.value = selectedInformed.value.filter(row => row.user !== user);
}

function validateScheduleForm(): string {
	if (!canWrite.value) return __('You can view this visit, but you do not have permission to update it.');
	if (!form.date || !form.startTime) return __('Date and start time are required.');
	if (!form.durationMinutes || Number(form.durationMinutes) <= 0) return __('Duration must be greater than zero.');
	if (!selectedStaff.value.length) return __('Select the staff member who will lead the visit.');
	if (isInPerson.value && !form.location && !form.building) return __('Select a building or meeting room for an in-person visit.');
	return '';
}

function baseSchedulePayload() {
	const users = selectedStaff.value.map(row => row.user).filter(Boolean);
	return {
		conversation: props.conversation || optionsPayload.value?.context?.conversation || null,
		inquiry: props.inquiry || optionsPayload.value?.context?.inquiry || null,
		student_applicant: props.studentApplicant || optionsPayload.value?.context?.student_applicant || null,
		organization: props.organization || optionsPayload.value?.context?.organization || null,
		school: props.school || optionsPayload.value?.context?.school || null,
		starts_on: `${form.date} ${form.startTime}`,
		duration_minutes: form.durationMinutes,
		visit_type: form.visitType,
		visit_mode: form.visitMode,
		building: isInPerson.value ? form.building || null : null,
		location: isInPerson.value ? form.location || null : null,
		lead_user: users[0] || null,
		staff_users: users,
		informed_users: selectedInformed.value.map(row => row.user).filter(Boolean),
		visitor_name: form.visitorName || null,
		visitor_email: form.visitorEmail || null,
		visitor_phone: form.visitorPhone || null,
		relationship_to_student: form.relationshipToStudent || null,
		requested_grade_level: form.requestedGradeLevel || null,
		program_interest: form.programInterest || null,
		party_size: form.partySize,
		internal_notes: form.internalNotes,
		suggestion_window_start_time: form.windowStartTime,
		suggestion_window_end_time: form.windowEndTime,
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
		const users = selectedStaff.value.map(row => row.user).filter(Boolean);
		const payload = await suggestAdmissionVisitSlots({
			conversation: props.conversation || optionsPayload.value?.context?.conversation || null,
			inquiry: props.inquiry || optionsPayload.value?.context?.inquiry || null,
			student_applicant: props.studentApplicant || optionsPayload.value?.context?.student_applicant || null,
			organization: props.organization || optionsPayload.value?.context?.organization || null,
			school: props.school || optionsPayload.value?.context?.school || null,
			visit_date: form.date,
			lead_user: users[0] || null,
			staff_users: users,
			visit_mode: form.visitMode,
			building: isInPerson.value ? form.building || null : null,
			location: isInPerson.value ? form.location || null : null,
			duration_minutes: form.durationMinutes,
			window_start_time: form.windowStartTime,
			window_end_time: form.windowEndTime,
		});
		suggestions.value = payload.slots || [];
		if (suggestions.value.length) applySuggestion(suggestions.value[0].start);
		else errorMessage.value = __('No common free time was found in the selected search window.');
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not fetch suggested times.');
	}
}

function applySuggestion(start: string) {
	const normalized = normalizeDateTime(start);
	if (normalized.length < 16) return;
	form.date = normalized.slice(0, 10);
	form.startTime = normalized.slice(11, 16);
}

async function submit() {
	const problem = validateScheduleForm();
	if (problem) {
		errorMessage.value = problem;
		return;
	}
	submitting.value = true;
	errorMessage.value = '';
	successMessage.value = '';
	conflicts.value = [];
	try {
		const payload = isEditMode.value
			? await rescheduleAdmissionVisit({
					...baseSchedulePayload(),
					admission_visit: String(props.admissionVisit || '').trim(),
				})
			: await scheduleAdmissionVisit(baseSchedulePayload());
		if (payload.ok) {
			emitClose('programmatic');
			return;
		}
		conflicts.value = payload.conflicts || [];
		suggestions.value = payload.suggestions || [];
		if (suggestions.value.length) applySuggestion(suggestions.value[0].start);
		errorMessage.value = payload.message || __('The selected time is not available.');
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not save visit.');
	} finally {
		submitting.value = false;
	}
}

async function completeVisit() {
	await runVisitAction(() => markAdmissionVisitCompleted(String(props.admissionVisit || '').trim()), __('Visit marked completed.'));
}

async function markNoShow() {
	await runVisitAction(() => markAdmissionVisitNoShow(String(props.admissionVisit || '').trim()), __('Visit marked no-show.'));
}

async function notifyInformed() {
	await runVisitAction(() => notifyAdmissionVisitInformedUsers(String(props.admissionVisit || '').trim()), __('Heads-up sent.'));
}

async function cancelVisit() {
	const reason = window.prompt(__('Reason for cancelling this visit')) || '';
	if (!reason.trim()) {
		errorMessage.value = __('Cancellation requires a reason.');
		return;
	}
	await runVisitAction(() => cancelAdmissionVisit(String(props.admissionVisit || '').trim(), reason), __('Visit cancelled.'));
}

async function runVisitAction(action: () => Promise<{ ok: boolean }>, success: string) {
	submitting.value = true;
	errorMessage.value = '';
	successMessage.value = '';
	try {
		const payload = await action();
		if (!payload?.ok) {
			errorMessage.value = __('The visit action did not complete.');
			return;
		}
		successMessage.value = success;
		await loadOptions();
	} catch (err: any) {
		errorMessage.value = err?.message || __('Could not update visit.');
	} finally {
		submitting.value = false;
	}
}

function conflictLabel(conflict: AdmissionVisitScheduleConflict) {
	const source = [conflict.source_doctype, conflict.source_name].filter(Boolean).join(' ');
	const windowLabel = [conflict.start_label, conflict.end_label].filter(Boolean).join(' - ');
	if (conflict.kind === 'room') {
		return [conflict.location_label || conflict.location || __('Room'), conflict.occupancy_type, source, windowLabel]
			.filter(Boolean)
			.join(' - ');
	}
	return [conflict.employee_name || conflict.employee || __('Employee'), conflict.booking_type, source, windowLabel]
		.filter(Boolean)
		.join(' - ');
}

function normalizeDateTime(value?: string | null) {
	return String(value || '').replace('T', ' ').slice(0, 19);
}
</script>
