<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';

import { academicYearScopeLabel, matchesAcademicYearScope } from './academicYearScope';
import { formatDate } from './formatters';
import type { PermissionFlags, Snapshot, TaskYearScope } from './types';

const props = defineProps<{
	snapshot: Snapshot;
	permissions: PermissionFlags;
}>();

const selectedCourse = ref<string | null>(null);
const taskYearScope = ref<TaskYearScope>('current');

watch(
	() => props.snapshot.meta.student,
	() => {
		selectedCourse.value = null;
	}
);

const courses = computed(() => props.snapshot.learning.current_courses || []);

const selectedCourseRow = computed(
	() => courses.value.find(course => course.course === selectedCourse.value) || null
);

const filteredStatusDistribution = computed(() => {
	const list = props.snapshot.learning.task_progress.status_distribution || [];
	return list.filter(item => {
		const yearMatch = matchesAcademicYearScope(item.year_scope, taskYearScope.value, {
			currentAcademicYear: props.snapshot.meta.current_academic_year,
			yearOptions: props.snapshot.history.year_options || [],
		});
		const courseMatch = selectedCourse.value
			? !item.course || item.course === selectedCourse.value
			: true;
		return yearMatch && courseMatch;
	});
});

const statusDonutData = computed(() => {
	const total =
		filteredStatusDistribution.value.reduce(
			(accumulator, current) => accumulator + (current.count || 0),
			0
		) || 1;
	return filteredStatusDistribution.value.map(item => ({
		name: item.status,
		value: item.count,
		pct: Math.round((item.count / total) * 100),
	}));
});

const taskStatusOption = computed(() => ({
	color: ['#0ea5e9', '#6366f1', '#f97316', '#22c55e', '#ef4444'],
	tooltip: {
		trigger: 'item',
		formatter: (payload: any) => `${payload.name}: ${payload.value} (${payload.data?.pct || 0}%)`,
	},
	legend: { show: false },
	series: [
		{
			type: 'pie',
			radius: ['40%', '70%'],
			itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 1 },
			data: statusDonutData.value,
			label: { show: false },
			emphasis: { label: { show: true, fontWeight: 'bold' } },
		},
	],
}));

const filteredCourseCompletion = computed(() => {
	const list = props.snapshot.learning.task_progress.by_course_completion || [];
	return list.filter(row =>
		matchesAcademicYearScope(row.academic_year, taskYearScope.value, {
			currentAcademicYear: props.snapshot.meta.current_academic_year,
			yearOptions: props.snapshot.history.year_options || [],
		})
	);
});

const completionOption = computed(() => {
	const completionRows = filteredCourseCompletion.value;
	if (!completionRows.length) return {};
	return {
		grid: { left: 100, right: 20, top: 10, bottom: 20 },
		xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
		yAxis: { type: 'category', data: completionRows.map(row => row.course_name || row.course) },
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
			formatter: (params: any) => {
				const payload = Array.isArray(params) ? params[0] : params;
				const row = completionRows[payload.dataIndex];
				return `${row.course_name || row.course}: ${Math.round((row.completion_rate || 0) * 100)}%`;
			},
		},
		series: [
			{
				type: 'bar',
				data: completionRows.map(row => Math.round((row.completion_rate || 0) * 100)),
				itemStyle: { color: '#0ea5e9' },
				showBackground: true,
				backgroundStyle: { color: '#f8fafc' },
			},
		],
	};
});

const recentTasks = computed(() => {
	const list = props.snapshot.learning.recent_tasks || [];
	if (props.permissions.can_view_tasks) return list;
	return list.filter(task => task.visible_to_student || task.visible_to_guardian);
});

function toggleCourse(courseId: string) {
	selectedCourse.value = selectedCourse.value === courseId ? null : courseId;
}
</script>

<template>
	<section class="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)_minmax(0,2fr)]">
		<div class="card-surface px-4 py-4">
			<header class="mb-3 flex items-center justify-between">
				<div>
					<h3 class="text-sm font-semibold text-slate-800">Current Courses</h3>
					<p class="text-[11px] text-slate-500">Tap a course to filter task views.</p>
				</div>
			</header>
			<div class="space-y-2">
				<div
					v-for="course in courses"
					:key="course.course"
					:class="[
						'cursor-pointer rounded-xl border px-3 py-2 text-sm transition',
						selectedCourse === course.course
							? 'border-[#1f7a45] bg-[rgba(31,122,69,0.08)]'
							: 'border-[rgb(var(--border-rgb)/0.65)] bg-[rgb(var(--surface-rgb)/0.88)] hover:bg-[rgb(var(--surface-rgb))]',
					]"
					@click="toggleCourse(course.course)"
				>
					<div class="flex items-center justify-between gap-2">
						<div class="font-semibold text-slate-900">
							{{ course.course_name || course.course }}
						</div>
						<span class="text-[11px] uppercase tracking-wide text-slate-500">
							{{ course.status || 'current' }}
						</span>
					</div>
					<div class="mt-1 flex items-center justify-between text-xs text-slate-600">
						<span>{{
							course.instructors?.map(instructor => instructor.full_name).join(', ')
						}}</span>
						<span v-if="course.completion_rate != null">
							{{ Math.round((course.completion_rate || 0) * 100) }}% tasks done
						</span>
					</div>
					<div class="text-[11px] text-slate-500">
						{{
							course.academic_summary?.latest_grade_label
								? `Latest: ${course.academic_summary.latest_grade_label}`
								: ''
						}}
					</div>
				</div>
				<div v-if="!courses.length" class="text-xs text-slate-400">No courses found.</div>
			</div>
		</div>

		<div class="card-surface px-4 py-4">
			<header class="mb-3 flex flex-wrap items-center justify-between gap-3">
				<div>
					<h3 class="text-sm font-semibold text-slate-800">Task Progress</h3>
					<p class="text-[11px] text-slate-500">
						Status distribution and completion by course ({{
							academicYearScopeLabel(taskYearScope)
						}}).
					</p>
				</div>
				<div class="flex items-center gap-2">
					<button
						v-for="scope in ['current', 'previous', 'all']"
						:key="scope"
						type="button"
						:class="[
							'rounded-full px-3 py-1 text-[11px] font-semibold',
							taskYearScope === scope
								? 'bg-emerald-500 text-white'
								: 'bg-slate-100 text-slate-600',
						]"
						@click="taskYearScope = scope as TaskYearScope"
					>
						{{ academicYearScopeLabel(scope) }}
					</button>
				</div>
			</header>
			<div class="grid gap-4 lg:grid-cols-5">
				<div class="lg:col-span-2 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
					<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-600">Task status</h4>
					<AnalyticsChart v-if="statusDonutData.length" :option="taskStatusOption" />
					<p v-else class="text-xs text-slate-400">No task data.</p>
				</div>
				<div class="lg:col-span-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
					<div class="mb-1 flex items-center justify-between text-xs text-slate-600">
						<h4 class="font-semibold uppercase tracking-wide">Completion by course</h4>
						<span class="text-[11px] text-slate-500">
							{{ selectedCourseRow ? selectedCourseRow.course_name : 'All courses' }}
						</span>
					</div>
					<AnalyticsChart v-if="filteredCourseCompletion.length" :option="completionOption" />
					<p v-else class="text-xs text-slate-400">No completion data.</p>
				</div>
			</div>
		</div>

		<div class="card-surface px-4 py-4">
			<header class="mb-3 flex items-center justify-between">
				<div>
					<h3 class="text-sm font-semibold text-slate-800">Most recent tasks</h3>
					<p class="text-[11px] text-slate-500">
						Latest {{ recentTasks.length }} items visible to you.
					</p>
				</div>
			</header>
			<div class="space-y-2">
				<div
					v-for="task in recentTasks"
					:key="task.task"
					class="rounded-xl border border-slate-200 bg-slate-50/60 px-3 py-2"
				>
					<div class="flex items-center justify-between text-xs text-slate-600">
						<div class="flex flex-wrap items-center gap-2">
							<span
								class="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-700"
							>
								{{ task.course_name || task.course }}
							</span>
							<span class="text-[11px] text-slate-500">{{ task.status || 'Assigned' }}</span>
							<span
								v-if="task.is_overdue || task.is_missed"
								class="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-700"
							>
								Overdue
							</span>
						</div>
						<span class="text-[11px] text-slate-500">{{ formatDate(task.due_date) }}</span>
					</div>
					<div class="text-sm font-semibold text-slate-900">{{ task.title }}</div>
					<div class="text-[11px] text-slate-500">
						<span v-if="props.permissions.can_view_task_marks && task.out_of">
							{{ task.mark_awarded ?? '—' }} / {{ task.out_of }}
						</span>
						<span v-else-if="!props.permissions.can_view_task_marks">Marks hidden</span>
						<span
							v-if="task.visible_to_student === false || task.visible_to_guardian === false"
							class="ml-2 text-amber-600"
						>
							Restricted
						</span>
					</div>
				</div>
				<div v-if="!recentTasks.length" class="text-xs text-slate-400">
					No recent tasks in this view.
				</div>
			</div>
		</div>
	</section>
</template>
