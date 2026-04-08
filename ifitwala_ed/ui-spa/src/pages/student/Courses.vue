<template>
	<div class="p-4 sm:p-6 lg:p-8">
		<div class="sm:flex sm:items-center sm:justify-between mb-6">
			<h1 class="text-2xl font-bold text-gray-900">My Courses</h1>

			<div v-if="!loading && academicYears.length" class="mt-4 sm:mt-0">
				<label for="academic-year" class="sr-only">Academic Year</label>
				<select
					id="academic-year"
					v-model="selectedYear"
					@change="fetchData"
					:disabled="loading"
					class="block w-full sm:w-auto pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-[var(--jacaranda)] focus:border-[var(--jacaranda)] sm:text-sm rounded-md"
				>
					<option v-for="year in academicYears" :key="year" :value="year">
						{{ year }}
					</option>
				</select>
			</div>
		</div>

		<div v-if="loading" class="text-center py-10">
			<p class="text-gray-500">Loading courses...</p>
		</div>

		<div v-else-if="error" class="bg-[var(--flame)]/5 border-l-4 border-[var(--flame)] p-4">
			<div class="flex">
				<div class="flex-shrink-0">
					<FeatherIcon name="alert-circle" class="h-5 w-5 text-[var(--flame)]" />
				</div>
				<div class="ml-3">
					<p class="text-sm text-[var(--flame)]">{{ error }}</p>
				</div>
			</div>
		</div>

		<div
			v-else-if="!courses.length"
			class="text-center py-10 border-2 border-dashed border-gray-300 rounded-lg"
		>
			<p class="mt-2 text-sm text-gray-500">No courses found for the selected academic year.</p>
		</div>

		<div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
			<component
				v-for="course in courses"
				:key="course.course"
				:is="course.learning_space.can_open ? RouterLink : 'article'"
				v-bind="courseCardProps(course)"
				class="group block overflow-hidden rounded-2xl border border-line-soft bg-white transition-shadow duration-300"
				:class="course.learning_space.can_open ? 'shadow-md hover:shadow-xl' : 'shadow-sm'"
			>
				<div class="relative">
					<div class="aspect-video">
						<img
							:src="course.course_image || PLACEHOLDER"
							:alt="course.course_name"
							class="object-cover w-full h-full"
							loading="lazy"
							@error="imgFallback"
						/>
					</div>
				</div>
				<div class="space-y-3 p-4">
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0">
							<p
								class="truncate text-base font-semibold text-gray-900"
								:class="
									course.learning_space.can_open ? 'group-hover:text-[var(--jacaranda)]' : ''
								"
							>
								{{ course.course_name }}
							</p>
							<p class="mt-1 text-sm text-gray-500">
								{{ course.course_group || '—' }}
							</p>
						</div>
						<span class="chip shrink-0">{{ course.learning_space.status_label }}</span>
					</div>
					<p class="min-h-[3rem] text-sm text-gray-600">
						{{ course.learning_space.summary }}
					</p>
					<div class="flex items-center justify-between gap-3 pt-1">
						<p class="text-xs text-gray-500">
							{{ courseSourceLabel(course.learning_space.source) }}
						</p>
						<span v-if="course.learning_space.can_open" class="if-action">
							{{ course.learning_space.cta_label }}
						</span>
						<button v-else type="button" class="if-action cursor-not-allowed opacity-60" disabled>
							{{ course.learning_space.cta_label }}
						</button>
					</div>
				</div>
			</component>
		</div>
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
