<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--focus"
			:style="overlayStyle"
			:initialFocus="closeBtnEl"
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
							<div class="space-y-1">
								<DialogTitle class="type-h2 text-ink"
									>Professional Development Request</DialogTitle
								>
								<p class="type-caption text-ink/60">
									{{
										budgetLocked
											? 'Budget is prefilled for this request.'
											: 'Choose a budget and submit one bounded request.'
									}}
								</p>
							</div>
							<button
								ref="closeBtnEl"
								type="button"
								class="if-overlay__icon-button"
								@click="emitClose('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-4 w-4" />
							</button>
						</div>

						<div class="if-overlay__body px-6 pb-6 space-y-5">
							<div v-if="loading" class="type-body text-ink/70">Loading request context...</div>
							<div
								v-else-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
							>
								<p class="type-body-strong text-rose-900">Could not load request context.</p>
								<p class="mt-1 type-caption text-rose-900/80">{{ errorMessage }}</p>
							</div>

							<template v-else>
								<div
									v-if="submitError"
									class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
								>
									<p class="type-body-strong text-rose-900">Request could not be submitted.</p>
									<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">
										{{ submitError }}
									</p>
								</div>

								<section class="grid gap-4 md:grid-cols-2">
									<label class="space-y-1">
										<span class="type-caption text-ink/70">Budget</span>
										<select
											v-model="form.professional_development_budget"
											class="if-overlay__input"
											:disabled="budgetLocked || submitting"
										>
											<option value="">Select budget</option>
											<option v-for="budget in budgets" :key="budget.value" :value="budget.value">
												{{ budget.label }}
											</option>
										</select>
									</label>
									<label class="space-y-1">
										<span class="type-caption text-ink/70">Theme</span>
										<select
											v-model="form.professional_development_theme"
											class="if-overlay__input"
											:disabled="submitting"
										>
											<option value="">Optional</option>
											<option v-for="theme in themes" :key="theme.value" :value="theme.value">
												{{ theme.label }}
											</option>
										</select>
									</label>
									<label class="space-y-1 md:col-span-2">
										<span class="type-caption text-ink/70">Title</span>
										<input v-model="form.title" class="if-overlay__input" :disabled="submitting" />
									</label>
									<label class="space-y-1">
										<span class="type-caption text-ink/70">Type</span>
										<select
											v-model="form.professional_development_type"
											class="if-overlay__input"
											:disabled="submitting"
										>
											<option value="">Select type</option>
											<option v-for="type in types" :key="type" :value="type">{{ type }}</option>
										</select>
									</label>
									<label class="space-y-1">
										<span class="type-caption text-ink/70">Provider</span>
										<input
											v-model="form.provider_name"
											class="if-overlay__input"
											:disabled="submitting"
										/>
									</label>
									<label class="space-y-1">
										<span class="type-caption text-ink/70">Start</span>
										<input
											v-model="form.start_datetime"
											type="datetime-local"
											class="if-overlay__input"
											:disabled="submitting"
										/>
									</label>
									<label class="space-y-1">
										<span class="type-caption text-ink/70">End</span>
										<input
											v-model="form.end_datetime"
											type="datetime-local"
											class="if-overlay__input"
											:disabled="submitting"
										/>
									</label>
									<label class="space-y-1 md:col-span-2">
										<span class="type-caption text-ink/70">Location</span>
										<input
											v-model="form.location"
											class="if-overlay__input"
											:disabled="submitting"
										/>
									</label>
								</section>

								<section class="grid gap-4 md:grid-cols-2">
									<label class="space-y-1">
										<span class="type-caption text-ink/70">PGP Plan</span>
										<select
											v-model="form.pgp_plan"
											class="if-overlay__input"
											:disabled="submitting"
										>
											<option value="">Optional</option>
											<option v-for="plan in plans" :key="plan.value" :value="plan.value">
												{{ plan.label }}
											</option>
										</select>
									</label>
									<label class="space-y-1">
										<span class="type-caption text-ink/70">PGP Goal</span>
										<select
											v-model="form.pgp_goal"
											class="if-overlay__input"
											:disabled="submitting"
										>
											<option value="">Optional</option>
											<option v-for="goal in activeGoals" :key="goal.value" :value="goal.value">
												{{ goal.label }}
											</option>
										</select>
									</label>
								</section>

								<section class="space-y-2">
									<div class="flex items-center justify-between">
										<span class="type-caption text-ink/70">Cost Breakdown</span>
										<button
											type="button"
											class="if-action"
											:disabled="submitting"
											@click="addCost"
										>
											Add cost
										</button>
									</div>
									<div
										v-for="(row, idx) in form.costs"
										:key="`pd-cost-${idx}`"
										class="grid gap-3 rounded-2xl border border-line-soft bg-surface-soft p-3 md:grid-cols-[1fr_120px_auto]"
									>
										<select
											v-model="row.cost_type"
											class="if-overlay__input"
											:disabled="submitting"
										>
											<option value="Registration">Registration</option>
											<option value="Travel">Travel</option>
											<option value="Accommodation">Accommodation</option>
											<option value="Substitute">Substitute</option>
											<option value="Materials">Materials</option>
											<option value="Other">Other</option>
										</select>
										<input
											v-model.number="row.amount"
											type="number"
											min="0"
											step="0.01"
											class="if-overlay__input"
											:disabled="submitting"
										/>
										<button
											type="button"
											class="if-action"
											:disabled="submitting || form.costs.length === 1"
											@click="removeCost(idx)"
										>
											Remove
										</button>
										<input
											v-model="row.notes"
											class="if-overlay__input md:col-span-3"
											:disabled="submitting"
											placeholder="Optional notes"
										/>
									</div>
								</section>

								<section class="space-y-2">
									<label class="flex items-center gap-2 type-caption text-ink/70">
										<input
											v-model="form.requires_substitute"
											type="checkbox"
											:disabled="submitting"
										/>
										<span>Substitute needed</span>
									</label>
									<label class="flex items-center gap-2 type-caption text-ink/70">
										<input
											v-model="form.sharing_commitment"
											type="checkbox"
											:disabled="submitting"
										/>
										<span>I will share the learning back internally</span>
									</label>
									<textarea
										v-model="form.learning_outcomes"
										rows="4"
										class="if-overlay__input"
										:disabled="submitting"
										placeholder="Expected learning outcomes"
									/>
								</section>
							</template>
						</div>

						<footer class="if-overlay__footer">
							<button
								type="button"
								class="if-button if-button--secondary"
								@click="emitClose('programmatic')"
							>
								Cancel
							</button>
							<button
								type="button"
								class="if-button if-button--primary"
								:disabled="submitting"
								@click="submitForm"
							>
								Submit request
							</button>
						</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	getProfessionalDevelopmentRequestContext,
	submitProfessionalDevelopmentRequest,
} from '@/lib/services/professionalDevelopment/professionalDevelopmentService';
import { SIGNAL_PROFESSIONAL_DEVELOPMENT_INVALIDATE, uiSignals } from '@/lib/uiSignals';
import type { Response as RequestContextResponse } from '@/types/contracts/professional_development/get_professional_development_request_context';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	budgetName?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlay = useOverlayStack();
const closeBtnEl = ref<HTMLButtonElement | null>(null);
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }));

const loading = ref(true);
const submitting = ref(false);
const errorMessage = ref('');
const submitError = ref('');
const context = ref<RequestContextResponse | null>(null);

const form = ref({
	professional_development_budget: '',
	professional_development_theme: '',
	pgp_plan: '',
	pgp_goal: '',
	title: '',
	professional_development_type: '',
	provider_name: '',
	location: '',
	start_datetime: '',
	end_datetime: '',
	requires_substitute: false,
	sharing_commitment: true,
	learning_outcomes: '',
	costs: [{ cost_type: 'Registration', amount: 0, notes: '' }],
});

const budgets = computed(() => context.value?.options?.budgets ?? []);
const themes = computed(() => context.value?.options?.themes ?? []);
const plans = computed(() => context.value?.options?.pgp_plans ?? []);
const types = computed(() => context.value?.options?.types ?? []);
const budgetLocked = computed(() => Boolean(props.budgetName));
const activePlan = computed(
	() => plans.value.find(plan => plan.value === form.value.pgp_plan) ?? null
);
const activeGoals = computed(() => activePlan.value?.goals ?? []);

function normalizeDateTimeLocal(value?: string | null) {
	return value ? value : '';
}

async function loadContext() {
	loading.value = true;
	errorMessage.value = '';
	try {
		const result = await getProfessionalDevelopmentRequestContext({
			budget_name: props.budgetName ?? undefined,
		});
		context.value = result;
		form.value = {
			professional_development_budget: result.defaults.professional_development_budget || '',
			professional_development_theme: result.defaults.professional_development_theme || '',
			pgp_plan: '',
			pgp_goal: '',
			title: '',
			professional_development_type: result.options.types[0] || '',
			provider_name: '',
			location: '',
			start_datetime: '',
			end_datetime: '',
			requires_substitute: false,
			sharing_commitment: true,
			learning_outcomes: '',
			costs: [{ cost_type: 'Registration', amount: 0, notes: '' }],
		};
	} catch (error: any) {
		errorMessage.value = error?.message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

watch(
	() => form.value.pgp_plan,
	() => {
		if (!activeGoals.value.find(goal => goal.value === form.value.pgp_goal)) {
			form.value.pgp_goal = '';
		}
	}
);

watch(
	() => form.value.professional_development_budget,
	value => {
		const selectedBudget = budgets.value.find(budget => budget.value === value);
		if (
			selectedBudget?.professional_development_theme &&
			!form.value.professional_development_theme
		) {
			form.value.professional_development_theme = selectedBudget.professional_development_theme;
		}
	}
);

onMounted(loadContext);

watch(
	() => [props.open, props.budgetName],
	([isOpen]) => {
		if (isOpen) {
			loadContext();
		}
	}
);

function emitClose(reason: CloseReason) {
	if (props.overlayId) {
		overlay.close(props.overlayId);
		return;
	}
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op: close is explicit
}

function addCost() {
	form.value.costs.push({ cost_type: 'Other', amount: 0, notes: '' });
}

function removeCost(index: number) {
	if (form.value.costs.length <= 1) return;
	form.value.costs.splice(index, 1);
}

async function submitForm() {
	submitting.value = true;
	submitError.value = '';
	try {
		await submitProfessionalDevelopmentRequest({
			professional_development_budget: form.value.professional_development_budget,
			professional_development_theme: form.value.professional_development_theme || undefined,
			pgp_plan: form.value.pgp_plan || undefined,
			pgp_goal: form.value.pgp_goal || undefined,
			title: form.value.title,
			professional_development_type: form.value.professional_development_type,
			provider_name: form.value.provider_name || undefined,
			location: form.value.location || undefined,
			start_datetime: normalizeDateTimeLocal(form.value.start_datetime),
			end_datetime: normalizeDateTimeLocal(form.value.end_datetime),
			requires_substitute: form.value.requires_substitute ? 1 : 0,
			sharing_commitment: form.value.sharing_commitment ? 1 : 0,
			learning_outcomes: form.value.learning_outcomes || undefined,
			costs: form.value.costs.map(row => ({
				cost_type: row.cost_type,
				amount: Number(row.amount || 0),
				notes: row.notes || undefined,
			})),
		});
		uiSignals.emit(SIGNAL_PROFESSIONAL_DEVELOPMENT_INVALIDATE);
		emitClose('programmatic');
	} catch (error: any) {
		submitError.value = error?.message || 'Could not submit request.';
	} finally {
		submitting.value = false;
	}
}
</script>
