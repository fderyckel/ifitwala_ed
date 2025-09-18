<template>
	<div class="p-4 sm:p-6 lg:p-8">
		<div class="mb-4">
			<RouterLink
				to="/student/courses"
				class="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
				aria-label="Back to courses"
			>
				<span class="mr-2">←</span> Back to Courses
			</RouterLink>
		</div>

		<h1 class="text-2xl font-bold text-gray-900 mb-2">
			Course Detail
		</h1>
		<p class="text-gray-600 mb-6">
			Course ID: <span class="font-mono">{{ course_id }}</span>
		</p>

		<!-- TODO: Replace this with real course detail fetch/render -->
		<div class="rounded-lg border border-dashed border-gray-300 p-6 bg-white">
			<p class="text-gray-500">
				Coming soon: syllabus, assignments, resources, attendance, grades…
			</p>
		</div>
	</div>
</template>

<script setup>
import { RouterLink } from 'vue-router'

// props from the route (registered via router props function)
defineProps<{
	course_id: string
}>()
</script>
