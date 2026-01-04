<!-- ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue -->
<template>
  <div class="space-y-8">
    <header class="border-b border-gray-200 pb-4">
      <h1 class="text-3xl font-bold text-gray-800">Welcome back, {{ user.fullname }}!</h1>
      <p class="mt-1 text-md text-gray-600">Here's a quick overview of your day.</p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 space-y-8">
        <section aria-labelledby="courses-heading">
          <div class="flex items-center justify-between mb-4">
            						<h2 id="courses-heading" class="text-xl font-semibold text-gray-700">My Courses</h2>
						<div class="flex items-center gap-3">
							<button
								type="button"
								class="inline-flex items-center gap-2 rounded-md border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 transition hover:border-[var(--jacaranda-rgb)]/30 hover:text-jacaranda disabled:cursor-not-allowed disabled:opacity-60"
								@click="courseResource.reload()"
								:disabled="loadingCourses"
							>
								<FeatherIcon name="refresh-cw" class="w-4 h-4" />
								Refresh
							</button>
							<RouterLink
								:to="{ name: 'student-courses' }"
								class="text-sm font-medium text-jacaranda hover:underline"
							>
								View All
							</RouterLink>
						</div>
					</div>
					<p v-if="daySummary" class="text-sm text-gray-500 mb-4">Today: {{ daySummary }}</p>
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						<template v-if="loadingCourses">
							<div class="col-span-full flex items-center justify-center h-32 bg-white border border-gray-200 rounded-lg text-gray-500">
								Loading today's courses…
							</div>
						</template>
						<template v-else-if="courseError">
							<div class="col-span-full bg-flame/5 border border-flame/20 text-flame px-4 py-3 rounded-lg">
								{{ courseErrorMessage || "Unable to load today's courses." }}
								<button
									type="button"
									class="ml-3 text-sm font-semibold underline hover:text-red-800 disabled:opacity-60"
									@click="courseResource.reload()"
									:disabled="loadingCourses"
								>
									Retry
								</button>
							</div>
						</template>
						<template v-else-if="!todayCourses.length">
							<div class="col-span-full border-2 border-dashed border-gray-300 rounded-lg p-6 text-center text-gray-500">
								No classes scheduled for today.
							</div>
						</template>
						<template v-else>
							<RouterLink
								v-for="course in todayCourses"
								:key="course.student_group"
								:to="course.href ?? { name: 'student-course-detail', params: { course_id: course.course } }"
								class="group bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-leaf"
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<h3 class="font-semibold text-gray-800 group-hover:text-jacaranda transition-colors">
											{{ course.course_name }}
										</h3>
										<p v-if="course.student_group_name && course.student_group_name !== course.course_name" class="text-sm text-gray-500">
											{{ course.student_group_name }}
										</p>
										<p v-if="course.rotation_day" class="text-xs uppercase tracking-wide text-leaf mt-2 font-medium">
											Day {{ course.rotation_day }}
										</p>
									</div>
									<div class="flex-shrink-0">
										<FeatherIcon name="book-open" class="w-6 h-6 text-gray-400 group-hover:text-jacaranda transition-colors" />
									</div>
								</div>
								<div v-if="course.instructors && course.instructors.length" class="mt-3 text-sm text-gray-600">
									{{ course.instructors.length > 1 ? 'Instructors' : 'Instructor' }}:
									{{ course.instructors.join(', ') }}
								</div>
								<ul class="mt-4 space-y-2">
									<li
										v-for="(slot, idx) in course.time_slots"
										:key="`${course.student_group}-${idx}`"
										class="flex items-start text-sm text-gray-600"
									>
										<FeatherIcon name="clock" class="w-4 h-4 mt-0.5 text-gray-400" />
										<span class="ml-2">
											<span v-if="slot.block_number">Block {{ slot.block_number }}</span>
											<span v-if="slot.block_number && (slot.time_range || slot.location)"> &bull; </span>
											<span v-if="slot.time_range">{{ slot.time_range }}</span>
											<span v-if="slot.location"> &bull; {{ slot.location }}</span>
										</span>
									</li>
								</ul>
							</RouterLink>
						</template>
					</div>
				</section>

				<section class="grid grid-cols-1 gap-8">
					<StudentCalendar :auto-refresh-interval="30 * 60 * 1000" />
				</section>
			</div>

			<div class="lg:col-span-1 space-y-6">
				<section aria-labelledby="more-heading">
					<h2 id="more-heading" class="text-xl font-semibold text-gray-700 mb-4">Quick Links</h2>
					<div class="space-y-4">
						<RouterLink v-for="item in moreLinks" :key="item.title" :to="item.to" class="group flex items-center bg-white p-4 border border-gray-200 rounded-lg shadow-sm hover:border-jacaranda hover:shadow-lg transition-all">
							<div class="mr-4 bg-sky-100 text-jacaranda rounded-lg p-2">
								<FeatherIcon :name="item.icon" class="w-6 h-6" />
							</div>
							<div>
								<h3 class="font-semibold text-gray-800">{{ item.title }}</h3>
								<p class="text-sm text-gray-500">{{ item.description }}</p>
							</div>
							<FeatherIcon name="chevron-right" class="w-5 h-5 text-gray-400 ml-auto group-hover:text-jacaranda" />
						</RouterLink>
					</div>
				</section>
			</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon, createResource } from 'frappe-ui';
import StudentCalendar from '@/components/calendar/StudentCalendar.vue';

// Get user info from Frappe's session object for the welcome message
const user = computed(() => {
	return window.frappe?.session?.user_info || { fullname: 'Student' };
});

// Resource-driven fetch for today's courses (Espresso way)
const courseResource = createResource({
	url: 'ifitwala_ed.api.course_schedule.get_today_courses',
	method: 'POST',
	auto: true,
	transform: (data) => {
		const payload =
			data && typeof data === 'object' && 'message' in data ? data.message : data;

		return {
			courses: Array.isArray(payload?.courses) ? payload.courses : [],
			date: payload?.date ?? null,
			weekday: payload?.weekday ?? null,
		};
	},
});

const loadingCourses = computed(() => courseResource.loading);
const courseError = computed(() => courseResource.error);
const courseErrorMessage = computed(() => {
	const err = courseError.value;
	if (!err) return '';
	if (typeof err === 'string') return err;
	if (err instanceof Error) return err.message || "Unable to load today's courses.";
	if (err && typeof err === 'object' && 'message' in err) {
		const message = typeof err.message === 'string' ? err.message : '';
		return message || "Unable to load today's courses.";
	}
	return "Unable to load today's courses.";
});
const todayCourses = computed(() => courseResource.data?.courses ?? []);
const scheduleMeta = computed(() => ({
	date: courseResource.data?.date ?? null,
	weekday: courseResource.data?.weekday ?? null,
}));

const daySummary = computed(() => {
	const { date, weekday } = scheduleMeta.value;
	if (date && weekday) return `${weekday}, ${date}`;
	return weekday || date || '';
});

// Data for the "More" section cards
const moreLinks = [
	{
		title: 'Student Log',
    description: 'View socio-emotional notes.',
    icon: 'file-text',
		to: { name: 'student-logs' }
  },
  {
    title: 'Wellbeing',
    description: 'Access resources and check-ins.',
    icon: 'heart',
    to: '/student/wellbeing'
  },
  {
    title: 'Demographics',
    description: 'Manage your profile and details.',
    icon: 'user',
    to: { name: 'student-profile' }
  },
];
</script>
