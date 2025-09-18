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
					class="block w-full sm:w-auto pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
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

		<div v-else-if="error" class="bg-red-50 border-l-4 border-red-400 p-4">
			<div class="flex">
				<div class="flex-shrink-0">
					<FeatherIcon name="alert-circle" class="h-5 w-5 text-red-400" />
				</div>
				<div class="ml-3">
					<p class="text-sm text-red-700">{{ error }}</p>
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
							:src="course.course_image"
							:alt="course.course_name"
							class="object-cover w-full h-full"
							loading="lazy"
						/>
					</div>
				</div>
				<div class="p-4">
					<p class="text-base font-semibold text-gray-900 truncate group-hover:text-blue-600">
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

async function fetchData() {
	loading.value = true
	error.value = null
	try {
		const response = await call({
			'ifitwala_ed.api.courses.get_courses_data',
			{ academic_year: selectedYear.value }
		})

		const msg = response?.message || {}
		if (msg.error) {
			error.value = msg.error
			courses.value = []
			academicYears.value = msg.academic_years || []
			// keep selectedYear as-is so the user can change it
		} else {
			academicYears.value = Array.isArray(msg.academic_years) ? msg.academic_years : []
			courses.value = Array.isArray(msg.courses) ? msg.courses : []
			// Only set on first load or when backend adjusts an invalid year
			if (selectedYear.value === null || (msg.selected_year && msg.selected_year !== selectedYear.value)) {
				selectedYear.value = msg.selected_year || null
			}
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
