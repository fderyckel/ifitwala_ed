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

		<div v-else-if="!courses.length" class="text-center py-10 border-2 border-dashed border-gray-300 rounded-lg">
			<p class="mt-2 text-sm text-gray-500">No courses found for the selected academic year.</p>
		</div>

		<div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
			<RouterLink
				v-for="course in courses"
				:key="course.course"
				:to="course.href"
				class="group block bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 overflow-hidden"
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
				<div class="p-4">
					<p class="text-base font-semibold text-gray-900 truncate group-hover:text-[var(--jacaranda)]">
						{{ course.course_name }}
					</p>
					<p class="text-sm text-gray-500 mt-1">
						{{ course.course_group || '—' }}
					</p>
				</div>
			</RouterLink>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { call, FeatherIcon } from 'frappe-ui'

const loading = ref(true)
const error = ref(null)
const courses = ref([])
const academicYears = ref([])
const selectedYear = ref(null)

// Absolute path for the public placeholder served by Frappe
const PLACEHOLDER = '/assets/ifitwala_ed/images/course_placeholder.jpg'

// If an image fails to load (404, etc.), swap to placeholder once
function imgFallback(e) {
	const el = e?.target
	// Ensure it's an <img>, and avoid infinite loop by checking current src
	if (!el || el.tagName !== 'IMG') return
	// If already the placeholder, do nothing
	const current = el.getAttribute('src') || ''
	if (current === PLACEHOLDER) return
	el.src = PLACEHOLDER
}

async function fetchData() {
	loading.value = true
	error.value = null
	try {
		const response = await call(
			'ifitwala_ed.api.courses.get_courses_data',
			{ academic_year: selectedYear.value }
		)

		// Support both shapes: {message: {...}} or payload directly
		const msg = (response && typeof response === 'object' && 'message' in response)
			? response.message
			: response

		if (msg?.error) {
			error.value = msg.error
			courses.value = Array.isArray(msg?.courses) ? msg.courses : []
			academicYears.value = Array.isArray(msg?.academic_years) ? msg.academic_years : []
			return
		}

		academicYears.value = Array.isArray(msg?.academic_years) ? msg.academic_years : []
		courses.value = Array.isArray(msg?.courses) ? msg.courses : []

		// Initialize or correct the selected year from backend
		if (selectedYear.value === null || (msg?.selected_year && msg.selected_year !== selectedYear.value)) {
			selectedYear.value = msg?.selected_year ?? null
		}
	} catch (e) {
		console.error(e)
		error.value = 'An unexpected error occurred while fetching courses.'
	} finally {
		loading.value = false
	}
}

onMounted(fetchData)
</script>

