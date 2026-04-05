<!-- ifitwala_ed/ui-spa/src/components/StudentContextSidebar.vue -->
<template>
	<aside class="hidden xl:block xl:w-[18rem] xl:shrink-0" aria-label="Student context navigation">
		<div class="sticky top-20 space-y-4 px-2 pb-6">
			<section class="card-surface p-4">
				<p class="type-overline text-ink/60">{{ currentPanel.kicker }}</p>
				<h2 class="mt-1 type-h3 text-ink">{{ currentPanel.title }}</h2>
				<p class="mt-2 type-caption text-ink/70">{{ currentPanel.description }}</p>

				<nav class="mt-4 space-y-2" :aria-label="`${currentPanel.title} links`">
					<RouterLink
						v-for="link in currentPanel.links"
						:key="link.label"
						:to="link.to"
						class="flex items-start gap-2 rounded-xl border px-3 py-2 transition"
						:class="
							isActiveLink(link)
								? 'border-jacaranda/40 bg-jacaranda/10 text-ink'
								: 'border-line-soft bg-surface-soft text-ink/80 hover:border-jacaranda/30'
						"
					>
						<FeatherIcon :name="link.icon" class="mt-0.5 h-4 w-4 shrink-0" />
						<span class="min-w-0">
							<span class="block type-body-strong text-current">{{ link.label }}</span>
							<span v-if="link.helper" class="block type-caption text-current/70">{{
								link.helper
							}}</span>
						</span>
					</RouterLink>
				</nav>
			</section>
		</div>
	</aside>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import type { RouteLocationRaw } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

type SidebarLink = {
	label: string;
	helper?: string;
	icon: string;
	to: RouteLocationRaw;
	activeNames?: string[];
};

type Panel = {
	kicker: string;
	title: string;
	description: string;
	links: SidebarLink[];
};

const route = useRoute();

const dashboardPanel = computed<Panel>(() => ({
	kicker: 'Dashboard',
	title: 'Today Workspace',
	description: 'Jump quickly across your daily student workflow.',
	links: [
		{
			label: 'Today',
			helper: 'See your current plan',
			icon: 'sun',
			to: { name: 'student-home' },
			activeNames: ['student-home'],
		},
		{
			label: 'My Courses',
			helper: 'Open your learning spaces',
			icon: 'book-open',
			to: { name: 'student-courses' },
			activeNames: ['student-courses', 'student-course-detail', 'student-quiz'],
		},
		{
			label: 'Activities',
			helper: 'Browse activity options',
			icon: 'star',
			to: { name: 'student-activities' },
			activeNames: ['student-activities'],
		},
		{
			label: 'Portfolio',
			helper: 'Review reflections and evidence',
			icon: 'layers',
			to: { name: 'student-portfolio' },
			activeNames: ['student-portfolio'],
		},
	],
}));

const activitiesPanel: Panel = {
	kicker: 'Activities',
	title: 'Activities Board',
	description: 'Manage bookings and return to your core learning flow.',
	links: [
		{
			label: 'Activities',
			helper: 'Current activity offers',
			icon: 'star',
			to: { name: 'student-activities' },
			activeNames: ['student-activities'],
		},
		{
			label: 'Today',
			helper: 'Back to daily cockpit',
			icon: 'home',
			to: { name: 'student-home' },
			activeNames: ['student-home'],
		},
		{
			label: 'My Courses',
			helper: 'Continue course learning',
			icon: 'book-open',
			to: { name: 'student-courses' },
			activeNames: ['student-courses', 'student-course-detail', 'student-quiz'],
		},
	],
};

const portfolioPanel: Panel = {
	kicker: 'Portfolio',
	title: 'Reflection Loop',
	description: 'Capture, review, and share portfolio-ready evidence.',
	links: [
		{
			label: 'Portfolio & Journal',
			helper: 'Your reflections and showcase',
			icon: 'layers',
			to: { name: 'student-portfolio' },
			activeNames: ['student-portfolio'],
		},
		{
			label: 'My Courses',
			helper: 'Return to class work',
			icon: 'book-open',
			to: { name: 'student-courses' },
			activeNames: ['student-courses', 'student-course-detail', 'student-quiz'],
		},
		{
			label: 'Today',
			helper: 'Back to plan',
			icon: 'home',
			to: { name: 'student-home' },
			activeNames: ['student-home'],
		},
	],
};

const coursesPanel = computed<Panel>(() => {
	const courseId = String(route.params.course_id || '').trim();
	const currentCourseTarget: RouteLocationRaw = courseId
		? {
				name: 'student-course-detail',
				params: { course_id: courseId },
				query: route.query,
			}
		: { name: 'student-courses' };

	return {
		kicker: 'Courses',
		title: 'Learning Workspace',
		description: 'Move between course overview and active class work without losing context.',
		links: [
			{
				label: 'All Courses',
				helper: 'Course list and year filter',
				icon: 'book-open',
				to: { name: 'student-courses' },
				activeNames: ['student-courses'],
			},
			{
				label: 'Current Course',
				helper: courseId ? `Course ${courseId}` : 'Open selected course',
				icon: 'compass',
				to: currentCourseTarget,
				activeNames: ['student-course-detail', 'student-quiz'],
			},
			{
				label: 'Today',
				helper: 'Return to daily routing',
				icon: 'home',
				to: { name: 'student-home' },
				activeNames: ['student-home'],
			},
		],
	};
});

const studentLogPanel: Panel = {
	kicker: 'Student Log',
	title: 'Student Log Surface',
	description: 'Review your student log entries with clear next actions.',
	links: [
		{
			label: 'Student Log',
			helper: 'Open entries and follow-ups',
			icon: 'file-text',
			to: { name: 'student-logs' },
			activeNames: ['student-logs'],
		},
		{
			label: 'Today',
			helper: 'Back to daily cockpit',
			icon: 'home',
			to: { name: 'student-home' },
			activeNames: ['student-home'],
		},
		{
			label: 'My Courses',
			helper: 'Continue learning',
			icon: 'book-open',
			to: { name: 'student-courses' },
			activeNames: ['student-courses', 'student-course-detail', 'student-quiz'],
		},
	],
};

const profilePanel: Panel = {
	kicker: 'Profile',
	title: 'Account Surface',
	description: 'Manage your identity settings and return to learning quickly.',
	links: [
		{
			label: 'Profile',
			helper: 'Account and personal info',
			icon: 'user',
			to: { name: 'student-profile' },
			activeNames: ['student-profile'],
		},
		{
			label: 'Today',
			helper: 'Back to plan',
			icon: 'home',
			to: { name: 'student-home' },
			activeNames: ['student-home'],
		},
		{
			label: 'My Courses',
			helper: 'Continue classwork',
			icon: 'book-open',
			to: { name: 'student-courses' },
			activeNames: ['student-courses', 'student-course-detail', 'student-quiz'],
		},
	],
};

const currentPanel = computed<Panel>(() => {
	const routeName = String(route.name || '').trim();
	if (routeName === 'student-activities') return activitiesPanel;
	if (routeName === 'student-portfolio') return portfolioPanel;
	if (
		routeName === 'student-courses' ||
		routeName === 'student-course-detail' ||
		routeName === 'student-quiz'
	) {
		return coursesPanel.value;
	}
	if (routeName === 'student-logs') return studentLogPanel;
	if (routeName === 'student-profile') return profilePanel;
	return dashboardPanel.value;
});

function isActiveLink(link: SidebarLink): boolean {
	const routeName = String(route.name || '').trim();
	if (Array.isArray(link.activeNames) && link.activeNames.includes(routeName)) return true;
	const to = link.to as { name?: string };
	if (to?.name) return String(to.name) === routeName;
	return false;
}
</script>
