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
								<p class="type-overline text-ink/60">{{ workspaceOverline }}</p>
								<DialogTitle class="type-h2 text-canopy truncate">
									{{ applicantDisplayName || 'Applicant Workspace' }}
								</DialogTitle>
								<p class="type-caption text-ink/65 mt-1">
									{{ interviewWindowLabel }}
								</p>
							</div>

							<div class="flex items-center gap-2">
								<button
									v-if="showBackToApplicant"
									type="button"
									class="if-action"
									@click="returnToApplicantMode"
								>
									Back to Applicant
								</button>
								<button
									ref="closeBtnRef"
									type="button"
									class="if-overlay__icon-button"
									@click="emitClose('programmatic')"
									aria-label="Close interview workspace"
								>
									<FeatherIcon name="x" class="h-5 w-5" />
								</button>
							</div>
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

							<div v-else-if="hasWorkspace" class="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
								<section class="space-y-4">
									<article class="interview-card">
										<h3 class="type-h3 text-ink">Applicant Brief</h3>
										<div class="mt-3 grid gap-3 sm:grid-cols-2">
											<div>
												<p class="type-caption text-ink/65">Status</p>
												<p class="type-body-strong text-ink">
													{{ workspaceApplicant?.application_status || '—' }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Program Intent</p>
												<p class="type-body-strong text-ink">
													{{ workspaceApplicant?.program || '—' }}
													<span v-if="workspaceApplicant?.program_offering" class="text-ink/65">
														· {{ workspaceApplicant.program_offering }}
													</span>
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">School</p>
												<p class="type-body text-ink">{{ workspaceApplicant?.school || '—' }}</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Applicant Email</p>
												<p class="type-body text-ink">
													{{ workspaceApplicant?.applicant_email || '—' }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Submitted</p>
												<p class="type-body text-ink">
													{{ formatDateTime(workspaceApplicant?.submitted_at) }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Date of Birth</p>
												<p class="type-body text-ink">
													{{ workspaceApplicant?.student_date_of_birth || '—' }}
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
												{{ workspaceApplicant?.guardians?.length || 0 }}
											</span>
										</div>
										<div
											v-if="!(workspaceApplicant?.guardians?.length || 0)"
											class="mt-2 type-caption text-ink/60"
										>
											No guardian details available.
										</div>
										<ul v-else class="mt-3 space-y-2">
											<li
												v-for="guardian in workspaceApplicant?.guardians || []"
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
												{{ workspaceDocuments.count }}
											</span>
										</div>
										<div
											v-if="!workspaceDocuments.rows.length"
											class="mt-2 type-caption text-ink/60"
										>
											No applicant documents found.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-64 overflow-y-auto pr-1">
											<li
												v-for="doc in workspaceDocuments.rows"
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
													{{ workspaceRecommendations.summary.required_total || 0 }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Received</p>
												<p class="type-body-strong text-ink">
													{{ workspaceRecommendations.summary.received_total || 0 }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Requested</p>
												<p class="type-body-strong text-ink">
													{{ workspaceRecommendations.summary.requested_total || 0 }}
												</p>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">Timeline Highlights</h3>
										<div v-if="!workspaceTimeline.length" class="mt-2 type-caption text-ink/60">
											No timeline entries yet.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-56 overflow-y-auto pr-1">
											<li
												v-for="row in workspaceTimeline"
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
										<div class="flex items-center justify-between gap-2">
											<h3 class="type-h3 text-ink">Interviews</h3>
											<span
												class="type-badge-label rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
											>
												{{ workspaceInterviews.length }}
											</span>
										</div>
										<div v-if="!workspaceInterviews.length" class="mt-2 type-caption text-ink/60">
											No interviews recorded yet for this applicant.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-72 overflow-y-auto pr-1">
											<li
												v-for="item in workspaceInterviews"
												:key="item.name"
												class="rounded-xl border px-3 py-2"
												:class="
													isActiveInterview(item.name)
														? 'border-canopy bg-canopy/5'
														: 'border-border/60 bg-white'
												"
											>
												<div class="flex items-start justify-between gap-3">
													<div class="min-w-0">
														<p class="type-body-strong text-ink truncate">
															{{ item.interview_type || 'Interview' }}
															<span class="text-ink/60">· {{ item.name }}</span>
														</p>
														<p class="type-caption text-ink/70 mt-1">
															{{
																item.interview_start_label || item.interview_date || 'No date set'
															}}
															<span v-if="item.interview_end_label">
																→ {{ item.interview_end_label }}</span
															>
														</p>
														<p
															v-if="item.interviewers?.length"
															class="type-caption text-ink/65 mt-1 truncate"
														>
															{{ item.interviewers.map(row => row.name || row.user).join(', ') }}
														</p>
													</div>
													<button
														type="button"
														class="if-action"
														:disabled="loading"
														@click="openInterview(item.name)"
													>
														{{ isActiveInterview(item.name) ? 'Opened' : 'Open' }}
													</button>
												</div>
											</li>
										</ul>
									</article>

									<template v-if="isInterviewMode && workspace">
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
													<span
														class="type-caption rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
													>
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
									</template>

									<article v-else class="interview-card">
										<h3 class="type-h3 text-ink">Interview Notes</h3>
										<p class="type-caption text-ink/70 mt-2">
											Select an interview to view panel feedback and submit interviewer notes.
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
	getApplicantWorkspace,
	getInterviewWorkspace,
	saveMyInterviewFeedback,
} from '@/lib/services/admissions/interviewWorkspaceService';
import type {
	ApplicantWorkspaceResponse,
	InterviewWorkspaceInterview,
	InterviewWorkspaceResponse,
} from '@/types/contracts/admissions/interview_workspace';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	interview?: string | null;
	schoolEvent?: string | null;
	mode?: 'interview' | 'applicant' | null;
	studentApplicant?: string | null;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type WorkspaceMode = 'interview' | 'applicant';

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
const applicantWorkspace = ref<ApplicantWorkspaceResponse | null>(null);
const currentMode = ref<WorkspaceMode>('interview');
const activeInterviewName = ref('');

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

const workspaceApplicant = computed(
	() => workspace.value?.applicant || applicantWorkspace.value?.applicant || null
);
const workspaceTimeline = computed(
	() => workspace.value?.timeline || applicantWorkspace.value?.timeline || []
);
const workspaceDocuments = computed(
	() => workspace.value?.documents || applicantWorkspace.value?.documents || { rows: [], count: 0 }
);
const workspaceRecommendations = computed(
	() =>
		workspace.value?.recommendations ||
		applicantWorkspace.value?.recommendations || {
			summary: {
				required_total: 0,
				received_total: 0,
				requested_total: 0,
			},
			requests: [],
			submissions: [],
		}
);
const workspaceInterviews = computed<InterviewWorkspaceInterview[]>(() => {
	if (applicantWorkspace.value?.interviews?.length) {
		return applicantWorkspace.value.interviews;
	}
	if (workspace.value?.interview?.name) {
		return [workspace.value.interview];
	}
	return [];
});

const hasWorkspace = computed(() => Boolean(workspace.value || applicantWorkspace.value));
const isInterviewMode = computed(() => currentMode.value === 'interview');
const showBackToApplicant = computed(
	() => isInterviewMode.value && Boolean(applicantWorkspace.value)
);

const applicantDisplayName = computed(() => workspaceApplicant.value?.display_name || '');

const workspaceOverline = computed(() =>
	isInterviewMode.value ? 'Admission Interview Workspace' : 'Admission Applicant Workspace'
);

const interviewWindowLabel = computed(() => {
	if (!isInterviewMode.value) {
		return 'Applicant admission file summary';
	}
	const startLabel = workspace.value?.interview?.interview_start_label;
	const endLabel = workspace.value?.interview?.interview_end_label;
	if (startLabel && endLabel) return `${startLabel} to ${endLabel}`;
	if (startLabel) return startLabel;
	return 'Interview schedule';
});

const canEdit = computed(() =>
	Boolean(isInterviewMode.value && workspace.value?.feedback?.can_edit)
);

function emitAfterLeave() {
	emit('after-leave');
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(payload: unknown) {
	void payload;
}

function clearRuntimeMessages() {
	formError.value = null;
	saveNotice.value = null;
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

async function loadInterviewWorkspace(
	interviewName: string,
	options: { preserveApplicantContext?: boolean } = {}
) {
	const normalizedInterview = String(interviewName || '').trim();
	if (!normalizedInterview) {
		errorText.value = 'Interview reference is missing from this request.';
		workspace.value = null;
		return;
	}

	loading.value = true;
	errorText.value = null;
	clearRuntimeMessages();
	if (!options.preserveApplicantContext) {
		applicantWorkspace.value = null;
	}

	try {
		workspace.value = await getInterviewWorkspace(normalizedInterview);
		currentMode.value = 'interview';
		activeInterviewName.value = workspace.value.interview.name;
		resetFormFromWorkspace();
	} catch (err) {
		const message = err instanceof Error ? err.message : 'Failed to load interview workspace.';
		workspace.value = null;
		if (options.preserveApplicantContext && applicantWorkspace.value) {
			formError.value = message;
		} else {
			errorText.value = message;
		}
	} finally {
		loading.value = false;
	}
}

async function loadApplicantWorkspace(studentApplicantName: string) {
	const normalizedApplicant = String(studentApplicantName || '').trim();
	if (!normalizedApplicant) {
		errorText.value = 'Applicant reference is missing from this cockpit action.';
		workspace.value = null;
		applicantWorkspace.value = null;
		return;
	}

	loading.value = true;
	errorText.value = null;
	clearRuntimeMessages();
	workspace.value = null;

	try {
		applicantWorkspace.value = await getApplicantWorkspace(normalizedApplicant);
		currentMode.value = 'applicant';
		activeInterviewName.value = '';
		resetFormFromWorkspace();
	} catch (err) {
		applicantWorkspace.value = null;
		errorText.value = err instanceof Error ? err.message : 'Failed to load applicant workspace.';
	} finally {
		loading.value = false;
	}
}

function resolveRequestedMode(): WorkspaceMode {
	const requested = String(props.mode || '')
		.trim()
		.toLowerCase();
	if (requested === 'applicant') return 'applicant';
	if (requested === 'interview') return 'interview';
	return String(props.interview || '').trim() ? 'interview' : 'applicant';
}

async function loadWorkspace() {
	const mode = resolveRequestedMode();
	if (mode === 'applicant') {
		const applicantName = String(props.studentApplicant || '').trim();
		if (applicantName) {
			await loadApplicantWorkspace(applicantName);
			return;
		}

		const fallbackInterview = String(props.interview || '').trim();
		if (fallbackInterview) {
			await loadInterviewWorkspace(fallbackInterview, { preserveApplicantContext: false });
			return;
		}

		errorText.value = 'Applicant reference is missing from this cockpit action.';
		workspace.value = null;
		applicantWorkspace.value = null;
		return;
	}

	const interviewName = String(props.interview || '').trim();
	if (interviewName) {
		await loadInterviewWorkspace(interviewName, { preserveApplicantContext: false });
		return;
	}

	const fallbackApplicant = String(props.studentApplicant || '').trim();
	if (fallbackApplicant) {
		await loadApplicantWorkspace(fallbackApplicant);
		return;
	}

	errorText.value = 'Interview reference is missing from this calendar event.';
	workspace.value = null;
	applicantWorkspace.value = null;
}

function returnToApplicantMode() {
	if (!applicantWorkspace.value) {
		return;
	}
	workspace.value = null;
	currentMode.value = 'applicant';
	activeInterviewName.value = '';
	clearRuntimeMessages();
	resetFormFromWorkspace();
}

function isActiveInterview(interviewName: string | null | undefined) {
	return isInterviewMode.value && activeInterviewName.value === String(interviewName || '').trim();
}

async function openInterview(interviewName: string | null | undefined) {
	const normalizedInterview = String(interviewName || '').trim();
	if (!normalizedInterview) {
		formError.value = 'Interview reference is missing.';
		return;
	}
	await loadInterviewWorkspace(normalizedInterview, { preserveApplicantContext: true });
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
	if (!workspace.value || !isInterviewMode.value) {
		formError.value = 'Open an interview before saving feedback.';
		return;
	}
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
	() => [props.open, props.interview, props.mode, props.studentApplicant] as const,
	([isOpen]) => {
		if (!isOpen) return;
		void loadWorkspace();
	},
	{ immediate: true }
);

watch(
	() => props.open,
	isOpen => {
		if (isOpen) {
			document.addEventListener('keydown', onKeydown, true);
			return;
		}
		document.removeEventListener('keydown', onKeydown, true);
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
