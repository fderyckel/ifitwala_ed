<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantEnrollmentChoices.vue -->

<template>
	<div class="admissions-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">{{ __('Course choices') }}</h1>
				<p class="type-meta text-ink/70">
					{{
						__(
							'Choose optional courses from your program offering. Required courses stay visible for reference, and enrollment baskets show which requirement group each course can satisfy.'
						)
					}}
				</p>
			</div>
			<div class="page-header__actions">
				<RouterLink
					:to="buildRouteLocation('admissions-status')"
					class="if-button if-button--secondary"
				>
					{{ __('Review offer') }}
				</RouterLink>
			</div>
		</header>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading course choices…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load course choices') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button type="button" class="if-button if-button--secondary mt-3" @click="loadChoices">
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80 whitespace-pre-wrap">{{ actionError }}</p>
			</div>

			<div v-if="successMessage" class="rounded-2xl border border-leaf/40 bg-leaf/10 px-4 py-3">
				<p class="type-body-strong text-emerald-900">{{ __('Saved') }}</p>
				<p class="mt-1 type-caption text-emerald-900/80">{{ successMessage }}</p>
			</div>

			<div class="grid gap-3 sm:grid-cols-3">
				<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
					<p class="type-caption text-ink/60">{{ __('Program Offering') }}</p>
					<p class="mt-1 type-body text-ink">{{ plan?.program_offering || __('—') }}</p>
				</div>
				<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
					<p class="type-caption text-ink/60">{{ __('Academic Year') }}</p>
					<p class="mt-1 type-body text-ink">{{ plan?.academic_year || __('—') }}</p>
				</div>
				<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
					<p class="type-caption text-ink/60">{{ __('Optional choices saved') }}</p>
					<p class="mt-1 type-body text-ink">
						{{
							__('{0} of {1}')
								.replace('{0}', String(summary?.selected_optional_count || 0))
								.replace('{1}', String(summary?.optional_course_count || 0))
						}}
					</p>
				</div>
			</div>

			<div
				v-if="summary?.has_plan"
				class="rounded-2xl px-4 py-4 shadow-soft"
				:class="
					validation?.ready_for_offer_response
						? 'border border-leaf/40 bg-leaf/10'
						: 'border border-amber-200 bg-amber-50'
				"
			>
				<p
					class="type-body-strong"
					:class="validation?.ready_for_offer_response ? 'text-emerald-900' : 'text-amber-900'"
				>
					{{
						validation?.ready_for_offer_response
							? __('Course choices are ready for offer response')
							: __('Course choices still need attention')
					}}
				</p>
				<p
					class="mt-1 type-caption whitespace-pre-wrap"
					:class="
						validation?.ready_for_offer_response ? 'text-emerald-900/80' : 'text-amber-900/80'
					"
				>
					{{ validationMessage }}
				</p>
			</div>

			<div
				v-if="!summary?.has_plan"
				class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
			>
				<p class="type-body-strong text-ink">{{ __('No enrollment offer yet') }}</p>
				<p class="mt-1 type-caption text-ink/60">
					{{
						summary?.message ||
						__('Course choices will appear once admissions sends your enrollment offer.')
					}}
				</p>
			</div>

			<template v-else>
				<section
					v-if="requiredCourses.length"
					class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
				>
					<div class="flex flex-wrap items-center justify-between gap-3">
						<div>
							<p class="type-body-strong text-ink">{{ __('Required courses') }}</p>
							<p class="mt-1 type-caption text-ink/60">
								{{
									__(
										'These courses are part of your program offering and stay locked by admissions.'
									)
								}}
							</p>
						</div>
						<p class="type-caption text-ink/55">
							{{ __('{0} course(s)').replace('{0}', String(requiredCourses.length)) }}
						</p>
					</div>

					<div class="mt-4 grid gap-3">
						<div
							v-for="course in requiredCourses"
							:key="`required:${course.course}`"
							class="rounded-xl border border-border/60 bg-surface/30 px-4 py-3"
						>
							<div class="flex flex-wrap items-start justify-between gap-3">
								<div>
									<p class="type-body text-ink">{{ course.course_name || course.course }}</p>
									<p class="mt-1 type-caption text-ink/60">{{ course.course }}</p>
								</div>
								<span
									class="rounded-full border border-border/60 bg-white px-3 py-1 type-caption text-ink/70"
								>
									{{ __('Required') }}
								</span>
							</div>

							<p v-if="course.basket_groups.length" class="mt-2 type-caption text-ink/60">
								{{
									__('Eligible enrollment baskets: {0}').replace(
										'{0}',
										course.basket_groups.join(', ')
									)
								}}
							</p>

							<div v-if="course.basket_groups.length > 1" class="mt-3 max-w-sm">
								<label class="type-caption text-ink/60">
									{{ __('Counts toward enrollment basket') }}
								</label>
								<select
									class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 text-sm text-ink disabled:bg-surface"
									:disabled="!canEditChoices"
									:value="course.applied_basket_group || ''"
									@change="handleRequiredBasketGroupChange(course.course, $event)"
								>
									<option value="">{{ __('Choose an enrollment basket') }}</option>
									<option
										v-for="basketGroup in course.basket_groups"
										:key="`${course.course}:${basketGroup}`"
										:value="basketGroup"
									>
										{{ basketGroup }}
									</option>
								</select>
								<p
									v-if="course.requires_basket_group_selection"
									class="mt-2 type-caption text-amber-800"
								>
									{{
										__('Choose the enrollment basket this required course should count toward.')
									}}
								</p>
							</div>

							<p
								v-else-if="course.basket_groups.length === 1"
								class="mt-3 type-caption text-ink/60"
							>
								{{ __('Counts toward {0}').replace('{0}', course.basket_groups[0]) }}
							</p>
						</div>
					</div>
				</section>

				<section
					v-for="section in basketSections"
					:key="section.basket_group"
					class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
				>
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<div class="flex flex-wrap items-center gap-2">
								<p class="type-body-strong text-ink">{{ section.basket_group }}</p>
								<span
									v-if="section.required_by_rule"
									class="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 type-caption text-amber-900"
								>
									{{ __('Required enrollment basket') }}
								</span>
							</div>
							<p class="mt-1 type-caption text-ink/60">
								{{
									section.required_by_rule
										? __(
												'Choose at least one course in this enrollment basket before accepting the offer.'
											)
										: __('Optional enrollment basket.')
								}}
							</p>
						</div>
						<p class="type-caption text-ink/55">
							{{ __('Selected {0}').replace('{0}', String(section.selected_count)) }}
						</p>
					</div>

					<div class="mt-4 grid gap-3">
						<label
							v-for="course in section.courses"
							:key="`${section.basket_group}:${course.course}`"
							class="rounded-xl border border-border/60 px-4 py-3"
							:class="course.selected_in_group ? 'bg-sand/35' : 'bg-white'"
						>
							<div class="flex items-start gap-3">
								<input
									type="checkbox"
									class="mt-1 h-4 w-4 rounded border-border text-ink"
									:checked="course.selected_in_group"
									:disabled="!canEditChoices || course.selected_elsewhere"
									@change="handleOptionalCourseToggle(course.course, section.basket_group, $event)"
								/>
								<div class="min-w-0 flex-1">
									<div class="flex flex-wrap items-center gap-2">
										<p class="type-body text-ink">{{ course.course_name || course.course }}</p>
										<span
											v-if="course.selected_elsewhere"
											class="rounded-full border border-border/60 bg-surface px-3 py-1 type-caption text-ink/65"
										>
											{{ __('Selected in {0}').replace('{0}', course.applied_basket_group || '') }}
										</span>
									</div>
									<p class="mt-1 type-caption text-ink/60">{{ course.course }}</p>
									<p v-if="course.basket_groups.length > 1" class="mt-1 type-caption text-ink/55">
										{{
											__('Also available in: {0}').replace(
												'{0}',
												course.basket_groups
													.filter(group => group !== section.basket_group)
													.join(', ')
											)
										}}
									</p>

									<div
										v-if="course.selected_in_group"
										class="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center"
									>
										<label class="type-caption text-ink/60">
											{{ __('Preference rank') }}
										</label>
										<input
											type="number"
											min="1"
											inputmode="numeric"
											class="w-24 rounded-xl border border-border/70 bg-white px-3 py-2 text-sm text-ink"
											:disabled="!canEditChoices"
											:value="course.choice_rank ?? ''"
											@input="handleChoiceRankInput(course.course, $event)"
										/>
										<p class="type-caption text-ink/50">
											{{
												__(
													'Optional. Use this only if you want to rank multiple choices in the same basket.'
												)
											}}
										</p>
									</div>
								</div>
							</div>
						</label>
					</div>
				</section>

				<section
					v-if="ungroupedCourses.length"
					class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
				>
					<div>
						<p class="type-body-strong text-ink">{{ __('Other optional courses') }}</p>
						<p class="mt-1 type-caption text-ink/60">
							{{ __('These optional courses are available without basket-group resolution.') }}
						</p>
					</div>

					<div class="mt-4 grid gap-3">
						<label
							v-for="course in ungroupedCourses"
							:key="`ungrouped:${course.course}`"
							class="rounded-xl border border-border/60 px-4 py-3"
							:class="course.is_selected ? 'bg-sand/35' : 'bg-white'"
						>
							<div class="flex items-start gap-3">
								<input
									type="checkbox"
									class="mt-1 h-4 w-4 rounded border-border text-ink"
									:checked="course.is_selected"
									:disabled="!canEditChoices"
									@change="handleUngroupedCourseToggle(course.course, $event)"
								/>
								<div class="min-w-0 flex-1">
									<p class="type-body text-ink">{{ course.course_name || course.course }}</p>
									<p class="mt-1 type-caption text-ink/60">{{ course.course }}</p>
								</div>
							</div>
						</label>
					</div>
				</section>

				<div class="flex flex-wrap items-center gap-3">
					<button
						type="button"
						class="if-button if-button--primary"
						:disabled="!canEditChoices || saving || !summary?.has_courses"
						@click="saveChoices"
					>
						{{ saving ? __('Saving…') : __('Save choices') }}
					</button>
					<p v-if="hasUnsavedChanges" class="type-caption text-amber-800">
						{{ __('You have unsaved course-choice changes.') }}
					</p>
					<p v-else class="type-caption text-ink/55">
						{{
							canEditChoices
								? __('Save before returning to your offer response.')
								: __('Course choices are read-only right now.')
						}}
					</p>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import {
	buildEnrollmentChoiceSections,
	haveEnrollmentChoiceRowsChanged,
	normalizeEnrollmentChoiceRow,
	enrollmentChoiceRowsForSubmit,
} from '@/pages/admissions/applicantEnrollmentChoices';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type {
	ApplicantEnrollmentChoiceCourse,
	Response as EnrollmentChoicesResponse,
} from '@/types/contracts/admissions/get_applicant_enrollment_choices';

const service = createAdmissionsService();
const { currentApplicantName, buildRouteLocation } = useAdmissionsSession();

const payload = ref<EnrollmentChoicesResponse | null>(null);
const formRows = ref<ApplicantEnrollmentChoiceCourse[]>([]);
const savedRows = ref<ApplicantEnrollmentChoiceCourse[]>([]);
const loading = ref(false);
const saving = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');
const successMessage = ref('');

const plan = computed(() => payload.value?.plan || null);
const summary = computed(() => payload.value?.summary || null);
const validation = computed(() => payload.value?.validation || null);
const requiredBasketGroups = computed(() => payload.value?.required_basket_groups || []);
const canEditChoices = computed(() => Boolean(plan.value?.can_edit_choices));
const hasUnsavedChanges = computed(() =>
	haveEnrollmentChoiceRowsChanged(formRows.value, savedRows.value)
);
const sections = computed(() =>
	buildEnrollmentChoiceSections(formRows.value, requiredBasketGroups.value)
);
const requiredCourses = computed(() => sections.value.required_courses);
const basketSections = computed(() => sections.value.basket_sections);
const ungroupedCourses = computed(() => sections.value.ungrouped_courses);

const validationMessage = computed(() => {
	if (validation.value?.ready_for_offer_response) {
		return canEditChoices.value
			? __(
					'Your saved course choices satisfy the current basket rules. You can return to the offer page when ready.'
				)
			: __('The saved course choices satisfy the current basket rules.');
	}

	const reasons = validation.value?.reasons || [];
	if (reasons.length) return reasons.join('\n');
	return (
		summary.value?.message || __('Save your course selections before responding to the offer.')
	);
});

function cloneRows(rows: ApplicantEnrollmentChoiceCourse[]) {
	return (rows || []).map(row => normalizeEnrollmentChoiceRow(row));
}

async function loadChoices() {
	if (!currentApplicantName.value) {
		payload.value = null;
		formRows.value = [];
		savedRows.value = [];
		error.value = null;
		return;
	}
	loading.value = true;
	error.value = null;
	actionError.value = '';
	successMessage.value = '';
	try {
		const response = await service.getApplicantEnrollmentChoices({
			student_applicant: currentApplicantName.value,
		});
		payload.value = response;
		savedRows.value = cloneRows(response.courses || []);
		formRows.value = cloneRows(response.courses || []);
	} catch (err) {
		error.value = err instanceof Error ? err.message : __('Unable to load course choices.');
	} finally {
		loading.value = false;
	}
}

function updateCourseRow(
	courseName: string,
	mutator: (row: ApplicantEnrollmentChoiceCourse) => ApplicantEnrollmentChoiceCourse
) {
	formRows.value = formRows.value.map(row => {
		if (row.course !== courseName) return row;
		return normalizeEnrollmentChoiceRow(
			mutator({ ...row, basket_groups: [...(row.basket_groups || [])] })
		);
	});
}

function handleRequiredBasketGroupChange(courseName: string, event: Event) {
	const value = ((event.target as HTMLSelectElement | null)?.value || '').trim();
	actionError.value = '';
	successMessage.value = '';
	updateCourseRow(courseName, row => ({
		...row,
		applied_basket_group: value || null,
	}));
}

function handleOptionalCourseToggle(courseName: string, basketGroup: string, event: Event) {
	const checked = Boolean((event.target as HTMLInputElement | null)?.checked);
	actionError.value = '';
	successMessage.value = '';
	updateCourseRow(courseName, row => ({
		...row,
		is_selected: checked,
		applied_basket_group: checked ? basketGroup : null,
		choice_rank: checked ? (row.choice_rank ?? null) : null,
	}));
}

function handleUngroupedCourseToggle(courseName: string, event: Event) {
	const checked = Boolean((event.target as HTMLInputElement | null)?.checked);
	actionError.value = '';
	successMessage.value = '';
	updateCourseRow(courseName, row => ({
		...row,
		is_selected: checked,
		applied_basket_group: null,
		choice_rank: null,
	}));
}

function handleChoiceRankInput(courseName: string, event: Event) {
	const raw = ((event.target as HTMLInputElement | null)?.value || '').trim();
	const rank = raw ? Number.parseInt(raw, 10) : null;
	actionError.value = '';
	successMessage.value = '';
	updateCourseRow(courseName, row => ({
		...row,
		choice_rank: rank && rank > 0 ? rank : null,
	}));
}

async function saveChoices() {
	if (!plan.value) {
		actionError.value = __('No enrollment plan is available yet.');
		return;
	}
	if (!canEditChoices.value) {
		actionError.value = __('Course choices are read-only right now.');
		return;
	}
	if (!summary.value?.has_courses) {
		actionError.value = __('No program-offering courses are configured for this offer.');
		return;
	}
	if (!hasUnsavedChanges.value) {
		actionError.value = __('No course-choice changes to save.');
		return;
	}
	if (!currentApplicantName.value) {
		actionError.value = __('Applicant context is unavailable.');
		return;
	}

	saving.value = true;
	actionError.value = '';
	successMessage.value = '';
	try {
		const response = await service.updateApplicantEnrollmentChoices({
			student_applicant: currentApplicantName.value,
			courses: enrollmentChoiceRowsForSubmit(formRows.value),
		});
		payload.value = response;
		savedRows.value = cloneRows(response.courses || []);
		formRows.value = cloneRows(response.courses || []);
		successMessage.value = __('Course choices saved.');
	} catch (err) {
		actionError.value = err instanceof Error ? err.message : __('Unable to save course choices.');
	} finally {
		saving.value = false;
	}
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadChoices();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadChoices();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
