<!-- ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantHealthOverlay.vue -->

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
					<DialogPanel class="if-overlay__panel">
						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">{{ __('Health information') }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{ __('Complete all relevant health details and vaccination records.') }}
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

						<div class="if-overlay__body px-6 pb-6 space-y-5">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">{{ __('Something went wrong') }}</p>
								<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">
									{{ errorMessage }}
								</p>
							</div>

							<section
								class="space-y-3 rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
							>
								<p class="type-body-strong text-ink">{{ __('General') }}</p>
								<div class="grid gap-3 md:grid-cols-2">
									<div class="space-y-2">
										<p class="type-caption text-ink/70">{{ __('Blood group') }}</p>
										<select
											v-model="form.blood_group"
											class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
											:disabled="isReadOnly || submitting"
										>
											<option value="">{{ __('Select blood group') }}</option>
											<option v-for="option in bloodGroupOptions" :key="option" :value="option">
												{{ option }}
											</option>
										</select>
									</div>
									<div class="space-y-2">
										<p class="type-caption text-ink/70">{{ __('Any allergies') }}</p>
										<label class="inline-flex items-center gap-2 type-body text-ink/80">
											<input
												type="checkbox"
												v-model="form.allergies"
												class="h-4 w-4 rounded border-border/70"
												:disabled="isReadOnly || submitting"
											/>
											<span>{{ __('Student has allergies') }}</span>
										</label>
									</div>
								</div>
								<div v-if="form.allergies" class="grid gap-3 md:grid-cols-3">
									<div class="space-y-2">
										<p class="type-caption text-ink/70">{{ __('Food allergies') }}</p>
										<textarea
											v-model="form.food_allergies"
											class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
											rows="2"
											:disabled="isReadOnly || submitting"
										/>
									</div>
									<div class="space-y-2">
										<p class="type-caption text-ink/70">{{ __('Insect bites') }}</p>
										<textarea
											v-model="form.insect_bites"
											class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
											rows="2"
											:disabled="isReadOnly || submitting"
										/>
									</div>
									<div class="space-y-2">
										<p class="type-caption text-ink/70">{{ __('Medication allergies') }}</p>
										<textarea
											v-model="form.medication_allergies"
											class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
											rows="2"
											:disabled="isReadOnly || submitting"
										/>
									</div>
								</div>
							</section>

							<section
								class="space-y-3 rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
							>
								<p class="type-body-strong text-ink">{{ __('Medical conditions') }}</p>
								<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
									<div v-for="field in conditionFields" :key="field.key" class="space-y-2">
										<p class="type-caption text-ink/70">{{ field.label }}</p>
										<textarea
											v-model="form[field.key]"
											class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
											rows="2"
											:disabled="isReadOnly || submitting"
										/>
									</div>
								</div>
							</section>

							<section
								class="space-y-3 rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
							>
								<p class="type-body-strong text-ink">{{ __('Other data') }}</p>
								<div class="grid gap-3 md:grid-cols-2">
									<div class="space-y-2">
										<p class="type-caption text-ink/70">{{ __('Diet requirements') }}</p>
										<textarea
											v-model="form.diet_requirements"
											class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
											rows="3"
											:disabled="isReadOnly || submitting"
										/>
									</div>
									<div class="space-y-2">
										<p class="type-caption text-ink/70">
											{{ __('Medical surgeries / hospitalizations') }}
										</p>
										<textarea
											v-model="form.medical_surgeries__hospitalizations"
											class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
											rows="3"
											:disabled="isReadOnly || submitting"
										/>
									</div>
								</div>
								<div class="space-y-2">
									<p class="type-caption text-ink/70">{{ __('Other medical information') }}</p>
									<textarea
										v-model="form.other_medical_information"
										class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
										rows="4"
										:disabled="isReadOnly || submitting"
									/>
								</div>
							</section>

							<section
								class="space-y-3 rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
							>
								<div class="flex items-center justify-between gap-2">
									<p class="type-body-strong text-ink">{{ __('Vaccinations') }}</p>
									<button
										type="button"
										class="rounded-full border border-border/70 bg-white px-3 py-1 type-caption text-ink/70 disabled:opacity-50"
										:disabled="isReadOnly || submitting"
										@click="addVaccination"
									>
										{{ __('Add vaccination') }}
									</button>
								</div>
								<div
									v-if="!form.vaccinations.length"
									class="rounded-xl border border-border/60 px-3 py-3"
								>
									<p class="type-caption text-ink/60">{{ __('No vaccination entries yet.') }}</p>
								</div>
								<div
									v-for="(row, idx) in form.vaccinations"
									:key="`vaccination-${idx}`"
									class="rounded-xl border border-border/60 px-3 py-3 space-y-3"
								>
									<div class="flex items-center justify-between gap-2">
										<p class="type-caption text-ink/70">{{ __('Vaccination') }} {{ idx + 1 }}</p>
										<button
											type="button"
											class="rounded-full border border-border/60 bg-white px-3 py-1 type-caption text-ink/70 disabled:opacity-50"
											:disabled="isReadOnly || submitting"
											@click="removeVaccination(idx)"
										>
											{{ __('Remove') }}
										</button>
									</div>
									<div class="grid gap-3 md:grid-cols-2">
										<div class="space-y-2">
											<p class="type-caption text-ink/70">{{ __('Vaccine name') }} *</p>
											<input
												v-model="row.vaccine_name"
												type="text"
												class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
												:disabled="isReadOnly || submitting"
											/>
										</div>
										<div class="space-y-2">
											<p class="type-caption text-ink/70">{{ __('Date') }} *</p>
											<input
												v-model="row.date"
												type="date"
												class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
												:disabled="isReadOnly || submitting"
											/>
										</div>
									</div>
									<div class="grid gap-3 md:grid-cols-2">
										<div class="space-y-2">
											<p class="type-caption text-ink/70">{{ __('Vaccination proof URL') }}</p>
											<input
												v-model="row.vaccination_proof"
												type="text"
												placeholder="/files/example.png"
												class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
												:disabled="isReadOnly || submitting"
											/>
										</div>
										<div class="space-y-2">
											<p class="type-caption text-ink/70">{{ __('Additional notes') }}</p>
											<input
												v-model="row.additional_notes"
												type="text"
												class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
												:disabled="isReadOnly || submitting"
											/>
										</div>
									</div>
								</div>
							</section>
						</div>

						<div
							class="if-overlay__footer px-6 pb-6 flex flex-wrap items-center justify-between gap-3"
						>
							<p class="type-caption text-ink/55">
								{{
									isReadOnly
										? __('This application is read-only.')
										: __('You can update this later if needed.')
								}}
							</p>
							<div class="flex items-center gap-3">
								<button
									type="button"
									class="rounded-full border border-border/70 bg-white px-4 py-2 type-caption text-ink/70"
									@click="emitClose('programmatic')"
								>
									{{ __('Cancel') }}
								</button>
								<button
									type="button"
									class="rounded-full bg-ink px-5 py-2 type-caption text-white shadow-soft disabled:opacity-50"
									:disabled="isReadOnly || submitting"
									@click="submit"
								>
									<span v-if="submitting" class="inline-flex items-center gap-2">
										<Spinner class="h-4 w-4" /> {{ __('Saving…') }}
									</span>
									<span v-else>{{ __('Save') }}</span>
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
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import type { Response as HealthPayload } from '@/types/contracts/admissions/get_applicant_health';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type ConditionKey =
	| 'asthma'
	| 'bladder__bowel_problems'
	| 'diabetes'
	| 'headache_migraine'
	| 'high_blood_pressure'
	| 'seizures'
	| 'bone_joints_scoliosis'
	| 'blood_disorder_info'
	| 'fainting_spells'
	| 'hearing_problems'
	| 'recurrent_ear_infections'
	| 'speech_problem'
	| 'birth_defect'
	| 'dental_problems'
	| 'g6pd'
	| 'heart_problems'
	| 'recurrent_nose_bleeding'
	| 'vision_problem';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	initial?: HealthPayload | null;
	readOnly?: boolean;
}>();
const emit = defineEmits(['close', 'after-leave', 'done']);

const overlay = useOverlayStack();
const service = createAdmissionsService();

const submitting = ref(false);
const errorMessage = ref('');

const bloodGroupOptions = [
	'A Positive',
	'A Negative',
	'AB Positive',
	'AB Negative',
	'B Positive',
	'B Negative',
	'O Positive',
	'O Negative',
];

const conditionFields: { key: ConditionKey; label: string }[] = [
	{ key: 'asthma', label: __('Asthma') },
	{ key: 'bladder__bowel_problems', label: __('Bladder / Bowel Problems') },
	{ key: 'diabetes', label: __('Diabetes') },
	{ key: 'headache_migraine', label: __('Headache / Migraine') },
	{ key: 'high_blood_pressure', label: __('Low/High Blood Pressure') },
	{ key: 'seizures', label: __('Seizures') },
	{ key: 'bone_joints_scoliosis', label: __('Bone Joints Scoliosis') },
	{ key: 'blood_disorder_info', label: __('Blood Disorder Info') },
	{ key: 'fainting_spells', label: __('Fainting Spells') },
	{ key: 'hearing_problems', label: __('Hearing Problems') },
	{ key: 'recurrent_ear_infections', label: __('Recurrent Ear infections') },
	{ key: 'speech_problem', label: __('Speech Problem') },
	{ key: 'birth_defect', label: __('Birth Defect') },
	{ key: 'dental_problems', label: __('Dental Problems') },
	{ key: 'g6pd', label: __('G6PD') },
	{ key: 'heart_problems', label: __('Heart Problems') },
	{ key: 'recurrent_nose_bleeding', label: __('Recurrent Nose Bleeding') },
	{ key: 'vision_problem', label: __('Vision Problems') },
];

const form = reactive<HealthPayload>({
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
});

const overlayStyle = computed(() => ({
	zIndex: props.zIndex || 0,
}));

const isReadOnly = computed(() => Boolean(props.readOnly));

function setError(err: unknown, fallback: string) {
	const msg =
		(typeof err === 'object' && err && 'message' in (err as any)
			? String((err as any).message)
			: '') ||
		(typeof err === 'string' ? err : '') ||
		fallback;
	errorMessage.value = msg;
}

function clearError() {
	errorMessage.value = '';
}

function resetForm() {
	const initial = props.initial;
	form.blood_group = initial?.blood_group || '';
	form.allergies = Boolean(initial?.allergies);
	form.food_allergies = initial?.food_allergies || '';
	form.insect_bites = initial?.insect_bites || '';
	form.medication_allergies = initial?.medication_allergies || '';
	form.asthma = initial?.asthma || '';
	form.bladder__bowel_problems = initial?.bladder__bowel_problems || '';
	form.diabetes = initial?.diabetes || '';
	form.headache_migraine = initial?.headache_migraine || '';
	form.high_blood_pressure = initial?.high_blood_pressure || '';
	form.seizures = initial?.seizures || '';
	form.bone_joints_scoliosis = initial?.bone_joints_scoliosis || '';
	form.blood_disorder_info = initial?.blood_disorder_info || '';
	form.fainting_spells = initial?.fainting_spells || '';
	form.hearing_problems = initial?.hearing_problems || '';
	form.recurrent_ear_infections = initial?.recurrent_ear_infections || '';
	form.speech_problem = initial?.speech_problem || '';
	form.birth_defect = initial?.birth_defect || '';
	form.dental_problems = initial?.dental_problems || '';
	form.g6pd = initial?.g6pd || '';
	form.heart_problems = initial?.heart_problems || '';
	form.recurrent_nose_bleeding = initial?.recurrent_nose_bleeding || '';
	form.vision_problem = initial?.vision_problem || '';
	form.diet_requirements = initial?.diet_requirements || '';
	form.medical_surgeries__hospitalizations = initial?.medical_surgeries__hospitalizations || '';
	form.other_medical_information = initial?.other_medical_information || '';
	form.vaccinations = (initial?.vaccinations || []).map(row => ({
		vaccine_name: row.vaccine_name || '',
		date: row.date || '',
		vaccination_proof: row.vaccination_proof || '',
		additional_notes: row.additional_notes || '',
	}));
}

function addVaccination() {
	form.vaccinations.push({
		vaccine_name: '',
		date: '',
		vaccination_proof: '',
		additional_notes: '',
	});
}

function removeVaccination(index: number) {
	form.vaccinations.splice(index, 1);
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
	clearError();
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op (A+ contract)
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	val => {
		if (val) {
			resetForm();
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

function cleanValue(value: unknown): string {
	return typeof value === 'string' ? value.trim() : String(value || '').trim();
}

async function submit() {
	if (isReadOnly.value) {
		setError('', __('This application is read-only.'));
		return;
	}
	const invalidVaccinationIndex = form.vaccinations.findIndex(
		row => !cleanValue(row.vaccine_name) || !cleanValue(row.date)
	);
	if (invalidVaccinationIndex >= 0) {
		setError(
			'',
			__('Each vaccination row requires vaccine name and date. Missing row: {0}.').replace(
				'{0}',
				String(invalidVaccinationIndex + 1)
			)
		);
		return;
	}

	submitting.value = true;
	clearError();
	try {
		await service.updateHealth({
			blood_group: cleanValue(form.blood_group),
			allergies: Boolean(form.allergies),
			food_allergies: cleanValue(form.food_allergies),
			insect_bites: cleanValue(form.insect_bites),
			medication_allergies: cleanValue(form.medication_allergies),
			asthma: cleanValue(form.asthma),
			bladder__bowel_problems: cleanValue(form.bladder__bowel_problems),
			diabetes: cleanValue(form.diabetes),
			headache_migraine: cleanValue(form.headache_migraine),
			high_blood_pressure: cleanValue(form.high_blood_pressure),
			seizures: cleanValue(form.seizures),
			bone_joints_scoliosis: cleanValue(form.bone_joints_scoliosis),
			blood_disorder_info: cleanValue(form.blood_disorder_info),
			fainting_spells: cleanValue(form.fainting_spells),
			hearing_problems: cleanValue(form.hearing_problems),
			recurrent_ear_infections: cleanValue(form.recurrent_ear_infections),
			speech_problem: cleanValue(form.speech_problem),
			birth_defect: cleanValue(form.birth_defect),
			dental_problems: cleanValue(form.dental_problems),
			g6pd: cleanValue(form.g6pd),
			heart_problems: cleanValue(form.heart_problems),
			recurrent_nose_bleeding: cleanValue(form.recurrent_nose_bleeding),
			vision_problem: cleanValue(form.vision_problem),
			diet_requirements: cleanValue(form.diet_requirements),
			medical_surgeries__hospitalizations: cleanValue(form.medical_surgeries__hospitalizations),
			other_medical_information: cleanValue(form.other_medical_information),
			vaccinations: form.vaccinations.map(row => ({
				vaccine_name: cleanValue(row.vaccine_name),
				date: cleanValue(row.date),
				vaccination_proof: cleanValue(row.vaccination_proof),
				additional_notes: cleanValue(row.additional_notes),
			})),
		});
		emitClose('programmatic');
		emit('done');
	} catch (err) {
		setError(err, __('Unable to save health information.'));
	} finally {
		submitting.value = false;
	}
}
</script>
