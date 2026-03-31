<!-- ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue -->
<template>
	<div class="space-y-6 p-4 sm:p-6 lg:p-8">
		<div>
			<RouterLink
				:to="{ name: 'student-courses' }"
				class="inline-flex items-center gap-2 type-body text-ink/70 transition hover:text-ink"
			>
				<span>←</span>
				<span>Back to Courses</span>
			</RouterLink>
		</div>

		<section
			v-if="errorMessage"
			class="rounded-2xl border border-flame/30 bg-[var(--flame)]/5 px-5 py-4"
		>
			<p class="type-body-strong text-flame">Could not load this learning space.</p>
			<p class="mt-1 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="loading && !learningSpace" class="card-surface p-6">
			<p class="type-body text-ink/70">Loading learning space...</p>
		</section>

		<template v-else-if="learningSpace">
			<header class="card-surface overflow-hidden">
				<div class="grid gap-5 p-5 sm:gap-6 sm:p-6 xl:grid-cols-[minmax(0,9rem),minmax(0,1fr)]">
					<div class="flex justify-center xl:justify-start">
						<div
							class="w-full max-w-[7.5rem] overflow-hidden rounded-2xl border border-line-soft bg-surface-soft shadow-sm sm:max-w-[8.5rem] xl:max-w-[9rem]"
						>
							<img
								:src="learningSpace.course.course_image || PLACEHOLDER"
								:alt="learningSpace.course.course_name"
								class="aspect-square h-full w-full object-cover"
								loading="lazy"
							/>
						</div>
					</div>

					<div class="min-w-0">
						<p class="type-overline text-ink/60">Learning Space</p>
						<h1 class="mt-2 type-h1 text-ink">{{ learningSpace.course.course_name }}</h1>
						<p v-if="learningSpace.course.course_group" class="mt-2 type-caption text-ink/70">
							{{ learningSpace.course.course_group }}
						</p>
						<p v-if="learningSpace.course.description" class="mt-4 type-body text-ink/80">
							{{ learningSpace.course.description }}
						</p>

						<div class="mt-4 flex flex-wrap gap-2">
							<span class="chip">{{ learningSpace.curriculum.counts.units }} units</span>
							<span class="chip">{{ learningSpace.curriculum.counts.sessions }} sessions</span>
							<span class="chip">{{ teachingPlanLabel }}</span>
						</div>

						<div
							class="mt-5 grid gap-4 rounded-2xl border border-line-soft bg-surface-soft p-4 lg:grid-cols-[minmax(0,1fr),auto]"
						>
							<div>
								<p class="type-caption text-ink/70">Current class</p>
								<p class="mt-1 type-body-strong text-ink">{{ resolvedClassLabel }}</p>
								<p class="mt-1 type-caption text-ink/70">
									Content is resolved for your class first, then shared course plan fallback.
								</p>
							</div>

							<label
								v-if="learningSpace.access.student_group_options.length > 1"
								class="block space-y-2 lg:min-w-[16rem]"
							>
								<span class="type-caption text-ink/70">Switch class</span>
								<select
									:value="learningSpace.access.resolved_student_group || ''"
									class="if-input w-full"
									@change="handleStudentGroupChange"
								>
									<option
										v-for="option in learningSpace.access.student_group_options"
										:key="option.student_group"
										:value="option.student_group"
									>
										{{ option.label }}
									</option>
								</select>
							</label>
						</div>
					</div>
				</div>
			</header>

			<section
				v-if="learningSpace.message"
				class="rounded-2xl border border-line-soft bg-surface-soft px-5 py-4"
			>
				<p class="type-body text-ink/80">{{ learningSpace.message }}</p>
			</section>

			<section
				class="grid gap-6 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)] 2xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]"
			>
				<aside class="space-y-6 xl:self-start">
					<section class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<h2 class="type-h3 text-ink">Unit Backbone</h2>
								<p class="mt-1 type-caption text-ink/70">
									Your class follows the shared unit sequence for this course plan.
								</p>
							</div>
							<span class="chip">{{ learningSpace.curriculum.units.length }}</span>
						</div>

						<div
							v-if="!learningSpace.curriculum.units.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-body text-ink/70">No units are available yet.</p>
						</div>

						<div v-else class="space-y-3">
							<button
								v-for="unit in learningSpace.curriculum.units"
								:key="unit.unit_plan"
								type="button"
								class="w-full rounded-2xl border p-4 text-left transition"
								:class="
									selectedUnit?.unit_plan === unit.unit_plan
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/30'
								"
								@click="selectUnit(unit.unit_plan)"
							>
								<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
								<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
								<p class="mt-1 type-caption text-ink/70">{{ unit.sessions.length }} sessions</p>
							</button>
						</div>
					</section>
				</aside>

				<div v-if="selectedUnit" class="space-y-6">
					<section class="card-surface p-6">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Current Unit</p>
								<h2 class="mt-2 type-h2 text-ink">{{ selectedUnit.title }}</h2>
								<p class="mt-2 type-body text-ink/80">
									{{ selectedUnit.sessions.length }}
									{{ selectedUnit.sessions.length === 1 ? 'session' : 'sessions' }}
									linked to this unit for your class.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span class="chip">Unit {{ selectedUnit.unit_order || '—' }}</span>
								<span class="chip">{{ selectedUnit.sessions.length }} sessions</span>
							</div>
						</div>
					</section>

					<section class="grid gap-6 lg:grid-cols-[minmax(0,16rem),minmax(0,1fr)]">
						<div class="card-surface p-5">
							<div class="mb-4 flex items-center justify-between gap-3">
								<div>
									<h2 class="type-h3 text-ink">Sessions</h2>
									<p class="mt-1 type-caption text-ink/70">
										What your class is currently working through in this unit.
									</p>
								</div>
								<span class="chip">{{ selectedUnit.sessions.length }}</span>
							</div>

							<div
								v-if="!selectedUnit.sessions.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">
									Your teacher has not published class sessions for this unit yet.
								</p>
							</div>

							<div v-else class="space-y-3">
								<button
									v-for="session in selectedUnit.sessions"
									:key="session.class_session"
									type="button"
									class="w-full rounded-2xl border p-4 text-left transition"
									:class="
										selectedSession?.class_session === session.class_session
											? 'border-canopy bg-canopy/10 shadow-soft'
											: 'border-line-soft bg-surface-soft hover:border-canopy/30'
									"
									@click="selectSession(session.class_session)"
								>
									<p class="type-body-strong text-ink">{{ session.title }}</p>
									<p class="mt-1 type-caption text-ink/70">
										{{ session.session_status || 'Planned' }}
										<span v-if="session.session_date">· {{ session.session_date }}</span>
									</p>
								</button>
							</div>
						</div>

						<section v-if="selectedSession" class="card-surface p-6">
							<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
								<div>
									<p class="type-overline text-ink/60">Selected Session</p>
									<h2 class="mt-2 type-h2 text-ink">{{ selectedSession.title }}</h2>
									<p class="mt-2 type-body text-ink/80">
										{{ selectedSession.session_status || 'Planned' }}
										<span v-if="selectedSession.session_date"
											>· {{ selectedSession.session_date }}</span
										>
									</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<span class="chip">{{ selectedSession.session_status || 'Planned' }}</span>
									<span v-if="selectedSession.activities.length" class="chip">
										{{ selectedSession.activities.length }} activities
									</span>
								</div>
							</div>

							<div
								v-if="selectedSession.learning_goal"
								class="mt-5 rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Learning Goal</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedSession.learning_goal }}</p>
							</div>

							<div class="mt-6 space-y-4">
								<div class="flex items-center justify-between gap-3">
									<h3 class="type-h3 text-ink">Session Flow</h3>
									<span class="chip">{{ selectedSession.activities.length }}</span>
								</div>

								<div
									v-if="!selectedSession.activities.length"
									class="rounded-2xl border border-dashed border-line-soft p-4"
								>
									<p class="type-caption text-ink/70">
										Activity details have not been published for this session yet.
									</p>
								</div>

								<div v-else class="space-y-3">
									<article
										v-for="activity in selectedSession.activities"
										:key="`${selectedSession.class_session}-${activity.sequence_index}-${activity.title}`"
										class="rounded-2xl border border-line-soft bg-surface-soft p-4"
									>
										<div class="flex flex-wrap items-center gap-2">
											<p class="type-body-strong text-ink">{{ activity.title }}</p>
											<span v-if="activity.activity_type" class="chip">
												{{ activity.activity_type }}
											</span>
											<span v-if="activity.estimated_minutes" class="chip">
												{{ activity.estimated_minutes }} min
											</span>
										</div>
										<p v-if="activity.student_direction" class="mt-3 type-body text-ink/80">
											{{ activity.student_direction }}
										</p>
										<p v-if="activity.resource_note" class="mt-2 type-caption text-ink/70">
											{{ activity.resource_note }}
										</p>
									</article>
								</div>
							</div>
						</section>

						<section v-else class="card-surface p-6">
							<p class="type-body text-ink/70">Select a session to view the class flow.</p>
						</section>
					</section>
				</div>

				<section v-else class="card-surface p-6">
					<p class="type-body text-ink/70">Select a unit to view the sessions for your class.</p>
				</section>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { getStudentLearningSpace } from '@/lib/services/student/studentLearningHubService';
import type {
	Response as StudentLearningSpaceResponse,
	StudentLearningSession,
	StudentLearningUnit,
} from '@/types/contracts/student_learning/get_student_learning_space';

const PLACEHOLDER =
	'data:image/svg+xml;charset=UTF-8,' +
	encodeURIComponent(
		`<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#f3ede2"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-size="32" fill="#8a7963">Course</text></svg>`
	);

const props = defineProps<{
	course_id: string;
	student_group?: string;
}>();

const router = useRouter();

const learningSpace = ref<StudentLearningSpaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const selectedUnitPlan = ref('');
const selectedSessionId = ref('');
const loadToken = ref(0);

const selectedUnit = computed<StudentLearningUnit | null>(() => {
	return (
		learningSpace.value?.curriculum.units.find(
			unit => unit.unit_plan === selectedUnitPlan.value
		) || null
	);
});

const selectedSession = computed<StudentLearningSession | null>(() => {
	return (
		selectedUnit.value?.sessions.find(
			session => session.class_session === selectedSessionId.value
		) || null
	);
});

const resolvedClassLabel = computed(() => {
	const resolvedGroup = learningSpace.value?.access.resolved_student_group;
	if (!resolvedGroup) return 'Class not available';
	return (
		learningSpace.value?.access.student_group_options.find(
			option => option.student_group === resolvedGroup
		)?.label || resolvedGroup
	);
});

const teachingPlanLabel = computed(() => {
	const source = learningSpace.value?.teaching_plan.source;
	if (source === 'class_teaching_plan') return 'Class plan published';
	if (source === 'course_plan_fallback') return 'Shared course plan';
	return 'Planning not published';
});

function applySelection(payload: StudentLearningSpaceResponse) {
	const currentUnitStillExists = payload.curriculum.units.some(
		unit => unit.unit_plan === selectedUnitPlan.value
	);
	if (!currentUnitStillExists) {
		selectedUnitPlan.value = payload.curriculum.units[0]?.unit_plan || '';
	}

	const unit =
		payload.curriculum.units.find(row => row.unit_plan === selectedUnitPlan.value) || null;
	const currentSessionStillExists = !!unit?.sessions.some(
		session => session.class_session === selectedSessionId.value
	);
	if (!currentSessionStillExists) {
		selectedSessionId.value = unit?.sessions[0]?.class_session || '';
	}
}

async function loadLearningSpace() {
	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getStudentLearningSpace({
			course_id: props.course_id,
			student_group: props.student_group || undefined,
		});
		if (ticket !== loadToken.value) return;
		learningSpace.value = payload;
		applySelection(payload);
	} catch (error) {
		if (ticket !== loadToken.value) return;
		learningSpace.value = null;
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

function selectUnit(unitPlan: string) {
	selectedUnitPlan.value = unitPlan;
	selectedSessionId.value =
		learningSpace.value?.curriculum.units.find(unit => unit.unit_plan === unitPlan)?.sessions[0]
			?.class_session || '';
}

function selectSession(classSession: string) {
	selectedSessionId.value = classSession;
}

async function handleStudentGroupChange(event: Event) {
	const target = event.target as HTMLSelectElement | null;
	const value = String(target?.value || '').trim();
	await router.replace({
		query: {
			student_group: value || undefined,
		},
	});
}

watch(
	() => [props.course_id, props.student_group],
	() => {
		loadLearningSpace();
	},
	{ immediate: true }
);
</script>
