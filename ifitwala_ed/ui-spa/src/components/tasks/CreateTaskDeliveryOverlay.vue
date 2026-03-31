<!-- ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue -->
<!--
  CreateTaskDeliveryOverlay.vue
  A multi-step wizard for creating a Task (content) and Task Delivery (assignment) in one flow.
  Supports creating assignments from Calendar, Class Hub, and other contexts.

  Used by:
  - OverlayHost.vue (registered globally)
  - ClassEventModal.vue
  - StaffHome.vue
-->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay"
			:style="{ zIndex }"
			:initialFocus="initialFocus"
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
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose('programmatic')"
						>
							Close
						</button>
						<!-- Header -->
						<div class="flex items-start justify-between gap-3 px-5 pt-5">
							<div>
								<p class="type-overline">Task</p>
								<DialogTitle class="type-h3 text-ink mt-1">Create task</DialogTitle>
							</div>

							<button
								type="button"
								class="if-overlay__icon-button"
								aria-label="Close"
								@click="emitClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<!-- Body -->
						<div class="if-overlay__body">
							<div class="space-y-6">
								<template v-if="!createdTask">
									<!-- Step 1 -->
									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Step 1</span>
											<h3 class="type-h3 text-ink">What are you giving students?</h3>
										</div>

										<div class="grid gap-4 md:grid-cols-2">
											<div class="space-y-1">
												<label class="type-label">Title</label>
												<FormControl
													v-model="form.title"
													type="text"
													placeholder="Assignment title"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Type</label>
												<FormControl
													v-model="form.task_type"
													type="select"
													:options="taskTypeOptions"
													option-label="label"
													option-value="value"
													placeholder="Select type (optional)"
												/>
											</div>
										</div>

										<div class="space-y-1">
											<label class="type-label">Instructions</label>
											<FormControl
												v-model="form.instructions"
												type="textarea"
												:rows="4"
												placeholder="Share directions, resources, or expectations..."
											/>
										</div>

										<div v-if="isQuizTask" class="grid gap-4 md:grid-cols-2">
											<div class="space-y-1">
												<label class="type-label">Question bank</label>
												<FormControl
													v-model="form.quiz_question_bank"
													type="select"
													:options="quizBankOptions"
													option-label="label"
													option-value="value"
													placeholder="Select a quiz bank"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Questions per attempt</label>
												<FormControl
													v-model="form.quiz_question_count"
													type="number"
													:min="1"
													:step="1"
													placeholder="Use all if blank"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Time limit (minutes)</label>
												<FormControl
													v-model="form.quiz_time_limit_minutes"
													type="number"
													:min="1"
													:step="1"
													placeholder="Optional"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Maximum attempts</label>
												<FormControl
													v-model="form.quiz_max_attempts"
													type="number"
													:min="0"
													:step="1"
													placeholder="Unlimited if blank"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Pass percentage</label>
												<FormControl
													v-model="form.quiz_pass_percentage"
													type="number"
													:min="0"
													:max="100"
													:step="1"
													placeholder="Optional"
												/>
											</div>
										</div>
									</section>

									<!-- Step 2 -->
									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Step 2</span>
											<h3 class="type-h3 text-ink">Which class?</h3>
										</div>

										<div class="space-y-1">
											<label class="type-label">Class</label>

											<div
												v-if="isGroupLocked"
												class="rounded-xl border border-border/80 bg-slate-50 px-3 py-2 text-sm text-ink/80"
											>
												{{ selectedGroupLabel || props.prefillStudentGroup || 'Class selected' }}
											</div>

											<FormControl
												v-else
												v-model="form.student_group"
												type="select"
												:options="groupOptions"
												option-label="label"
												option-value="value"
												:disabled="groupsLoading"
												placeholder="Select a class"
											/>

											<p
												v-if="!groupsLoading && !groupOptions.length"
												class="type-caption text-slate-token/70"
											>
												No classes available for your role yet.
											</p>
										</div>
									</section>

									<!-- Step 3 -->
									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Step 3</span>
											<h3 class="type-h3 text-ink">What will happen?</h3>
										</div>

										<div class="grid gap-3 md:grid-cols-3">
											<button
												v-for="option in deliveryOptions"
												:key="option.value"
												type="button"
												class="rounded-2xl border px-4 py-4 text-left transition"
												:class="
													form.delivery_mode === option.value
														? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
														: 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'
												"
												@click="form.delivery_mode = option.value"
											>
												<p class="text-sm font-semibold text-ink">{{ option.label }}</p>
												<p class="mt-1 text-xs text-ink/60">{{ option.help }}</p>
											</button>
										</div>

										<p v-if="isQuizTask" class="type-caption text-ink/70">
											Quiz mode is controlled here: use `Assess` for an official graded quiz, or
											choose another mode for practice.
										</p>
									</section>

									<!-- Step 4 -->
									<section v-if="!isQuizTask" class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Step 4</span>
											<h3 class="type-h3 text-ink">Dates</h3>
										</div>

										<div class="grid gap-4 md:grid-cols-3">
											<div class="space-y-1">
												<label class="type-label">Available from</label>
												<input
													v-model="form.available_from"
													type="datetime-local"
													class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Due date</label>
												<input
													v-model="form.due_date"
													type="datetime-local"
													class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Lock date</label>
												<input
													v-model="form.lock_date"
													type="datetime-local"
													class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
												/>
											</div>
										</div>

										<div class="grid gap-4 md:grid-cols-2">
											<label
												v-if="showLateSubmission"
												class="flex items-center gap-2 text-sm text-ink/80"
											>
												<input
													v-model="form.allow_late_submission"
													type="checkbox"
													class="rounded border-border/70 text-jacaranda"
												/>
												Allow late submissions
											</label>
											<div
												class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-3 py-2 text-sm text-ink/70"
											>
												Group submission is paused until the subgroup workflow is implemented.
											</div>
										</div>
									</section>

									<!-- Step 5 -->
									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Step 5</span>
											<h3 class="type-h3 text-ink">Grading (optional)</h3>
										</div>

										<div class="space-y-2">
											<p class="type-label">Will you assess it?</p>
											<div class="flex flex-wrap gap-2">
												<button
													type="button"
													class="rounded-full border px-4 py-2 text-sm font-medium transition"
													:class="
														gradingEnabled
															? 'border-leaf/60 bg-sky/20 text-ink'
															: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
													"
													@click="setGradingEnabled(true)"
												>
													Yes
												</button>
												<button
													type="button"
													class="rounded-full border px-4 py-2 text-sm font-medium transition"
													:class="
														!gradingEnabled
															? 'border-leaf/60 bg-sky/20 text-ink'
															: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
													"
													@click="setGradingEnabled(false)"
												>
													No
												</button>
											</div>
										</div>

										<div v-if="gradingEnabled" class="space-y-4">
											<div class="grid gap-3 md:grid-cols-3">
												<button
													v-for="option in gradingOptions"
													:key="option.value"
													type="button"
													class="rounded-2xl border px-4 py-4 text-left transition"
													:class="
														form.grading_mode === option.value
															? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
															: 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'
													"
													@click="form.grading_mode = option.value"
												>
													<p class="text-sm font-semibold text-ink">{{ option.label }}</p>
													<p class="mt-1 text-xs text-ink/60">{{ option.help }}</p>
												</button>
											</div>

											<div v-if="form.grading_mode === 'Points'" class="max-w-xs space-y-1">
												<label class="type-label">Max points</label>
												<FormControl
													v-model="form.max_points"
													type="number"
													:min="0"
													:step="0.5"
													placeholder="Enter max points"
												/>
											</div>
										</div>

										<p class="text-xs text-ink/60">
											Moderation happens after grading (peer check).
										</p>
									</section>

									<div
										v-if="errorMessage"
										class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
									>
										{{ errorMessage }}
									</div>
								</template>

								<template v-else>
									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Created</span>
											<h3 class="type-h3 text-ink">Task saved</h3>
										</div>
										<p class="type-body text-ink/80">
											Add supporting materials while you are still in the task flow. Lesson text
											stays in lessons; these are separately openable materials for students.
										</p>
										<div class="grid gap-3 md:grid-cols-3">
											<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
												<p class="type-overline text-ink/60">Task</p>
												<p class="mt-1 type-body-strong text-ink">{{ createdTask.task }}</p>
											</div>
											<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
												<p class="type-overline text-ink/60">Delivery</p>
												<p class="mt-1 type-body-strong text-ink">
													{{ createdTask.task_delivery }}
												</p>
											</div>
											<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
												<p class="type-overline text-ink/60">Outcomes</p>
												<p class="mt-1 type-body-strong text-ink">
													{{ createdTask.outcomes_created ?? '—' }}
												</p>
											</div>
										</div>
									</section>

									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Materials</span>
											<h3 class="type-h3 text-ink">Add task materials</h3>
										</div>

										<div class="flex flex-wrap gap-2">
											<button
												type="button"
												class="rounded-full border px-4 py-2 text-sm font-medium transition"
												:class="
													materialComposerMode === 'link'
														? 'border-leaf/60 bg-sky/20 text-ink'
														: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
												"
												@click="materialComposerMode = 'link'"
											>
												Add link
											</button>
											<button
												type="button"
												class="rounded-full border px-4 py-2 text-sm font-medium transition"
												:class="
													materialComposerMode === 'file'
														? 'border-leaf/60 bg-sky/20 text-ink'
														: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
												"
												@click="materialComposerMode = 'file'"
											>
												Upload file
											</button>
										</div>

										<div class="grid gap-4 md:grid-cols-2">
											<div class="space-y-1">
												<label class="type-label">Title</label>
												<FormControl
													v-model="materialForm.title"
													type="text"
													placeholder="Material title"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">How students use it</label>
												<FormControl
													v-model="materialForm.modality"
													type="select"
													:options="materialModalityOptions"
													option-label="label"
													option-value="value"
												/>
											</div>
										</div>

										<div class="grid gap-4 md:grid-cols-2">
											<div class="space-y-1">
												<label class="type-label">Usage role</label>
												<FormControl
													v-model="materialForm.usage_role"
													type="select"
													:options="materialUsageRoleOptions"
													option-label="label"
													option-value="value"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Teacher note</label>
												<FormControl
													v-model="materialForm.placement_note"
													type="text"
													placeholder="Optional note for students"
												/>
											</div>
										</div>

										<div class="space-y-1">
											<label class="type-label">Description</label>
											<FormControl
												v-model="materialForm.description"
												type="textarea"
												:rows="3"
												placeholder="Optional context about this material"
											/>
										</div>

										<div v-if="materialComposerMode === 'link'" class="space-y-1">
											<label class="type-label">Reference URL</label>
											<FormControl
												v-model="materialForm.reference_url"
												type="text"
												placeholder="https://..."
											/>
										</div>

										<div v-else class="space-y-3">
											<input
												ref="materialFileInput"
												type="file"
												class="hidden"
												@change="onMaterialFileSelected"
											/>
											<div class="flex flex-wrap items-center gap-3">
												<Button appearance="secondary" @click="materialFileInput?.click()">
													Choose file
												</Button>
												<p class="type-caption text-ink/70">
													{{ selectedMaterialFile?.name || 'No file selected yet.' }}
												</p>
											</div>
										</div>

										<div
											v-if="materialError"
											class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
										>
											{{ materialError }}
										</div>

										<div class="flex justify-end">
											<Button
												appearance="primary"
												:loading="materialSubmitting"
												:disabled="!canAddMaterial"
												@click="addMaterial"
											>
												{{ materialComposerMode === 'link' ? 'Add link' : 'Upload file' }}
											</Button>
										</div>
									</section>

									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center justify-between gap-3">
											<div class="flex items-center gap-3">
												<span class="chip">Shared</span>
												<h3 class="type-h3 text-ink">Current task materials</h3>
											</div>
											<span class="chip">{{ taskMaterials.length }} items</span>
										</div>

										<div
											v-if="materialsLoading"
											class="rounded-xl border border-line-soft bg-surface-soft px-4 py-3 text-sm text-ink/70"
										>
											Loading materials...
										</div>

										<div
											v-else-if="!taskMaterials.length"
											class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-4 py-3 text-sm text-ink/70"
										>
											No materials shared on this task yet.
										</div>

										<div v-else class="space-y-3">
											<article
												v-for="material in taskMaterials"
												:key="material.placement"
												class="rounded-2xl border border-line-soft bg-surface-soft p-4"
											>
												<div class="flex items-start justify-between gap-3">
													<div class="min-w-0">
														<div class="flex flex-wrap items-center gap-2">
															<p class="type-body-strong text-ink">{{ material.title }}</p>
															<span class="chip">{{ material.material_type }}</span>
															<span v-if="material.usage_role" class="chip">
																{{ material.usage_role }}
															</span>
														</div>
														<p v-if="material.description" class="mt-2 type-caption text-ink/70">
															{{ material.description }}
														</p>
														<p
															v-if="material.placement_note"
															class="mt-2 type-caption text-ink/70"
														>
															{{ material.placement_note }}
														</p>
														<p
															v-if="material.file_name || material.reference_url"
															class="mt-2 type-caption text-ink/70"
														>
															{{ material.file_name || material.reference_url }}
														</p>
													</div>
													<div class="flex items-center gap-2">
														<a
															v-if="material.open_url"
															:href="material.open_url"
															target="_blank"
															rel="noreferrer"
															class="if-action"
														>
															Open
														</a>
														<Button
															appearance="secondary"
															:loading="removingPlacement === material.placement"
															@click="removeMaterial(material.placement)"
														>
															Remove
														</Button>
													</div>
												</div>
											</article>
										</div>
									</section>
								</template>
							</div>
						</div>

						<!-- Footer -->
						<div class="if-overlay__footer">
							<Button appearance="secondary" @click="emitClose('programmatic')">
								{{ createdTask ? 'Done' : 'Cancel' }}
							</Button>
							<Button
								v-if="!createdTask"
								appearance="primary"
								:loading="submitting"
								:disabled="!canSubmit"
								@click="submit"
							>
								Create
							</Button>
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
import { Button, FormControl, createResource, toast, FeatherIcon } from 'frappe-ui';
import type { CreateTaskDeliveryInput, CreateTaskDeliveryPayload } from '@/types/tasks';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	prefillStudentGroup?: string | null;
	prefillDueDate?: string | null;
	prefillAvailableFrom?: string | null;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'created', payload: CreateTaskDeliveryPayload): void;
	(e: 'after-leave'): void;
}>();

const open = computed(() => props.open);
const zIndex = computed(() => props.zIndex ?? 60);

const submitting = ref(false);
const errorMessage = ref('');
const createdTask = ref<CreateTaskDeliveryPayload | null>(null);
const taskMaterials = ref<TaskMaterialRow[]>([]);
const materialComposerMode = ref<'link' | 'file'>('link');
const materialSubmitting = ref(false);
const materialError = ref('');
const selectedMaterialFile = ref<File | null>(null);
const materialFileInput = ref<HTMLInputElement | null>(null);
const removingPlacement = ref<string | null>(null);

const initialFocus = ref<HTMLElement | null>(null);

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

/**
 * HeadlessUI Dialog @close payload is ambiguous (boolean/undefined).
 * Under A+, ignore it and close only via explicit backdrop/esc/button paths.
 */
function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

const taskTypeOptions = [
	{ label: 'Assignment', value: 'Assignment' },
	{ label: 'Homework', value: 'Homework' },
	{ label: 'Classwork', value: 'Classwork' },
	{ label: 'Quiz', value: 'Quiz' },
	{ label: 'Test', value: 'Test' },
	{ label: 'Summative assessment', value: 'Summative assessment' },
	{ label: 'Formative assessment', value: 'Formative assessment' },
	{ label: 'Discussion', value: 'Discussion' },
	{ label: 'Project', value: 'Project' },
	{ label: 'Long Term Project', value: 'Long Term Project' },
	{ label: 'Exam', value: 'Exam' },
	{ label: 'Other', value: 'Other' },
];

type DeliveryMode = CreateTaskDeliveryInput['delivery_mode'];
type TaskMaterialRow = {
	placement: string;
	material: string;
	title: string;
	material_type: 'File' | 'Reference Link';
	modality?: 'Read' | 'Watch' | 'Listen' | 'Use' | null;
	description?: string | null;
	reference_url?: string | null;
	open_url?: string | null;
	file_name?: string | null;
	file_size?: string | null;
	usage_role?: 'Required' | 'Reference' | 'Template' | 'Example' | null;
	placement_note?: string | null;
};

const deliveryOptions: Array<{ label: string; value: DeliveryMode; help: string }> = [
	{
		label: 'Just post it',
		value: 'Assign Only',
		help: 'Share the assignment without collecting work.',
	},
	{
		label: 'Collect work',
		value: 'Collect Work',
		help: 'Students submit evidence; grading is optional.',
	},
	{ label: 'Collect and assess', value: 'Assess', help: 'Collect evidence and grade it.' },
];

const gradingOptions = [
	{ label: 'Points', value: 'Points', help: 'Score work with a numeric total.' },
	{ label: 'Complete / Not complete', value: 'Completion', help: 'Track completion only.' },
	{ label: 'Yes / No', value: 'Binary', help: 'Simple yes or no grading.' },
];
const materialModalityOptions = [
	{ label: 'Read', value: 'Read' },
	{ label: 'Watch', value: 'Watch' },
	{ label: 'Listen', value: 'Listen' },
	{ label: 'Use', value: 'Use' },
];
const materialUsageRoleOptions = [
	{ label: 'Reference', value: 'Reference' },
	{ label: 'Required', value: 'Required' },
	{ label: 'Template', value: 'Template' },
	{ label: 'Example', value: 'Example' },
];

type FormState = {
	title: string;
	instructions: string;
	task_type: string;
	quiz_question_bank: string;
	quiz_question_count: string;
	quiz_time_limit_minutes: string;
	quiz_max_attempts: string;
	quiz_pass_percentage: string;
	student_group: string;
	delivery_mode: DeliveryMode;
	available_from: string;
	due_date: string;
	lock_date: string;
	allow_late_submission: boolean;
	group_submission: boolean;
	grading_mode: string;
	max_points: string;
};
type MaterialFormState = {
	title: string;
	description: string;
	reference_url: string;
	modality: 'Read' | 'Watch' | 'Listen' | 'Use';
	usage_role: 'Required' | 'Reference' | 'Template' | 'Example';
	placement_note: string;
};

const form = reactive<FormState>({
	title: '',
	instructions: '',
	task_type: '',
	quiz_question_bank: '',
	quiz_question_count: '',
	quiz_time_limit_minutes: '',
	quiz_max_attempts: '',
	quiz_pass_percentage: '',
	student_group: '',
	delivery_mode: 'Assign Only',
	available_from: '',
	due_date: '',
	lock_date: '',
	allow_late_submission: false,
	group_submission: false,
	grading_mode: '',
	max_points: '',
});
const materialForm = reactive<MaterialFormState>({
	title: '',
	description: '',
	reference_url: '',
	modality: 'Read',
	usage_role: 'Reference',
	placement_note: '',
});

const gradingEnabled = ref(false);

function unwrapMessage<T>(res: any): T | undefined {
	if (res && typeof res === 'object' && 'message' in res) return (res as any).message;
	return res as T;
}

const isGroupLocked = computed(() => !!props.prefillStudentGroup);

const groups = ref<Array<{ name: string; student_group_name?: string }>>([]);

const groupResource = createResource({
	url: 'ifitwala_ed.api.student_groups.fetch_groups',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (rows: any) => {
		groups.value = Array.isArray(rows) ? rows : [];
	},
	onError: () => {
		groups.value = [];
		toast.create({ appearance: 'danger', message: 'Unable to load classes right now.' });
	},
});

const groupsLoading = computed(() => groupResource.loading);

const quizBanks = ref<Array<{ name: string; bank_title?: string; course?: string }>>([]);

const quizBankResource = createResource({
	url: 'ifitwala_ed.api.quiz.list_question_banks',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (rows: any) => {
		quizBanks.value = Array.isArray(rows) ? rows : [];
	},
	onError: () => {
		quizBanks.value = [];
	},
});

const groupOptions = computed(() =>
	groups.value.map(row => ({
		label: row.student_group_name || row.name,
		value: row.name,
	}))
);

const quizBankOptions = computed(() =>
	quizBanks.value.map(row => ({
		label: row.course
			? `${row.bank_title || row.name} · ${row.course}`
			: row.bank_title || row.name,
		value: row.name,
	}))
);

const selectedGroupLabel = computed(() => {
	const match = groupOptions.value.find(o => o.value === form.student_group);
	return match?.label || '';
});

const showLateSubmission = computed(() => form.delivery_mode !== 'Assign Only');
const isQuizTask = computed(() => form.task_type === 'Quiz');

watch(
	() => form.delivery_mode,
	mode => {
		if (mode === 'Assign Only') {
			form.allow_late_submission = false;
		}
	}
);

const canSubmit = computed(() => {
	if (!form.title.trim()) return false;
	if (!form.student_group) return false;
	if (!form.delivery_mode) return false;
	if (isQuizTask.value && !form.quiz_question_bank) return false;
	if (!gradingEnabled.value) return true;
	if (!form.grading_mode) return false;
	if (form.grading_mode === 'Points' && !String(form.max_points || '').trim()) return false;
	return true;
});
const canAddMaterial = computed(() => {
	if (!createdTask.value || materialSubmitting.value) return false;
	if (!materialForm.title.trim()) return false;
	if (materialComposerMode.value === 'link') return Boolean(materialForm.reference_url.trim());
	return Boolean(selectedMaterialFile.value);
});

watch(
	() => props.open,
	openNow => {
		if (!openNow) return;

		initializeForm();

		// quick-link mode (no prefill) => load dropdown list
		if (!isGroupLocked.value) {
			groupResource.submit({});
		}
		quizBankResource.submit({});
	},
	{ immediate: true }
);

watch(
	() => props.open,
	v => {
		if (v) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});

function initializeForm() {
	createdTask.value = null;
	form.title = '';
	form.instructions = '';
	form.task_type = '';
	form.quiz_question_bank = '';
	form.quiz_question_count = '';
	form.quiz_time_limit_minutes = '';
	form.quiz_max_attempts = '';
	form.quiz_pass_percentage = '';
	form.student_group = props.prefillStudentGroup || '';
	form.delivery_mode = 'Assign Only';
	form.available_from = toDateTimeInput(props.prefillAvailableFrom);
	form.due_date = toDateTimeInput(props.prefillDueDate);
	form.lock_date = '';
	form.allow_late_submission = false;
	form.group_submission = false;
	form.grading_mode = '';
	form.max_points = '';
	gradingEnabled.value = false;
	errorMessage.value = '';
	resetMaterialComposer();
}

function setGradingEnabled(value: boolean) {
	gradingEnabled.value = value;
	if (!value) {
		form.grading_mode = '';
		form.max_points = '';
	}
}

watch(
	() => form.task_type,
	taskType => {
		if (taskType === 'Quiz') {
			form.delivery_mode = 'Assign Only';
			gradingEnabled.value = false;
			form.grading_mode = '';
			form.max_points = '';
			return;
		}
		form.quiz_question_bank = '';
		form.quiz_question_count = '';
		form.quiz_time_limit_minutes = '';
		form.quiz_max_attempts = '';
		form.quiz_pass_percentage = '';
	}
);

function toDateTimeInput(value?: string | null) {
	if (!value) return '';
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00'] = timeRaw.split(':');
		return `${date}T${hour}:${minute}`;
	}
	if (value.includes(' ')) {
		const [date, timeRaw] = value.split(' ');
		const [hour = '00', minute = '00'] = timeRaw.split(':');
		return `${date}T${hour}:${minute}`;
	}
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return '';
	return formatDateTimeInput(date);
}

function formatDateTimeInput(date: Date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');
	return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function toFrappeDatetime(value: string) {
	if (!value) return null;
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00', second = '00'] = timeRaw.split(':');
		return `${date} ${hour}:${minute}:${second}`;
	}
	return value;
}

/**
 * SPA POST contract: send the payload body directly.
 */
const createTaskResource = createResource({
	url: 'ifitwala_ed.assessment.task_creation_service.create_task_and_delivery',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] createTaskResource:error', err);
	},
});
const listTaskMaterialsResource = createResource({
	url: 'ifitwala_ed.api.materials.list_task_materials',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (payload: any) => {
		taskMaterials.value = Array.isArray(payload?.materials) ? payload.materials : [];
	},
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] listTaskMaterials:error', err);
		taskMaterials.value = [];
	},
});
const createTaskReferenceMaterialResource = createResource({
	url: 'ifitwala_ed.api.materials.create_task_reference_material',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] createTaskReferenceMaterial:error', err);
	},
});
const removeTaskMaterialResource = createResource({
	url: 'ifitwala_ed.api.materials.remove_task_material',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] removeTaskMaterial:error', err);
	},
});
const materialsLoading = computed(() => listTaskMaterialsResource.loading);

function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== 'string' || !raw.trim()) {
		return [];
	}
	try {
		const entries = JSON.parse(raw);
		if (!Array.isArray(entries)) return [];
		return entries
			.map((entry: unknown) => {
				if (typeof entry !== 'string') return String(entry || '');
				try {
					const payload = JSON.parse(entry);
					return typeof payload?.message === 'string' ? payload.message : entry;
				} catch {
					return entry;
				}
			})
			.filter((message: string) => Boolean((message || '').trim()));
	} catch {
		return [];
	}
}

function resetMaterialDraftFields() {
	materialForm.title = '';
	materialForm.description = '';
	materialForm.reference_url = '';
	materialForm.modality = 'Read';
	materialForm.usage_role = 'Reference';
	materialForm.placement_note = '';
	selectedMaterialFile.value = null;
	if (materialFileInput.value) materialFileInput.value.value = '';
}

function resetMaterialComposer() {
	materialComposerMode.value = 'link';
	materialSubmitting.value = false;
	materialError.value = '';
	taskMaterials.value = [];
	removingPlacement.value = null;
	resetMaterialDraftFields();
}

async function loadTaskMaterials() {
	if (!createdTask.value) return;
	await listTaskMaterialsResource.submit({ task: createdTask.value.task });
}

function onMaterialFileSelected(event: Event) {
	const target = event.target as HTMLInputElement | null;
	const file = target?.files?.[0] || null;
	selectedMaterialFile.value = file;
	materialError.value = '';
	if (file && !materialForm.title.trim()) {
		materialForm.title = file.name;
	}
}

async function uploadTaskMaterialFileRequest(task: string): Promise<TaskMaterialRow> {
	if (!selectedMaterialFile.value) {
		throw new Error('Please choose a file first.');
	}

	const formData = new FormData();
	formData.append('task', task);
	formData.append('title', materialForm.title.trim());
	if (materialForm.description.trim())
		formData.append('description', materialForm.description.trim());
	if (materialForm.placement_note.trim())
		formData.append('placement_note', materialForm.placement_note.trim());
	formData.append('modality', materialForm.modality);
	formData.append('usage_role', materialForm.usage_role);
	formData.append('file', selectedMaterialFile.value, selectedMaterialFile.value.name);

	const csrfToken =
		((window as any)?.csrf_token as string | undefined) ||
		((window as any)?.frappe?.csrf_token as string | undefined) ||
		'';
	const response = await fetch('/api/method/ifitwala_ed.api.materials.upload_task_material_file', {
		method: 'POST',
		credentials: 'same-origin',
		body: formData,
		headers: csrfToken ? { 'X-Frappe-CSRF-Token': csrfToken } : undefined,
	});

	const data = await response.json().catch(() => ({}));
	if (!response.ok || data?.exception || data?.exc) {
		const serverMessages = parseServerMessages(data?._server_messages);
		throw new Error(
			serverMessages.join('\n') || data?.message || response.statusText || 'Upload failed.'
		);
	}
	return (data?.message ?? data) as TaskMaterialRow;
}

async function addMaterial() {
	if (!createdTask.value) return;
	if (!canAddMaterial.value) {
		materialError.value =
			materialComposerMode.value === 'link'
				? 'Please provide a title and link.'
				: 'Please provide a title and choose a file.';
		return;
	}

	materialSubmitting.value = true;
	materialError.value = '';
	try {
		if (materialComposerMode.value === 'link') {
			await createTaskReferenceMaterialResource.submit({
				task: createdTask.value.task,
				title: materialForm.title.trim(),
				reference_url: materialForm.reference_url.trim(),
				description: materialForm.description.trim() || undefined,
				modality: materialForm.modality,
				usage_role: materialForm.usage_role,
				placement_note: materialForm.placement_note.trim() || undefined,
			});
		} else {
			await uploadTaskMaterialFileRequest(createdTask.value.task);
		}

		await loadTaskMaterials();
		resetMaterialDraftFields();
		toast.create({ appearance: 'success', message: 'Material added to the task.' });
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to add the material right now.';
		materialError.value = message;
		toast.create({ appearance: 'danger', message });
	} finally {
		materialSubmitting.value = false;
	}
}

async function removeMaterial(placement: string) {
	if (!createdTask.value || !placement) return;
	removingPlacement.value = placement;
	try {
		await removeTaskMaterialResource.submit({
			task: createdTask.value.task,
			placement,
		});
		await loadTaskMaterials();
		toast.create({ appearance: 'success', message: 'Material removed from this task.' });
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to remove this material right now.';
		materialError.value = message;
		toast.create({ appearance: 'danger', message });
	} finally {
		removingPlacement.value = null;
	}
}

async function submit() {
	if (!canSubmit.value) {
		const missing: string[] = [];
		if (!form.title.trim()) missing.push('Title');
		if (!form.student_group) missing.push('Class');
		if (isQuizTask.value && !form.quiz_question_bank) missing.push('Quiz question bank');
		if (gradingEnabled.value) {
			if (!form.grading_mode) missing.push('Grading mode');
			if (form.grading_mode === 'Points' && !String(form.max_points || '').trim())
				missing.push('Max points');
		}

		const msg = missing.length
			? `Please complete: ${missing.join(', ')}.`
			: 'Please complete the required fields.';
		errorMessage.value = msg;
		toast.create({ appearance: 'warning', message: msg });
		return;
	}

	submitting.value = true;
	errorMessage.value = '';

	const payload: CreateTaskDeliveryInput = {
		title: form.title.trim(),
		student_group: form.student_group,
		delivery_mode: form.delivery_mode,
		allow_late_submission:
			form.delivery_mode === 'Assign Only' ? 0 : form.allow_late_submission ? 1 : 0,
		group_submission: form.group_submission ? 1 : 0,
	};

	if (form.instructions.trim()) payload.instructions = form.instructions.trim();
	if (form.task_type) payload.task_type = form.task_type;
	if (isQuizTask.value) {
		payload.quiz_question_bank = form.quiz_question_bank;
		if (form.quiz_question_count) payload.quiz_question_count = form.quiz_question_count as any;
		if (form.quiz_time_limit_minutes)
			payload.quiz_time_limit_minutes = form.quiz_time_limit_minutes as any;
		if (form.quiz_max_attempts) payload.quiz_max_attempts = form.quiz_max_attempts as any;
		if (form.quiz_pass_percentage) payload.quiz_pass_percentage = form.quiz_pass_percentage as any;
	}
	if (form.available_from) payload.available_from = toFrappeDatetime(form.available_from) as any;
	if (form.due_date) payload.due_date = toFrappeDatetime(form.due_date) as any;
	if (form.lock_date) payload.lock_date = toFrappeDatetime(form.lock_date) as any;

	if (isQuizTask.value) {
		payload.grading_mode = form.delivery_mode === 'Assess' ? ('Points' as any) : ('None' as any);
	} else if (gradingEnabled.value) {
		payload.grading_mode = form.grading_mode as any;
		if (form.grading_mode === 'Points') payload.max_points = form.max_points as any;
	} else {
		payload.grading_mode = 'None' as any;
	}

	try {
		const res = await createTaskResource.submit(payload);
		const out = res as CreateTaskDeliveryPayload | undefined;

		if (!out?.task || !out?.task_delivery) throw new Error('Unexpected server response.');

		emit('created', out);
		createdTask.value = out;
		await loadTaskMaterials();
		toast.create({
			appearance: 'success',
			message: 'Task created. Add materials or close when done.',
		});
	} catch (error) {
		console.error('[CreateTaskDeliveryOverlay] submit:error', error);
		const msg =
			error instanceof Error ? error.message : 'Unable to create the assignment right now.';
		errorMessage.value = msg;
		toast.create({ appearance: 'danger', message: msg });
	} finally {
		submitting.value = false;
	}
}
</script>
