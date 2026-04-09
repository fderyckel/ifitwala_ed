<!-- ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--meeting"
			:style="overlayStyle"
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

						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<p class="type-overline text-ink/55">Class Session</p>
								<DialogTitle class="type-h2 text-ink">Plan This Session</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									Use the clicked calendar slot to plan the actual lesson flow for this class
									without leaving the calendar context.
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								aria-label="Close"
								@click="emitClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body space-y-5 px-6 pb-6">
							<section class="rounded-[1.75rem] border border-line-soft bg-surface-soft p-5">
								<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
									<div class="space-y-1">
										<p class="type-overline text-ink/55">Calendar Context</p>
										<h3 class="type-h3 text-ink">
											{{ props.classTitle || surface?.group.title || 'Selected class' }}
										</h3>
										<p class="type-caption text-ink/70">
											{{ courseLabel }}
										</p>
									</div>
									<div class="flex flex-wrap gap-2">
										<span v-if="sessionDateLabel" class="chip">{{ sessionDateLabel }}</span>
										<span v-if="timeLabel" class="chip">{{ timeLabel }}</span>
										<span v-if="props.blockLabel" class="chip">{{ props.blockLabel }}</span>
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

							<section
								v-if="loading && !surface"
								class="rounded-2xl border border-line-soft bg-white px-5 py-8"
							>
								<p class="type-body text-ink/70">Loading class planning surface...</p>
							</section>

							<template v-else-if="surface">
								<section
									v-if="!surface.teaching_plan"
									class="grid gap-5 rounded-[1.75rem] border border-line-soft bg-white p-5 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)]"
								>
									<div class="space-y-2">
										<p class="type-overline text-ink/55">Step 1</p>
										<h3 class="type-h3 text-ink">Initialize the class teaching plan</h3>
										<p class="type-caption text-ink/70">
											This class needs a class-owned planning record before the session can be
											saved.
										</p>
									</div>

									<div class="space-y-4">
										<div
											v-if="!surface.course_plans.length"
											class="rounded-2xl border border-dashed border-line-soft px-4 py-4"
										>
											<p class="type-body-strong text-ink">No shared course plan is available.</p>
											<p class="mt-1 type-caption text-ink/70">
												Create the shared course plan first, then return here to plan this class
												session.
											</p>
										</div>

										<template v-else>
											<label class="block space-y-2">
												<span class="type-caption text-ink/70">Governing course plan</span>
												<select v-model="draftCoursePlan" class="if-input w-full">
													<option value="">Select a course plan</option>
													<option
														v-for="plan in surface.course_plans"
														:key="plan.course_plan"
														:value="plan.course_plan"
													>
														{{ plan.title }}
													</option>
												</select>
											</label>

											<div class="grid gap-3 md:grid-cols-2">
												<article
													v-for="plan in surface.course_plans"
													:key="plan.course_plan"
													class="rounded-2xl border border-line-soft bg-surface-soft p-4"
												>
													<p class="type-body-strong text-ink">{{ plan.title }}</p>
													<p class="mt-1 type-caption text-ink/70">
														{{ plan.academic_year || 'No academic year' }}
														<span v-if="plan.cycle_label">· {{ plan.cycle_label }}</span>
													</p>
												</article>
											</div>

											<div class="flex flex-wrap gap-3">
												<button
													type="button"
													class="if-action"
													:disabled="!draftCoursePlan || createPending"
													@click="handleCreatePlan"
												>
													{{ createPending ? 'Creating...' : 'Create Class Teaching Plan' }}
												</button>
												<button
													type="button"
													class="if-action if-action--subtle"
													@click="openFullPlanning"
												>
													Open Full Class Planning
												</button>
											</div>
										</template>
									</div>
								</section>

								<section
									v-else-if="!surface.curriculum.units.length"
									class="rounded-[1.75rem] border border-line-soft bg-white p-5"
								>
									<p class="type-body-strong text-ink">No governed units are available yet.</p>
									<p class="mt-1 type-caption text-ink/70">
										Add governed units to the shared course plan before planning class sessions.
									</p>
									<div class="mt-4">
										<button
											type="button"
											class="if-action if-action--subtle"
											@click="openFullPlanning"
										>
											Open Full Class Planning
										</button>
									</div>
								</section>

								<section v-else class="space-y-5">
									<section class="rounded-[1.75rem] border border-line-soft bg-white p-5">
										<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
											<div class="space-y-1">
												<p class="type-overline text-ink/55">Class Planning Context</p>
												<h3 class="type-h3 text-ink">{{ surface.teaching_plan.title }}</h3>
												<p class="type-caption text-ink/70">
													Session planning stays class-owned while the shared course plan stays
													governed.
												</p>
											</div>
											<div class="flex flex-wrap gap-2">
												<span class="chip">{{
													surface.teaching_plan.planning_status || 'Draft'
												}}</span>
												<span class="chip">{{ surface.curriculum.units.length }} units</span>
												<span class="chip">{{ surface.curriculum.session_count }} sessions</span>
											</div>
										</div>

										<div class="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr),auto]">
											<label
												v-if="surface.class_teaching_plans.length > 1"
												class="block space-y-2"
											>
												<span class="type-caption text-ink/70">Switch class teaching plan</span>
												<select
													:value="requestedPlan || surface.teaching_plan.class_teaching_plan"
													class="if-input w-full"
													@change="handlePlanSelectionChange"
												>
													<option
														v-for="plan in surface.class_teaching_plans"
														:key="plan.class_teaching_plan"
														:value="plan.class_teaching_plan"
													>
														{{ plan.title }}
													</option>
												</select>
											</label>

											<div class="flex flex-wrap gap-3 lg:justify-end">
												<button
													type="button"
													class="if-action if-action--subtle"
													@click="openFullPlanning"
												>
													Open Full Class Planning
												</button>
											</div>
										</div>
									</section>

									<section
										v-if="dateMatchedSession"
										class="rounded-[1.75rem] border border-canopy/30 bg-canopy/8 p-5"
									>
										<div
											class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
										>
											<div>
												<p class="type-body-strong text-ink">
													A class session already exists for this calendar date.
												</p>
												<p class="mt-1 type-caption text-ink/70">
													{{
														currentSessionId === dateMatchedSession.class_session
															? `You are editing ${dateMatchedSession.title || 'the saved session'}.`
															: `The saved session is ${dateMatchedSession.title || 'untitled'}.`
													}}
												</p>
											</div>
											<div class="flex flex-wrap gap-3">
												<button
													v-if="currentSessionId !== dateMatchedSession.class_session"
													type="button"
													class="if-action if-action--subtle"
													@click="editMatchedSession"
												>
													Edit Existing
												</button>
												<button
													v-if="currentSessionId === dateMatchedSession.class_session"
													type="button"
													class="if-action if-action--subtle"
													@click="startNewSessionDraft"
												>
													Start Another Session
												</button>
											</div>
										</div>
									</section>

									<section class="grid gap-5 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)]">
										<aside
											class="space-y-4 rounded-[1.75rem] border border-line-soft bg-white p-5"
										>
											<div>
												<p class="type-overline text-ink/55">Suggested Unit</p>
												<h3 class="mt-1 type-h3 text-ink">
													{{ selectedUnit?.title || 'Select unit' }}
												</h3>
												<p class="mt-1 type-caption text-ink/70">
													The system suggests the current in-progress unit first, then the next
													untaught unit.
												</p>
											</div>

											<label class="block space-y-2">
												<span class="type-caption text-ink/70">Unit plan</span>
												<select
													v-model="selectedUnitPlan"
													class="if-input w-full"
													@change="handleUnitSelectionChange"
												>
													<option
														v-for="unit in surface.curriculum.units"
														:key="unit.unit_plan"
														:value="unit.unit_plan"
													>
														{{ unit.unit_order ? `Unit ${unit.unit_order} · ` : ''
														}}{{ unit.title }}
													</option>
												</select>
											</label>

											<div
												v-if="selectedUnit"
												class="space-y-3 rounded-2xl border border-line-soft bg-surface-soft p-4"
											>
												<div class="flex flex-wrap gap-2">
													<span class="chip">{{
														selectedUnit.pacing_status || 'Not Started'
													}}</span>
													<span class="chip">{{ selectedUnit.sessions.length }} sessions</span>
													<span v-if="selectedUnit.unit_status" class="chip">
														{{ selectedUnit.unit_status }}
													</span>
												</div>
												<p v-if="selectedUnit.overview" class="type-caption text-ink/70">
													{{ selectedUnit.overview }}
												</p>
											</div>
										</aside>

										<section
											class="space-y-4 rounded-[1.75rem] border border-line-soft bg-white p-5"
										>
											<div class="flex items-start justify-between gap-3">
												<div>
													<p class="type-overline text-ink/55">
														{{ currentSessionId ? 'Edit session' : 'New session' }}
													</p>
													<h3 class="mt-1 type-h3 text-ink">
														{{ form.title || 'Plan this class session' }}
													</h3>
												</div>
												<span class="chip">{{ form.session_status || 'Draft' }}</span>
											</div>

											<div class="grid gap-4 md:grid-cols-2">
												<label class="block space-y-2 md:col-span-2">
													<span class="type-caption text-ink/70">Session title</span>
													<input
														v-model="form.title"
														type="text"
														class="if-input w-full"
														placeholder="e.g. Evidence walk and structured discussion"
													/>
												</label>

												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Session status</span>
													<select v-model="form.session_status" class="if-input w-full">
														<option value="Draft">Draft</option>
														<option value="Planned">Planned</option>
														<option value="In Progress">In Progress</option>
														<option value="Taught">Taught</option>
														<option value="Changed">Changed</option>
														<option value="Canceled">Canceled</option>
													</select>
												</label>

												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Session date</span>
													<input v-model="form.session_date" type="date" class="if-input w-full" />
												</label>

												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Sequence</span>
													<input
														v-model.number="form.sequence_index"
														type="number"
														min="1"
														step="1"
														class="if-input w-full"
													/>
												</label>

												<label class="block space-y-2 md:col-span-2">
													<span class="type-caption text-ink/70">Learning goal</span>
													<textarea
														v-model="form.learning_goal"
														rows="3"
														class="if-input min-h-[6rem] w-full resize-y"
														placeholder="State the learning goal students should understand and act on."
													/>
												</label>

												<label class="block space-y-2 md:col-span-2">
													<span class="type-caption text-ink/70">Teacher note</span>
													<textarea
														v-model="form.teacher_note"
														rows="4"
														class="if-input min-h-[7rem] w-full resize-y"
														placeholder="Capture delivery notes, reminders, or reflection prompts for this class."
													/>
												</label>
											</div>

											<div class="space-y-3 border-t border-line-soft pt-4">
												<div class="flex items-center justify-between gap-3">
													<div>
														<p class="type-overline text-ink/55">Lesson Flow</p>
														<p class="type-caption text-ink/70">
															Add the sequence of activities students will experience.
														</p>
													</div>
													<button
														type="button"
														class="if-action if-action--subtle"
														@click="addActivity"
													>
														Add Activity
													</button>
												</div>

												<div
													v-if="!form.activities.length"
													class="rounded-2xl border border-dashed border-line-soft px-4 py-4"
												>
													<p class="type-caption text-ink/70">
														Add teaching moves, practice, checks for understanding, or reflection.
													</p>
												</div>

												<div v-else class="space-y-3">
													<div
														v-for="(activity, index) in form.activities"
														:key="activity.local_id"
														class="rounded-2xl border border-line-soft bg-surface-soft p-4"
													>
														<div class="grid gap-4 md:grid-cols-2">
															<label class="block space-y-2 md:col-span-2">
																<span class="type-caption text-ink/70">Activity title</span>
																<input
																	v-model="activity.title"
																	type="text"
																	class="if-input w-full"
																	:placeholder="`Activity ${index + 1}`"
																/>
															</label>

															<label class="block space-y-2">
																<span class="type-caption text-ink/70">Activity type</span>
																<select v-model="activity.activity_type" class="if-input w-full">
																	<option value="Discuss">Discuss</option>
																	<option value="Practice">Practice</option>
																	<option value="Read">Read</option>
																	<option value="Watch">Watch</option>
																	<option value="Write">Write</option>
																	<option value="Collaborate">Collaborate</option>
																	<option value="Check for Understanding">
																		Check for Understanding
																	</option>
																	<option value="Reflect">Reflect</option>
																	<option value="Assess">Assess</option>
																	<option value="Other">Other</option>
																</select>
															</label>

															<label class="block space-y-2">
																<span class="type-caption text-ink/70">Estimated minutes</span>
																<input
																	v-model.number="activity.estimated_minutes"
																	type="number"
																	min="0"
																	step="1"
																	class="if-input w-full"
																/>
															</label>

															<label class="block space-y-2 md:col-span-2">
																<span class="type-caption text-ink/70">Student direction</span>
																<textarea
																	v-model="activity.student_direction"
																	rows="2"
																	class="if-input min-h-[5rem] w-full resize-y"
																/>
															</label>

															<label class="block space-y-2">
																<span class="type-caption text-ink/70">Teacher prompt</span>
																<textarea
																	v-model="activity.teacher_prompt"
																	rows="2"
																	class="if-input min-h-[5rem] w-full resize-y"
																/>
															</label>

															<label class="block space-y-2">
																<span class="type-caption text-ink/70">Resource note</span>
																<textarea
																	v-model="activity.resource_note"
																	rows="2"
																	class="if-input min-h-[5rem] w-full resize-y"
																/>
															</label>
														</div>

														<div class="mt-3 flex justify-end">
															<button
																type="button"
																class="rounded-full border border-line-soft px-4 py-2 type-button-label text-ink transition hover:border-flame hover:text-flame"
																@click="removeActivity(activity.local_id)"
															>
																Remove Activity
															</button>
														</div>
													</div>
												</div>
											</div>

											<div class="flex flex-wrap gap-3 border-t border-line-soft pt-4">
												<button
													type="button"
													class="if-action"
													:disabled="sessionPending || !canSave"
													@click="handleSaveSession"
												>
													{{
														sessionPending
															? 'Saving...'
															: currentSessionId
																? 'Save Session'
																: 'Create Session'
													}}
												</button>
												<button
													v-if="currentSessionId"
													type="button"
													class="if-action if-action--subtle"
													@click="startNewSessionDraft"
												>
													Start New Draft
												</button>
												<button
													type="button"
													class="rounded-full border border-line-soft px-4 py-2 type-button-label text-ink transition hover:border-ink/30"
													@click="emitClose('programmatic')"
												>
													Cancel
												</button>
											</div>
										</section>
									</section>
								</section>
							</template>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon, toast } from 'frappe-ui';
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import {
	createClassTeachingPlan,
	getStaffClassPlanningSurface,
	saveClassSession,
} from '@/lib/services/staff/staffTeachingService';
import type {
	Response as StaffClassPlanningSurfaceResponse,
	StaffPlanningActivity,
	StaffPlanningSession,
	StaffPlanningUnit,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface';

import {
	findSessionForDate,
	sessionBelongsToUnit,
	suggestedSessionTitle,
	suggestSessionSequence,
	suggestUnitPlan,
} from './quickClassSessionRules';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type EditableActivity = StaffPlanningActivity & {
	local_id: number;
};

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	studentGroup?: string | null;
	classTitle?: string | null;
	course?: string | null;
	courseName?: string | null;
	sessionDate?: string | null;
	blockLabel?: string | null;
	start?: string | null;
	end?: string | null;
	timezone?: string | null;
	classTeachingPlan?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const router = useRouter();

const overlayStyle = computed(() => {
	return props.zIndex ? ({ zIndex: props.zIndex } as Record<string, number>) : undefined;
});

const loading = ref(false);
const errorMessage = ref('');
const surface = ref<StaffClassPlanningSurfaceResponse | null>(null);
const createPending = ref(false);
const sessionPending = ref(false);
const loadToken = ref(0);
const nextActivityId = ref(1);

const requestedPlan = ref('');
const draftCoursePlan = ref('');
const selectedUnitPlan = ref('');
const currentSessionId = ref('');
const dateMatchedSessionId = ref('');

const form = reactive({
	class_session: '',
	title: '',
	session_status: 'Draft',
	session_date: '',
	sequence_index: null as number | null,
	learning_goal: '',
	teacher_note: '',
	activities: [] as EditableActivity[],
});

const selectedUnit = computed<StaffPlanningUnit | null>(() => {
	return (
		surface.value?.curriculum.units.find(unit => unit.unit_plan === selectedUnitPlan.value) || null
	);
});

const dateMatchedSession = computed<StaffPlanningSession | null>(() => {
	const unit = surface.value?.curriculum.units.find(candidate =>
		(candidate.sessions || []).some(
			session => session.class_session === dateMatchedSessionId.value
		)
	);
	return (
		unit?.sessions.find(session => session.class_session === dateMatchedSessionId.value) || null
	);
});

const courseLabel = computed(() => {
	return props.courseName || props.course || surface.value?.group.course || 'Course pending';
});

const sessionDateLabel = computed(() => {
	const raw = String(props.sessionDate || '').trim();
	if (!raw) return '';
	try {
		const date = new Date(raw.includes('T') ? raw : `${raw}T12:00:00`);
		return new Intl.DateTimeFormat(undefined, {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
			year: 'numeric',
		}).format(date);
	} catch {
		return raw;
	}
});

function safeDate(value?: string | null) {
	if (!value) return null;
	const parsed = new Date(value);
	return Number.isNaN(parsed.getTime()) ? null : parsed;
}

const timeLabel = computed(() => {
	const start = safeDate(props.start);
	if (!start) return '';
	const end = safeDate(props.end);
	const formatter = new Intl.DateTimeFormat(undefined, {
		hour: 'numeric',
		minute: '2-digit',
		timeZone: props.timezone || undefined,
	});
	if (!end) return formatter.format(start);
	return `${formatter.format(start)} – ${formatter.format(end)}`;
});

const canSave = computed(() => {
	return Boolean(
		surface.value?.teaching_plan?.class_teaching_plan && selectedUnit.value && form.title.trim()
	);
});

function buildEditableActivity(activity?: StaffPlanningActivity): EditableActivity {
	return {
		local_id: nextActivityId.value++,
		title: activity?.title || '',
		activity_type: activity?.activity_type || 'Other',
		estimated_minutes: activity?.estimated_minutes ?? null,
		sequence_index: activity?.sequence_index ?? null,
		student_direction: activity?.student_direction || '',
		teacher_prompt: activity?.teacher_prompt || '',
		resource_note: activity?.resource_note || '',
	};
}

function resetDraftForSelectedUnit() {
	form.class_session = '';
	form.title = suggestedSessionTitle(selectedUnit.value);
	form.session_status = props.sessionDate ? 'Planned' : 'Draft';
	form.session_date = String(props.sessionDate || '').trim();
	form.sequence_index = suggestSessionSequence(selectedUnit.value);
	form.learning_goal = '';
	form.teacher_note = '';
	form.activities = [];
}

function syncSessionForm(session: StaffPlanningSession | null) {
	if (!session) {
		resetDraftForSelectedUnit();
		return;
	}

	form.class_session = session.class_session || '';
	form.title = session.title || '';
	form.session_status = session.session_status || 'Draft';
	form.session_date = session.session_date || String(props.sessionDate || '').trim();
	form.sequence_index = session.sequence_index ?? suggestSessionSequence(selectedUnit.value);
	form.learning_goal = session.learning_goal || '';
	form.teacher_note = session.teacher_note || '';
	form.activities = (session.activities || []).map(activity => buildEditableActivity(activity));
}

function applySurfaceSelection(payload: StaffClassPlanningSurfaceResponse) {
	if (!draftCoursePlan.value && payload.course_plans.length === 1) {
		draftCoursePlan.value = payload.course_plans[0].course_plan;
	}

	const matched = findSessionForDate(payload.curriculum.units, props.sessionDate);
	dateMatchedSessionId.value = matched?.class_session || '';

	const currentUnitStillExists = payload.curriculum.units.some(
		unit => unit.unit_plan === selectedUnitPlan.value
	);
	if (!currentUnitStillExists) {
		selectedUnitPlan.value =
			matched?.unit_plan ||
			suggestUnitPlan(payload.curriculum.units) ||
			payload.curriculum.units[0]?.unit_plan ||
			'';
	}

	const unit =
		payload.curriculum.units.find(candidate => candidate.unit_plan === selectedUnitPlan.value) ||
		null;
	const currentSession = sessionBelongsToUnit(unit, currentSessionId.value);

	if (!currentSession && matched?.class_session) {
		selectedUnitPlan.value = matched.unit_plan;
		const matchedUnit =
			payload.curriculum.units.find(candidate => candidate.unit_plan === matched.unit_plan) ||
			null;
		currentSessionId.value = matched.class_session;
		syncSessionForm(sessionBelongsToUnit(matchedUnit, currentSessionId.value));
		return;
	}

	if (currentSession) {
		syncSessionForm(currentSession);
		return;
	}

	currentSessionId.value = '';
	syncSessionForm(null);
}

async function loadSurface() {
	const studentGroup = String(props.studentGroup || '').trim();
	if (!studentGroup) {
		loading.value = false;
		surface.value = null;
		errorMessage.value =
			'Could not determine which class to plan. Please close this overlay and try again.';
		return;
	}

	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getStaffClassPlanningSurface({
			student_group: studentGroup,
			class_teaching_plan: requestedPlan.value || undefined,
		});
		if (ticket !== loadToken.value) return;
		surface.value = payload;
		applySurfaceSelection(payload);
	} catch (error) {
		if (ticket !== loadToken.value) return;
		surface.value = null;
		errorMessage.value =
			error instanceof Error ? error.message : 'Could not load the class planning surface.';
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

async function handleCreatePlan() {
	const studentGroup = String(props.studentGroup || '').trim();
	if (!studentGroup || !draftCoursePlan.value) return;

	createPending.value = true;
	try {
		const result = await createClassTeachingPlan({
			student_group: studentGroup,
			course_plan: draftCoursePlan.value,
		});
		requestedPlan.value = result.class_teaching_plan;
		await loadSurface();
		toast.success('Class teaching plan created.');
	} catch (error) {
		toast.error(
			error instanceof Error ? error.message : 'Could not create the class teaching plan.'
		);
	} finally {
		createPending.value = false;
	}
}

function handlePlanSelectionChange(event: Event) {
	const target = event.target as HTMLSelectElement | null;
	requestedPlan.value = String(target?.value || '').trim();
	void loadSurface();
}

function handleUnitSelectionChange() {
	currentSessionId.value = '';
	syncSessionForm(null);
}

function editMatchedSession() {
	const match = dateMatchedSession.value;
	if (!match || !surface.value) return;

	const unit = surface.value.curriculum.units.find(candidate =>
		(candidate.sessions || []).some(session => session.class_session === match.class_session)
	);
	selectedUnitPlan.value = unit?.unit_plan || selectedUnitPlan.value;
	currentSessionId.value = match.class_session;
	syncSessionForm(sessionBelongsToUnit(selectedUnit.value, currentSessionId.value));
}

function startNewSessionDraft() {
	currentSessionId.value = '';
	syncSessionForm(null);
}

function addActivity() {
	form.activities.push(buildEditableActivity());
}

function removeActivity(localId: number) {
	form.activities = form.activities.filter(activity => activity.local_id !== localId);
}

function isBlankActivity(activity: EditableActivity): boolean {
	const activityType = (activity.activity_type || 'Other').trim() || 'Other';
	return !(
		(activity.title || '').trim() ||
		(activity.student_direction || '').trim() ||
		(activity.teacher_prompt || '').trim() ||
		(activity.resource_note || '').trim() ||
		activityType !== 'Other' ||
		activity.estimated_minutes
	);
}

async function handleSaveSession() {
	if (!surface.value?.teaching_plan?.class_teaching_plan || !selectedUnit.value) return;

	sessionPending.value = true;
	try {
		await saveClassSession({
			class_teaching_plan: surface.value.teaching_plan.class_teaching_plan,
			unit_plan: selectedUnit.value.unit_plan,
			class_session: currentSessionId.value || undefined,
			title: form.title.trim(),
			session_status: form.session_status,
			session_date: form.session_date || null,
			sequence_index: form.sequence_index,
			learning_goal: form.learning_goal,
			teacher_note: form.teacher_note,
			activities: form.activities
				.filter(activity => !isBlankActivity(activity))
				.map((activity, index) => ({
					title: activity.title,
					activity_type: activity.activity_type,
					estimated_minutes: activity.estimated_minutes,
					sequence_index: activity.sequence_index ?? (index + 1) * 10,
					student_direction: activity.student_direction,
					teacher_prompt: activity.teacher_prompt,
					resource_note: activity.resource_note,
				})),
		});
		toast.success(currentSessionId.value ? 'Class session updated.' : 'Class session created.');
		emitClose('programmatic');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the class session.');
	} finally {
		sessionPending.value = false;
	}
}

function openFullPlanning() {
	const studentGroup = String(props.studentGroup || '').trim();
	if (!studentGroup) return;

	emitClose('programmatic');
	void router.push({
		name: 'staff-class-planning',
		params: { studentGroup },
		query: {
			class_teaching_plan:
				surface.value?.teaching_plan?.class_teaching_plan || requestedPlan.value || undefined,
		},
	});
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

const initialFocus = ref<HTMLElement | null>(null);

function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

watch(
	() => [props.open, props.studentGroup, props.classTeachingPlan] as const,
	([isOpen, _studentGroup, classTeachingPlan]) => {
		if (!isOpen) return;
		requestedPlan.value = String(classTeachingPlan || '').trim();
		void loadSurface();
	},
	{ immediate: true }
);

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
