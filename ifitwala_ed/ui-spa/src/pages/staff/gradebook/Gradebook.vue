<template>
	<div class="gradebook-shell min-h-full px-4 pb-8 pt-6 md:px-6 lg:px-8 xl:px-10">
		<div class="mx-auto flex w-full max-w-[1640px] flex-col gap-6 xl:gap-8">
			<header class="flex flex-col gap-5">
				<div class="page-header">
					<div class="page-header__intro">
						<h1 class="type-h1 text-canopy">Gradebook</h1>
						<p class="type-meta text-slate-token/80">
							Pick a student group, then switch between fast single-task grading and the full class
							overview.
						</p>
					</div>

					<div class="page-header__actions">
						<div class="if-segmented">
							<button
								type="button"
								class="if-segmented__item"
								:class="{ 'if-segmented__item--active': viewMode === 'task' }"
								@click="setViewMode('task')"
							>
								Task View
							</button>
							<button
								type="button"
								class="if-segmented__item"
								:class="{ 'if-segmented__item--active': viewMode === 'overview' }"
								:disabled="!selectedGroup"
								@click="setViewMode('overview')"
							>
								Overview
							</button>
						</div>
					</div>
				</div>

				<div
					class="surface-toolbar ifit-filters flex items-center gap-2 overflow-x-auto no-scrollbar rounded-2xl border border-border/80 bg-white/90 px-4 py-3 shadow-sm backdrop-blur sm:px-5"
				>
					<div class="w-48 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="schoolOptions"
							option-label="school_name"
							option-value="name"
							:model-value="filters.school"
							:disabled="schoolsLoading || !schoolOptions.length"
							placeholder="School"
							@update:modelValue="onSchoolSelected"
						/>
					</div>

					<div class="w-36 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="yearOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.academic_year"
							:disabled="!yearOptions.length"
							placeholder="Year"
							@update:modelValue="onYearSelected"
						/>
					</div>

					<div class="w-40 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="programOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.program"
							:disabled="!programOptions.length"
							placeholder="Program"
							@update:modelValue="onProgramSelected"
						/>
					</div>

					<div class="w-40 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="courseOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.course"
							:disabled="!courseOptions.length"
							placeholder="Course"
							@update:modelValue="onCourseSelected"
						/>
					</div>

					<div class="w-48 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="groupPickerOptions"
							option-label="label"
							option-value="value"
							:model-value="selectedGroup?.name || null"
							:disabled="!groupPickerOptions.length"
							placeholder="Select group"
							@update:modelValue="onGroupSelectedFromToolbar"
						/>
					</div>

					<div class="ml-auto">
						<button
							v-if="hasActiveFilters"
							type="button"
							class="if-button if-button--quiet"
							@click="resetFilters"
						>
							<FeatherIcon name="x" class="h-4 w-4" />
							Reset
						</button>
					</div>
				</div>
			</header>

			<div class="grid gap-6 xl:gap-8 lg:grid-cols-[minmax(21rem,1fr)_minmax(0,2fr)]">
				<div class="flex flex-col gap-6 xl:gap-8">
					<section
						class="flex flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
					>
						<div class="border-b border-border/50 bg-gray-50/50 px-4 py-3">
							<div class="flex items-center justify-between gap-2">
								<h2 class="text-sm font-semibold uppercase tracking-wide text-ink/70">
									Student Groups
								</h2>
								<button
									type="button"
									class="if-button if-button--quiet if-button--icon"
									:disabled="groupsLoading"
									@click="reloadGroups()"
									aria-label="Reload groups"
								>
									<FeatherIcon name="refresh-cw" class="h-4 w-4" />
								</button>
							</div>
						</div>

						<div class="flex-1 space-y-2 overflow-y-auto p-4" style="max-height: 24rem">
							<div v-if="groupsLoading" class="space-y-2">
								<div
									v-for="n in 6"
									:key="`group-skeleton-${n}`"
									class="h-14 animate-pulse rounded-lg bg-gray-100"
								/>
							</div>
							<div
								v-else-if="!derivedGroups.length"
								class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-6 text-center text-sm text-ink/60"
							>
								<FeatherIcon name="users" class="mb-2 h-8 w-8 text-ink/20" />
								<p>No groups match filters.</p>
							</div>
							<ul v-else class="space-y-2">
								<li v-for="group in derivedGroups" :key="group.name">
									<button
										type="button"
										class="relative w-full rounded-lg border px-4 py-3 text-left transition-all"
										:class="[
											selectedGroup?.name === group.name
												? 'border-leaf bg-sky/20 text-ink shadow-sm ring-1 ring-leaf/20'
												: 'border-transparent bg-gray-50 hover:bg-gray-100 hover:text-ink',
										]"
										@click="selectGroup(group)"
									>
										<div class="flex items-center justify-between gap-2">
											<p
												class="truncate text-sm font-semibold"
												:class="selectedGroup?.name === group.name ? 'text-ink' : 'text-ink/80'"
											>
												{{ group.label }}
											</p>
											<span
												v-if="group.program || group.course"
												class="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider"
												:class="
													selectedGroup?.name === group.name
														? 'bg-white/60 text-ink/70'
														: 'bg-gray-200/60 text-ink/50'
												"
											>
												{{ [group.program, group.course].filter(Boolean).join(' • ') }}
											</span>
										</div>
										<p v-if="group.cohort" class="mt-1 truncate text-xs text-ink/50">
											Cohort {{ group.cohort }}
										</p>
									</button>
								</li>
							</ul>
						</div>
					</section>

					<section
						class="flex flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
					>
						<div class="border-b border-border/50 bg-gray-50/50 px-4 py-3">
							<div class="flex items-center justify-between gap-2">
								<div>
									<h2 class="text-sm font-semibold uppercase tracking-wide text-ink/70">Tasks</h2>
									<p class="text-xs text-ink/50" v-if="selectedGroup">{{ selectedGroup.label }}</p>
								</div>
								<p class="text-xs text-ink/45" v-if="viewMode === 'overview'">
									Select one to quick-grade
								</p>
							</div>
						</div>

						<div
							v-if="selectedGroup && (taskSummaries.length || derivedTasks.length)"
							class="border-b border-border/50 bg-white px-4 py-2"
						>
							<div class="grid grid-cols-2 gap-2">
								<FormControl
									type="select"
									size="sm"
									:options="taskTypeOptions"
									option-label="label"
									option-value="value"
									placeholder="All Types"
									v-model="filters.task_type"
									class="!mb-0"
								/>
								<FormControl
									type="select"
									size="sm"
									:options="deliveryTypeOptions"
									option-label="label"
									option-value="value"
									placeholder="All Modes"
									v-model="filters.delivery_type"
									class="!mb-0"
								/>
							</div>
						</div>

						<div class="flex-1 space-y-3 p-4">
							<div
								v-if="!selectedGroup"
								class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-8 text-center text-sm text-ink/60"
							>
								<FeatherIcon name="arrow-up" class="mb-2 h-8 w-8 text-ink/20" />
								<p>Select a group above.</p>
							</div>

							<div v-else class="space-y-3 overflow-y-auto pr-1" style="max-height: 26rem">
								<div v-if="tasksLoading" class="space-y-2">
									<div
										v-for="n in 4"
										:key="`task-skeleton-${n}`"
										class="h-16 animate-pulse rounded-lg bg-gray-100"
									/>
								</div>
								<div
									v-else-if="!taskSummaries.length"
									class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-6 text-center text-sm text-ink/60"
								>
									<p>No tasks assigned.</p>
								</div>
								<div
									v-else-if="!derivedTasks.length"
									class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-6 text-center text-sm text-ink/60"
								>
									<p>No tasks match filters.</p>
								</div>
								<ul v-else class="space-y-2">
									<li v-for="task in derivedTasks" :key="task.name">
										<button
											type="button"
											class="w-full rounded-lg border px-4 py-3 text-left transition-all"
											:class="[
												selectedTask?.name === task.name
													? 'border-leaf bg-sky/20 text-ink shadow-sm ring-1 ring-leaf/20'
													: 'border-transparent bg-gray-50 hover:bg-gray-100 hover:text-ink',
											]"
											@click="selectTask(task)"
										>
											<div class="flex flex-col gap-1">
												<div class="flex items-start justify-between gap-2">
													<p
														class="text-sm font-semibold"
														:class="selectedTask?.name === task.name ? 'text-ink' : 'text-ink/80'"
													>
														{{ task.title }}
													</p>
												</div>
												<div class="flex flex-col gap-1.5 text-xs text-ink/60">
													<div class="flex items-center gap-2">
														<Badge
															v-if="task.status"
															:variant="task.status === 'Open' ? 'solid' : 'subtle'"
															theme="gray"
														>
															{{ task.status }}
														</Badge>
														<span>Due {{ formatDate(task.due_date) || '—' }}</span>
													</div>
													<div class="flex flex-wrap gap-1 opacity-80">
														<Badge v-if="taskModeBadge(task)" variant="subtle">
															{{ taskModeBadge(task) }}
														</Badge>
														<Badge v-if="task.allow_feedback" variant="subtle">Comment</Badge>
													</div>
												</div>
											</div>
										</button>
									</li>
								</ul>
							</div>
						</div>
					</section>
				</div>

				<GradebookTaskView
					v-if="viewMode === 'task'"
					:task-name="selectedTask?.name || null"
					:focus-student="focusedStudent"
					@select-student="onTaskViewSelectStudent"
				/>
				<GradebookOverviewView
					v-else
					:group="selectedGroup"
					:school="filters.school"
					:academic-year="filters.academic_year"
					:course="filters.course"
					:task-type="filters.task_type"
					:delivery-type="filters.delivery_type"
					:selected-task-name="selectedTask?.name || null"
					@open-task="onOverviewOpenTask"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router';
import { Badge, FeatherIcon, FormControl, toast } from 'frappe-ui';
import { createGradebookService } from '@/lib/services/gradebook/gradebookService';
import { createStudentAttendanceService } from '@/lib/services/studentAttendance/studentAttendanceService';
import type { FetchSchoolFilterContextResponse } from '@/types/contracts/studentAttendance';
import type { GroupSummary } from '@/types/contracts/gradebook/fetch_groups';
import type { TaskSummary } from '@/types/contracts/gradebook/fetch_group_tasks';
import GradebookOverviewView from './components/GradebookOverviewView.vue';
import GradebookTaskView from './components/GradebookTaskView.vue';
import { formatDate, taskModeBadge } from './gradebookUtils';

const route = useRoute();
const router = useRouter();
const gradebookService = createGradebookService();
const studentAttendanceService = createStudentAttendanceService();

const filters = reactive({
	school: null as string | null,
	academic_year: null as string | null,
	program: null as string | null,
	course: null as string | null,
	task_type: null as string | null,
	delivery_type: null as string | null,
});

const defaultSchool = ref<string | null>(null);
const schools = ref<FetchSchoolFilterContextResponse['schools']>([]);
const schoolsLoading = ref(false);
const routeGroupResolving = ref(false);

const groups = ref<GroupSummary[]>([]);
const groupsLoading = ref(false);
const selectedGroup = ref<GroupSummary | null>(null);
const taskSummaries = ref<TaskSummary[]>([]);
const tasksLoading = ref(false);
const selectedTask = ref<TaskSummary | null>(null);
const viewMode = ref<'task' | 'overview'>(currentRouteView());
const focusedStudent = ref<string | null>(currentRouteStudent());

function showToast(title: string, appearance: 'danger' | 'success' | 'warning' = 'danger') {
	const toastApi = toast as unknown as
		| ((payload: { title: string; appearance?: string }) => void)
		| {
				error?: (message: string) => void;
				create?: (payload: { title: string; appearance?: string }) => void;
		  };
	if (typeof toastApi === 'function') {
		toastApi({ title, appearance });
		return;
	}
	if (appearance === 'danger' && toastApi && typeof toastApi.error === 'function') {
		toastApi.error(title);
		return;
	}
	if (toastApi && typeof toastApi.create === 'function') {
		toastApi.create({ title, appearance });
	}
}

function showDangerToast(title: string) {
	showToast(title, 'danger');
}

function onSchoolsLoaded(data: FetchSchoolFilterContextResponse) {
	const rows = Array.isArray(data.schools) ? data.schools : [];
	schools.value = rows;
	const defaultValue = data.default_school || null;
	if (defaultValue) {
		defaultSchool.value = defaultValue;
		if (!filters.school) {
			filters.school = defaultValue;
		}
	}
}

async function loadSchoolContext() {
	schoolsLoading.value = true;
	try {
		const payload = await studentAttendanceService.fetchSchoolContext({});
		onSchoolsLoaded(payload);
	} catch (error) {
		console.error('Failed to load school context', error);
		showDangerToast('Could not load schools');
	} finally {
		schoolsLoading.value = false;
	}
}

async function loadGroups(options: { skipRouteGroupSync?: boolean } = {}) {
	groupsLoading.value = true;
	try {
		const rows = await gradebookService.fetchGroups({
			school: filters.school,
		});
		if (selectedGroup.value?.name && !rows.find(row => row.name === selectedGroup.value?.name)) {
			rows.unshift(selectedGroup.value);
		}
		groups.value = rows;
		if (!options.skipRouteGroupSync) {
			await applyRouteGroupFromQuery();
		}
	} catch (error) {
		console.error('Failed to load student groups', error);
		showDangerToast('Could not load student groups');
	} finally {
		groupsLoading.value = false;
	}
}

function reloadGroups() {
	void loadGroups();
}

async function loadTasks(groupName: string) {
	tasksLoading.value = true;
	try {
		const payload = await gradebookService.fetchGroupTasks({
			student_group: groupName,
		});
		taskSummaries.value = payload?.tasks ?? [];
		applyRouteTaskFromQuery(taskSummaries.value);
	} catch (error) {
		console.error('Failed to load tasks', error);
		showDangerToast('Could not load tasks');
	} finally {
		tasksLoading.value = false;
	}
}

const schoolOptions = computed(() => {
	const base = schools.value.map(school => ({
		label: school.school_name || school.name,
		value: school.name,
	}));
	if (defaultSchool.value) return base;
	return [{ label: 'All Schools', value: null }, ...base];
});

const derivedGroups = computed(() => {
	let list = groups.value;
	if (filters.school) {
		list = list.filter(group => group.school === filters.school);
	}
	if (filters.academic_year) {
		list = list.filter(group => group.academic_year === filters.academic_year);
	}
	if (filters.program) {
		list = list.filter(group => group.program === filters.program);
	}
	if (filters.course) {
		list = list.filter(group => group.course === filters.course);
	}
	return list;
});

const groupPickerOptions = computed(() =>
	derivedGroups.value.map(group => ({
		label: group.label,
		value: group.name,
	}))
);

const availableGroupsForOptions = computed(() => {
	let list = groups.value;
	if (filters.school) {
		list = list.filter(group => group.school === filters.school);
	}
	return list;
});

const yearOptions = computed(() => {
	const years = new Set(
		availableGroupsForOptions.value.map(group => group.academic_year).filter(Boolean)
	);
	return Array.from(years)
		.sort()
		.reverse()
		.map(year => ({ label: year, value: year }));
});

const programOptions = computed(() => {
	let list = availableGroupsForOptions.value;
	if (filters.academic_year) {
		list = list.filter(group => group.academic_year === filters.academic_year);
	}
	const values = new Set(list.map(group => group.program).filter(Boolean));
	return Array.from(values)
		.sort()
		.map(program => ({ label: program, value: program }));
});

const courseOptions = computed(() => {
	let list = availableGroupsForOptions.value;
	if (filters.academic_year) {
		list = list.filter(group => group.academic_year === filters.academic_year);
	}
	if (filters.program) {
		list = list.filter(group => group.program === filters.program);
	}
	const values = new Set(list.map(group => group.course).filter(Boolean));
	return Array.from(values)
		.sort()
		.map(course => ({ label: course, value: course }));
});

const hasActiveFilters = computed(() => {
	return Boolean(filters.school || filters.academic_year || filters.program || filters.course);
});

const derivedTasks = computed(() => {
	let list = taskSummaries.value;
	if (filters.task_type) {
		list = list.filter(task => task.task_type === filters.task_type);
	}
	if (filters.delivery_type) {
		list = list.filter(task => task.delivery_type === filters.delivery_type);
	}
	return list;
});

const taskTypeOptions = computed(() => {
	const types = new Set(taskSummaries.value.map(task => task.task_type).filter(Boolean));
	return [
		{ label: 'All Types', value: null },
		...Array.from(types)
			.sort()
			.map(type => ({ label: type, value: type })),
	];
});

const deliveryTypeOptions = computed(() => {
	const types = new Set(taskSummaries.value.map(task => task.delivery_type).filter(Boolean));
	return [
		{ label: 'All Modes', value: null },
		...Array.from(types)
			.sort()
			.map(type => ({ label: type, value: type })),
	];
});

function onSchoolSelected(value: string | null) {
	filters.school = value;
	filters.academic_year = null;
	filters.program = null;
	filters.course = null;
	void loadGroups();
}

function onYearSelected(value: string | null) {
	filters.academic_year = value;
	filters.program = null;
	filters.course = null;
}

function onProgramSelected(value: string | null) {
	filters.program = value;
	filters.course = null;
}

function onCourseSelected(value: string | null) {
	filters.course = value;
}

function onGroupSelectedFromToolbar(groupName: string | null) {
	if (!groupName) {
		selectGroup(null);
		return;
	}

	const match = derivedGroups.value.find(group => group.name === groupName);
	if (!match) {
		showDangerToast('Selected group is no longer available.');
		return;
	}

	selectGroup(match);
}

function resetFilters() {
	filters.school = defaultSchool.value;
	filters.academic_year = null;
	filters.program = null;
	filters.course = null;
	void loadGroups();
}

function syncFiltersToGroup(group: GroupSummary) {
	filters.school = group.school || null;
	filters.academic_year = group.academic_year || null;
	filters.program = group.program || null;
	filters.course = group.course || null;
}

function currentRouteStudentGroup(): string | null {
	const value = route.query.student_group;
	return typeof value === 'string' && value ? value : null;
}

function currentRouteTask(): string | null {
	const value = route.query.task;
	return typeof value === 'string' && value ? value : null;
}

function currentRouteView(): 'task' | 'overview' {
	return route.query.view === 'overview' ? 'overview' : 'task';
}

function currentRouteStudent(): string | null {
	const value = route.query.student;
	return typeof value === 'string' && value ? value : null;
}

const pendingRouteGroup = ref<string | null>(currentRouteStudentGroup());
const pendingRouteTask = ref<string | null>(currentRouteTask());

async function findRouteGroup(target: string) {
	const rows = await gradebookService.fetchGroups({
		search: target,
		limit: 20,
	});
	return rows.find(row => row.name === target) || null;
}

async function applyRouteGroupFromQuery() {
	const target = pendingRouteGroup.value;
	if (!target || routeGroupResolving.value) return;

	routeGroupResolving.value = true;
	try {
		const visibleMatch = groups.value.find(row => row.name === target);
		if (visibleMatch) {
			syncFiltersToGroup(visibleMatch);
			selectedGroup.value = visibleMatch;
			pendingRouteGroup.value = null;
			return;
		}

		const resolvedMatch = await findRouteGroup(target);
		if (!resolvedMatch) {
			pendingRouteGroup.value = null;
			showDangerToast('Linked student group is no longer available.');
			return;
		}

		syncFiltersToGroup(resolvedMatch);
		await loadGroups({ skipRouteGroupSync: true });
		selectedGroup.value = groups.value.find(row => row.name === target) || resolvedMatch;
		pendingRouteGroup.value = null;
	} catch (error) {
		console.error('Failed to resolve linked student group', error);
		showDangerToast('Could not load the linked student group');
	} finally {
		routeGroupResolving.value = false;
	}
}

function applyRouteTaskFromQuery(taskList: TaskSummary[] = taskSummaries.value) {
	const target = pendingRouteTask.value;
	if (!target) return;

	const match = taskList.find(task => task.name === target) || null;
	if (match) {
		selectedTask.value = match;
		pendingRouteTask.value = null;
		return;
	}

	if (!taskList.length) {
		if (tasksLoading.value || !selectedGroup.value) {
			return;
		}
		pendingRouteTask.value = null;
		return;
	}

	pendingRouteTask.value = null;
	showDangerToast('Linked assigned work is no longer available for this class.');
}

function updateRouteQuery(mutator: (nextQuery: LocationQueryRaw) => void) {
	const nextQuery: LocationQueryRaw = { ...route.query };
	mutator(nextQuery);
	router.replace({ query: nextQuery }).catch(() => {});
}

function updateRouteStudentGroup(groupName: string | null) {
	const current = currentRouteStudentGroup();
	if (current === groupName || (!current && !groupName)) {
		return;
	}
	updateRouteQuery(nextQuery => {
		if (groupName) {
			nextQuery.student_group = groupName;
		} else {
			delete nextQuery.student_group;
		}
	});
}

function updateRouteTask(taskName: string | null) {
	const current = currentRouteTask();
	if (current === taskName || (!current && !taskName)) {
		return;
	}
	updateRouteQuery(nextQuery => {
		if (taskName) {
			nextQuery.task = taskName;
		} else {
			delete nextQuery.task;
		}
	});
}

function updateRouteView(mode: 'task' | 'overview') {
	const current = currentRouteView();
	if (current === mode) {
		return;
	}
	updateRouteQuery(nextQuery => {
		if (mode === 'overview') {
			nextQuery.view = 'overview';
		} else {
			delete nextQuery.view;
		}
	});
}

function updateRouteStudent(student: string | null) {
	const current = currentRouteStudent();
	if (current === student || (!current && !student)) {
		return;
	}
	updateRouteQuery(nextQuery => {
		if (student) {
			nextQuery.student = student;
		} else {
			delete nextQuery.student;
		}
	});
}

function setViewMode(mode: 'task' | 'overview') {
	if (mode === 'overview' && !selectedGroup.value) {
		showToast('Select a student group first.', 'warning');
		return;
	}
	viewMode.value = mode;
	updateRouteView(mode);
}

function selectGroup(group: GroupSummary | null) {
	const previousGroup = selectedGroup.value?.name || null;
	selectedGroup.value = group;
	if (previousGroup !== (group?.name || null)) {
		selectedTask.value = null;
		taskSummaries.value = [];
		updateRouteTask(null);
		updateRouteStudent(null);
		focusedStudent.value = null;
	}
	if (group) {
		updateRouteStudentGroup(group.name);
	} else {
		updateRouteStudentGroup(null);
	}
}

function selectTask(
	task: TaskSummary | null,
	options: { switchMode?: boolean; focusStudent?: string | null } = {}
) {
	selectedTask.value = task;
	updateRouteTask(task?.name || null);

	if (options.switchMode !== false && task) {
		viewMode.value = 'task';
		updateRouteView('task');
	}

	const nextFocusedStudent = options.focusStudent === undefined ? null : options.focusStudent;
	focusedStudent.value = nextFocusedStudent;
	updateRouteStudent(nextFocusedStudent);
}

function onOverviewOpenTask(payload: { taskName: string; student: string }) {
	const match = taskSummaries.value.find(task => task.name === payload.taskName) || null;
	if (!match) {
		showDangerToast('That delivery is no longer available in this class.');
		return;
	}
	selectTask(match, {
		switchMode: true,
		focusStudent: payload.student,
	});
}

function onTaskViewSelectStudent(student: string | null) {
	focusedStudent.value = student;
	updateRouteStudent(student);
}

watch(derivedGroups, newList => {
	if (selectedGroup.value) {
		const stillVisible = newList.find(group => group.name === selectedGroup.value?.name);
		if (!stillVisible) {
			selectGroup(null);
		}
	}
});

watch(derivedTasks, newList => {
	if (selectedTask.value) {
		const stillVisible = newList.find(task => task.name === selectedTask.value?.name);
		if (!stillVisible) {
			selectTask(null, { switchMode: false, focusStudent: null });
		}
	}
});

watch(
	() => route.query.student_group,
	() => {
		pendingRouteGroup.value = currentRouteStudentGroup();
		if (pendingRouteGroup.value) {
			void applyRouteGroupFromQuery();
		} else {
			selectGroup(null);
		}
	}
);

watch(
	() => route.query.task,
	() => {
		pendingRouteTask.value = currentRouteTask();
		if (pendingRouteTask.value) {
			applyRouteTaskFromQuery();
		} else {
			selectedTask.value = null;
		}
	}
);

watch(
	() => route.query.view,
	() => {
		viewMode.value = currentRouteView();
	}
);

watch(
	() => route.query.student,
	() => {
		focusedStudent.value = currentRouteStudent();
	}
);

watch(
	() => selectedGroup.value?.name,
	groupName => {
		taskSummaries.value = [];
		selectedTask.value = null;
		if (groupName) {
			void loadTasks(groupName);
		} else {
			updateRouteStudentGroup(null);
		}
	}
);

onMounted(() => {
	void (async () => {
		await loadSchoolContext();
		await loadGroups();
	})();
});
</script>
