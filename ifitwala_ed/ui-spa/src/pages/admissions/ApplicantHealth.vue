<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantHealth.vue -->

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<p class="type-h2 text-ink">{{ __('Health information') }}</p>
				<p class="mt-1 type-caption text-ink/60">
					{{ __('Provide complete medical details, including vaccination records.') }}
				</p>
			</div>
			<button
				type="button"
				class="rounded-full bg-ink px-4 py-2 type-caption text-white shadow-soft disabled:opacity-50"
				:disabled="isReadOnly || loading"
				@click="openEdit"
			>
				{{ __('Edit') }}
			</button>
		</div>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading health details…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load health information') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
				@click="loadHealth"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="grid gap-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ actionError }}</p>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<div class="grid gap-4 md:grid-cols-2">
					<div>
						<p class="type-caption text-ink/60">{{ __('Blood group') }}</p>
						<p class="mt-1 type-body text-ink/80">{{ displayText(health?.blood_group) }}</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Any allergies') }}</p>
						<p class="mt-1 type-body text-ink/80">
							{{ hasAllergies ? __('Yes') : __('No') }}
						</p>
					</div>
				</div>
				<div v-if="hasAllergies" class="mt-4 grid gap-3 md:grid-cols-3">
					<div>
						<p class="type-caption text-ink/60">{{ __('Food allergies') }}</p>
						<p class="mt-1 type-body text-ink/80 whitespace-pre-wrap">
							{{ displayText(health?.food_allergies) }}
						</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Insect bites') }}</p>
						<p class="mt-1 type-body text-ink/80 whitespace-pre-wrap">
							{{ displayText(health?.insect_bites) }}
						</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Medication allergies') }}</p>
						<p class="mt-1 type-body text-ink/80 whitespace-pre-wrap">
							{{ displayText(health?.medication_allergies) }}
						</p>
					</div>
				</div>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Medical conditions') }}</p>
				<div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
					<div
						v-for="item in conditionRows"
						:key="item.key"
						class="rounded-xl border border-border/60 px-3 py-2"
					>
						<p class="type-caption text-ink/60">{{ item.label }}</p>
						<p class="mt-1 type-body text-ink/80 whitespace-pre-wrap">
							{{ displayText(item.value) }}
						</p>
					</div>
				</div>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<div class="grid gap-4 md:grid-cols-2">
					<div>
						<p class="type-body-strong text-ink">{{ __('Diet requirements') }}</p>
						<p class="mt-1 type-body text-ink/80 whitespace-pre-wrap">
							{{ displayText(health?.diet_requirements) }}
						</p>
					</div>
					<div>
						<p class="type-body-strong text-ink">
							{{ __('Medical surgeries / hospitalizations') }}
						</p>
						<p class="mt-1 type-body text-ink/80 whitespace-pre-wrap">
							{{ displayText(health?.medical_surgeries__hospitalizations) }}
						</p>
					</div>
				</div>
				<div class="mt-4">
					<p class="type-body-strong text-ink">{{ __('Other medical information') }}</p>
					<p class="mt-1 type-body text-ink/80 whitespace-pre-wrap">
						{{ displayText(health?.other_medical_information) }}
					</p>
				</div>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<div class="flex items-center justify-between gap-3">
					<p class="type-body-strong text-ink">{{ __('Vaccinations') }}</p>
					<p class="type-caption text-ink/60">
						{{ vaccinationRows.length }} {{ __('record(s)') }}
					</p>
				</div>
				<div
					v-if="!vaccinationRows.length"
					class="mt-3 rounded-xl border border-border/60 px-3 py-3"
				>
					<p class="type-body text-ink/70">{{ __('No vaccinations recorded.') }}</p>
				</div>
				<div v-else class="mt-3 overflow-x-auto">
					<table class="min-w-full divide-y divide-border/70 text-left text-sm">
						<thead>
							<tr class="text-ink/60">
								<th class="py-2 pr-4">{{ __('Vaccine') }}</th>
								<th class="py-2 pr-4">{{ __('Date') }}</th>
								<th class="py-2 pr-4">{{ __('Proof') }}</th>
								<th class="py-2">{{ __('Notes') }}</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-border/50">
							<tr v-for="(row, idx) in vaccinationRows" :key="`vac-${idx}`" class="text-ink/80">
								<td class="py-2 pr-4">{{ displayText(row.vaccine_name) }}</td>
								<td class="py-2 pr-4">{{ displayText(row.date) }}</td>
								<td class="py-2 pr-4">
									<a
										v-if="row.vaccination_proof"
										:href="row.vaccination_proof"
										target="_blank"
										rel="noopener noreferrer"
										class="text-ink underline"
									>
										{{ __('View') }}
									</a>
									<span v-else>{{ __('Not provided') }}</span>
								</td>
								<td class="py-2 whitespace-pre-wrap">{{ displayText(row.additional_notes) }}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type {
	Response as HealthResponse,
	VaccinationRow,
} from '@/types/contracts/admissions/get_applicant_health';

const service = createAdmissionsService();
const overlay = useOverlayStack();
const { session } = useAdmissionsSession();

const health = ref<HealthResponse | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

function createEmptyHealth(): HealthResponse {
	return {
		blood_group: '',
		allergies: false,
		food_allergies: '',
		insect_bites: '',
		medication_allergies: '',
		asthma: '',
		bladder__bowel_problems: '',
		diabetes: '',
		headache_migraine: '',
		high_blood_pressure: '',
		seizures: '',
		bone_joints_scoliosis: '',
		blood_disorder_info: '',
		fainting_spells: '',
		hearing_problems: '',
		recurrent_ear_infections: '',
		speech_problem: '',
		birth_defect: '',
		dental_problems: '',
		g6pd: '',
		heart_problems: '',
		recurrent_nose_bleeding: '',
		vision_problem: '',
		diet_requirements: '',
		medical_surgeries__hospitalizations: '',
		other_medical_information: '',
		vaccinations: [],
	};
}

const hasAllergies = computed(() => {
	return Boolean(health.value?.allergies);
});

const conditionRows = computed(() => {
	const row = health.value || createEmptyHealth();
	return [
		{ key: 'asthma', label: __('Asthma'), value: row.asthma },
		{
			key: 'bladder__bowel_problems',
			label: __('Bladder / Bowel Problems'),
			value: row.bladder__bowel_problems,
		},
		{ key: 'diabetes', label: __('Diabetes'), value: row.diabetes },
		{ key: 'headache_migraine', label: __('Headache / Migraine'), value: row.headache_migraine },
		{
			key: 'high_blood_pressure',
			label: __('Low/High Blood Pressure'),
			value: row.high_blood_pressure,
		},
		{ key: 'seizures', label: __('Seizures'), value: row.seizures },
		{
			key: 'bone_joints_scoliosis',
			label: __('Bone Joints Scoliosis'),
			value: row.bone_joints_scoliosis,
		},
		{
			key: 'blood_disorder_info',
			label: __('Blood Disorder Info'),
			value: row.blood_disorder_info,
		},
		{ key: 'fainting_spells', label: __('Fainting Spells'), value: row.fainting_spells },
		{ key: 'hearing_problems', label: __('Hearing Problems'), value: row.hearing_problems },
		{
			key: 'recurrent_ear_infections',
			label: __('Recurrent Ear infections'),
			value: row.recurrent_ear_infections,
		},
		{ key: 'speech_problem', label: __('Speech Problem'), value: row.speech_problem },
		{ key: 'birth_defect', label: __('Birth Defect'), value: row.birth_defect },
		{ key: 'dental_problems', label: __('Dental Problems'), value: row.dental_problems },
		{ key: 'g6pd', label: __('G6PD'), value: row.g6pd },
		{ key: 'heart_problems', label: __('Heart Problems'), value: row.heart_problems },
		{
			key: 'recurrent_nose_bleeding',
			label: __('Recurrent Nose Bleeding'),
			value: row.recurrent_nose_bleeding,
		},
		{ key: 'vision_problem', label: __('Vision Problems'), value: row.vision_problem },
	];
});

const vaccinationRows = computed<VaccinationRow[]>(() => {
	return (health.value?.vaccinations || []).map(row => ({
		vaccine_name: row.vaccine_name || '',
		date: row.date || '',
		vaccination_proof: row.vaccination_proof || '',
		additional_notes: row.additional_notes || '',
	}));
});

function displayText(value: unknown): string {
	const text = typeof value === 'string' ? value.trim() : String(value || '').trim();
	return text || __('Not provided');
}

async function loadHealth() {
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		health.value = await service.getHealth();
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load health information.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

function openEdit() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	actionError.value = '';
	overlay.open('admissions-health', {
		initial: health.value || createEmptyHealth(),
		readOnly: isReadOnly.value,
	});
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadHealth();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadHealth();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
