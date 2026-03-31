<template>
	<div class="staff-shell space-y-6">
		<section class="overflow-hidden rounded-[2rem] border border-line-soft bg-white shadow-soft">
			<div class="grid gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr),auto] lg:items-end">
				<div class="space-y-4">
					<RouterLink
						:to="{ name: 'ClassHub', params: { studentGroup } }"
						class="inline-flex items-center gap-2 type-caption text-ink/70 transition hover:text-ink"
					>
						<span>←</span>
						<span>Back to Class Hub</span>
					</RouterLink>
					<div>
						<p class="type-overline text-ink/60">Curriculum Planning</p>
						<h1 class="mt-2 type-h1 text-ink">
							{{ surface?.group.title || studentGroup || 'Class Planning' }}
						</h1>
						<p class="mt-2 max-w-3xl type-body text-ink/80">
							Keep the shared unit backbone intact while adapting pacing, session design, and
							teaching moves for this class.
						</p>
					</div>
				</div>
				<div class="flex flex-wrap gap-2 lg:justify-end">
					<span class="chip">{{ surface?.group.course || 'Course pending' }}</span>
					<span class="chip">{{ surface?.curriculum.units.length || 0 }} units</span>
					<span class="chip">{{ surface?.curriculum.session_count || 0 }} sessions</span>
					<span v-if="surface?.teaching_plan?.planning_status" class="chip">
						{{ surface.teaching_plan.planning_status }}
					</span>
				</div>
			</div>
		</section>

		<section
			v-if="errorMessage"
			class="rounded-2xl border border-flame/30 bg-[var(--flame)]/5 px-5 py-4"
		>
			<p class="type-body-strong text-flame">Could not load the class teaching plan.</p>
			<p class="mt-1 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section
			v-else-if="loading && !surface"
			class="rounded-2xl border border-line-soft bg-white px-5 py-8"
		>
			<p class="type-body text-ink/70">Loading class planning surface...</p>
		</section>

		<template v-else-if="surface">
			<section
				v-if="!surface.teaching_plan"
				class="grid gap-6 rounded-[2rem] border border-line-soft bg-white p-6 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)]"
			>
				<div class="space-y-3">
					<p class="type-overline text-ink/60">Step 1</p>
					<h2 class="type-h2 text-ink">Create the class teaching plan</h2>
					<p class="type-body text-ink/80">
						Select the governing course plan for this class. Teachers will then plan within the
						shared unit backbone instead of editing the curriculum master.
					</p>
				</div>

				<div class="space-y-5">
					<div
						v-if="!surface.course_plans.length"
						class="rounded-2xl border border-dashed border-line-soft p-5"
					>
						<p class="type-body-strong text-ink">No course plans are available yet.</p>
						<p class="mt-2 type-caption text-ink/70">
							Create the shared course plan and unit backbone before starting class planning.
						</p>
					</div>

					<template v-else>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Governing Course Plan</span>
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
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="type-body-strong text-ink">{{ plan.title }}</p>
										<p class="mt-1 type-caption text-ink/70">
											{{ plan.academic_year || 'No academic year' }}
											<span v-if="plan.cycle_label">· {{ plan.cycle_label }}</span>
										</p>
									</div>
									<span class="chip">{{ plan.plan_status || 'Draft' }}</span>
								</div>
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
							<p class="type-caption text-ink/70">
								The unit backbone stays governed. Pacing and sessions stay class-owned.
							</p>
						</div>
					</template>
				</div>
			</section>

			<section
				v-else
				class="grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)] 2xl:grid-cols-[minmax(0,22rem),minmax(0,1fr)]"
			>
				<aside class="space-y-6 xl:self-start">
					<section class="rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft">
						<div class="space-y-4">
							<div class="flex items-center justify-between gap-3">
								<div>
									<p class="type-overline text-ink/60">Class Teaching Plan</p>
									<h2 class="mt-1 type-h3 text-ink">{{ surface.teaching_plan.title }}</h2>
								</div>
								<span class="chip">{{ surface.teaching_plan.planning_status || 'Draft' }}</span>
							</div>

							<label v-if="surface.class_teaching_plans.length > 1" class="block space-y-2">
								<span class="type-caption text-ink/70">Switch plan</span>
								<select
									:value="surface.resolved.class_teaching_plan || ''"
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

							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Publishing status</span>
								<select v-model="planForm.planning_status" class="if-input w-full">
									<option value="Draft">Draft</option>
									<option value="Active">Active</option>
									<option value="Archived">Archived</option>
								</select>
							</label>

							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Teaching team note</span>
								<textarea
									v-model="planForm.team_note"
									rows="5"
									class="if-input min-h-[8rem] w-full resize-y"
									placeholder="Shared planning note for the teaching team"
								/>
							</label>

							<button
								type="button"
								class="if-action"
								:disabled="planPending"
								@click="handleSavePlan"
							>
								{{ planPending ? 'Saving...' : 'Save Plan Overview' }}
							</button>
						</div>
					</section>

					<section class="rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft">
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<p class="type-overline text-ink/60">Unit Backbone</p>
								<h2 class="mt-1 type-h3 text-ink">Class-owned pacing</h2>
							</div>
							<span class="chip">{{ surface.curriculum.units.length }} units</span>
						</div>

						<div
							v-if="!surface.curriculum.units.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-caption text-ink/70">
								This course plan does not have any governed units yet.
							</p>
						</div>

						<div v-else class="space-y-3">
							<button
								v-for="unit in surface.curriculum.units"
								:key="unit.unit_plan"
								type="button"
								class="w-full rounded-2xl border p-4 text-left transition"
								:class="
									selectedUnit?.unit_plan === unit.unit_plan
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
								"
								@click="selectUnit(unit.unit_plan)"
							>
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
										<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
										<p class="mt-1 type-caption text-ink/70">
											{{ unit.sessions.length }} sessions
										</p>
									</div>
									<span class="chip">{{ unit.pacing_status || 'Not Started' }}</span>
								</div>
							</button>
						</div>
					</section>
				</aside>

				<div v-if="selectedUnit" class="space-y-6">
					<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
						<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr),auto] lg:items-start">
							<div>
								<p class="type-overline text-ink/60">Selected Unit</p>
								<h2 class="mt-2 type-h2 text-ink">{{ selectedUnit.title }}</h2>
								<p class="mt-2 type-body text-ink/80">
									Plan pacing and teacher focus for this class without breaking the shared course
									sequence.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span class="chip">Unit {{ selectedUnit.unit_order || '—' }}</span>
								<span class="chip">{{ selectedUnit.sessions.length }} sessions</span>
								<span class="chip">{{ unitForm.pacing_status || 'Not Started' }}</span>
							</div>
						</div>

						<div class="mt-6 grid gap-4 lg:grid-cols-3">
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Pacing status</span>
								<select v-model="unitForm.pacing_status" class="if-input w-full">
									<option value="Not Started">Not Started</option>
									<option value="In Progress">In Progress</option>
									<option value="Completed">Completed</option>
									<option value="Hold">Hold</option>
								</select>
							</label>
							<label class="block space-y-2 lg:col-span-2">
								<span class="type-caption text-ink/70">Teacher focus</span>
								<input
									v-model="unitForm.teacher_focus"
									type="text"
									class="if-input w-full"
									placeholder="What matters most for this class inside the unit"
								/>
							</label>
						</div>

						<label class="mt-4 block space-y-2">
							<span class="type-caption text-ink/70">Pacing note</span>
							<textarea
								v-model="unitForm.pacing_note"
								rows="4"
								class="if-input min-h-[7rem] w-full resize-y"
								placeholder="Record adjustments, substitutions, or class-specific constraints"
							/>
						</label>

						<div class="mt-4 flex flex-wrap gap-3">
							<button
								type="button"
								class="if-action"
								:disabled="unitPending"
								@click="handleSaveUnit"
							>
								{{ unitPending ? 'Saving...' : 'Save Unit Plan For This Class' }}
							</button>
							<p class="type-caption text-ink/70">
								The unit order remains governed across all classes on this course plan.
							</p>
						</div>
					</section>

					<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Class Sessions</p>
								<h2 class="mt-1 type-h3 text-ink">Plan what this class will actually do</h2>
							</div>
							<button type="button" class="if-action" @click="startNewSession">
								New Class Session
							</button>
						</div>

						<div class="mt-5 grid gap-6 lg:grid-cols-[minmax(0,16rem),minmax(0,1fr)]">
							<div class="space-y-3">
								<button
									v-for="session in selectedUnit.sessions"
									:key="session.class_session"
									type="button"
									class="w-full rounded-2xl border p-4 text-left transition"
									:class="
										selectedSessionId === session.class_session
											? 'border-canopy bg-canopy/10 shadow-soft'
											: 'border-line-soft bg-surface-soft hover:border-canopy/40'
									"
									@click="selectSession(session.class_session)"
								>
									<p class="type-body-strong text-ink">{{ session.title }}</p>
									<p class="mt-1 type-caption text-ink/70">
										{{ session.session_status || 'Draft' }}
										<span v-if="session.session_date">· {{ session.session_date }}</span>
									</p>
								</button>

								<div
									v-if="!selectedUnit.sessions.length"
									class="rounded-2xl border border-dashed border-line-soft p-4 type-caption text-ink/70"
								>
									No sessions planned yet for this unit.
								</div>
							</div>

							<div class="space-y-4 rounded-[1.75rem] border border-line-soft bg-surface-soft p-5">
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="type-overline text-ink/60">
											{{ selectedSessionId ? 'Edit Session' : 'New Session' }}
										</p>
										<h3 class="mt-1 type-h3 text-ink">
											{{
												selectedSessionId
													? sessionForm.title || 'Untitled session'
													: 'Plan a class session'
											}}
										</h3>
									</div>
									<span class="chip">{{ sessionForm.session_status || 'Draft' }}</span>
								</div>

								<div class="grid gap-4 md:grid-cols-2">
									<label class="block space-y-2 md:col-span-2">
										<span class="type-caption text-ink/70">Session title</span>
										<input
											v-model="sessionForm.title"
											type="text"
											class="if-input w-full"
											placeholder="e.g. Evidence walk and structured discussion"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Session status</span>
										<select v-model="sessionForm.session_status" class="if-input w-full">
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
										<input
											v-model="sessionForm.session_date"
											type="date"
											class="if-input w-full"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Sequence</span>
										<input
											v-model.number="sessionForm.sequence_index"
											type="number"
											min="1"
											step="1"
											class="if-input w-full"
										/>
									</label>
									<label class="block space-y-2 md:col-span-2">
										<span class="type-caption text-ink/70">Learning goal</span>
										<textarea
											v-model="sessionForm.learning_goal"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											placeholder="State the learning goal students should understand and act on"
										/>
									</label>
									<label class="block space-y-2 md:col-span-2">
										<span class="type-caption text-ink/70">Teacher note</span>
										<textarea
											v-model="sessionForm.teacher_note"
											rows="4"
											class="if-input min-h-[7rem] w-full resize-y"
											placeholder="Private teacher-facing note for delivery and reflection"
										/>
									</label>
								</div>

								<div class="space-y-3">
									<div class="flex items-center justify-between gap-3">
										<div>
											<p class="type-overline text-ink/60">Session Activities</p>
											<p class="type-caption text-ink/70">
												Capture the flow students will experience in this class.
											</p>
										</div>
										<button type="button" class="if-action" @click="addActivity">
											Add Activity
										</button>
									</div>

									<div
										v-if="!sessionForm.activities.length"
										class="rounded-2xl border border-dashed border-line-soft p-4"
									>
										<p class="type-caption text-ink/70">
											Add teaching steps, checks for understanding, practice, or reflection.
										</p>
									</div>

									<div v-else class="space-y-3">
										<div
											v-for="(activity, index) in sessionForm.activities"
											:key="activity.local_id"
											class="rounded-2xl border border-line-soft bg-white p-4"
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

								<div class="flex flex-wrap gap-3">
									<button
										type="button"
										class="if-action"
										:disabled="sessionPending || !sessionForm.title.trim()"
										@click="handleSaveSession"
									>
										{{
											sessionPending
												? 'Saving...'
												: selectedSessionId
													? 'Save Session'
													: 'Create Session'
										}}
									</button>
									<button
										v-if="selectedSessionId"
										type="button"
										class="rounded-full border border-line-soft px-4 py-2 type-button-label text-ink transition hover:border-line-strong"
										@click="startNewSession"
									>
										Start New Session Draft
									</button>
								</div>
							</div>
						</div>
					</section>
				</div>

				<section v-else class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
					<p class="type-body text-ink/70">Select a governed unit to plan this class.</p>
				</section>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { useRoute, useRouter } from 'vue-router';

import {
	createClassTeachingPlan,
	getStaffClassPlanningSurface,
	saveClassSession,
	saveClassTeachingPlan,
	saveClassTeachingPlanUnit,
} from '@/lib/services/staff/staffTeachingService';
import type {
	Response as StaffClassPlanningSurfaceResponse,
	StaffPlanningActivity,
	StaffPlanningSession,
	StaffPlanningUnit,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface';

type EditableActivity = StaffPlanningActivity & {
	local_id: number;
};

const route = useRoute();
const router = useRouter();

const surface = ref<StaffClassPlanningSurfaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');

const createPending = ref(false);
const planPending = ref(false);
const unitPending = ref(false);
const sessionPending = ref(false);

const draftCoursePlan = ref('');
const selectedUnitPlan = ref('');
const selectedSessionId = ref('');
const nextActivityId = ref(1);
const loadToken = ref(0);

const planForm = reactive({
	planning_status: 'Draft',
	team_note: '',
});

const unitForm = reactive({
	pacing_status: 'Not Started',
	teacher_focus: '',
	pacing_note: '',
});

const sessionForm = reactive({
	class_session: '',
	title: '',
	session_status: 'Draft',
	session_date: '',
	sequence_index: null as number | null,
	learning_goal: '',
	teacher_note: '',
	activities: [] as EditableActivity[],
});

const studentGroup = computed(() => String(route.params.studentGroup || '').trim());
const requestedPlan = computed(() =>
	typeof route.query.class_teaching_plan === 'string' ? route.query.class_teaching_plan : ''
);

const selectedUnit = computed<StaffPlanningUnit | null>(() => {
	return (
		surface.value?.curriculum.units.find(unit => unit.unit_plan === selectedUnitPlan.value) || null
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

function syncPlanForm() {
	planForm.planning_status = surface.value?.teaching_plan?.planning_status || 'Draft';
	planForm.team_note = surface.value?.teaching_plan?.team_note || '';
}

function syncUnitForm(unit: StaffPlanningUnit | null) {
	unitForm.pacing_status = unit?.pacing_status || 'Not Started';
	unitForm.teacher_focus = unit?.teacher_focus || '';
	unitForm.pacing_note = unit?.pacing_note || '';
}

function syncSessionForm(session: StaffPlanningSession | null) {
	sessionForm.class_session = session?.class_session || '';
	sessionForm.title = session?.title || '';
	sessionForm.session_status = session?.session_status || 'Draft';
	sessionForm.session_date = session?.session_date || '';
	sessionForm.sequence_index = session?.sequence_index ?? null;
	sessionForm.learning_goal = session?.learning_goal || '';
	sessionForm.teacher_note = session?.teacher_note || '';
	sessionForm.activities = (session?.activities || []).map(activity =>
		buildEditableActivity(activity)
	);
}

function startNewSession() {
	selectedSessionId.value = '';
	syncSessionForm(null);
}

function selectUnit(unitPlan: string) {
	selectedUnitPlan.value = unitPlan;
	const unit = surface.value?.curriculum.units.find(row => row.unit_plan === unitPlan) || null;
	syncUnitForm(unit);
	const firstSession = unit?.sessions[0] || null;
	selectedSessionId.value = firstSession?.class_session || '';
	syncSessionForm(firstSession);
}

function selectSession(classSession: string) {
	const session =
		selectedUnit.value?.sessions.find(row => row.class_session === classSession) || null;
	selectedSessionId.value = session?.class_session || '';
	syncSessionForm(session);
}

function applySurfaceSelection(payload: StaffClassPlanningSurfaceResponse) {
	syncPlanForm();

	if (!draftCoursePlan.value && payload.course_plans.length === 1) {
		draftCoursePlan.value = payload.course_plans[0].course_plan;
	}

	const currentUnitStillExists = payload.curriculum.units.some(
		unit => unit.unit_plan === selectedUnitPlan.value
	);
	if (!currentUnitStillExists) {
		selectedUnitPlan.value = payload.curriculum.units[0]?.unit_plan || '';
	}

	const unit =
		payload.curriculum.units.find(row => row.unit_plan === selectedUnitPlan.value) || null;
	syncUnitForm(unit);

	const currentSessionStillExists = !!unit?.sessions.some(
		session => session.class_session === selectedSessionId.value
	);
	if (!currentSessionStillExists) {
		selectedSessionId.value = unit?.sessions[0]?.class_session || '';
	}

	const session =
		unit?.sessions.find(row => row.class_session === selectedSessionId.value) || null;
	syncSessionForm(session);
}

async function loadSurface() {
	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getStaffClassPlanningSurface({
			student_group: studentGroup.value,
			class_teaching_plan: requestedPlan.value || undefined,
		});
		if (ticket !== loadToken.value) return;
		surface.value = payload;
		applySurfaceSelection(payload);
	} catch (error) {
		if (ticket !== loadToken.value) return;
		surface.value = null;
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

async function handleCreatePlan() {
	if (!studentGroup.value || !draftCoursePlan.value) return;
	createPending.value = true;
	try {
		const result = await createClassTeachingPlan({
			student_group: studentGroup.value,
			course_plan: draftCoursePlan.value,
		});
		await router.replace({
			query: {
				...route.query,
				class_teaching_plan: result.class_teaching_plan,
			},
		});
		toast.success('Class teaching plan created.');
	} catch (error) {
		toast.error(
			error instanceof Error ? error.message : 'Could not create the class teaching plan.'
		);
	} finally {
		createPending.value = false;
	}
}

async function handleSavePlan() {
	if (!surface.value?.teaching_plan?.class_teaching_plan) return;
	planPending.value = true;
	try {
		await saveClassTeachingPlan({
			class_teaching_plan: surface.value.teaching_plan.class_teaching_plan,
			planning_status: planForm.planning_status,
			team_note: planForm.team_note,
		});
		await loadSurface();
		toast.success('Class teaching plan updated.');
	} catch (error) {
		toast.error(
			error instanceof Error ? error.message : 'Could not save the class teaching plan.'
		);
	} finally {
		planPending.value = false;
	}
}

async function handleSaveUnit() {
	if (!surface.value?.teaching_plan?.class_teaching_plan || !selectedUnit.value) return;
	unitPending.value = true;
	try {
		await saveClassTeachingPlanUnit({
			class_teaching_plan: surface.value.teaching_plan.class_teaching_plan,
			unit_plan: selectedUnit.value.unit_plan,
			pacing_status: unitForm.pacing_status,
			teacher_focus: unitForm.teacher_focus,
			pacing_note: unitForm.pacing_note,
		});
		await loadSurface();
		toast.success('Unit pacing updated for this class.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the unit pacing.');
	} finally {
		unitPending.value = false;
	}
}

async function handleSaveSession() {
	if (!surface.value?.teaching_plan?.class_teaching_plan || !selectedUnit.value) return;
	sessionPending.value = true;
	try {
		const result = await saveClassSession({
			class_teaching_plan: surface.value.teaching_plan.class_teaching_plan,
			unit_plan: selectedUnit.value.unit_plan,
			class_session: sessionForm.class_session || undefined,
			title: sessionForm.title.trim(),
			session_status: sessionForm.session_status,
			session_date: sessionForm.session_date || null,
			sequence_index: sessionForm.sequence_index,
			learning_goal: sessionForm.learning_goal,
			teacher_note: sessionForm.teacher_note,
			activities: sessionForm.activities.map((activity, index) => ({
				title: activity.title,
				activity_type: activity.activity_type,
				estimated_minutes: activity.estimated_minutes,
				sequence_index: activity.sequence_index ?? (index + 1) * 10,
				student_direction: activity.student_direction,
				teacher_prompt: activity.teacher_prompt,
				resource_note: activity.resource_note,
			})),
		});
		selectedSessionId.value = result.class_session;
		await loadSurface();
		toast.success('Class session saved.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the class session.');
	} finally {
		sessionPending.value = false;
	}
}

async function handlePlanSelectionChange(event: Event) {
	const target = event.target as HTMLSelectElement | null;
	const value = String(target?.value || '').trim();
	await router.replace({
		query: {
			...route.query,
			class_teaching_plan: value || undefined,
		},
	});
}

function addActivity() {
	sessionForm.activities.push(buildEditableActivity());
}

function removeActivity(localId: number) {
	sessionForm.activities = sessionForm.activities.filter(
		activity => activity.local_id !== localId
	);
}

watch(
	() => [studentGroup.value, requestedPlan.value],
	() => {
		loadSurface();
	},
	{ immediate: true }
);
</script>
