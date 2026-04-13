<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--meeting"
			:style="overlayStyle"
			:initialFocus="closeButtonEl"
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

			<div class="if-overlay__wrap" @click.self="emitClose('backdrop')">
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
								<p class="type-overline text-ink/55">Standards Alignment</p>
								<DialogTitle class="type-h2 text-ink">Select Learning Standards</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									Choose standards from the approved catalog so the unit keeps a validated
									alignment snapshot without manual retyping.
								</p>
							</div>
							<button
								ref="closeButtonEl"
								type="button"
								class="if-overlay__close"
								aria-label="Close"
								@click="emitClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body space-y-5 px-6 pb-6">
							<section class="rounded-[1.75rem] border border-line-soft bg-surface-soft/60 p-5">
								<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
									<div class="space-y-1">
										<p class="type-overline text-ink/55">Current Unit</p>
										<h3 class="type-h3 text-ink">{{ props.unitTitle || 'Selected Unit' }}</h3>
										<p class="type-caption text-ink/70">
											{{
												props.unitProgram
													? `Program preselected: ${props.unitProgram}`
													: 'No program preselected. Choose the taxonomy path step by step.'
											}}
										</p>
									</div>
									<div class="flex flex-wrap gap-2">
										<span class="chip">{{ existingStandardsSet.size }} already on this unit</span>
										<span class="chip">{{ selectedRows.length }} selected now</span>
									</div>
								</div>
							</section>

							<section
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">Action blocked</p>
								<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">
									{{ errorMessage }}
								</p>
							</section>

							<section class="rounded-[1.75rem] border border-line-soft bg-white p-5">
								<div class="grid gap-4 lg:grid-cols-2">
									<label v-if="showFrameworkSelect" class="block space-y-2">
										<span class="type-caption text-ink/70">Framework</span>
										<select v-model="filters.framework_name" class="if-input w-full">
											<option value="">All frameworks</option>
											<option
												v-for="option in pickerOptions.frameworks"
												:key="option"
												:value="option"
											>
												{{ option }}
											</option>
										</select>
									</label>

									<label v-if="showProgramSelect" class="block space-y-2">
										<span class="type-caption text-ink/70">Program</span>
										<select v-model="filters.program" class="if-input w-full">
											<option value="">All programs</option>
											<option
												v-for="option in pickerOptions.programs"
												:key="option"
												:value="option"
											>
												{{ option }}
											</option>
										</select>
									</label>

									<label v-if="showStrandSelect" class="block space-y-2">
										<span class="type-caption text-ink/70">Strand</span>
										<select v-model="filters.strand" class="if-input w-full">
											<option value="">Choose strand</option>
											<option
												v-for="option in pickerOptions.strands"
												:key="option"
												:value="option"
											>
												{{ option }}
											</option>
										</select>
									</label>

									<label v-if="showSubstrandSelect" class="block space-y-2">
										<span class="type-caption text-ink/70">Substrand</span>
										<select v-model="filters.substrand" class="if-input w-full">
											<option value="">Choose substrand</option>
											<option
												v-for="option in substrandOptions"
												:key="option.value"
												:value="option.value"
											>
												{{ option.label }}
											</option>
										</select>
									</label>

									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">Search standards</span>
										<input
											v-model="filters.search_text"
											type="text"
											class="if-input w-full"
											placeholder="Search by code or description"
										/>
									</label>
								</div>
							</section>

							<section
								v-if="loading && !pickerResponse"
								class="rounded-2xl border border-line-soft bg-white px-5 py-8"
							>
								<p class="type-body text-ink/70">Loading learning standards...</p>
							</section>

							<section v-else class="space-y-4">
								<div
									v-if="!filters.strand"
									class="rounded-2xl border border-dashed border-line-soft bg-white px-5 py-6"
								>
									<p class="type-body-strong text-ink">
										Choose a strand to see matching standards.
									</p>
									<p class="mt-1 type-caption text-ink/70">
										The overlay narrows the catalog from framework to program to strand before
										showing the standards checklist.
									</p>
								</div>

								<div
									v-else-if="showSubstrandSelect && !filters.substrand"
									class="rounded-2xl border border-dashed border-line-soft bg-white px-5 py-6"
								>
									<p class="type-body-strong text-ink">Choose a substrand to continue.</p>
									<p class="mt-1 type-caption text-ink/70">
										This strand has one or more substrands in the approved catalog.
									</p>
								</div>

								<div
									v-else-if="!visibleStandards.length"
									class="rounded-2xl border border-dashed border-line-soft bg-white px-5 py-6"
								>
									<p class="type-body-strong text-ink">
										No learning standards match this selection.
									</p>
									<p class="mt-1 type-caption text-ink/70">
										Clear one filter or search term to broaden the result set.
									</p>
								</div>

								<div v-else class="space-y-3">
									<div class="flex flex-wrap items-center justify-between gap-3">
										<div>
											<p class="type-overline text-ink/55">Checklist</p>
											<p class="type-caption text-ink/70">
												Tick the standards that apply to this unit. Existing unit rows stay
												disabled to prevent duplicates.
											</p>
										</div>
										<div class="flex flex-wrap gap-2">
											<span class="chip">{{ visibleStandards.length }} matches</span>
											<span class="chip">{{ selectableCount }} selectable</span>
										</div>
									</div>

									<div class="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
										<label
											v-for="standard in visibleStandards"
											:key="standard.learning_standard"
											class="block rounded-2xl border border-line-soft bg-white p-4 transition"
											:class="
												existingStandardsSet.has(standard.learning_standard)
													? 'opacity-65'
													: selectedStandardIds.has(standard.learning_standard)
														? 'border-jacaranda bg-jacaranda/5'
														: 'hover:border-jacaranda/35'
											"
										>
											<div class="flex items-start gap-3">
												<input
													:checked="selectedStandardIds.has(standard.learning_standard)"
													:disabled="existingStandardsSet.has(standard.learning_standard)"
													type="checkbox"
													class="mt-1"
													@change="toggleSelection(standard, $event)"
												/>
												<div class="min-w-0 flex-1">
													<div class="flex flex-wrap items-center gap-2">
														<p class="type-body-strong text-ink">
															{{ standard.standard_code || 'Standard' }}
														</p>
														<span v-if="standard.alignment_type" class="type-caption text-ink/55">
															{{ standard.alignment_type }}
														</span>
														<span
															v-if="existingStandardsSet.has(standard.learning_standard)"
															class="type-caption text-leaf"
														>
															Already added
														</span>
													</div>
													<p class="mt-1 type-caption text-ink/80">
														{{ standard.standard_description || 'No description' }}
													</p>
													<p class="mt-2 type-caption text-ink/60">
														{{ formatTaxonomyPath(standard) }}
													</p>
												</div>
											</div>
										</label>
									</div>
								</div>
							</section>
						</div>

						<footer class="if-overlay__footer">
							<Button appearance="minimal" @click="emitClose('programmatic')">Cancel</Button>
							<Button
								appearance="primary"
								:disabled="!selectedRows.length"
								@click="applySelection"
							>
								Add Selected
							</Button>
						</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { Button, FeatherIcon } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { getLearningStandardPicker } from '@/lib/services/staff/staffTeachingService';
import type {
	Response as LearningStandardPickerResponse,
	StaffLearningStandardPickerRow,
} from '@/types/contracts/staff_teaching/get_learning_standard_picker';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	unitTitle?: string | null;
	unitProgram?: string | null;
	existingStandards?: string[];
	onApply?: (rows: StaffLearningStandardPickerRow[]) => void;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlay = useOverlayStack();
const closeButtonEl = ref<HTMLButtonElement | null>(null);
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));
const loading = ref(false);
const errorMessage = ref('');
const pickerResponse = ref<LearningStandardPickerResponse | null>(null);
const loadToken = ref(0);
const resettingFilters = ref(false);
let searchTimer: ReturnType<typeof setTimeout> | null = null;

const filters = reactive({
	framework_name: '',
	program: '',
	strand: '',
	substrand: '',
	search_text: '',
});

const selectedStandards = ref<Record<string, StaffLearningStandardPickerRow>>({});
const existingStandardsSet = computed(
	() => new Set((props.existingStandards || []).filter(value => Boolean((value || '').trim())))
);
const pickerOptions = computed(
	() =>
		pickerResponse.value?.options || {
			frameworks: [],
			programs: [],
			strands: [],
			substrands: [],
			has_blank_substrand: false,
		}
);
const substrandOptions = computed(() => [
	...(pickerOptions.value.has_blank_substrand
		? [{ value: '[No Substrand]', label: 'No Substrand' }]
		: []),
	...pickerOptions.value.substrands.map(option => ({ value: option, label: option })),
]);
const selectedRows = computed(() => Object.values(selectedStandards.value));
const selectedStandardIds = computed(() => new Set(Object.keys(selectedStandards.value)));
const visibleStandards = computed(() => pickerResponse.value?.standards || []);
const selectableCount = computed(
	() =>
		visibleStandards.value.filter(row => !existingStandardsSet.value.has(row.learning_standard))
			.length
);
const showFrameworkSelect = computed(
	() => Boolean(filters.framework_name) || pickerOptions.value.frameworks.length > 1
);
const showProgramSelect = computed(
	() =>
		Boolean(filters.framework_name) ||
		Boolean(filters.program) ||
		pickerOptions.value.frameworks.length <= 1
);
const showStrandSelect = computed(
	() =>
		Boolean(filters.program) || Boolean(filters.strand) || pickerOptions.value.programs.length <= 1
);
const showSubstrandSelect = computed(
	() =>
		Boolean(filters.strand) &&
		(pickerOptions.value.substrands.length > 0 || Boolean(pickerOptions.value.has_blank_substrand))
);

function resetOverlayState() {
	resettingFilters.value = true;
	errorMessage.value = '';
	pickerResponse.value = null;
	selectedStandards.value = {};
	filters.framework_name = '';
	filters.program = props.unitProgram || '';
	filters.strand = '';
	filters.substrand = '';
	filters.search_text = '';
	resettingFilters.value = false;
}

async function loadPicker() {
	if (!props.open) {
		return;
	}
	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const response = await getLearningStandardPicker({
			framework_name: filters.framework_name || undefined,
			program: filters.program || undefined,
			strand: filters.strand || undefined,
			substrand: filters.substrand || undefined,
			search_text: filters.search_text || undefined,
		});
		if (ticket !== loadToken.value) {
			return;
		}
		pickerResponse.value = response;
	} catch (error) {
		if (ticket !== loadToken.value) {
			return;
		}
		errorMessage.value =
			error instanceof Error ? error.message : 'Unable to load learning standards.';
		pickerResponse.value = {
			filters: {},
			options: { frameworks: [], programs: [], strands: [], substrands: [] },
			standards: [],
		};
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

function emitClose(reason: CloseReason = 'programmatic') {
	const overlayId = (props.overlayId || '').trim();
	if (overlayId) {
		try {
			overlay.close(overlayId);
			return;
		} catch {
			// Fall through to emit fallback.
		}
	}
	emit('close', reason);
}

function emitAfterLeave() {
	if (searchTimer) {
		clearTimeout(searchTimer);
		searchTimer = null;
	}
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op by design
}

function toggleSelection(standard: StaffLearningStandardPickerRow, event: Event) {
	const checked = Boolean((event.target as HTMLInputElement | null)?.checked);
	if (!standard.learning_standard || existingStandardsSet.value.has(standard.learning_standard)) {
		return;
	}
	if (checked) {
		selectedStandards.value = {
			...selectedStandards.value,
			[standard.learning_standard]: standard,
		};
		return;
	}
	const next = { ...selectedStandards.value };
	delete next[standard.learning_standard];
	selectedStandards.value = next;
}

function applySelection() {
	if (!selectedRows.value.length) {
		return;
	}
	props.onApply?.(selectedRows.value);
	emitClose('programmatic');
}

function formatTaxonomyPath(standard: StaffLearningStandardPickerRow) {
	return [
		standard.framework_name,
		standard.program,
		standard.strand,
		standard.substrand || (pickerOptions.value.has_blank_substrand ? 'No Substrand' : ''),
	]
		.filter(Boolean)
		.join(' • ');
}

watch(
	() => props.open,
	async (isOpen, wasOpen) => {
		if (isOpen && !wasOpen) {
			resetOverlayState();
			await loadPicker();
			await nextTick();
			closeButtonEl.value?.focus();
		}
	}
);

watch(
	() => [filters.framework_name, filters.program, filters.strand, filters.substrand] as const,
	(nextFilters, previousFilters) => {
		if (!props.open || resettingFilters.value) {
			return;
		}
		if (JSON.stringify(nextFilters) === JSON.stringify(previousFilters)) {
			return;
		}
		void loadPicker();
	}
);

watch(
	() => filters.search_text,
	() => {
		if (!props.open || resettingFilters.value) {
			return;
		}
		if (searchTimer) {
			clearTimeout(searchTimer);
		}
		searchTimer = setTimeout(() => {
			void loadPicker();
		}, 180);
	}
);
</script>
