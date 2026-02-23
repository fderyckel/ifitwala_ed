<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue -->

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<p class="type-h2 text-ink">{{ __('Profile information') }}</p>
				<p class="mt-1 type-caption text-ink/60">
					{{ __('Provide core student profile details used at promotion time.') }}
				</p>
			</div>
			<button
				type="button"
				class="rounded-full bg-ink px-4 py-2 type-caption text-white shadow-soft disabled:opacity-50"
				:disabled="isReadOnly || loading || saving || Boolean(error)"
				@click="saveProfile"
			>
				<span v-if="saving">{{ __('Saving…') }}</span>
				<span v-else>{{ __('Save profile') }}</span>
			</button>
		</div>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading profile…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load profile information') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
				@click="loadProfile"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ actionError }}</p>
			</div>
			<div
				v-if="!options.languages.length || !options.countries.length"
				class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3"
			>
				<p class="type-body-strong text-amber-900">{{ __('Setup required') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">
					{{
						__(
							'Some profile option lists are not configured yet. Please contact the admissions office.'
						)
					}}
				</p>
			</div>

			<div
				class="rounded-2xl px-4 py-4 shadow-soft"
				:class="
					completeness.ok
						? 'border border-leaf/40 bg-leaf/10'
						: 'border border-amber-200 bg-amber-50'
				"
			>
				<p
					class="type-body-strong"
					:class="completeness.ok ? 'text-emerald-900' : 'text-amber-900'"
				>
					{{
						completeness.ok
							? __('Profile information complete')
							: __('Profile information still required')
					}}
				</p>
				<p v-if="!completeness.ok" class="mt-1 type-caption text-amber-900/80">
					{{ __('Missing: {0}').replace('{0}', completeness.missing.join(', ')) }}
				</p>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Application details') }}</p>
				<div class="mt-3 grid gap-3 md:grid-cols-2">
					<div>
						<p class="type-caption text-ink/60">{{ __('School') }}</p>
						<p class="mt-1 type-body text-ink/80">{{ displayText(applicationContext.school) }}</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Organization') }}</p>
						<p class="mt-1 type-body text-ink/80">
							{{ displayText(applicationContext.organization) }}
						</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Academic year') }}</p>
						<p class="mt-1 type-body text-ink/80">
							{{ displayText(applicationContext.academic_year) }}
						</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Program') }}</p>
						<p class="mt-1 type-body text-ink/80">{{ displayText(applicationContext.program) }}</p>
					</div>
				</div>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Student profile') }}</p>
				<div class="mt-4 grid gap-4 md:grid-cols-2">
					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Preferred name') }}</span>
						<input
							v-model="profile.student_preferred_name"
							type="text"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Date of birth') }}</span>
						<input
							v-model="profile.student_date_of_birth"
							type="date"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Gender') }}</span>
						<select
							v-model="profile.student_gender"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option v-for="item in options.genders" :key="item" :value="item">
								{{ item }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Mobile number') }}</span>
						<input
							v-model="profile.student_mobile_number"
							type="text"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Joining date') }}</span>
						<input
							v-model="profile.student_joining_date"
							type="date"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Residency status') }}</span>
						<select
							v-model="profile.residency_status"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option v-for="item in options.residency_statuses" :key="item" :value="item">
								{{ item }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('First language') }}</span>
						<select
							v-model="profile.student_first_language"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.languages"
								:key="`fl-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Second language') }}</span>
						<select
							v-model="profile.student_second_language"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.languages"
								:key="`sl-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Nationality') }}</span>
						<select
							v-model="profile.student_nationality"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.countries"
								:key="`nat-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Second nationality') }}</span>
						<select
							v-model="profile.student_second_nationality"
							class="mt-1 w-full rounded-xl border border-border/70 bg-white px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.countries"
								:key="`nat2-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, computed } from 'vue';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as ApplicantProfileResponse } from '@/types/contracts/admissions/get_applicant_profile';
import type { ApplicantProfile } from '@/types/contracts/admissions/types';

const service = createAdmissionsService();
const { session } = useAdmissionsSession();

const loading = ref(false);
const saving = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');

const profile = ref<ApplicantProfile>(createEmptyProfile());
const options = ref<ApplicantProfileResponse['options']>(createEmptyOptions());
const completeness = ref<ApplicantProfileResponse['completeness']>(createEmptyCompleteness());
const applicationContext = ref<ApplicantProfileResponse['application_context']>(
	createEmptyApplicationContext()
);

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

function createEmptyProfile(): ApplicantProfile {
	return {
		student_preferred_name: '',
		student_date_of_birth: '',
		student_gender: '',
		student_mobile_number: '',
		student_joining_date: '',
		student_first_language: '',
		student_second_language: '',
		student_nationality: '',
		student_second_nationality: '',
		residency_status: '',
	};
}

function createEmptyOptions(): ApplicantProfileResponse['options'] {
	return {
		genders: [],
		residency_statuses: [],
		languages: [],
		countries: [],
	};
}

function createEmptyCompleteness(): ApplicantProfileResponse['completeness'] {
	return {
		ok: false,
		missing: [],
		required: [],
	};
}

function createEmptyApplicationContext(): ApplicantProfileResponse['application_context'] {
	return {
		organization: '',
		school: '',
		academic_year: '',
		term: '',
		program: '',
		program_offering: '',
	};
}

function displayText(value: unknown): string {
	const text = typeof value === 'string' ? value.trim() : String(value || '').trim();
	return text || __('Not provided');
}

function applyPayload(payload: ApplicantProfileResponse) {
	profile.value = {
		...createEmptyProfile(),
		...(payload.profile || {}),
	};
	options.value = payload.options || createEmptyOptions();
	completeness.value = payload.completeness || createEmptyCompleteness();
	applicationContext.value = payload.application_context || createEmptyApplicationContext();
}

async function loadProfile() {
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		const payload = await service.getProfile();
		applyPayload(payload);
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load profile information.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

async function saveProfile() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	if (error.value) {
		actionError.value = __('Please reload profile information before saving.');
		return;
	}

	saving.value = true;
	actionError.value = '';
	try {
		const payload = await service.updateProfile({
			student_preferred_name: profile.value.student_preferred_name || '',
			student_date_of_birth: profile.value.student_date_of_birth || '',
			student_gender: profile.value.student_gender || '',
			student_mobile_number: profile.value.student_mobile_number || '',
			student_joining_date: profile.value.student_joining_date || '',
			student_first_language: profile.value.student_first_language || '',
			student_second_language: profile.value.student_second_language || '',
			student_nationality: profile.value.student_nationality || '',
			student_second_nationality: profile.value.student_second_nationality || '',
			residency_status: profile.value.residency_status || '',
		});
		applyPayload(payload);
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to save profile information.');
		actionError.value = message;
	} finally {
		saving.value = false;
	}
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadProfile();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadProfile();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
