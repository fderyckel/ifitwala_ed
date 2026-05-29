<!-- ifitwala_ed/ui-spa/src/components/overlays/class-hub/QuickCFUOverlay.vue -->
<!--
  QuickCFUOverlay.vue
  A specialized overlay for "Check For Understanding" (CFU) entries during a class session.
  Allows capturing signals (Thumbs, etc.) for multiple selected students.

  Used by:
  - ClassHub.vue (via OverlayHost)
-->
<template>
	<TransitionRoot :show="open" as="template" @after-leave="$emit('after-leave')">
		<Dialog
			as="div"
			class="if-overlay if-overlay--class-hub"
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
							<div class="flex items-start justify-between gap-4">
								<div>
									<p class="type-overline text-slate-token/70">{{ __('Quick CFU') }}</p>
									<h2 class="type-h2 text-ink">{{ __('Check for understanding') }}</h2>
								</div>
								<button
									type="button"
									class="if-overlay__icon-button"
									:aria-label="__('Close')"
									@click="emitClose('programmatic')"
								>
									<span aria-hidden="true">&times;</span>
								</button>
							</div>
						</div>

						<div class="if-overlay__body space-y-5">
							<section class="space-y-2">
								<p class="type-caption text-slate-token/70">{{ __('CFU type') }}</p>
								<div class="flex flex-wrap gap-2">
									<button
										v-for="option in cfuOptions"
										:key="option"
										type="button"
										class="rounded-full border px-4 py-1 type-button-label"
										:class="
											cfuType === option
												? 'border-canopy bg-canopy/10 text-canopy'
												: 'border-slate-200 bg-white text-slate-token/70'
										"
										@click="cfuType = option"
									>
										{{ cfuOptionLabel(option) }}
									</button>
								</div>
							</section>

							<section class="space-y-2">
								<label class="type-caption text-slate-token/70" for="cfu-note">
									{{ __('Class note') }}
								</label>
								<textarea
									id="cfu-note"
									v-model="classNote"
									rows="3"
									class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 type-body text-ink"
									:placeholder="__('Capture a quick class note...')"
								></textarea>
							</section>

							<section class="space-y-2">
								<p class="type-caption text-slate-token/70">{{ __('Apply signal') }}</p>
								<div class="flex flex-wrap gap-2">
									<button
										v-for="option in signalOptions"
										:key="option"
										type="button"
										class="rounded-full border px-4 py-1 type-button-label"
										:class="
											signal === option
												? 'border-jacaranda bg-jacaranda/10 text-jacaranda'
												: 'border-slate-200 bg-white text-slate-token/70'
										"
										@click="signal = option"
									>
										{{ signalOptionLabel(option) }}
									</button>
								</div>
							</section>

							<section class="space-y-2">
								<p class="type-caption text-slate-token/70">{{ __('Students') }}</p>
								<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
									<label
										v-for="student in students"
										:key="student.student"
										class="flex items-center gap-2 rounded-xl border border-slate-200 bg-white/90 px-3 py-2"
									>
										<input
											type="checkbox"
											class="h-4 w-4"
											:value="student.student"
											v-model="selectedStudents"
										/>
										<span class="type-body text-ink">{{ student.student_name }}</span>
									</label>
								</div>
							</section>

							<p v-if="errorMessage" class="type-caption text-flame">
								{{ errorMessage }}
							</p>
						</div>

						<div class="if-overlay__footer">
							<button
								type="button"
								class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink"
								@click="emitClose('programmatic')"
							>
								{{ __('Cancel') }}
							</button>
							<button
								type="button"
								class="rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft"
								@click="submit"
							>
								{{ __('Save CFU') }}
							</button>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { Dialog, DialogPanel, TransitionChild, TransitionRoot } from '@headlessui/vue';
import { createClassHubService } from '@/lib/classHubService';
import { __ } from '@/lib/i18n';
import type { ClassHubSignal } from '@/types/classHub';

type StudentOption = { student: string; student_name: string };
type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	student_group: string;
	class_session?: string | null;
	students?: StudentOption[];
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const service = createClassHubService();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));

const cfuOptions = ['Thumbs', 'Mini-whiteboard', 'Exit ticket'] as const;
const signalOptions: ClassHubSignal['signal'][] = ['Not Yet', 'Almost', 'Got It', 'Exceeded'];

const cfuType = ref<(typeof cfuOptions)[number]>('Thumbs');
const signal = ref<ClassHubSignal['signal'] | ''>('');
const classNote = ref('');
const errorMessage = ref('');

const students = computed(() => props.students || []);
const selectedStudents = ref<string[]>([]);

function cfuOptionLabel(option: (typeof cfuOptions)[number]): string {
	if (option === 'Mini-whiteboard') return __('Mini-whiteboard');
	if (option === 'Exit ticket') return __('Exit ticket');
	return __('Thumbs');
}

function signalOptionLabel(option: ClassHubSignal['signal']): string {
	if (option === 'Not Yet') return __('Not Yet');
	if (option === 'Almost') return __('Almost');
	if (option === 'Got It') return __('Got It');
	if (option === 'Exceeded') return __('Exceeded');
	return option;
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

async function submit() {
	errorMessage.value = '';

	if (!props.class_session) {
		errorMessage.value = __('Start a session before saving CFU signals.');
		return;
	}

	if (!signal.value) {
		errorMessage.value = __('Choose a signal to apply.');
		return;
	}
	const selectedSignal = signal.value;

	if (!selectedStudents.value.length) {
		errorMessage.value = __('Select at least one student.');
		return;
	}

	const payload: ClassHubSignal[] = selectedStudents.value.map(student => ({
		student,
		signal: selectedSignal,
		note: classNote.value.trim() || __('CFU: {0}', [cfuOptionLabel(cfuType.value)]),
	}));

	try {
		await service.saveSignals(props.class_session, payload);
		emitClose('programmatic');
	} catch (err) {
		errorMessage.value = __('Unable to save right now.');
		console.error('[QuickCFUOverlay] submit failed', err);
	}
}

function onDialogClose(payload: unknown) {
	void payload;
	// OverlayHost owns close enforcement.
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	value => {
		if (value) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>
