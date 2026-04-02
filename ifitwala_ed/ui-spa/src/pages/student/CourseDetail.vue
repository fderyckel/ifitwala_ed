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
						<p class="mt-4 type-body text-ink/80">
							{{
								learningFocus.statement ||
								learningSpace.course.description ||
								'Your next learning steps appear here first.'
							}}
						</p>

						<div class="mt-4 flex flex-wrap gap-2">
							<span class="chip">{{ resolvedClassLabel }}</span>
							<span class="chip">{{ learningSpace.curriculum.counts.units }} units</span>
							<span class="chip"
								>{{ learningSpace.curriculum.counts.assigned_work }} assignments</span
							>
						</div>

						<div
							class="mt-5 grid gap-4 rounded-2xl border border-line-soft bg-surface-soft p-4 lg:grid-cols-[minmax(0,1fr),auto]"
						>
							<div>
								<p class="type-caption text-ink/70">Current class</p>
								<p class="mt-1 type-body-strong text-ink">{{ resolvedClassLabel }}</p>
								<p class="mt-1 type-caption text-ink/70">
									Everything here is already filtered for your class, your current unit, and your
									next steps.
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

			<section class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr),minmax(0,0.8fr)]">
				<article class="card-surface p-6">
					<p class="type-overline text-ink/60">Learning Focus</p>
					<h2 class="mt-2 type-h2 text-ink">
						{{ learningFocus.current_unit?.title || selectedUnit?.title || 'Current learning' }}
					</h2>
					<p class="mt-3 type-body text-ink/80">
						{{
							learningFocus.statement ||
							'Your class focus will appear here when the plan is published.'
						}}
					</p>

					<div class="mt-5 grid gap-4 lg:grid-cols-2">
						<article class="rounded-2xl border border-line-soft bg-surface-soft p-4">
							<p class="type-overline text-ink/60">Current Unit</p>
							<p class="mt-2 type-body-strong text-ink">
								{{
									learningFocus.current_unit?.title || selectedUnit?.title || 'Not available yet'
								}}
							</p>
							<p v-if="selectedUnit?.overview" class="mt-2 type-caption text-ink/70">
								{{ selectedUnit.overview }}
							</p>
						</article>

						<article class="rounded-2xl border border-line-soft bg-surface-soft p-4">
							<p class="type-overline text-ink/60">Next Class Experience</p>
							<p class="mt-2 type-body-strong text-ink">
								{{
									learningFocus.current_session?.title ||
									selectedSession?.title ||
									'Your next class will appear here soon'
								}}
							</p>
							<p class="mt-2 type-caption text-ink/70">
								{{
									learningFocus.current_session?.session_date ||
									selectedSession?.session_date ||
									'Date not published yet'
								}}
							</p>
							<p
								v-if="
									learningFocus.current_session?.learning_goal || selectedSession?.learning_goal
								"
								class="mt-2 type-caption text-ink/70"
							>
								{{
									learningFocus.current_session?.learning_goal || selectedSession?.learning_goal
								}}
							</p>
						</article>
					</div>
				</article>

				<article class="card-surface p-6">
					<div class="flex items-center justify-between gap-3">
						<div>
							<p class="type-overline text-ink/60">Next Actions</p>
							<h2 class="mt-2 type-h2 text-ink">What to do next</h2>
						</div>
						<span class="chip">{{ nextActions.length }}</span>
					</div>

					<div
						v-if="!nextActions.length"
						class="mt-5 rounded-2xl border border-dashed border-line-soft p-4"
					>
						<p class="type-body text-ink/70">
							You are up to date for now. Check back here for the next session or assignment.
						</p>
					</div>

					<div v-else class="mt-5 space-y-3">
						<article
							v-for="action in nextActions"
							:key="`${action.kind}-${action.task_delivery || action.class_session || action.unit_plan || action.label}`"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<div class="flex flex-wrap items-center gap-2">
								<p class="type-body-strong text-ink">{{ action.label }}</p>
								<span class="chip">{{ nextActionChip(action) }}</span>
							</div>
							<p v-if="action.supporting_text" class="mt-2 type-caption text-ink/70">
								{{ action.supporting_text }}
							</p>
							<p v-if="nextActionContext(action)" class="mt-1 type-caption text-ink/60">
								{{ nextActionContext(action) }}
							</p>
							<div class="mt-3">
								<RouterLink
									v-if="action.kind === 'quiz' && action.task_delivery"
									:to="quizRouteForAction(action)"
									class="if-action"
								>
									Open now
								</RouterLink>
								<button v-else type="button" class="if-action" @click="handleNextAction(action)">
									Show in this course
								</button>
							</div>
						</article>
					</div>
				</article>
			</section>

			<section
				class="grid gap-6 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)] 2xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]"
			>
				<aside class="space-y-6 xl:self-start">
					<section class="card-surface p-5">
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<h2 class="type-h3 text-ink">Unit Journey</h2>
								<p class="mt-1 type-caption text-ink/70">
									Follow the shared unit sequence for your class.
								</p>
							</div>
							<span class="chip">{{ unitNavigation.length }}</span>
						</div>

						<div
							v-if="!unitNavigation.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-body text-ink/70">No units are available yet.</p>
						</div>

						<div v-else class="space-y-3">
							<button
								v-for="unit in unitNavigation"
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
								<p class="mt-1 type-caption text-ink/70">
									{{ unit.session_count }} sessions · {{ unit.assigned_work_count }} tasks
								</p>
							</button>
						</div>
					</section>
				</aside>

				<div v-if="selectedUnit" class="space-y-6">
					<section class="card-surface p-6">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">This Unit</p>
								<h2 class="mt-2 type-h2 text-ink">{{ selectedUnit.title }}</h2>
								<p v-if="selectedUnit.essential_understanding" class="mt-3 type-body text-ink/80">
									{{ selectedUnit.essential_understanding }}
								</p>
								<p v-else-if="selectedUnit.overview" class="mt-3 type-body text-ink/80">
									{{ selectedUnit.overview }}
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span class="chip">Unit {{ selectedUnit.unit_order || '—' }}</span>
								<span v-if="selectedUnit.duration" class="chip">{{ selectedUnit.duration }}</span>
								<span v-if="selectedUnit.estimated_duration" class="chip">
									{{ selectedUnit.estimated_duration }}
								</span>
							</div>
						</div>

						<div class="mt-6 grid gap-4 xl:grid-cols-3">
							<article
								v-if="selectedUnit.content"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">What you will explore</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.content }}</p>
							</article>
							<article
								v-if="selectedUnit.skills"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Skills you will practice</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.skills }}</p>
							</article>
							<article
								v-if="selectedUnit.concepts"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Big ideas</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.concepts }}</p>
							</article>
						</div>

						<details
							v-if="selectedUnit.standards.length"
							class="mt-6 rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<summary class="cursor-pointer list-none">
								<div class="flex items-center justify-between gap-3">
									<div>
										<p class="type-body-strong text-ink">Learning goals</p>
										<p class="mt-1 type-caption text-ink/70">
											See the published curriculum goals for this unit.
										</p>
									</div>
									<span class="chip">{{ selectedUnit.standards.length }}</span>
								</div>
							</summary>
							<div class="mt-4 space-y-3">
								<article
									v-for="standard in selectedUnit.standards"
									:key="`${selectedUnit.unit_plan}-${standard.standard_code}-${standard.standard_description}`"
									class="rounded-2xl border border-line-soft bg-white p-4"
								>
									<div class="flex flex-wrap items-center gap-2">
										<p class="type-body-strong text-ink">
											{{ standard.standard_code || 'Learning goal' }}
										</p>
										<span v-if="standard.coverage_level" class="chip">{{
											standard.coverage_level
										}}</span>
									</div>
									<p v-if="standard.standard_description" class="mt-2 type-body text-ink/80">
										{{ standard.standard_description }}
									</p>
								</article>
							</div>
						</details>
					</section>

					<section class="grid gap-6 lg:grid-cols-[minmax(0,16rem),minmax(0,1fr)]">
						<div class="card-surface p-5">
							<div class="mb-4 flex items-center justify-between gap-3">
								<div>
									<h2 class="type-h3 text-ink">Session Journey</h2>
									<p class="mt-1 type-caption text-ink/70">See the class flow for this unit.</p>
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
										{{ sessionTimingLabel(session) }}
									</p>
								</button>
							</div>
						</div>

						<section v-if="selectedSession" class="card-surface p-6">
							<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
								<div>
									<p class="type-overline text-ink/60">Selected Class Experience</p>
									<h2 class="mt-2 type-h2 text-ink">{{ selectedSession.title }}</h2>
									<p class="mt-2 type-body text-ink/80">
										{{ sessionTimingLabel(selectedSession) }}
									</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<span v-if="selectedSession.session_date" class="chip">
										{{ selectedSession.session_date }}
									</span>
									<span v-if="selectedSession.activities.length" class="chip">
										{{ selectedSession.activities.length }} activities
									</span>
								</div>
							</div>

							<div
								v-if="selectedSession.learning_goal"
								class="mt-5 rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Learning goal</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedSession.learning_goal }}</p>
							</div>

							<div class="mt-6 space-y-4">
								<div class="flex items-center justify-between gap-3">
									<h3 class="type-h3 text-ink">How this session works</h3>
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

							<div v-if="selectedSession.resources.length" class="mt-6 space-y-3">
								<div class="flex items-center justify-between gap-3">
									<h3 class="type-h3 text-ink">Resources for this session</h3>
									<span class="chip">{{ selectedSession.resources.length }}</span>
								</div>
								<div class="grid gap-3 lg:grid-cols-2">
									<article
										v-for="resource in selectedSession.resources"
										:key="resource.placement || resource.material"
										class="rounded-2xl border border-line-soft bg-surface-soft p-4"
									>
										<p class="type-body-strong text-ink">{{ resource.title }}</p>
										<p v-if="resource.description" class="mt-2 type-caption text-ink/70">
											{{ resource.description }}
										</p>
										<p v-if="resource.placement_note" class="mt-2 type-caption text-ink/60">
											{{ resource.placement_note }}
										</p>
										<a
											v-if="resource.open_url"
											:href="resource.open_url"
											target="_blank"
											rel="noreferrer"
											class="mt-3 inline-flex text-sm font-medium text-jacaranda transition hover:text-jacaranda/80"
										>
											Open resource
										</a>
									</article>
								</div>
							</div>

							<div v-if="selectedSession.assigned_work.length" class="mt-6 space-y-3">
								<div class="flex items-center justify-between gap-3">
									<h3 class="type-h3 text-ink">Work connected to this class</h3>
									<span class="chip">{{ selectedSession.assigned_work.length }}</span>
								</div>
								<div class="grid gap-3">
									<article
										v-for="item in selectedSession.assigned_work"
										:key="item.task_delivery"
										class="rounded-2xl border border-line-soft bg-surface-soft p-4"
									>
										<div class="flex flex-wrap items-center gap-2">
											<p class="type-body-strong text-ink">{{ item.title }}</p>
											<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
											<span v-if="item.quiz_state?.status_label" class="chip">
												{{ item.quiz_state.status_label }}
											</span>
										</div>
										<p v-if="item.due_date" class="mt-2 type-caption text-ink/70">
											Due {{ item.due_date }}
										</p>
										<div v-if="isQuizAssignedWork(item)" class="mt-3">
											<RouterLink :to="quizRouteFor(item)" class="if-action">
												{{ quizActionLabel(item) }}
											</RouterLink>
										</div>
									</article>
								</div>
							</div>
						</section>

						<section v-else class="card-surface p-6">
							<p class="type-body text-ink/70">
								Select a session to see what your class is doing.
							</p>
						</section>
					</section>
				</div>

				<section v-else class="card-surface p-6">
					<p class="type-body text-ink/70">
						Select a unit to view the learning journey for this course.
					</p>
				</section>
			</section>

			<section v-if="selectedUnit || displayedAssignedWork.length" class="card-surface p-6">
				<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p class="type-overline text-ink/60">Assigned Work</p>
						<h2 class="mt-2 type-h2 text-ink">Keep track of what needs to be done</h2>
						<p class="mt-2 type-body text-ink/80">
							{{
								selectedUnit
									? `This work is connected to ${selectedUnit.title}.`
									: 'Published work for this course will appear here.'
							}}
						</p>
					</div>
					<span class="chip">{{ displayedAssignedWork.length }}</span>
				</div>

				<div
					v-if="!displayedAssignedWork.length"
					class="mt-5 rounded-2xl border border-dashed border-line-soft p-4"
				>
					<p class="type-body text-ink/70">
						No assigned work is published for this unit right now.
					</p>
				</div>

				<div v-else class="mt-5 grid gap-3 xl:grid-cols-2">
					<article
						v-for="item in displayedAssignedWork"
						:key="item.task_delivery"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-wrap items-center gap-2">
							<p class="type-body-strong text-ink">{{ item.title }}</p>
							<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
							<span v-if="assignedWorkStatusLabel(item)" class="chip">
								{{ assignedWorkStatusLabel(item) }}
							</span>
						</div>
						<p v-if="assignedWorkTimingLabel(item)" class="mt-2 type-caption text-ink/70">
							{{ assignedWorkTimingLabel(item) }}
						</p>
						<p v-if="assignedWorkContextLine(item)" class="mt-1 type-caption text-ink/60">
							{{ assignedWorkContextLine(item) }}
						</p>
						<div class="mt-3 flex flex-wrap gap-2">
							<RouterLink
								v-if="isQuizAssignedWork(item)"
								:to="quizRouteFor(item)"
								class="if-action"
							>
								{{ quizActionLabel(item) }}
							</RouterLink>
							<button
								v-else-if="item.class_session || item.unit_plan"
								type="button"
								class="if-action"
								@click="focusAssignedWork(item)"
							>
								Show in this course
							</button>
						</div>
					</article>
				</div>
			</section>

			<section
				v-if="
					selectedUnit ||
					learningSpace.resources.class_resources.length ||
					learningSpace.resources.shared_resources.length
				"
				class="card-surface p-6"
			>
				<div class="flex items-center justify-between gap-3">
					<div>
						<p class="type-overline text-ink/60">Helpful Resources</p>
						<h2 class="mt-2 type-h2 text-ink">What you may need</h2>
					</div>
				</div>

				<div class="mt-5 grid gap-4 xl:grid-cols-3">
					<article
						v-if="selectedUnit?.shared_resources.length"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<p class="type-body-strong text-ink">This unit</p>
						<div class="mt-3 space-y-3">
							<div
								v-for="resource in selectedUnit.shared_resources"
								:key="resource.placement || resource.material"
							>
								<p class="type-caption text-ink/70">{{ resource.title }}</p>
								<a
									v-if="resource.open_url"
									:href="resource.open_url"
									target="_blank"
									rel="noreferrer"
									class="mt-1 inline-flex text-sm font-medium text-jacaranda transition hover:text-jacaranda/80"
								>
									Open resource
								</a>
							</div>
						</div>
					</article>

					<article
						v-if="learningSpace.resources.class_resources.length"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<p class="type-body-strong text-ink">Your class</p>
						<div class="mt-3 space-y-3">
							<div
								v-for="resource in learningSpace.resources.class_resources"
								:key="resource.placement || resource.material"
							>
								<p class="type-caption text-ink/70">{{ resource.title }}</p>
								<a
									v-if="resource.open_url"
									:href="resource.open_url"
									target="_blank"
									rel="noreferrer"
									class="mt-1 inline-flex text-sm font-medium text-jacaranda transition hover:text-jacaranda/80"
								>
									Open resource
								</a>
							</div>
						</div>
					</article>

					<article
						v-if="learningSpace.resources.shared_resources.length"
						class="rounded-2xl border border-line-soft bg-surface-soft p-4"
					>
						<p class="type-body-strong text-ink">Across this course</p>
						<div class="mt-3 space-y-3">
							<div
								v-for="resource in learningSpace.resources.shared_resources"
								:key="resource.placement || resource.material"
							>
								<p class="type-caption text-ink/70">{{ resource.title }}</p>
								<a
									v-if="resource.open_url"
									:href="resource.open_url"
									target="_blank"
									rel="noreferrer"
									class="mt-1 inline-flex text-sm font-medium text-jacaranda transition hover:text-jacaranda/80"
								>
									Open resource
								</a>
							</div>
						</div>
					</article>
				</div>
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
	StudentAssignedWork,
	StudentLearningNextAction,
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
	unit_plan?: string;
	class_session?: string;
}>();

const router = useRouter();

const learningSpace = ref<StudentLearningSpaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const selectedUnitPlan = ref('');
const selectedSessionId = ref('');
const loadToken = ref(0);

const learningFocus = computed(() => learningSpace.value?.learning.focus || {});
const nextActions = computed(() => learningSpace.value?.learning.next_actions || []);
const unitNavigation = computed(() => learningSpace.value?.learning.unit_navigation || []);

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

const displayedAssignedWork = computed<StudentAssignedWork[]>(() => {
	if (selectedUnit.value) {
		return dedupeAssignedWork(selectedUnit.value.assigned_work || []);
	}
	return dedupeAssignedWork(learningSpace.value?.resources.general_assigned_work || []);
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

function applySelection(payload: StudentLearningSpaceResponse) {
	const requestedSession = String(props.class_session || '').trim();
	const requestedUnit = String(props.unit_plan || '').trim();
	const defaultUnit = String(payload.learning.selected_context.unit_plan || '').trim();
	const defaultSession = String(payload.learning.selected_context.class_session || '').trim();
	const requestedSessionUnit = requestedSession
		? payload.curriculum.units.find(unit =>
				unit.sessions.some(session => session.class_session === requestedSession)
			)
		: null;

	const currentUnitStillExists = payload.curriculum.units.some(
		unit => unit.unit_plan === selectedUnitPlan.value
	);
	if (requestedSessionUnit) {
		selectedUnitPlan.value = requestedSessionUnit.unit_plan;
	} else if (
		requestedUnit &&
		payload.curriculum.units.some(unit => unit.unit_plan === requestedUnit)
	) {
		selectedUnitPlan.value = requestedUnit;
	} else if (
		defaultUnit &&
		payload.curriculum.units.some(unit => unit.unit_plan === defaultUnit)
	) {
		selectedUnitPlan.value = defaultUnit;
	} else if (!currentUnitStillExists) {
		selectedUnitPlan.value = payload.curriculum.units[0]?.unit_plan || '';
	}

	const unit =
		payload.curriculum.units.find(row => row.unit_plan === selectedUnitPlan.value) || null;
	const requestedSessionStillExists = !!unit?.sessions.some(
		session => session.class_session === requestedSession
	);
	const currentSessionStillExists = !!unit?.sessions.some(
		session => session.class_session === selectedSessionId.value
	);
	if (requestedSessionStillExists) {
		selectedSessionId.value = requestedSession;
	} else if (
		defaultSession &&
		unit?.sessions.some(session => session.class_session === defaultSession)
	) {
		selectedSessionId.value = defaultSession;
	} else if (!currentSessionStillExists) {
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

function isQuizAssignedWork(item: StudentAssignedWork) {
	return (item.task_type || '').trim() === 'Quiz';
}

function dedupeAssignedWork(items: StudentAssignedWork[]) {
	const seen = new Set<string>();
	return items.filter(item => {
		const key = String(item.task_delivery || '').trim();
		if (!key || seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

function findUnitByPlan(unitPlan?: string | null) {
	const target = String(unitPlan || '').trim();
	if (!target) return null;
	return learningSpace.value?.curriculum.units.find(unit => unit.unit_plan === target) || null;
}

function findSessionById(classSession?: string | null) {
	const target = String(classSession || '').trim();
	if (!target) return null;
	for (const unit of learningSpace.value?.curriculum.units || []) {
		const session = unit.sessions.find(row => row.class_session === target);
		if (session) return session;
	}
	return null;
}

function sessionTimingLabel(session: StudentLearningSession) {
	return session.session_date || 'Details coming soon';
}

function nextActionContext(action: StudentLearningNextAction) {
	const session = findSessionById(action.class_session);
	if (session) {
		return session.session_date ? `${session.title} · ${session.session_date}` : session.title;
	}
	const unit = findUnitByPlan(action.unit_plan);
	return unit?.title || '';
}

function humanizeLabel(value?: string | null) {
	const text = String(value || '').trim();
	if (!text) return '';
	return text.replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

function quizActionLabel(item: StudentAssignedWork) {
	if (!isQuizAssignedWork(item)) return 'Open task';
	if (item.quiz_state?.can_continue) return 'Continue quiz';
	if (item.quiz_state?.can_retry) return 'Retry quiz';
	if (item.quiz_state?.can_start) {
		return Number(item.quiz_state.attempts_used || 0) > 0 ? 'Start next attempt' : 'Start quiz';
	}
	if (item.quiz_state?.latest_attempt) return 'Review quiz';
	return 'Open quiz';
}

function quizRouteFor(item: StudentAssignedWork) {
	return {
		name: 'student-quiz',
		params: {
			course_id: props.course_id,
			task_delivery: item.task_delivery,
		},
		query: {
			student_group: learningSpace.value?.access.resolved_student_group || undefined,
			unit_plan: item.unit_plan || selectedUnitPlan.value || undefined,
			class_session: item.class_session || selectedSessionId.value || undefined,
			lesson: item.lesson || undefined,
		},
	};
}

function quizRouteForAction(action: StudentLearningNextAction) {
	return {
		name: 'student-quiz',
		params: {
			course_id: props.course_id,
			task_delivery: action.task_delivery,
		},
		query: {
			student_group: learningSpace.value?.access.resolved_student_group || undefined,
			unit_plan: action.unit_plan || undefined,
			class_session: action.class_session || undefined,
		},
	};
}

function nextActionChip(action: StudentLearningNextAction) {
	if (action.kind === 'quiz') return 'Quiz';
	if (action.kind === 'session') return 'Session';
	return 'Assigned work';
}

function assignedWorkStatusLabel(item: StudentAssignedWork) {
	if (item.quiz_state?.status_label) return item.quiz_state.status_label;
	if (item.is_complete) return 'Completed';
	return humanizeLabel(item.submission_status || item.grading_status || '');
}

function assignedWorkTimingLabel(item: StudentAssignedWork) {
	if (item.due_date) return `Due ${item.due_date}`;
	if (item.available_from) return `Available ${item.available_from}`;
	return '';
}

function assignedWorkContextLine(item: StudentAssignedWork) {
	const session = findSessionById(item.class_session);
	if (session) {
		return session.session_date ? `${session.title} · ${session.session_date}` : session.title;
	}
	const unit = findUnitByPlan(item.unit_plan);
	if (unit) return `In ${unit.title}`;
	return '';
}

function handleNextAction(action: StudentLearningNextAction) {
	if (action.unit_plan) {
		selectUnit(action.unit_plan);
	}
	if (action.class_session) {
		selectSession(action.class_session);
	}
}

function focusAssignedWork(item: StudentAssignedWork) {
	if (item.unit_plan) {
		selectUnit(item.unit_plan);
	}
	if (item.class_session) {
		selectSession(item.class_session);
	}
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
	() => [props.course_id, props.student_group, props.unit_plan, props.class_session],
	() => {
		loadLearningSpace();
	},
	{ immediate: true }
);
</script>
