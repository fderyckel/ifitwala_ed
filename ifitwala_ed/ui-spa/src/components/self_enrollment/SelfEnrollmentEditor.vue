<!-- ifitwala_ed/ui-spa/src/components/self_enrollment/SelfEnrollmentEditor.vue -->
<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
				<div class="flex items-start gap-4">
					<img
						v-if="payload?.student.student_image"
						:src="payload.student.student_image"
						:alt="payload.student.full_name"
						class="h-16 w-16 rounded-2xl object-cover ring-1 ring-line-soft"
					/>
					<div>
						<p class="type-overline text-ink/60">{{ overline }}</p>
						<h1 class="type-h1 text-ink">{{ payload?.window.title || __('Course Selection') }}</h1>
						<p class="type-body text-ink/70">
							{{ subtitle }}
						</p>
						<p v-if="payload?.window.instructions" class="mt-3 type-caption text-ink/70">
							{{ payload.window.instructions }}
						</p>
					</div>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<RouterLink class="if-button if-button--secondary" :to="backTo">{{
						backLabel
					}}</RouterLink>
					<button
						type="button"
						class="if-button if-button--quiet"
						:disabled="loading"
						@click="emit('refresh')"
					>
						{{ __('Refresh') }}
					</button>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">{{ __('Required') }}</p>
				<p class="mini-kpi-value">{{ payload?.summary.required_course_count || 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">{{ __('Optional') }}</p>
				<p class="mini-kpi-value">{{ payload?.summary.optional_course_count || 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">{{ __('Selected') }}</p>
				<p class="mini-kpi-value">{{ payload?.summary.selected_optional_count || 0 }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">{{ __('Due') }}</p>
				<p class="mini-kpi-value text-base">
					{{ dueLabel }}
				</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">{{ __('Loading course selection…') }}</p>
		</section>
		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">{{ __('Unable to load course selection.') }}</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else-if="payload">
			<section
				v-if="payload.permissions.locked_reason"
				class="card-surface border border-line-soft bg-surface-soft p-5"
			>
				<p class="type-body-strong text-ink">{{ __('Selection locked') }}</p>
				<p class="mt-2 type-body text-ink/70">{{ payload.permissions.locked_reason }}</p>
			</section>

			<section class="card-surface p-5">
				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<div>
						<h2 class="type-h3 text-ink">{{ __('Request Status') }}</h2>
						<p class="type-caption text-ink/70">
							{{ __('Request {0} · {1}', [payload.request.name, payload.request.status]) }}
						</p>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<span :class="statusClass(payload.request.status)" class="chip">
							{{ payload.request.status }}
						</span>
						<span :class="validationClass(payload.request.validation_status)" class="chip">
							{{ payload.request.validation_status }}
						</span>
					</div>
				</div>
			</section>

			<section v-if="payload.window.collect_enrollment_intent === 1" class="card-surface p-5">
				<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<h2 class="type-h3 text-ink">{{ __('Enrollment Intent') }}</h2>
						<p class="type-caption text-ink/70">
							{{ __('Tell the school whether this student plans to enroll next year.') }}
						</p>
					</div>
					<div class="grid w-full gap-2 lg:max-w-xl">
						<label
							v-for="option in enrollmentIntentOptions"
							:key="option.value"
							class="rounded-xl border border-line-soft bg-surface-soft p-3"
							:class="{
								'border-jacaranda/40 bg-jacaranda/5': draftEnrollmentIntent === option.value,
							}"
						>
							<span class="flex items-start gap-3">
								<input
									v-model="draftEnrollmentIntent"
									type="radio"
									class="mt-1"
									:value="option.value"
									:disabled="!canEdit"
								/>
								<span>
									<span class="block type-body-strong text-ink">{{ option.label }}</span>
									<span class="block type-caption text-ink/70">{{ option.description }}</span>
								</span>
							</span>
						</label>
					</div>
				</div>
			</section>

			<section v-if="showCourseChoices" class="space-y-4">
				<div class="flex items-center justify-between gap-3">
					<div>
						<h2 class="type-h3 text-ink">{{ __('Required Courses') }}</h2>
						<p class="type-caption text-ink/60">
							{{ __('These courses are part of the program and stay visible for reference.') }}
						</p>
					</div>
				</div>
				<div
					v-if="!sections.required_courses.length"
					class="card-surface p-5 type-body text-ink/70"
				>
					{{ __('No required courses are set up for this offering.') }}
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="course in sections.required_courses"
						:key="course.course"
						class="card-surface border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<div class="flex flex-wrap items-center gap-2">
									<p class="type-body-strong text-ink">{{ course.course_name }}</p>
									<span class="chip">{{ __('Required') }}</span>
									<span v-if="course.basket_groups.length" class="chip">
										{{ course.basket_groups.join(' · ') }}
									</span>
								</div>
								<p class="mt-2 type-caption text-ink/70">{{ course.course }}</p>
							</div>
							<div v-if="course.basket_groups.length > 1" class="w-full max-w-sm">
								<label class="flex flex-col gap-1">
									<span class="type-label">{{ __('Counts Toward') }}</span>
									<select
										:value="course.applied_basket_group || ''"
										class="rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink disabled:bg-surface-soft"
										:disabled="!canEdit"
										@change="handleAppliedGroupChange(course.course, $event)"
									>
										<option value="">{{ __('Select basket group') }}</option>
										<option
											v-for="basketGroup in course.basket_groups"
											:key="`${course.course}-${basketGroup}`"
											:value="basketGroup"
										>
											{{ basketGroup }}
										</option>
									</select>
								</label>
							</div>
						</div>
					</article>
				</div>
			</section>

			<section v-if="showCourseChoices" class="space-y-4">
				<div class="flex items-center justify-between gap-3">
					<div>
						<h2 class="type-h3 text-ink">{{ __('Choice Groups') }}</h2>
						<p class="type-caption text-ink/60">
							{{ __('Choose from the sections below where the school offers options.') }}
						</p>
					</div>
				</div>

				<div
					v-if="!sections.basket_sections.length"
					class="card-surface p-5 type-body text-ink/70"
				>
					{{ __('No choice sections are set up for this offering.') }}
				</div>
				<div v-else class="space-y-4">
					<section
						v-for="section in sections.basket_sections"
						:key="section.basket_group"
						class="card-surface p-5"
					>
						<div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
							<div>
								<h3 class="type-body-strong text-ink">{{ section.basket_group }}</h3>
								<p class="type-caption text-ink/60">
									{{
										section.required_by_rule
											? __('Choose at least one course in this section.')
											: __('Optional choices in this section.')
									}}
								</p>
							</div>
							<span class="chip">{{ __('{0} selected', [section.selected_count]) }}</span>
						</div>
						<div class="space-y-3">
							<article
								v-for="course in section.courses"
								:key="`${section.basket_group}-${course.course}`"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								:class="{
									'border-jacaranda/30 bg-jacaranda/5': course.selected_in_group,
									'opacity-65': course.selected_elsewhere,
								}"
							>
								<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
									<div class="min-w-0 flex-1">
										<label
											class="inline-flex items-start gap-3"
											:class="{ 'cursor-not-allowed': !canEdit || course.selected_elsewhere }"
										>
											<input
												:checked="course.selected_in_group"
												type="checkbox"
												class="mt-1 rounded border-line-soft"
												:disabled="!canEdit || course.selected_elsewhere"
												@change="handleOptionalToggle(course.course, section.basket_group, $event)"
											/>
											<span class="min-w-0">
												<span class="type-body-strong text-ink">{{ course.course_name }}</span>
												<span class="mt-1 block type-caption text-ink/70">{{
													course.course
												}}</span>
											</span>
										</label>
										<p v-if="course.selected_elsewhere" class="mt-2 type-caption text-ink/60">
											{{ __('Already chosen in {0}.', [course.applied_basket_group || '']) }}
										</p>
									</div>

									<div
										v-if="course.selected_in_group"
										class="grid w-full gap-3 lg:max-w-xl lg:grid-cols-2"
									>
										<label v-if="course.basket_groups.length > 1" class="flex flex-col gap-1">
											<span class="type-label">{{ __('Counts In') }}</span>
											<select
												:value="course.applied_basket_group || ''"
												class="rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink"
												:disabled="!canEdit"
												@change="handleAppliedGroupChange(course.course, $event)"
											>
												<option value="">{{ __('Choose section') }}</option>
												<option
													v-for="basketGroup in course.basket_groups"
													:key="`${course.course}-${basketGroup}`"
													:value="basketGroup"
												>
													{{ basketGroup }}
												</option>
											</select>
										</label>
										<label class="flex flex-col gap-1">
											<span class="type-label">{{ __('Preference Rank') }}</span>
											<input
												:value="course.choice_rank ?? ''"
												type="number"
												min="1"
												inputmode="numeric"
												class="rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink"
												:disabled="!canEdit"
												@input="handleChoiceRankInput(course.course, $event)"
											/>
											<span v-if="showGuardianChoiceRankHelp" class="type-caption text-ink/60">
												{{
													__(
														'1 is the first choice in this section. We fill this in for you, and you can change it if needed.'
													)
												}}
											</span>
										</label>
									</div>
								</div>
							</article>
						</div>
					</section>
				</div>
			</section>

			<section v-if="showCourseChoices" class="space-y-4">
				<div class="flex items-center justify-between gap-3">
					<div>
						<h2 class="type-h3 text-ink">{{ __('More Options') }}</h2>
						<p class="type-caption text-ink/60">
							{{ __('Extra course options that are not part of a choice section.') }}
						</p>
					</div>
				</div>
				<div
					v-if="!sections.ungrouped_courses.length"
					class="card-surface p-5 type-body text-ink/70"
				>
					{{ __('No extra course options are available for this offering.') }}
				</div>
				<div v-else class="space-y-3">
					<article
						v-for="course in sections.ungrouped_courses"
						:key="course.course"
						class="card-surface p-4"
					>
						<label class="inline-flex items-start gap-3">
							<input
								:checked="course.is_selected"
								type="checkbox"
								class="mt-1 rounded border-line-soft"
								:disabled="!canEdit"
								@change="handleOptionalToggle(course.course, '', $event)"
							/>
							<span class="min-w-0">
								<span class="type-body-strong text-ink">{{ course.course_name }}</span>
								<span class="mt-1 block type-caption text-ink/70">{{ course.course }}</span>
							</span>
						</label>
					</article>
				</div>
			</section>

			<section
				v-if="showCourseChoices || payload.window.collect_enrollment_intent === 1"
				class="card-surface p-5"
			>
				<div class="mb-3 flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">{{ __('Submission Check') }}</h2>
					<span :class="validationToneClass(validationDisplayState)" class="chip">
						{{ validationDisplayLabel }}
					</span>
				</div>
				<div v-if="!validationMessages.length" class="type-body text-ink/70">
					{{ validationEmptyMessage }}
				</div>
				<ul v-else class="space-y-2">
					<li
						v-for="(message, index) in validationMessages"
						:key="`validation-${index}`"
						class="rounded-xl border border-line-soft bg-surface-soft p-3 type-body text-ink/80"
					>
						{{ message }}
					</li>
				</ul>
			</section>

			<section class="card-surface p-5">
				<div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
					<div>
						<p class="type-body-strong text-ink">
							{{ hasUnsavedChanges ? __('Unsaved changes') : __('Selections saved') }}
						</p>
						<p class="type-caption text-ink/70">
							{{ submissionGuidance }}
						</p>
						<p v-if="submissionWarning" class="mt-2 type-caption text-flame">
							{{ submissionWarning }}
						</p>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<button
							type="button"
							class="if-button if-button--secondary"
							:disabled="!canEdit || !hasUnsavedChanges || saving"
							@click="emit('save', submitPayload)"
						>
							{{ saving ? __('Saving...') : __('Save Draft') }}
						</button>
						<button
							type="button"
							class="if-button if-button--primary"
							:disabled="!canAttemptSubmit || submitting"
							@click="emit('submit', submitPayload)"
						>
							{{ submitting ? __('Submitting...') : submitButtonLabel }}
						</button>
					</div>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import type { RouteLocationRaw } from 'vue-router';

import {
	applyDefaultChoiceRanks,
	buildChoiceSections,
	choiceRowsForSubmit,
	haveChoiceRowsChanged,
	normalizeChoiceRow,
} from '@/components/self_enrollment/choiceSections';
import { __ } from '@/lib/i18n';
import type {
	EnrollmentIntent,
	Response as ChoiceStateResponse,
	SelfEnrollmentChoiceCourse,
} from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state';
import type { ChoiceSubmitRow } from '@/types/contracts/self_enrollment/save_self_enrollment_choices';

type IntentDraftValue = EnrollmentIntent | '';
type SelfEnrollmentSubmitPayload = {
	courses: ChoiceSubmitRow[];
	enrollment_intent?: IntentDraftValue;
};

const props = defineProps<{
	payload: ChoiceStateResponse | null;
	loading: boolean;
	saving: boolean;
	submitting: boolean;
	errorMessage: string;
	backTo: RouteLocationRaw;
	backLabel: string;
	overline: string;
}>();

const emit = defineEmits<{
	(e: 'refresh'): void;
	(e: 'save', payload: SelfEnrollmentSubmitPayload): void;
	(e: 'submit', payload: SelfEnrollmentSubmitPayload): void;
}>();

const draftRows = ref<SelfEnrollmentChoiceCourse[]>([]);
const savedRows = ref<SelfEnrollmentChoiceCourse[]>([]);
const draftEnrollmentIntent = ref<IntentDraftValue>('');
const savedEnrollmentIntent = ref<IntentDraftValue>('');
const showGuardianChoiceRankHelp = computed(() => props.payload?.viewer.actor_type === 'Guardian');

const enrollmentIntentOptions: Array<{
	value: EnrollmentIntent;
	label: string;
	description: string;
}> = [
	{
		value: 'Intends to Enroll',
		label: __('Yes, intends to enroll'),
		description: __('Continue with course choices for next year.'),
	},
	{
		value: 'Does Not Intend to Enroll',
		label: __('No, not returning'),
		description: __('Submit the response without choosing courses.'),
	},
	{
		value: 'Undecided',
		label: __('Maybe / undecided'),
		description: __('Ask the school to follow up before enrollment is confirmed.'),
	},
];

watch(
	() => props.payload,
	value => {
		const rows = applyEditorDefaults(
			value?.courses || [],
			value?.viewer.actor_type === 'Guardian'
		);
		draftRows.value = rows;
		savedRows.value = rows;
		const intent = (value?.request.enrollment_intent || '') as IntentDraftValue;
		draftEnrollmentIntent.value = intent;
		savedEnrollmentIntent.value = intent;
	},
	{ immediate: true }
);

const canEdit = computed(() => props.payload?.permissions.can_edit === 1);
const canSubmit = computed(() => props.payload?.permissions.can_submit === 1);
const readyForSubmit = computed(() => props.payload?.summary.ready_for_submit === true);
const submitRows = computed(() => choiceRowsForSubmit(draftRows.value));
const collectEnrollmentIntent = computed(
	() => props.payload?.window.collect_enrollment_intent === 1
);
const hasIntentResponse = computed(
	() => !collectEnrollmentIntent.value || Boolean(draftEnrollmentIntent.value)
);
const showCourseChoices = computed(
	() => !collectEnrollmentIntent.value || draftEnrollmentIntent.value === 'Intends to Enroll'
);
const submitPayload = computed<SelfEnrollmentSubmitPayload>(() => ({
	courses: showCourseChoices.value ? submitRows.value : [],
	enrollment_intent: collectEnrollmentIntent.value ? draftEnrollmentIntent.value : undefined,
}));
const hasUnsavedChanges = computed(
	() =>
		haveChoiceRowsChanged(draftRows.value, savedRows.value) ||
		draftEnrollmentIntent.value !== savedEnrollmentIntent.value
);
const allowGuardianDirectSubmit = computed(
	() =>
		props.payload?.viewer.actor_type === 'Guardian' &&
		canSubmit.value &&
		hasUnsavedChanges.value &&
		hasIntentResponse.value
);
const canAttemptSubmit = computed(
	() =>
		canSubmit.value &&
		hasIntentResponse.value &&
		((!showCourseChoices.value && draftEnrollmentIntent.value !== '') ||
			readyForSubmit.value ||
			allowGuardianDirectSubmit.value)
);
const subtitle = computed(() => {
	if (!props.payload) return __('Review the course choices and confirm your selections.');
	const childLabel =
		props.payload.viewer.actor_type === 'Guardian'
			? `${props.payload.student.full_name} · ${props.payload.window.academic_year}`
			: props.payload.window.academic_year;
	return __('Review the course choices and confirm your selections for {0}.', [childLabel]);
});

const dueLabel = computed(() => {
	const due = props.payload?.window.due_on;
	if (!due) return __('No deadline');
	return formatShortDate(due);
});

const sections = computed(() =>
	buildChoiceSections(draftRows.value, props.payload?.required_basket_groups || [])
);
const submissionGuidance = computed(() => {
	if (collectEnrollmentIntent.value && !draftEnrollmentIntent.value) {
		return __('Choose an enrollment intent before submitting.');
	}
	if (!showCourseChoices.value) {
		return __('Submit this response so the school can plan next steps.');
	}
	if (allowGuardianDirectSubmit.value) {
		return __(
			'Submit uses your latest changes. Save Draft is optional if you want to come back later.'
		);
	}
	return __('Save your work while you review options, then submit when everything looks right.');
});
const submissionWarning = computed(() => {
	if (collectEnrollmentIntent.value && !draftEnrollmentIntent.value) {
		return __('Please answer the enrollment intent question first.');
	}
	if (!showCourseChoices.value) {
		return '';
	}
	if (allowGuardianDirectSubmit.value) {
		return __(
			'You can submit now. If anything still needs attention, we will show you what to fix.'
		);
	}
	if (canEdit.value && !readyForSubmit.value) {
		return __('Please finish the items above before submitting.');
	}
	return '';
});

const validationMessages = computed(() => {
	const payload = props.payload;
	if (!payload) return [];
	if (!showCourseChoices.value) return [];
	const messages = [
		...(payload.validation.reasons || []),
		...(payload.validation.violations || []),
	]
		.map(message => String(message || '').trim())
		.filter(Boolean);
	return Array.from(new Set(messages));
});

const validationDisplayState = computed<'invalid' | 'pending' | 'valid'>(() => {
	const payload = props.payload;
	if (!payload) return 'pending';
	if (collectEnrollmentIntent.value && !draftEnrollmentIntent.value) return 'pending';
	if (!showCourseChoices.value) return 'valid';

	const liveStatus = String(payload.validation.status || '').trim();
	if (liveStatus === 'invalid') return 'invalid';
	if (payload.summary.ready_for_submit || liveStatus === 'ok' || liveStatus === 'not_configured') {
		return 'valid';
	}

	const storedStatus = String(payload.request.validation_status || '').trim();
	if (storedStatus === 'Invalid') return 'invalid';
	if (storedStatus === 'Valid') return 'valid';
	return 'pending';
});

const validationDisplayLabel = computed(() => {
	if (collectEnrollmentIntent.value && !draftEnrollmentIntent.value) return __('Intent required');
	if (!showCourseChoices.value) return __('Response ready');
	if (validationDisplayState.value === 'valid') return __('Ready to submit');
	if (validationDisplayState.value === 'invalid') return __('Action needed');
	return __('Review choices');
});

const validationEmptyMessage = computed(() => {
	if (collectEnrollmentIntent.value && !draftEnrollmentIntent.value) {
		return __('Choose whether the student intends to enroll before submitting.');
	}
	if (!showCourseChoices.value) {
		return __('Course choices are not required for this response.');
	}
	if (validationDisplayState.value === 'valid') {
		return __('Everything needed for submission is in place.');
	}
	if (validationDisplayState.value === 'invalid') {
		return __('Please review the course choices above before submitting.');
	}
	return __('No issues to show right now.');
});

const submitButtonLabel = computed(() =>
	showCourseChoices.value ? __('Submit Selection') : __('Submit Response')
);

function formatShortDate(value?: string | null) {
	if (!value) return __('No deadline');
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return date.toLocaleDateString(undefined, {
		month: 'short',
		day: 'numeric',
	});
}

function statusClass(status?: string | null) {
	const normalized = String(status || '').trim();
	if (normalized === 'Approved') return 'bg-leaf/10 text-leaf';
	if (normalized === 'Submitted' || normalized === 'Under Review')
		return 'bg-jacaranda/10 text-jacaranda';
	if (normalized === 'Rejected' || normalized === 'Cancelled') return 'bg-flame/10 text-flame';
	return 'bg-surface-soft text-ink/70';
}

function validationClass(status?: string | null) {
	const normalized = String(status || '').trim();
	if (normalized === 'Valid') return 'bg-leaf/10 text-leaf';
	if (normalized === 'Invalid') return 'bg-flame/10 text-flame';
	return 'bg-surface-soft text-ink/70';
}

function validationToneClass(state: 'invalid' | 'pending' | 'valid') {
	if (state === 'valid') return 'bg-leaf/10 text-leaf';
	if (state === 'invalid') return 'bg-flame/10 text-flame';
	return 'bg-surface-soft text-ink/70';
}

function applyEditorDefaults(
	rows: SelfEnrollmentChoiceCourse[],
	useChoiceRankDefaults = showGuardianChoiceRankHelp.value
) {
	const normalizedRows = (rows || []).map(normalizeChoiceRow);
	return useChoiceRankDefaults ? applyDefaultChoiceRanks(normalizedRows) : normalizedRows;
}

function updateAppliedGroup(courseName: string, basketGroup: string) {
	draftRows.value = applyEditorDefaults(
		draftRows.value.map(row =>
			row.course === courseName
				? {
						...row,
						applied_basket_group: basketGroup || null,
						choice_rank: basketGroup ? (row.choice_rank ?? null) : null,
					}
				: row
		)
	);
}

function updateChoiceRank(courseName: string, rawValue: string) {
	const parsed = Number.parseInt(String(rawValue || '').trim(), 10);
	draftRows.value = draftRows.value.map(row =>
		row.course === courseName
			? {
					...row,
					choice_rank: Number.isFinite(parsed) && parsed > 0 ? parsed : null,
				}
			: row
	);
}

function toggleOptionalSelection(courseName: string, selected: boolean, basketGroup?: string) {
	draftRows.value = applyEditorDefaults(
		draftRows.value.map(row => {
			if (row.course !== courseName) return row;
			if (!selected) {
				return {
					...row,
					is_selected: false,
					applied_basket_group: null,
					choice_rank: null,
				};
			}
			return {
				...row,
				is_selected: true,
				applied_basket_group:
					row.applied_basket_group ||
					basketGroup ||
					(row.basket_groups.length === 1 ? row.basket_groups[0] : null),
			};
		})
	);
}

function handleAppliedGroupChange(courseName: string, event: Event) {
	const target = event.target;
	const value = target instanceof HTMLSelectElement ? target.value : '';
	updateAppliedGroup(courseName, value);
}

function handleChoiceRankInput(courseName: string, event: Event) {
	const target = event.target;
	const value = target instanceof HTMLInputElement ? target.value : '';
	updateChoiceRank(courseName, value);
}

function handleOptionalToggle(courseName: string, basketGroup: string, event: Event) {
	const target = event.target;
	toggleOptionalSelection(
		courseName,
		target instanceof HTMLInputElement ? target.checked : false,
		basketGroup
	);
}
</script>
