<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
				<div>
					<p class="type-overline text-ink/60">Student Hub</p>
					<h1 class="type-h1 text-ink">My Courses</h1>
					<p class="type-body text-ink/70">
						Open the class spaces that are ready and see what is still waiting on release.
					</p>
				</div>

				<div v-if="!loading && academicYears.length" class="w-full lg:w-auto">
					<label for="academic-year" class="type-caption text-ink/70">Academic year</label>
					<select
						id="academic-year"
						v-model="selectedYear"
						@change="fetchData"
						:disabled="loading"
						class="if-input mt-2 w-full min-w-[14rem] lg:w-auto"
					>
						<option v-for="year in academicYears" :key="year" :value="year">
							{{ year }}
						</option>
					</select>
				</div>
			</div>
		</header>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading courses...</p>
		</section>

		<section v-else-if="error" class="card-surface border border-flame/30 bg-[var(--flame)]/5 p-5">
			<div class="flex">
				<div class="flex-shrink-0">
					<FeatherIcon name="alert-circle" class="h-5 w-5 text-[var(--flame)]" />
				</div>
				<div class="ml-3">
					<p class="type-body text-[var(--flame)]">{{ error }}</p>
				</div>
			</div>
		</section>

		<section
			v-else-if="!courses.length"
			class="card-surface border border-dashed border-line-soft p-10 text-center"
		>
			<p class="type-body text-ink/70">No courses found for the selected academic year.</p>
		</section>

		<section v-else class="space-y-4">
			<div class="flex items-center justify-between">
				<div>
					<p class="type-overline text-ink/60">Learning Spaces</p>
					<h2 class="type-h3 text-ink">Available courses this year</h2>
				</div>
				<span class="chip">{{ courses.length }} courses</span>
			</div>

			<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
				<component
					v-for="course in courses"
					:key="course.course"
					:is="course.learning_space.can_open ? RouterLink : 'article'"
					v-bind="courseCardProps(course)"
					class="group card-surface flex h-full flex-col overflow-hidden p-0 transition"
					:class="
						course.learning_space.can_open
							? 'hover:-translate-y-0.5 hover:border-jacaranda/35 hover:shadow-strong'
							: 'opacity-95'
					"
				>
					<div class="h-40 overflow-hidden bg-surface-soft sm:h-44">
						<img
							:src="course.course_image || PLACEHOLDER"
							:alt="course.course_name"
							class="h-full w-full object-cover"
							loading="lazy"
							@error="imgFallback"
						/>
					</div>

					<div class="flex flex-1 flex-col gap-4 p-5">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<h3
									class="truncate type-h3 text-ink"
									:class="
										course.learning_space.can_open ? 'group-hover:text-[var(--jacaranda)]' : ''
									"
								>
									{{ course.course_name }}
								</h3>
								<p class="mt-1 type-caption text-ink/70">
									{{ course.course_group || '—' }}
								</p>
							</div>
							<span class="chip shrink-0">{{ course.learning_space.status_label }}</span>
						</div>

						<p class="type-body text-ink/80">
							{{ course.learning_space.summary }}
						</p>

						<div class="mt-auto flex items-center justify-between gap-3 pt-1">
							<p class="type-caption text-ink/60">
								{{ courseSourceLabel(course.learning_space.source) }}
							</p>
							<span v-if="course.learning_space.can_open" class="if-action">
								{{ course.learning_space.cta_label }}
							</span>
							<button
								v-else
								type="button"
								class="if-action cursor-not-allowed opacity-60"
								disabled
							>
								{{ course.learning_space.cta_label }}
							</button>
						</div>
					</div>
				</component>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import { getStudentCoursesData } from '@/lib/services/student/studentLearningHubService';
import type {
	Response as StudentCoursesDataResponse,
	StudentCourseCard,
} from '@/types/contracts/student_hub/get_student_courses_data';

const loading = ref(true);
const error = ref<string | null>(null);
const courses = ref<StudentCourseCard[]>([]);
const academicYears = ref<string[]>([]);
const selectedYear = ref<string | null>(null);

// Absolute path for the public placeholder served by Frappe
const PLACEHOLDER = '/assets/ifitwala_ed/images/course_placeholder.jpg';

// If an image fails to load (404, etc.), swap to placeholder once
function imgFallback(e: Event) {
	const el = e?.target as HTMLImageElement | null;
	// Ensure it's an <img>, and avoid infinite loop by checking current src
	if (!el || el.tagName !== 'IMG') return;
	// If already the placeholder, do nothing
	const current = el.getAttribute('src') || '';
	if (current === PLACEHOLDER) return;
	el.src = PLACEHOLDER;
}

function courseCardProps(course: StudentCourseCard) {
	return course.learning_space.can_open && course.href ? { to: course.href } : {};
}

function courseSourceLabel(source: StudentCourseCard['learning_space']['source']) {
	if (source === 'class_teaching_plan') return 'Class learning space';
	if (source === 'course_plan_fallback') return 'Shared course plan';
	return 'Waiting for release';
}

async function fetchData() {
	loading.value = true;
	error.value = null;
	try {
		const response: StudentCoursesDataResponse = await getStudentCoursesData({
			academic_year: selectedYear.value,
		});

		if (response?.error) {
			error.value = response.error;
			courses.value = Array.isArray(response?.courses) ? response.courses : [];
			academicYears.value = Array.isArray(response?.academic_years) ? response.academic_years : [];
			return;
		}

		academicYears.value = Array.isArray(response?.academic_years) ? response.academic_years : [];
		courses.value = Array.isArray(response?.courses) ? response.courses : [];

		// Initialize or correct the selected year from backend
		if (
			selectedYear.value === null ||
			(response?.selected_year && response.selected_year !== selectedYear.value)
		) {
			selectedYear.value = response?.selected_year ?? null;
		}
	} catch (e: unknown) {
		console.error(e);
		error.value = 'An unexpected error occurred while fetching courses.';
	} finally {
		loading.value = false;
	}
}

onMounted(fetchData);
</script>
