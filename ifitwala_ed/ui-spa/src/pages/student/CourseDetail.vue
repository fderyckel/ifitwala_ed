<!-- ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue -->
<template>
	<div class="space-y-6 p-4 sm:p-6 lg:p-8">
		<div>
			<RouterLink
				:to="{ name: 'student-courses' }"
				class="inline-flex items-center type-body text-ink/70 transition hover:text-ink"
				aria-label="Back to courses"
			>
				<span class="mr-2">←</span>
				Back to Courses
			</RouterLink>
		</div>

		<div v-if="loading" class="card-surface p-6">
			<p class="type-body text-ink/70">Loading course space...</p>
		</div>

		<div
			v-else-if="errorMessage"
			class="card-surface border border-flame/30 bg-[var(--flame)]/5 p-6"
		>
			<p class="type-body-strong text-flame">Could not load this course.</p>
			<p class="mt-2 type-caption text-ink/70">{{ errorMessage }}</p>
		</div>

		<template v-else-if="courseDetail">
			<header class="card-surface overflow-hidden">
				<div class="grid gap-6 lg:grid-cols-[220px,1fr]">
					<div class="bg-surface-soft">
						<img
							:src="courseDetail.course.course_image || PLACEHOLDER"
							:alt="courseDetail.course.course_name"
							class="h-full w-full object-cover"
							loading="lazy"
						/>
					</div>
					<div class="p-6">
						<p class="type-overline text-ink/60">My Course</p>
						<h1 class="mt-2 type-h1 text-ink">{{ courseDetail.course.course_name }}</h1>
						<p v-if="courseDetail.course.course_group" class="mt-2 type-caption text-ink/70">
							{{ courseDetail.course.course_group }}
						</p>
						<p v-if="courseDetail.course.description" class="mt-4 type-body text-ink/80">
							{{ courseDetail.course.description }}
						</p>
						<div class="mt-4 flex flex-wrap gap-2">
							<span class="chip">{{ courseDetail.curriculum.counts.units }} units</span>
							<span class="chip">{{ courseDetail.curriculum.counts.lessons }} lessons</span>
							<span class="chip">{{ courseDetail.curriculum.counts.activities }} activities</span>
							<span class="chip">{{ totalLinkedTasks }} linked tasks</span>
						</div>
					</div>
				</div>
			</header>

			<section class="card-surface p-5">
				<div class="mb-3 flex items-center justify-between">
					<h2 class="type-h3 text-ink">Entry Context</h2>
					<span class="chip">{{ courseDetail.deep_link.resolved.source }}</span>
				</div>
				<p class="type-body text-ink/80">{{ deepLinkSummary }}</p>
				<p v-if="courseDetail.access.student_groups.length" class="mt-3 type-caption text-ink/70">
					Available in
					{{ courseDetail.access.student_groups.length }}
					{{ courseDetail.access.student_groups.length > 1 ? 'groups' : 'group' }}.
				</p>
			</section>

			<section v-if="courseDetail.curriculum.course_tasks.length" class="card-surface p-5">
				<h2 class="mb-3 type-h3 text-ink">Course-Level Tasks</h2>
				<div class="space-y-3">
					<div
						v-for="task in courseDetail.curriculum.course_tasks"
						:key="task.task"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="flex flex-wrap items-center gap-2">
							<p class="type-body-strong text-ink">{{ task.title }}</p>
							<span v-if="task.task_type" class="chip">{{ task.task_type }}</span>
							<span v-if="task.deliveries.length" class="chip">
								{{ task.deliveries.length }}
								{{ task.deliveries.length > 1 ? 'deliveries' : 'delivery' }}
							</span>
						</div>
					</div>
				</div>
			</section>

			<section class="space-y-4">
				<div class="flex items-center justify-between">
					<h2 class="type-h2 text-ink">Curriculum Outline</h2>
					<p class="type-caption text-ink/70">Phase 1 aggregated learning structure</p>
				</div>

				<div
					v-if="!courseDetail.curriculum.units.length"
					class="card-surface border border-dashed border-line-soft p-5"
				>
					<p class="type-body text-ink/70">No learning units are available for this course yet.</p>
				</div>

				<article
					v-for="unit in courseDetail.curriculum.units"
					:key="unit.name"
					class="card-surface p-5"
				>
					<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
						<div>
							<p class="type-overline text-ink/60">Unit {{ unit.unit_order ?? '—' }}</p>
							<h3 class="type-h3 text-ink">{{ unit.unit_name }}</h3>
							<p class="mt-1 type-caption text-ink/70">
								{{ unit.lessons.length }} lessons
								<span v-if="unit.estimated_duration">· {{ unit.estimated_duration }}</span>
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<span v-if="unit.unit_status" class="chip">{{ unit.unit_status }}</span>
							<span v-if="unit.linked_tasks.length" class="chip">
								{{ unit.linked_tasks.length }} unit tasks
							</span>
						</div>
					</div>

					<div v-if="unit.linked_tasks.length" class="mt-4 space-y-2">
						<p class="type-caption text-ink/70">Linked unit tasks</p>
						<div class="flex flex-wrap gap-2">
							<span v-for="task in unit.linked_tasks" :key="task.task" class="chip">
								{{ task.title }}
							</span>
						</div>
					</div>

					<div class="mt-5 space-y-3">
						<div
							v-for="lesson in unit.lessons"
							:key="lesson.name"
							class="rounded-xl border border-line-soft bg-surface-soft p-4"
						>
							<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
								<div>
									<p class="type-body-strong text-ink">{{ lesson.title }}</p>
									<p class="type-caption text-ink/70">
										{{ lesson.lesson_type || 'Lesson' }}
										<span v-if="lesson.duration">· {{ lesson.duration }} periods</span>
										<span v-if="lesson.lesson_activities.length">
											· {{ lesson.lesson_activities.length }} activities
										</span>
									</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<span v-if="lesson.linked_tasks.length" class="chip">
										{{ lesson.linked_tasks.length }} lesson tasks
									</span>
								</div>
							</div>

							<div v-if="lesson.linked_tasks.length" class="mt-3 flex flex-wrap gap-2">
								<span v-for="task in lesson.linked_tasks" :key="task.task" class="chip">
									{{ task.title }}
								</span>
							</div>

							<div v-if="lesson.lesson_activities.length" class="mt-4 flex flex-wrap gap-2">
								<span
									v-for="activity in lesson.lesson_activities"
									:key="activity.name"
									class="chip"
								>
									{{ activity.title || activity.activity_type || 'Activity' }}
									<span v-if="activity.activity_type"> · {{ activity.activity_type }} </span>
								</span>
							</div>
						</div>
					</div>
				</article>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import { getStudentCourseDetail } from '@/lib/services/student/studentLearningHubService';
import type { Response as StudentCourseDetailResponse } from '@/types/contracts/student_hub/get_student_course_detail';

const PLACEHOLDER = '/assets/ifitwala_ed/images/course_placeholder.jpg';

const props = defineProps<{
	course_id: string;
	learning_unit?: string;
	lesson?: string;
	lesson_instance?: string;
}>();

const courseDetail = ref<StudentCourseDetailResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');

const totalLinkedTasks = computed(() => {
	if (!courseDetail.value) return 0;
	const counts = courseDetail.value.curriculum.counts;
	return counts.course_tasks + counts.unit_tasks + counts.lesson_tasks;
});

const deepLinkSummary = computed(() => {
	if (!courseDetail.value) return '';
	const resolved = courseDetail.value.deep_link.resolved;
	if (resolved.lesson_instance) {
		return `Opened from lesson instance ${resolved.lesson_instance} and anchored to this course space.`;
	}
	if (resolved.lesson) {
		return `Opened at lesson ${resolved.lesson} inside the current course structure.`;
	}
	if (resolved.learning_unit) {
		return `Opened at learning unit ${resolved.learning_unit}.`;
	}
	return 'Opened at the course level because no deeper context was available.';
});

async function loadCourseDetail() {
	loading.value = true;
	errorMessage.value = '';
	try {
		courseDetail.value = await getStudentCourseDetail({
			course_id: props.course_id,
			learning_unit: props.learning_unit || undefined,
			lesson: props.lesson || undefined,
			lesson_instance: props.lesson_instance || undefined,
		});
	} catch (error: unknown) {
		courseDetail.value = null;
		if (error instanceof Error && error.message) {
			errorMessage.value = error.message;
		} else if (typeof error === 'string' && error) {
			errorMessage.value = error;
		} else {
			errorMessage.value = 'Unable to load this course.';
		}
	} finally {
		loading.value = false;
	}
}

watch(
	() => [props.course_id, props.learning_unit, props.lesson, props.lesson_instance],
	() => {
		loadCourseDetail();
	},
	{ immediate: true }
);
</script>
