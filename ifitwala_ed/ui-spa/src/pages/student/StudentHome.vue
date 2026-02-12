<!-- ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Student Portal</p>
					<h1 class="type-h1 text-ink">Welcome, {{ user.fullname }}.</h1>
					<p class="type-body text-ink/70">Keep your day clear with one-click access to learning and activities.</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink :to="{ name: 'student-activities' }" class="if-action">Book Activities</RouterLink>
					<button type="button" class="if-action" :disabled="loadingCourses" @click="courseResource.reload()">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="card-surface p-5">
			<div class="mb-3 flex items-center justify-between">
				<h2 class="type-h3 text-ink">Today’s Classes</h2>
				<RouterLink :to="{ name: 'student-courses' }" class="if-action">All Courses</RouterLink>
			</div>

			<p v-if="daySummary" class="mb-3 type-caption text-ink/70">{{ daySummary }}</p>

			<div v-if="loadingCourses" class="type-body text-ink/70">Loading today’s classes...</div>
			<div v-else-if="courseError" class="rounded-lg border border-line-soft bg-surface-soft p-3">
				<p class="type-body-strong text-flame">Could not load classes.</p>
				<p class="type-caption text-ink/70">{{ courseErrorMessage }}</p>
			</div>
			<div v-else-if="!todayCourses.length" class="rounded-lg border border-line-soft bg-surface-soft p-3">
				<p class="type-body text-ink/70">No classes scheduled for today.</p>
			</div>
			<div v-else class="space-y-3">
				<RouterLink
					v-for="course in todayCourses"
					:key="course.student_group"
					:to="course.href ?? { name: 'student-course-detail', params: { course_id: course.course } }"
					class="block rounded-xl border border-line-soft bg-surface-soft p-4 transition hover:shadow-soft"
				>
					<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
						<div>
							<p class="type-body-strong text-ink">{{ course.course_name }}</p>
							<p v-if="course.student_group_name && course.student_group_name !== course.course_name" class="type-caption text-ink/70">
								{{ course.student_group_name }}
							</p>
							<p v-if="course.instructors?.length" class="type-caption text-ink/70">
								{{ course.instructors.length > 1 ? 'Instructors' : 'Instructor' }}: {{ course.instructors.join(', ') }}
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<span v-for="(slot, idx) in course.time_slots" :key="`${course.student_group}-${idx}`" class="chip">
								{{ slot.block_number ? `B${slot.block_number}` : 'Slot' }}
								<span v-if="slot.time_range">· {{ slot.time_range }}</span>
							</span>
						</div>
					</div>
				</RouterLink>
			</div>
		</section>

		<section class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">Calendar</h2>
			<StudentCalendar :auto-refresh-interval="30 * 60 * 1000" />
		</section>

		<section class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">Quick Links</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<RouterLink v-for="item in quickLinks" :key="item.title" :to="item.to" class="action-tile group">
					<div class="action-tile__icon">
						<FeatherIcon :name="item.icon" class="h-5 w-5" />
					</div>
					<div class="min-w-0 flex-1">
						<p class="type-body-strong text-ink transition-colors group-hover:text-jacaranda">{{ item.title }}</p>
						<p class="truncate type-caption text-ink/70">{{ item.description }}</p>
					</div>
					<FeatherIcon name="chevron-right" class="h-4 w-4 text-ink/40" />
				</RouterLink>
			</div>
		</section>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { FeatherIcon, createResource } from 'frappe-ui'

import StudentCalendar from '@/components/calendar/StudentCalendar.vue'

const user = computed(() => window.frappe?.session?.user_info || { fullname: 'Student' })

const courseResource = createResource({
	url: 'ifitwala_ed.api.course_schedule.get_today_courses',
	method: 'POST',
	auto: true,
	transform: (data) => {
		const payload = data && typeof data === 'object' && 'message' in data ? data.message : data
		return {
			courses: Array.isArray(payload?.courses) ? payload.courses : [],
			date: payload?.date ?? null,
			weekday: payload?.weekday ?? null,
		}
	},
})

const loadingCourses = computed(() => courseResource.loading)
const courseError = computed(() => courseResource.error)
const courseErrorMessage = computed(() => {
	const err = courseError.value
	if (!err) return ''
	if (typeof err === 'string') return err
	if (err instanceof Error) return err.message || "Unable to load today's courses."
	if (err && typeof err === 'object' && 'message' in err) {
		const message = typeof err.message === 'string' ? err.message : ''
		return message || "Unable to load today's courses."
	}
	return "Unable to load today's courses."
})

const todayCourses = computed(() => courseResource.data?.courses ?? [])
const scheduleMeta = computed(() => ({
	date: courseResource.data?.date ?? null,
	weekday: courseResource.data?.weekday ?? null,
}))
const daySummary = computed(() => {
	const { date, weekday } = scheduleMeta.value
	if (date && weekday) return `${weekday}, ${date}`
	return weekday || date || ''
})

const quickLinks = [
	{
		title: 'Activity Booking',
		description: 'Browse and book extra-curricular activities.',
		icon: 'star',
		to: { name: 'student-activities' },
	},
	{
		title: 'My Courses',
		description: 'Open your course spaces.',
		icon: 'book-open',
		to: { name: 'student-courses' },
	},
	{
		title: 'Portfolio & Journal',
		description: 'Curate showcase evidence and reflections.',
		icon: 'layers',
		to: { name: 'student-portfolio' },
	},
	{
		title: 'Student Log',
		description: 'Review socio-emotional notes.',
		icon: 'file-text',
		to: { name: 'student-logs' },
	},
	{
		title: 'Profile',
		description: 'Manage your personal details.',
		icon: 'user',
		to: { name: 'student-profile' },
	},
]
</script>
