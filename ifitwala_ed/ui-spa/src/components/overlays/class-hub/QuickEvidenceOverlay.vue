<!-- ifitwala_ed/ui-spa/src/components/overlays/class-hub/QuickEvidenceOverlay.vue -->
<!--
  QuickEvidenceOverlay.vue
  A specialized overlay for capturing evidence (text or link) for selected students during a class session.

  Used by:
  - ClassHub.vue (via OverlayHost)
  - StudentContextOverlay.vue
-->
<template>
	<TransitionRoot :show="open" as="template" @after-leave="$emit('after-leave')">
		<Dialog
			as="div"
			class="if-overlay if-overlay--class-hub"
			:style="overlayStyle"
			@close="emitClose"
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
				<div class="if-overlay__backdrop" />
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
							<div class="flex items-start justify-between gap-4">
								<div>
									<p class="type-overline text-slate-token/70">Quick Evidence</p>
									<h2 class="type-h2 text-ink">Capture observation</h2>
								</div>
								<button
									type="button"
									class="if-overlay__icon-button"
									aria-label="Close"
									@click="emitClose"
								>
									<span aria-hidden="true">x</span>
								</button>
							</div>
						</div>

						<div class="if-overlay__body space-y-5">
							<section class="space-y-2">
								<p class="type-caption text-slate-token/70">Students</p>
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

							<section class="space-y-2">
								<p class="type-caption text-slate-token/70">Evidence type</p>
								<div class="flex flex-wrap gap-2">
									<button
										v-for="option in evidenceTypes"
										:key="option.value"
										type="button"
										class="rounded-full border px-4 py-1 type-button-label"
										:class="
											evidenceType === option.value
												? 'border-canopy bg-canopy/10 text-canopy'
												: 'border-slate-200 bg-white text-slate-token/70'
										"
										@click="evidenceType = option.value"
									>
										{{ option.label }}
									</button>
								</div>
							</section>

							<section v-if="evidenceType === 'text'" class="space-y-2">
								<label class="type-caption text-slate-token/70" for="evidence-text"
									>Evidence text</label
								>
								<textarea
									id="evidence-text"
									v-model="evidenceText"
									rows="4"
									class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 type-body text-ink"
									placeholder="Capture what you noticed."
								></textarea>
							</section>

							<section v-else class="space-y-2">
								<label class="type-caption text-slate-token/70" for="evidence-link"
									>Evidence link</label
								>
								<input
									id="evidence-link"
									v-model="evidenceLink"
									type="text"
									class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 type-body text-ink"
									placeholder="Paste a link"
								/>
							</section>

							<p v-if="errorMessage" class="type-caption text-flame">
								{{ errorMessage }}
							</p>
						</div>

						<div class="if-overlay__footer">
							<button
								type="button"
								class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink"
								@click="emitClose"
							>
								Cancel
							</button>
							<button
								type="button"
								class="rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft"
								@click="submit"
							>
								Save evidence
							</button>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Dialog, DialogPanel, TransitionChild, TransitionRoot } from '@headlessui/vue';
import { createClassHubService } from '@/lib/classHubService';
import type { ClassHubQuickEvidencePayload } from '@/types/classHub';

type StudentOption = { student: string; student_name: string };

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	student_group: string;
	lesson_instance?: string | null;
	students?: StudentOption[];
	preselected_students?: StudentOption[];
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'after-leave'): void;
}>();

const service = createClassHubService();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));

const evidenceTypes = [
	{ value: 'text', label: 'Text note' },
	{ value: 'link', label: 'Link' },
] as const;

const evidenceType = ref<ClassHubQuickEvidencePayload['evidence_type']>('text');
const evidenceText = ref('');
const evidenceLink = ref('');
const errorMessage = ref('');

const students = computed(() => {
	const preselected = props.preselected_students || [];
	const base = props.students && props.students.length ? props.students : preselected;
	const seen = new Set<string>();
	return base.filter(row => {
		if (!row.student || seen.has(row.student)) return false;
		seen.add(row.student);
		return true;
	});
});

const selectedStudents = ref<string[]>((props.preselected_students || []).map(row => row.student));

function emitClose() {
	emit('close');
}

async function submit() {
	errorMessage.value = '';

	if (!selectedStudents.value.length) {
		errorMessage.value = 'Select at least one student.';
		return;
	}

	if (evidenceType.value === 'text' && !evidenceText.value.trim()) {
		errorMessage.value = 'Add evidence text before saving.';
		return;
	}

	if (evidenceType.value === 'link' && !evidenceLink.value.trim()) {
		errorMessage.value = 'Add a link before saving.';
		return;
	}

	const payload: ClassHubQuickEvidencePayload = {
		student_group: props.student_group,
		lesson_instance: props.lesson_instance ?? null,
		students: selectedStudents.value,
		evidence_type: evidenceType.value,
		text: evidenceType.value === 'text' ? evidenceText.value.trim() : null,
		link_url: evidenceType.value === 'link' ? evidenceLink.value.trim() : null,
	};

	try {
		await service.quickEvidence(payload);
		emitClose();
	} catch (err) {
		errorMessage.value = 'Unable to save right now.';
		console.error('[QuickEvidenceOverlay] submit failed', err);
	}
}
</script>
