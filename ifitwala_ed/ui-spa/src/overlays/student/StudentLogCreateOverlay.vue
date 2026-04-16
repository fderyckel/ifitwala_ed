<!-- ui-spa/src/overlays/student/StudentLogCreateOverlay.vue -->

<!--
Used by:
- StaffHome.vue
- StudentAttendanceTool.vue
- Student Log quick-create flows
-->

<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--student-log"
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
						<!-- Header -->
						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">
									{{ step === 'review' ? __('Review student note') : __('New student note') }}
								</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{
										step === 'review'
											? __('Once submitted, this note cannot be edited.')
											: mode === 'attendance'
												? __('Fast capture for the selected student.')
												: __('Search across your school.')
									}}
								</p>
								<span
									class="mt-2 inline-flex items-center rounded-full border border-border/70 bg-[rgb(var(--surface-strong-rgb))] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink/70"
								>
									{{ sourcePillLabel }}
								</span>
							</div>

							<button
								ref="closeBtnEl"
								type="button"
								class="if-overlay__close"
								@click="emitClose('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<!-- Body -->
						<div class="if-overlay__body px-6 pb-6 space-y-5">
							<!-- A+ UX: overlays never toast. Errors are shown inline. -->
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">
									{{ __('Something went wrong') }}
								</p>
								<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">
									{{ errorMessage }}
								</p>
							</div>

							<!-- EDIT STEP -->
							<template v-if="step !== 'review'">
								<!-- Student -->
								<section class="space-y-2">
									<p class="type-caption text-ink/70">{{ __('Student') }}</p>

									<!-- Attendance mode: locked student context -->
									<div
										v-if="mode === 'attendance'"
										class="rounded-2xl border border-border/70 bg-white px-4 py-3 shadow-soft"
									>
										<div class="flex items-center gap-3">
											<img
												v-if="selectedStudentImage"
												:src="selectedStudentImage"
												alt=""
												class="h-10 w-10 rounded-full object-cover ring-1 ring-black/5"
												loading="lazy"
												decoding="async"
											/>
											<div class="min-w-0">
												<p class="type-body-strong truncate text-ink">
													{{ selectedStudentLabel || form.student }}
												</p>
												<p v-if="selectedStudentMeta" class="type-caption truncate text-ink/55">
													{{ selectedStudentMeta }}
												</p>
											</div>
										</div>
										<p v-if="attendanceContextLabel" class="mt-2 type-caption text-ink/55">
											{{ attendanceContextLabel }}
										</p>
									</div>

									<!-- Home mode: search OR selected card -->
									<div v-else class="space-y-2">
										<!-- Search UI: only when no student selected -->
										<div v-if="!form.student" class="space-y-2">
											<FormControl
												type="text"
												size="md"
												:model-value="studentQuery"
												:disabled="submitting"
												placeholder="Search student name…"
												@update:modelValue="onStudentQuery"
											/>

											<div v-if="studentSearchLoading" class="flex items-center gap-2 text-ink/60">
												<Spinner class="h-4 w-4" />
												<span class="type-caption">{{ __('Searching…') }}</span>
											</div>

											<div
												v-if="studentCandidates.length"
												class="rounded-2xl border border-border/70 bg-white shadow-soft overflow-hidden"
											>
												<button
													v-for="c in studentCandidates"
													:key="c.value"
													type="button"
													class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-sky/30 transition"
													@click="onStudentSelected(c.value)"
												>
													<img
														v-if="c.image"
														:src="c.image"
														alt=""
														class="h-9 w-9 rounded-full object-cover ring-1 ring-black/5"
														loading="lazy"
														decoding="async"
													/>
													<div class="min-w-0 flex-1">
														<p class="type-body-strong text-ink truncate">{{ c.label }}</p>
														<p class="type-caption text-ink/55 truncate">{{ c.meta }}</p>
													</div>
													<FeatherIcon name="chevron-right" class="h-4 w-4 text-ink/40" />
												</button>
											</div>
										</div>

										<!-- Selected student card: replaces search UI -->
										<div
											v-else
											class="rounded-2xl border border-border/70 bg-white px-4 py-3 shadow-soft flex items-center justify-between gap-3"
										>
											<div class="flex items-center gap-3 min-w-0">
												<img
													v-if="selectedStudentImage"
													:src="selectedStudentImage"
													alt=""
													class="h-10 w-10 rounded-full object-cover ring-1 ring-black/5"
													loading="lazy"
													decoding="async"
												/>
												<div class="min-w-0">
													<p class="type-body-strong text-ink truncate">
														{{ selectedStudentLabel }}
													</p>
													<p v-if="selectedStudentMeta" class="type-caption text-ink/55 truncate">
														{{ selectedStudentMeta }}
													</p>
												</div>
											</div>

											<button
												type="button"
												class="type-caption text-ink/70 hover:text-ink underline underline-offset-4"
												:disabled="submitting"
												v-if="mode === 'home'"
												@click="changeStudent()"
											>
												{{ __('Change') }}
											</button>
										</div>
									</div>
								</section>

								<!-- Type -->
								<section class="space-y-2">
									<div class="flex items-center justify-between">
										<p class="type-caption text-ink/70">{{ __('Type') }}</p>
										<span
											v-if="optionsLoading"
											class="type-caption text-ink/55 flex items-center gap-2"
										>
											<Spinner class="h-4 w-4" /> {{ __('Loading…') }}
										</span>
									</div>

									<select
										class="w-full rounded-xl border border-border/70 bg-white px-3 py-2 text-sm text-ink shadow-soft outline-none transition focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)] disabled:cursor-not-allowed disabled:bg-surface-soft disabled:text-ink/45"
										:value="form.log_type"
										:disabled="
											!form.student || optionsLoading || submitting || !logTypeOptions.length
										"
										@change="
											event =>
												(form.log_type = String((event.target as HTMLSelectElement)?.value || ''))
										"
									>
										<option value="">{{ __('Select type') }}</option>
										<option
											v-for="option in logTypeOptions"
											:key="option.value"
											:value="option.value"
										>
											{{ option.label }}
										</option>
									</select>

									<p
										v-if="form.student && !optionsLoading && !logTypeOptions.length"
										class="type-caption text-ink/55"
									>
										{{ __('No note types are available for this student yet.') }}
									</p>
								</section>

								<!-- Note -->
								<section class="space-y-2">
									<div class="flex items-center justify-between">
										<p class="type-caption text-ink/70">{{ __('Note') }}</p>
										<button
											v-if="hasSpeechSupport"
											type="button"
											class="flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] font-semibold transition-all"
											:class="
												isListening
													? 'bg-flame/10 text-flame animate-pulse'
													: 'bg-surface-soft text-slate-token/70 hover:text-jacaranda'
											"
											:disabled="submitting || speechAvailability === 'unsupported'"
											@click="toggleSpeech"
										>
											<FeatherIcon name="mic" class="h-3 w-3" />
											{{ isListening ? __('Listening…') : __('Dictate') }}
										</button>
									</div>
									<p v-if="speechHint" class="type-caption text-ink/55">
										{{ speechHint }}
									</p>
									<textarea
										v-model="form.log"
										class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
										rows="6"
										:placeholder="__('Write what you observed…')"
										:disabled="submitting"
									/>
								</section>

								<!-- Visibility (defaults OFF in SPA) -->
								<section class="space-y-2">
									<p class="type-caption text-ink/70">{{ __('Visibility') }}</p>

									<div class="rounded-2xl border border-border/70 bg-white px-4 py-3 shadow-soft">
										<div
											class="student-log-create__visibility-grid grid grid-cols-1 gap-3 min-[480px]:grid-cols-2"
										>
											<label
												class="flex gap-3 rounded-xl border border-border/60 bg-white px-3 py-3 hover:bg-sky/20 transition"
											>
												<input
													v-model="form.visible_to_student"
													type="checkbox"
													class="mt-1 h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
													:disabled="submitting"
												/>
												<div class="min-w-0">
													<p class="type-body-strong text-ink">{{ __('Visible to student') }}</p>
													<p class="type-caption text-ink/55">
														{{ __('Show this note in the student portal.') }}
													</p>
												</div>
											</label>

											<label
												class="flex gap-3 rounded-xl border border-border/60 bg-white px-3 py-3 hover:bg-sky/20 transition"
											>
												<input
													v-model="form.visible_to_guardians"
													type="checkbox"
													class="mt-1 h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
													:disabled="submitting"
												/>
												<div class="min-w-0">
													<p class="type-body-strong text-ink">{{ __('Visible to parents') }}</p>
													<p class="type-caption text-ink/55">
														{{ __('Show this note in the guardian portal.') }}
													</p>
												</div>
											</label>
										</div>
									</div>
								</section>

								<!-- Follow-up -->
								<section class="space-y-2">
									<p class="type-caption text-ink/70">{{ __('Follow-up') }}</p>

									<div
										class="rounded-2xl border border-border/70 bg-white px-4 py-3 shadow-soft space-y-3"
									>
										<label class="flex items-start gap-3">
											<input
												v-model="form.requires_follow_up"
												type="checkbox"
												class="mt-1 h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
												:disabled="submitting || !form.student"
											/>
											<div class="min-w-0">
												<p class="type-body-strong text-ink">{{ __('Needs follow-up') }}</p>
												<p class="type-caption text-ink/55">
													{{ __('Assign this note to someone else, with a clear next step.') }}
												</p>
											</div>
										</label>

										<div v-if="form.requires_follow_up" class="space-y-3 pt-1">
											<select
												class="w-full rounded-xl border border-border/70 bg-white px-3 py-2 text-sm text-ink shadow-soft outline-none transition focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)] disabled:cursor-not-allowed disabled:bg-surface-soft disabled:text-ink/45"
												:value="form.next_step"
												:disabled="submitting || optionsLoading || !nextStepOptions.length"
												@change="
													event =>
														onNextStepSelected(
															String((event.target as HTMLSelectElement)?.value || '')
														)
												"
											>
												<option value="">{{ __('Select next step') }}</option>
												<option
													v-for="option in nextStepOptions"
													:key="option.value"
													:value="option.value"
												>
													{{ option.label }}
												</option>
											</select>

											<p
												v-if="!optionsLoading && !nextStepOptions.length"
												class="type-caption text-ink/55"
											>
												{{ __('No follow-up steps are available for this student yet.') }}
											</p>

											<div v-if="followUpRoleHint" class="type-caption text-ink/55">
												{{ followUpRoleHint }}
											</div>

											<FormControl
												type="text"
												size="md"
												:model-value="assigneeQuery"
												:disabled="submitting || !form.next_step"
												placeholder="Search staff to assign…"
												@update:modelValue="onAssigneeQuery"
											/>

											<div
												v-if="assigneeSearchLoading"
												class="flex items-center gap-2 text-ink/60"
											>
												<Spinner class="h-4 w-4" />
												<span class="type-caption">{{ __('Searching…') }}</span>
											</div>

											<div
												v-if="assigneeCandidates.length"
												class="rounded-2xl border border-border/70 bg-[rgb(var(--surface-strong-rgb))] overflow-hidden"
											>
												<button
													v-for="u in assigneeCandidates"
													:key="u.value"
													type="button"
													class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-sky/30 transition"
													@click="selectAssignee(u.value, u.label)"
												>
													<div class="min-w-0">
														<p class="type-body-strong text-ink truncate">{{ u.label }}</p>
														<p class="type-caption text-ink/55 truncate">{{ u.meta }}</p>
													</div>
													<FeatherIcon
														name="check"
														class="h-4 w-4 text-leaf"
														v-if="form.follow_up_person === u.value"
													/>
												</button>
											</div>

											<div v-if="selectedAssigneeLabel" class="type-caption text-ink/60">
												{{ __('Assigned to:') }}
												<span class="text-ink">{{ selectedAssigneeLabel }}</span>
											</div>
										</div>
									</div>
								</section>
							</template>

							<!-- REVIEW STEP -->
							<template v-else>
								<section class="space-y-3">
									<div
										class="rounded-2xl border border-border/70 bg-white px-5 py-4 shadow-soft space-y-4"
									>
										<!-- Student + Type -->
										<div class="flex items-start justify-between gap-4">
											<div class="min-w-0">
												<p class="type-caption text-ink/55">{{ __('Student') }}</p>
												<div class="mt-1 flex items-center gap-3 min-w-0">
													<img
														v-if="selectedStudentImage"
														:src="selectedStudentImage"
														alt=""
														class="h-10 w-10 rounded-full object-cover ring-1 ring-black/5"
														loading="lazy"
														decoding="async"
													/>
													<div class="min-w-0">
														<p class="type-body-strong text-ink truncate">
															{{ selectedStudentLabel || form.student }}
														</p>
														<p
															v-if="selectedStudentMeta"
															class="type-caption text-ink/55 truncate"
														>
															{{ selectedStudentMeta }}
														</p>
													</div>
												</div>
											</div>

											<div class="text-right shrink-0">
												<p class="type-caption text-ink/55">{{ __('Type') }}</p>
												<p class="mt-1 type-body-strong text-ink">
													{{ selectedLogTypeLabel || form.log_type || '—' }}
												</p>
											</div>
										</div>

										<!-- Note preview -->
										<div class="space-y-1">
											<p class="type-caption text-ink/55">{{ __('Note') }}</p>
											<div
												class="rounded-xl border border-border/60 bg-[rgb(var(--surface-strong-rgb))] px-4 py-3"
											>
												<p class="text-sm text-ink/90 whitespace-pre-wrap">
													{{ reviewNotePreview || '—' }}
												</p>
											</div>
											<p v-if="isNoteTruncated" class="type-caption text-ink/55">
												{{ __('Preview truncated. Go back to edit to review full text.') }}
											</p>
										</div>

										<!-- Visibility + Follow-up summary -->
										<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
											<div class="rounded-xl border border-border/60 bg-white px-4 py-3">
												<p class="type-caption text-ink/55">{{ __('Visibility') }}</p>
												<ul class="mt-2 space-y-1 text-sm text-ink/85">
													<li class="flex items-center justify-between gap-3">
														<span class="text-ink/70">{{ __('Student') }}</span>
														<span class="type-body-strong text-ink">{{
															form.visible_to_student ? __('Yes') : __('No')
														}}</span>
													</li>
													<li class="flex items-center justify-between gap-3">
														<span class="text-ink/70">{{ __('Parents') }}</span>
														<span class="type-body-strong text-ink">{{
															form.visible_to_guardians ? __('Yes') : __('No')
														}}</span>
													</li>
												</ul>
											</div>

											<div class="rounded-xl border border-border/60 bg-white px-4 py-3">
												<p class="type-caption text-ink/55">{{ __('Follow-up') }}</p>
												<div class="mt-2 text-sm text-ink/85 space-y-1">
													<p>
														<span class="text-ink/70">{{ __('Needs follow-up') }}:</span>
														<span class="type-body-strong text-ink ml-1">{{
															form.requires_follow_up ? __('Yes') : __('No')
														}}</span>
													</p>
													<p v-if="form.requires_follow_up">
														<span class="text-ink/70">{{ __('Next step') }}:</span>
														<span class="type-body-strong text-ink ml-1">{{
															selectedNextStepLabel || form.next_step || '—'
														}}</span>
													</p>
													<p v-if="form.requires_follow_up">
														<span class="text-ink/70">{{ __('Assigned to') }}:</span>
														<span class="type-body-strong text-ink ml-1">{{
															selectedAssigneeLabel || form.follow_up_person || '—'
														}}</span>
													</p>
												</div>
											</div>
										</div>
									</div>
								</section>
							</template>
						</div>

						<!-- Footer -->
						<div class="if-overlay__footer">
							<!-- EDIT FOOTER -->
							<div v-if="step !== 'review'" class="w-full flex flex-col items-stretch gap-2">
								<Button
									variant="solid"
									class="w-full"
									:loading="submitting"
									:disabled="!canSubmit || submitting"
									@click="goReview"
								>
									<template #prefix><FeatherIcon name="eye" class="h-4 w-4" /></template>
									{{ __('Review & submit') }}
								</Button>

								<p class="type-caption text-ink/50 whitespace-normal leading-snug">
									{{ footerHint }}
								</p>
							</div>

							<!-- REVIEW FOOTER -->
							<div v-else class="w-full flex flex-col gap-3">
								<div class="flex items-center gap-3">
									<Button variant="outline" class="flex-1" :disabled="submitting" @click="goEdit">
										<template #prefix><FeatherIcon name="edit-2" class="h-4 w-4" /></template>
										{{ __('Go back and edit') }}
									</Button>

									<Button
										variant="solid"
										class="flex-1"
										:loading="submitting"
										:disabled="!canSubmit || submitting"
										@click="submit"
									>
										<template #prefix><FeatherIcon name="send" class="h-4 w-4" /></template>
										{{ __('Confirm & submit') }}
									</Button>
								</div>

								<p class="type-caption text-ink/50 whitespace-normal leading-snug">
									{{
										__(
											'Submitting will create a new student log entry. You won’t be able to edit it afterwards.'
										)
									}}
								</p>
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
import { Button, FormControl, FeatherIcon, Spinner } from 'frappe-ui';
import { __ } from '@/lib/i18n';
import { createStudentLogService } from '@/lib/services/studentLog/studentLogService';
import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	hasStudentLogDraftContent,
	normalizeStudentLogOverlayMode,
	shouldPromptStudentLogDiscard,
} from './studentLogOverlayRules';
import type { Response as GetFormOptionsResponse } from '@/types/contracts/student_log/get_form_options';
import type { Response as SearchFollowUpUsersResponse } from '@/types/contracts/student_log/search_follow_up_users';
import type { Response as SearchStudentsResponse } from '@/types/contracts/student_log/search_students';
import type { Request as SubmitStudentLogRequest } from '@/types/contracts/student_log/submit_student_log';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type Mode = 'attendance' | 'home';

type OverlayStudent = {
	id: string;
	label?: string | null;
	image?: string | null;
	meta?: string | null;
};

type OverlayStudentGroup = {
	id: string;
	label?: string | null;
};

type PickerItem = {
	value: string;
	label: string;
	image?: string | null;
	meta?: string | null;
};

type SpeechAvailability = 'unknown' | 'ready' | 'blocked' | 'unsupported';
type SpeechRecognitionLike = {
	continuous: boolean;
	interimResults: boolean;
	lang: string;
	onstart: null | (() => void);
	onresult: null | ((event: any) => void);
	onerror: null | ((event: any) => void);
	onend: null | (() => void);
	start: () => void;
	stop: () => void;
	abort?: () => void;
};
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	mode: Mode;
	student?: OverlayStudent | null;
	student_group?: OverlayStudentGroup | null;
	context_school?: string | null;
	sourceLabel?: string | null;
	initial_log_text?: string | null;
	overlayId?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlay = useOverlayStack();
const studentLogService = createStudentLogService();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));

const closeBtnEl = ref<HTMLButtonElement | null>(null);

// A+ UX: overlays show errors inline (no toasts here)
const errorMessage = ref<string>('');

// Review step state
const step = ref<'edit' | 'review'>('edit');

const NOTE_PREVIEW_LEN = 220;

const reviewNotePreview = computed(() => {
	const txt = (form.log || '').trim();
	if (!txt) return '';
	return txt.length > NOTE_PREVIEW_LEN ? txt.slice(0, NOTE_PREVIEW_LEN).trim() + '…' : txt;
});

const isNoteTruncated = computed(() => {
	const txt = (form.log || '').trim();
	return !!txt && txt.length > NOTE_PREVIEW_LEN;
});

const selectedLogTypeLabel = computed(() => {
	if (!form.log_type) return '';
	const row = logTypeOptions.value.find(x => x.value === form.log_type);
	return row?.label || '';
});

const selectedNextStepLabel = computed(() => {
	if (!form.next_step) return '';
	const row = nextStepOptions.value.find(x => x.value === form.next_step);
	return row?.label || '';
});

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

function hasDraftContent() {
	return hasStudentLogDraftContent({
		log: form.log,
		log_type: form.log_type,
		requires_follow_up: form.requires_follow_up,
		next_step: form.next_step,
		follow_up_person: form.follow_up_person,
		visible_to_student: form.visible_to_student,
		visible_to_guardians: form.visible_to_guardians,
	});
}

function emitClose(reason: CloseReason) {
	if (shouldPromptStudentLogDiscard(reason, hasDraftContent())) {
		const shouldDiscard = window.confirm(__('Discard this log?'));
		if (!shouldDiscard) return;
	}

	const overlayId = props.overlayId || null;
	if (overlayId) {
		try {
			if (typeof overlay.close === 'function') {
				overlay.close(overlayId);
				return;
			}
		} catch (err) {
			// fall through to emit fallback
		}
	}

	emit('close', reason);
}

function emitAfterLeave() {
	step.value = 'edit';
	clearError();
	stopSpeechRecognition();
	emit('after-leave');
}

/**
 * HeadlessUI Dialog @close is ambiguous.
 * Under A+ we DO NOT forward it or close from it.
 * Backdrop + ESC + explicit buttons are the only closing paths.
 */
function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

function resetFormState() {
	step.value = 'edit';
	form.student = '';
	form.log_type = '';
	form.log = '';
	form.requires_follow_up = false;
	form.next_step = '';
	form.follow_up_person = '';
	form.visible_to_student = false;
	form.visible_to_guardians = false;

	selectedStudentLabel.value = '';
	selectedStudentImage.value = null;
	selectedStudentMeta.value = null;
	selectedAssigneeLabel.value = '';
	assigneeQuery.value = '';
	assigneeCandidates.value = [];
	studentQuery.value = '';
	studentCandidates.value = [];
	optionsData.value = null;
}

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
	const maybeWindow = window as any;
	return maybeWindow.SpeechRecognition || maybeWindow.webkitSpeechRecognition || null;
}

/* Voice to Text */
const isListening = ref(false);
const speechAvailability = ref<SpeechAvailability>('unknown');
const speechHint = ref('');
const hasSpeechSupport = computed(() => speechAvailability.value !== 'unsupported');
let recognition: SpeechRecognitionLike | null = null;

function stopSpeechRecognition() {
	if (!recognition) {
		isListening.value = false;
		return;
	}

	try {
		recognition.onstart = null;
		recognition.onresult = null;
		recognition.onerror = null;
		recognition.onend = null;
		recognition.abort?.();
	} catch (_err) {
		try {
			recognition.stop();
		} catch (_stopErr) {
			// Best effort cleanup only.
		}
	} finally {
		recognition = null;
		isListening.value = false;
	}
}

function setSpeechState(state: SpeechAvailability, message = '') {
	speechAvailability.value = state;
	speechHint.value = message;
}

async function refreshSpeechAvailability() {
	const SpeechRecognition = getSpeechRecognitionCtor();
	if (!SpeechRecognition) {
		setSpeechState(
			'unsupported',
			__('Dictation is not available in this browser. Type the note instead.')
		);
		return;
	}

	if (!window.isSecureContext) {
		setSpeechState(
			'blocked',
			__(
				'Dictation needs a secure connection. Open this site on HTTPS or localhost, then try again.'
			)
		);
		return;
	}

	setSpeechState('ready');

	try {
		const permissionsApi = navigator.permissions;
		if (!permissionsApi?.query) return;

		const status = await permissionsApi.query({ name: 'microphone' as PermissionName });
		if (status.state === 'denied') {
			setSpeechState(
				'blocked',
				__(
					'Microphone access is blocked for this site. Allow microphone access in your browser settings, then try dictation again.'
				)
			);
		}
	} catch (_err) {
		// Some browsers do not expose microphone permissions through the Permissions API.
	}
}

function getSpeechErrorMessage(errorCode: string) {
	switch (errorCode) {
		case 'audio-capture':
			return __(
				'No working microphone was found. Check your device input and browser microphone selection.'
			);
		case 'language-not-supported':
			return __('This browser does not support dictation for the selected language.');
		case 'network':
			return __(
				'Speech recognition could not reach the browser service. Check your connection and try again.'
			);
		case 'not-allowed':
			if (!window.isSecureContext) {
				return __(
					'Dictation needs a secure connection. Open this site on HTTPS or localhost, then try again.'
				);
			}
			return __(
				'Microphone access is blocked for this site. Allow microphone access in your browser settings, then try dictation again.'
			);
		case 'service-not-allowed':
			return __(
				'This browser blocked speech recognition on this page. Check browser permissions and try again.'
			);
		default:
			return __('Microphone error');
	}
}

function hydrateFromAttendanceProps() {
	const studentId = (props.student?.id || '').trim();
	if (!studentId) {
		setError(null, __('Attendance mode requires a selected student.'));
		return;
	}

	form.student = studentId;
	selectedStudentLabel.value = (props.student?.label || studentId).trim();
	selectedStudentImage.value = props.student?.image || null;
	selectedStudentMeta.value = (props.student?.meta || '').trim() || null;

	loadFormOptions(studentId);
}

function initializeForOpen() {
	clearError();
	resetFormState();
	stopSpeechRecognition();
	setSpeechState('unknown');
	void refreshSpeechAvailability();
	form.log = (props.initial_log_text || '').trim();

	if (mode.value === 'attendance') {
		hydrateFromAttendanceProps();
	}
}

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
	stopSpeechRecognition();
});

function goReview() {
	clearError();
	if (!canSubmit.value) return;
	step.value = 'review';
}

function goEdit() {
	clearError();
	step.value = 'edit';
}

const mode = computed<Mode>(() => normalizeStudentLogOverlayMode(props.mode));
const sourcePillLabel = computed(() => {
	const explicit = (props.sourceLabel || '').trim();
	if (explicit) return explicit;
	return mode.value === 'attendance' ? __('Attendance') : __('Staff Home');
});
const attendanceContextLabel = computed(() => {
	if (mode.value !== 'attendance') return '';
	const groupLabel = (props.student_group?.label || props.student_group?.id || '').trim();
	return groupLabel ? __('Group: {0}', [groupLabel]) : '';
});

const submitting = ref(false);

const form = reactive({
	student: '' as string,
	log_type: '' as string,
	log: '' as string,
	requires_follow_up: false,
	next_step: '' as string,
	follow_up_person: '' as string,
	// ✅ SPA safety defaults (override DocType defaults)
	visible_to_student: false,
	visible_to_guardians: false,
});

const selectedStudentLabel = ref('');
const selectedStudentImage = ref<string | null>(null);
const selectedStudentMeta = ref<string | null>(null);

const footerHint = computed(() => {
	if (!form.student) return __('Select a student first.');
	if (!form.log_type) return __('Choose a note type.');
	if (!form.log.trim()) return __('Write a short note.');
	if (form.requires_follow_up && !form.next_step) return __('Choose a next step.');
	if (form.requires_follow_up && !form.follow_up_person)
		return __('Assign the follow-up to someone.');
	return __('Saved immediately. For changes, add a clarification note later.');
});

const canSubmit = computed(() => {
	if (!form.student || !form.log_type || !form.log.trim()) return false;
	if (form.requires_follow_up) {
		if (!form.next_step) return false;
		if (!form.follow_up_person) return false;
	}
	return true;
});

/* Student search */
const studentQuery = ref('');
const studentSearchLoading = ref(false);
const studentCandidates = ref<PickerItem[]>([]);

async function onStudentQuery(v: string) {
	clearError();
	studentQuery.value = v;
	if (!v || v.trim().length < 2) {
		studentCandidates.value = [];
		return;
	}

	studentSearchLoading.value = true;
	try {
		const data: SearchStudentsResponse = await studentLogService.searchStudents({
			query: v.trim(),
			limit: 10,
		});
		studentCandidates.value = (data || []).map(x => ({
			value: x.student,
			label: x.label,
			image: x.image || null,
			meta: x.meta || null,
		}));
	} catch (err: any) {
		setError(err, __('Could not search students'));
	} finally {
		studentSearchLoading.value = false;
	}
}

/* Form options */
const optionsLoading = ref(false);
const optionsData = ref<GetFormOptionsResponse | null>(null);

const logTypeOptions = computed(() => optionsData.value?.log_types || []);
const nextStepOptions = computed(() => optionsData.value?.next_steps || []);

const followUpRoleHint = computed(() => {
	if (!form.next_step) return '';
	const row = nextStepOptions.value.find(x => x.value === form.next_step);
	const role = row?.role;
	if (!role) return __('Assignee will be filtered by role.');
	return `${__('Assignee role:')} ${role}`;
});

/* Assignee search */
const assigneeQuery = ref('');
const assigneeSearchLoading = ref(false);
const assigneeCandidates = ref<SearchFollowUpUsersResponse>([]);
const selectedAssigneeLabel = ref('');

async function onAssigneeQuery(v: string) {
	clearError();
	assigneeQuery.value = v;
	if (!form.next_step) return;
	if (!v || v.trim().length < 2) return;

	assigneeSearchLoading.value = true;
	try {
		const data: SearchFollowUpUsersResponse = await studentLogService.searchFollowUpUsers({
			next_step: form.next_step,
			student: form.student,
			query: v.trim(),
			limit: 50,
		});
		assigneeCandidates.value = data || [];
	} catch (err: any) {
		setError(err, __('Could not search staff'));
	} finally {
		assigneeSearchLoading.value = false;
	}
}

function selectAssignee(user: string, label: string) {
	clearError();
	form.follow_up_person = user;
	selectedAssigneeLabel.value = label;
	assigneeCandidates.value = [];
	assigneeQuery.value = label;
}

watch(
	() => props.open,
	v => {
		if (v) {
			document.addEventListener('keydown', onKeydown, true);
			initializeForOpen();
			return;
		}
		document.removeEventListener('keydown', onKeydown, true);
		stopSpeechRecognition();
	},
	{ immediate: true }
);

function loadFormOptions(studentId: string) {
	optionsLoading.value = true;
	studentLogService
		.getFormOptions({ student: studentId })
		.then((data: GetFormOptionsResponse) => {
			optionsData.value = data;
		})
		.catch((err: any) => {
			setError(err, __('Could not load options'));
			optionsData.value = null;
		})
		.finally(() => {
			optionsLoading.value = false;
		});
}

/* Student selection */
function onStudentSelected(studentId: string) {
	clearError();

	const picked =
		mode.value === 'home' ? studentCandidates.value.find(x => x.value === studentId) : null;

	form.student = studentId;

	form.log_type = '';
	form.next_step = '';
	form.follow_up_person = '';
	selectedAssigneeLabel.value = '';
	assigneeQuery.value = '';
	assigneeCandidates.value = [];

	studentCandidates.value = [];
	studentQuery.value = '';

	selectedStudentLabel.value = picked?.label || studentId;
	selectedStudentImage.value = picked?.image || null;
	selectedStudentMeta.value = picked?.meta || null;

	loadFormOptions(studentId);
}

async function toggleSpeech() {
	if (!hasSpeechSupport.value) return;

	if (isListening.value) {
		recognition?.stop();
		isListening.value = false;
		return;
	}

	clearError();
	await refreshSpeechAvailability();
	if (speechAvailability.value === 'blocked' || speechAvailability.value === 'unsupported') {
		setError(speechHint.value, __('Microphone error'));
		return;
	}

	try {
		const SpeechRecognition = getSpeechRecognitionCtor();
		if (!SpeechRecognition) {
			setSpeechState(
				'unsupported',
				__('Dictation is not available in this browser. Type the note instead.')
			);
			setError(speechHint.value, __('Microphone error'));
			return;
		}

		stopSpeechRecognition();
		recognition = new SpeechRecognition();
		recognition.continuous = true;
		recognition.interimResults = false;
		recognition.lang = 'en-US'; // default, could be configurable

		recognition.onstart = () => {
			isListening.value = true;
			clearError();
			setSpeechState('ready');
		};

		recognition.onresult = (event: any) => {
			const transcript = Array.from(event.results)
				.slice(event.resultIndex || 0)
				.map((result: any) => result[0].transcript)
				.join(' ')
				.trim();

			if (transcript) {
				// Append with space if needed
				const current = form.log || '';
				const spacer = current && !current.endsWith(' ') ? ' ' : '';
				form.log = current + spacer + transcript;
			}
		};

		recognition.onerror = (event: any) => {
			console.warn('Speech error', event);
			isListening.value = false;
			if (event.error !== 'no-speech' && event.error !== 'aborted') {
				const message = getSpeechErrorMessage(String(event.error || ''));
				if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
					setSpeechState('blocked', message);
				}
				setError(message, __('Microphone error'));
			}
		};

		recognition.onend = () => {
			isListening.value = false;
			recognition = null;
		};

		recognition.start();
	} catch (e) {
		console.error(e);
		isListening.value = false;
		setError(
			e instanceof Error && e.message ? e.message : getSpeechErrorMessage('service-not-allowed'),
			__('Microphone error')
		);
	}
}

function changeStudent() {
	clearError();
	if (mode.value !== 'home') return;
	if (hasDraftContent()) {
		const shouldDiscard = window.confirm(
			__('Changing student will discard this draft. Continue?')
		);
		if (!shouldDiscard) return;
	}
	resetFormState();
}

function onNextStepSelected(v: string) {
	clearError();
	form.next_step = v;
	form.follow_up_person = '';
	selectedAssigneeLabel.value = '';
	assigneeQuery.value = '';
	assigneeCandidates.value = [];

	if (form.next_step && form.student) {
		assigneeSearchLoading.value = true;
		studentLogService
			.searchFollowUpUsers({
				next_step: form.next_step,
				student: form.student,
				query: '',
				limit: 50,
			})
			.then((data: SearchFollowUpUsersResponse) => {
				assigneeCandidates.value = data || [];
			})
			.catch((err: any) => {
				setError(err, __('Could not search staff'));
				assigneeCandidates.value = [];
			})
			.finally(() => {
				assigneeSearchLoading.value = false;
			});
	}
}

async function submit() {
	clearError();
	if (!canSubmit.value) return;

	if (step.value !== 'review') {
		step.value = 'review';
		return;
	}

	submitting.value = true;
	try {
		const payload: SubmitStudentLogRequest = {
			student: form.student,
			log_type: form.log_type,
			log: form.log,
			requires_follow_up: form.requires_follow_up ? 1 : 0,
			next_step: form.requires_follow_up ? form.next_step : null,
			follow_up_person: form.requires_follow_up ? form.follow_up_person : null,
			visible_to_student: form.visible_to_student ? 1 : 0,
			visible_to_guardians: form.visible_to_guardians ? 1 : 0,
		};

		await studentLogService.submitStudentLog(payload);

		emitClose('programmatic');
	} catch (err: any) {
		console.error('[StudentLogCreateOverlay] submit:error', err);
		setError(err, __('Could not submit'));
	} finally {
		submitting.value = false;
	}
}
</script>
