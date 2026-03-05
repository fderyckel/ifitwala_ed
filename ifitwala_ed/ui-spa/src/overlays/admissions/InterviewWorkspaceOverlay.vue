<!-- ifitwala_ed/ui-spa/src/overlays/admissions/InterviewWorkspaceOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--admissions"
			:style="overlayStyle"
			:initialFocus="closeBtnRef"
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
					<DialogPanel class="if-overlay__panel interview-workspace__panel">
						<header class="interview-workspace__header px-6 pt-6">
							<div class="min-w-0">
								<p class="type-overline text-ink/60">Admission Interview Workspace</p>
								<DialogTitle class="type-h2 text-canopy truncate">
									{{ applicantDisplayName || 'Applicant Interview' }}
								</DialogTitle>
								<p class="type-caption text-ink/65 mt-1">
									{{ interviewWindowLabel }}
								</p>
							</div>
							<button
								ref="closeBtnRef"
								type="button"
								class="if-overlay__icon-button"
								@click="emitClose('programmatic')"
								aria-label="Close interview workspace"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</header>

						<section class="if-overlay__body interview-workspace__body px-6 pb-6">
							<div v-if="loading" class="space-y-3 py-10">
								<div class="if-skel h-6 w-2/3" />
								<div class="if-skel h-20 w-full rounded-xl" />
								<div class="if-skel h-48 w-full rounded-xl" />
							</div>

							<div
								v-else-if="errorText"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
							>
								<p class="type-body-strong text-rose-900">Unable to load interview workspace</p>
								<p class="type-caption text-rose-900/85 mt-1">{{ errorText }}</p>
								<div class="mt-4 flex justify-end gap-2">
									<button class="if-action" type="button" @click="emitClose('programmatic')">
										Close
									</button>
									<button class="if-action" type="button" @click="loadWorkspace">Retry</button>
								</div>
							</div>

							<div v-else-if="workspace" class="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
								<section class="space-y-4">
									<article class="interview-card">
										<h3 class="type-h3 text-ink">Applicant Brief</h3>
										<div class="mt-3 grid gap-3 sm:grid-cols-2">
											<div>
												<p class="type-caption text-ink/65">Status</p>
												<p class="type-body-strong text-ink">
													{{ workspace.applicant.application_status || '—' }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Program Intent</p>
												<p class="type-body-strong text-ink">
													{{ workspace.applicant.program || '—' }}
													<span v-if="workspace.applicant.program_offering" class="text-ink/65">
														· {{ workspace.applicant.program_offering }}
													</span>
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">School</p>
												<p class="type-body text-ink">{{ workspace.applicant.school || '—' }}</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Applicant Email</p>
												<p class="type-body text-ink">
													{{ workspace.applicant.applicant_email || '—' }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Submitted</p>
												<p class="type-body text-ink">
													{{ formatDateTime(workspace.applicant.submitted_at) }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Date of Birth</p>
												<p class="type-body text-ink">
													{{ workspace.applicant.student_date_of_birth || '—' }}
												</p>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<div class="flex items-center justify-between gap-2">
											<h3 class="type-h3 text-ink">Guardians</h3>
											<span
												class="type-badge-label rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
											>
												{{ workspace.applicant.guardians.length }}
											</span>
										</div>
										<div
											v-if="!workspace.applicant.guardians.length"
											class="mt-2 type-caption text-ink/60"
										>
											No guardian details available.
										</div>
										<ul v-else class="mt-3 space-y-2">
											<li
												v-for="guardian in workspace.applicant.guardians"
												:key="guardian.guardian || guardian.full_name"
												class="rounded-xl border border-border/60 bg-white px-3 py-2"
											>
												<p class="type-body-strong text-ink">
													{{ guardian.full_name || 'Guardian' }}
													<span class="text-ink/60">· {{ guardian.relationship || '—' }}</span>
												</p>
												<p class="type-caption text-ink/70 mt-1">
													{{ guardian.email || 'No personal email' }}
													<span v-if="guardian.mobile_phone"> · {{ guardian.mobile_phone }}</span>
												</p>
											</li>
										</ul>
									</article>

									<article class="interview-card">
										<div class="flex items-center justify-between gap-2">
											<h3 class="type-h3 text-ink">Documents</h3>
											<span
												class="type-badge-label rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
											>
												{{ workspace.documents.count }}
											</span>
										</div>
										<div
											v-if="!workspace.documents.rows.length"
											class="mt-2 type-caption text-ink/60"
										>
											No applicant documents found.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-64 overflow-y-auto pr-1">
											<li
												v-for="doc in workspace.documents.rows"
												:key="doc.name"
												class="rounded-xl border border-border/60 px-3 py-2"
											>
												<p class="type-body-strong text-ink">
													{{ doc.document_label || doc.document_type || doc.name }}
													<span class="text-ink/60">· {{ doc.review_status || 'Pending' }}</span>
												</p>
												<p class="type-caption text-ink/70 mt-1">
													{{ doc.items.length }} file{{ doc.items.length === 1 ? '' : 's' }}
												</p>
												<ul class="mt-1 space-y-1">
													<li
														v-for="item in doc.items"
														:key="item.name || item.item_key || item.item_label"
														class="type-caption text-ink/75"
													>
														<a
															v-if="item.file_url"
															:href="item.file_url"
															target="_blank"
															rel="noreferrer"
															class="underline"
														>
															{{ item.item_label || item.file_name || 'View file' }}
														</a>
														<span v-else>{{
															item.item_label || item.item_key || 'Document item'
														}}</span>
													</li>
												</ul>
											</li>
										</ul>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">Recommendations</h3>
										<div class="mt-3 grid gap-2 sm:grid-cols-3">
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Required</p>
												<p class="type-body-strong text-ink">
													{{ workspace.recommendations.summary.required_total || 0 }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Received</p>
												<p class="type-body-strong text-ink">
													{{ workspace.recommendations.summary.received_total || 0 }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Requested</p>
												<p class="type-body-strong text-ink">
													{{ workspace.recommendations.summary.requested_total || 0 }}
												</p>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">Timeline Highlights</h3>
										<div v-if="!workspace.timeline.length" class="mt-2 type-caption text-ink/60">
											No timeline entries yet.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-56 overflow-y-auto pr-1">
											<li
												v-for="row in workspace.timeline"
												:key="row.name"
												class="rounded-xl border border-border/60 px-3 py-2"
											>
												<p class="type-caption text-ink/65">
													{{ row.comment_by || row.comment_email || 'System' }} ·
													{{ formatDateTime(row.creation) }}
												</p>
												<p class="type-body text-ink/80 mt-1" v-html="row.content || ''"></p>
											</li>
										</ul>
									</article>
								</section>

								<section class="space-y-4">
									<article class="interview-card">
										<h3 class="type-h3 text-ink">Panel Feedback</h3>
										<ul class="mt-3 space-y-2">
											<li
												v-for="member in workspace.feedback.panel"
												:key="member.interviewer_user"
												class="rounded-xl border border-border/60 px-3 py-2 flex items-center justify-between gap-2"
											>
												<p class="type-body text-ink">
													{{ member.interviewer_name || member.interviewer_user }}
												</p>
												<span class="type-caption rounded-full bg-sky/20 px-2 py-0.5 text-ink/70">
													{{ member.feedback_status || 'Pending' }}
												</span>
											</li>
										</ul>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">My Interview Feedback</h3>
										<p class="type-caption text-ink/65 mt-1">
											Separate notes per interviewer to avoid edit collisions.
										</p>

										<div
											v-if="formError"
											class="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 type-caption text-rose-900"
										>
											{{ formError }}
										</div>
										<div
											v-if="saveNotice"
											class="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 type-caption text-emerald-900"
										>
											{{ saveNotice }}
										</div>

										<div class="mt-3 space-y-3">
											<label class="block space-y-1">
												<span class="type-caption text-ink/70">Recommendation</span>
												<select
													v-model="formRecommendation"
													class="if-field"
													:disabled="!canEdit || submitting"
												>
													<option value="">Select recommendation</option>
													<option
														v-for="option in recommendationOptions"
														:key="option"
														:value="option"
													>
														{{ option }}
													</option>
												</select>
											</label>

											<label class="block space-y-1">
												<span class="type-caption text-ink/70">Strengths</span>
												<textarea
													v-model="formStrengths"
													class="if-field"
													rows="3"
													:disabled="!canEdit || submitting"
												></textarea>
											</label>

											<label class="block space-y-1">
												<span class="type-caption text-ink/70">Concerns</span>
												<textarea
													v-model="formConcerns"
													class="if-field"
													rows="3"
													:disabled="!canEdit || submitting"
												></textarea>
											</label>

											<label class="block space-y-1">
												<span class="type-caption text-ink/70">Shared Values</span>
												<textarea
													v-model="formSharedValues"
													class="if-field"
													rows="3"
													:disabled="!canEdit || submitting"
												></textarea>
											</label>

											<label class="block space-y-1">
												<span class="type-caption text-ink/70">Other Notes</span>
												<textarea
													v-model="formOtherNotes"
													class="if-field"
													rows="4"
													:disabled="!canEdit || submitting"
												></textarea>
											</label>
										</div>

										<div class="mt-4 flex flex-wrap items-center justify-end gap-2">
											<button
												type="button"
												class="if-action"
												:disabled="!canEdit || submitting"
												@click="saveDraft"
											>
												{{ submitting ? 'Saving…' : 'Save Draft' }}
											</button>
											<button
												type="button"
												class="if-action if-action--primary"
												:disabled="!canEdit || submitting"
												@click="submitFeedback"
											>
												{{ submitting ? 'Submitting…' : 'Submit Feedback' }}
											</button>
										</div>
										<p v-if="!canEdit" class="type-caption text-ink/60 mt-3">
											You are not assigned to edit feedback for this interview.
										</p>
									</article>
								</section>
							</div>
						</section>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import {
	getInterviewWorkspace,
	saveMyInterviewFeedback,
} from '@/lib/services/admissions/interviewWorkspaceService';
import type { InterviewWorkspaceResponse } from '@/types/contracts/admissions/interview_workspace';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	interview?: string | null;
	schoolEvent?: string | null;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 70 }));
const closeBtnRef = ref<HTMLButtonElement | null>(null);

const loading = ref(false);
const submitting = ref(false);
const errorText = ref<string | null>(null);
const formError = ref<string | null>(null);
const saveNotice = ref<string | null>(null);

const workspace = ref<InterviewWorkspaceResponse | null>(null);

const formStrengths = ref('');
const formConcerns = ref('');
const formSharedValues = ref('');
const formOtherNotes = ref('');
const formRecommendation = ref('');

const recommendationOptions = [
	'Strongly Recommend',
	'Recommend',
	'Recommend with Conditions',
	'Do Not Recommend',
];

const applicantDisplayName = computed(() => workspace.value?.applicant?.display_name || '');

const interviewWindowLabel = computed(() => {
	const startLabel = workspace.value?.interview?.interview_start_label;
	const endLabel = workspace.value?.interview?.interview_end_label;
	if (startLabel && endLabel) return `${startLabel} to ${endLabel}`;
	if (startLabel) return startLabel;
	return 'Interview schedule';
});

const canEdit = computed(() => Boolean(workspace.value?.feedback?.can_edit));

function emitAfterLeave() {
	emit('after-leave');
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(payload: unknown) {
	void payload;
}

function resetFormFromWorkspace() {
	formError.value = null;
	saveNotice.value = null;
	formStrengths.value = workspace.value?.feedback?.my_feedback?.strengths || '';
	formConcerns.value = workspace.value?.feedback?.my_feedback?.concerns || '';
	formSharedValues.value = workspace.value?.feedback?.my_feedback?.shared_values || '';
	formOtherNotes.value = workspace.value?.feedback?.my_feedback?.other_notes || '';
	formRecommendation.value = workspace.value?.feedback?.my_feedback?.recommendation || '';
}

async function loadWorkspace() {
	const interviewName = String(props.interview || '').trim();
	if (!interviewName) {
		errorText.value = 'Interview reference is missing from this calendar event.';
		workspace.value = null;
		return;
	}

	loading.value = true;
	errorText.value = null;
	formError.value = null;
	saveNotice.value = null;

	try {
		workspace.value = await getInterviewWorkspace(interviewName);
		resetFormFromWorkspace();
	} catch (err) {
		workspace.value = null;
		errorText.value = err instanceof Error ? err.message : 'Failed to load interview workspace.';
	} finally {
		loading.value = false;
	}
}

function hasAnyFeedbackContent() {
	return Boolean(
		formStrengths.value.trim() ||
		formConcerns.value.trim() ||
		formSharedValues.value.trim() ||
		formOtherNotes.value.trim() ||
		formRecommendation.value.trim()
	);
}

async function persistFeedback(status: 'Draft' | 'Submitted') {
	if (!workspace.value) return;
	formError.value = null;
	saveNotice.value = null;

	if (!canEdit.value) {
		formError.value = 'You are not allowed to edit feedback for this interview.';
		return;
	}

	if (status === 'Submitted' && !hasAnyFeedbackContent()) {
		formError.value = 'Add at least one feedback note before submitting.';
		return;
	}

	submitting.value = true;
	try {
		const result = await saveMyInterviewFeedback({
			interview: workspace.value.interview.name,
			strengths: formStrengths.value,
			concerns: formConcerns.value,
			shared_values: formSharedValues.value,
			other_notes: formOtherNotes.value,
			recommendation: formRecommendation.value,
			feedback_status: status,
		});

		if (workspace.value) {
			workspace.value.feedback = result.feedback;
		}
		resetFormFromWorkspace();
		saveNotice.value = status === 'Submitted' ? 'Feedback submitted.' : 'Draft saved.';
	} catch (err) {
		formError.value = err instanceof Error ? err.message : 'Failed to save feedback.';
	} finally {
		submitting.value = false;
	}
}

async function saveDraft() {
	await persistFeedback('Draft');
}

async function submitFeedback() {
	await persistFeedback('Submitted');
}

function formatDateTime(value?: string | null) {
	if (!value) return '—';
	const parsed = new Date(value);
	if (Number.isNaN(parsed.getTime())) return value;
	return parsed.toLocaleString();
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

watch(
	() => [props.open, props.interview] as const,
	([isOpen]) => {
		if (!isOpen) return;
		void loadWorkspace();
	},
	{ immediate: true }
);

watch(
	() => props.open,
	isOpen => {
		if (isOpen) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>

<style scoped>
.interview-workspace__panel {
	max-width: min(1220px, calc(100vw - 2rem));
	width: 100%;
}

.interview-workspace__header {
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.8);
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
	padding-bottom: 1rem;
}

.interview-workspace__body {
	max-height: calc(100vh - 9rem);
	overflow: auto;
	padding-top: 1rem;
}

.interview-card {
	background: white;
	border: 1px solid rgb(var(--border-rgb) / 0.7);
	border-radius: 1rem;
	padding: 1rem;
	box-shadow: 0 8px 24px rgb(15 23 42 / 0.05);
}

.if-field {
	width: 100%;
	border-radius: 0.85rem;
	border: 1px solid rgb(var(--border-rgb) / 0.85);
	background: white;
	padding: 0.62rem 0.78rem;
	font-size: 0.95rem;
	outline: none;
}

.if-field:focus {
	box-shadow: 0 0 0 2px rgb(var(--leaf-rgb) / 0.25);
}

.if-field:disabled {
	background: rgb(var(--sand-rgb) / 0.3);
	cursor: not-allowed;
}
</style>
