<template>
	<div class="gradebook-shell min-h-full px-4 pb-8 pt-6 md:px-6 lg:px-8 xl:px-10">
		<div class="mx-auto flex w-full max-w-[1640px] flex-col gap-6 xl:gap-8">
			<header class="flex flex-col gap-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="space-y-1">
						<h1 class="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Gradebook</h1>
						<p class="max-w-3xl text-base text-ink/70">
							Pick a student group, choose a task, and record student outcomes.
						</p>
					</div>
				</div>

				<!-- TOP FILTER BAR -->
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
						<Button
							v-if="hasActiveFilters"
							appearance="minimal"
							size="md"
							icon="x"
							@click="resetFilters"
						>
							Reset
						</Button>
					</div>
				</div>
			</header>

			<div class="grid gap-6 xl:gap-8 lg:grid-cols-[minmax(21rem,1fr)_minmax(0,2fr)]">
				<div class="flex flex-col gap-6 xl:gap-8">
					<!-- Student groups Panel -->
					<section
						class="flex flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
					>
						<div class="border-b border-border/50 bg-gray-50/50 px-4 py-3">
							<div class="flex items-center justify-between gap-2">
								<h2 class="text-sm font-semibold uppercase tracking-wide text-ink/70">
									Student Groups
								</h2>
								<Button
									size="sm"
									appearance="minimal"
									icon="refresh-cw"
									:loading="groupsLoading"
									@click="reloadGroups()"
								/>
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

					<!-- Tasks Panel -->
					<section
						class="flex flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
					>
						<div class="border-b border-border/50 bg-gray-50/50 px-4 py-3">
							<div class="flex items-center justify-between gap-2">
								<div>
									<h2 class="text-sm font-semibold uppercase tracking-wide text-ink/70">Tasks</h2>
									<p class="text-xs text-ink/50" v-if="selectedGroup">
										{{ selectedGroup.label }}
									</p>
								</div>
							</div>
						</div>

						<!-- Task Filters within Panel -->
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
														<Badge v-if="task.points" variant="subtle">Pts</Badge>
														<Badge v-if="task.binary" variant="subtle">Binary</Badge>
														<Badge v-if="task.criteria" variant="subtle">Crit</Badge>
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

				<!-- Grade entry -->
				<section
					class="flex h-fit flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
				>
					<div class="border-b border-border/50 bg-gray-50/50 px-6 py-4">
						<div class="flex flex-wrap items-center justify-between gap-4">
							<div class="flex items-center gap-3">
								<h2 class="text-lg font-semibold text-ink">Grade Entry</h2>
								<div
									v-if="selectedTask"
									class="flex items-center gap-2 rounded-full bg-white px-2 py-0.5 text-xs text-ink/60 shadow-sm border border-border/50"
								>
									<span class="font-medium">Max Points:</span>
									<span class="font-bold text-ink">{{ gradebook.task?.max_points || '—' }}</span>
								</div>
							</div>

							<div v-if="gradebook.students.length" class="flex flex-wrap items-center gap-2">
								<span class="text-xs font-medium uppercase tracking-wider text-ink/50"
									>Visible to all:</span
								>
								<Button
									size="sm"
									appearance="minimal"
									:class="
										allStudentsVisible
											? 'bg-sky/30 text-ink font-semibold'
											: 'text-ink/60 hover:text-ink'
									"
									@click="toggleVisibilityGroup('student')"
								>
									Students
								</Button>
								<Button
									size="sm"
									appearance="minimal"
									:class="
										allGuardiansVisible
											? 'bg-sky/30 text-ink font-semibold'
											: 'text-ink/60 hover:text-ink'
									"
									@click="toggleVisibilityGroup('guardian')"
								>
									Guardians
								</Button>
							</div>
						</div>
					</div>

					<div class="min-h-[400px] flex-1 bg-white p-6">
						<div
							v-if="gradebookLoading"
							class="flex h-full flex-col items-center justify-center gap-3 pt-20"
						>
							<Spinner class="h-8 w-8 text-canopy" />
							<p class="text-sm text-ink/50">Loading gradebook...</p>
						</div>

						<div
							v-else-if="!selectedTask"
							class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
						>
							<div class="rounded-full bg-gray-100 p-4">
								<FeatherIcon name="check-square" class="h-8 w-8 text-ink/30" />
							</div>
							<p class="text-lg font-medium text-ink">No Task Selected</p>
							<p class="max-w-xs text-sm">
								Choose a task from the left panel to begin entering grades.
							</p>
						</div>

						<div
							v-else-if="!gradebook.students.length"
							class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
						>
							<p class="text-lg font-medium text-ink">No Students Assigned</p>
							<p class="max-w-xs text-sm">This task has no students in the roster.</p>
							<Button size="md" appearance="primary" :loading="rosterSyncing" @click="syncRoster">
								Sync roster
							</Button>
						</div>

						<div v-else class="space-y-6">
							<article
								v-for="student in gradebook.students"
								:key="student.task_student"
								class="group relative rounded-xl border border-border bg-gray-50/30 p-5 transition-all hover:bg-white hover:shadow-md"
							>
								<!-- Current Student Header -->
								<div
									class="flex flex-wrap items-start justify-between gap-4 border-b border-border/40 pb-4 mb-4"
								>
									<div class="flex items-center gap-4">
										<img
											:src="student.student_image || DEFAULT_STUDENT_IMAGE"
											alt=""
											class="h-12 w-12 rounded-full border border-white bg-white object-cover shadow-sm"
											loading="lazy"
											@error="onImgError"
										/>
										<div>
											<p class="text-base font-bold text-ink hover:text-leaf transition-colors">
												{{ student.student_name }}
											</p>
											<div class="flex items-center gap-2 text-xs text-ink/50">
												<span v-if="student.student_id" class="font-mono">{{
													student.student_id
												}}</span>
												<span>•</span>
												<span
													:class="{
														'text-leaf font-medium':
															studentStates[student.task_student]?.status === 'Finalized' ||
															studentStates[student.task_student]?.status === 'Released',
													}"
												>
													{{ studentStates[student.task_student]?.status || '—' }}
												</span>
											</div>
										</div>
									</div>

									<div class="flex flex-wrap items-center gap-2">
										<Badge
											v-if="studentStates[student.task_student]?.complete"
											variant="subtle"
											theme="green"
											class="!bg-leaf/10 !text-leaf"
										>
											<FeatherIcon name="check" class="mr-1 h-3 w-3" />
											Complete
										</Badge>
										<Badge v-else-if="gradebook.task?.binary" variant="outline" theme="gray">
											Incomplete
										</Badge>

										<div
											class="flex items-center rounded-lg bg-white px-3 py-1.5 shadow-sm border border-border/40"
										>
											<span class="mr-2 text-xs font-medium uppercase tracking-wider text-ink/40"
												>Score</span
											>
											<span class="text-lg font-bold text-ink">
												{{ formatPoints(studentStates[student.task_student]?.mark_awarded) }}
											</span>
										</div>
									</div>
								</div>

								<!-- Grading Controls -->
								<div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
									<div class="space-y-4">
										<FormControl
											type="select"
											label="Status"
											:options="statusOptions"
											option-label="label"
											option-value="value"
											placeholder="Select status"
											:model-value="studentStates[student.task_student]?.status || ''"
											@update:modelValue="onStatusChanged(student.task_student, $event)"
										/>

										<div v-if="gradebook.task?.points" class="space-y-1.5">
											<label
												class="block text-xs font-semibold uppercase tracking-wide text-ink/50"
												>Points Awarded</label
											>
											<FormControl
												type="number"
												placeholder="Points"
												:step="0.5"
												:min="0"
												:max="gradebook.task?.max_points || undefined"
												:model-value="studentStates[student.task_student]?.mark_awarded"
												@update:modelValue="onPointsChanged(student.task_student, $event)"
											/>
										</div>

										<div v-if="gradebook.task?.binary" class="space-y-1.5">
											<label
												class="block text-xs font-semibold uppercase tracking-wide text-ink/50"
												>Completion</label
											>
											<button
												type="button"
												class="flex w-full items-center justify-center gap-2 rounded-md border border-border/60 bg-white px-4 py-2 text-sm font-medium transition-all hover:border-leaf hover:text-leaf active:scale-95"
												:class="{
													'!bg-leaf !text-white !border-leaf':
														studentStates[student.task_student]?.complete,
												}"
												@click="toggleComplete(student.task_student)"
											>
												<FeatherIcon
													:name="
														studentStates[student.task_student]?.complete ? 'check' : 'circle'
													"
													class="h-4 w-4"
												/>
												{{
													studentStates[student.task_student]?.complete
														? 'Marked Complete'
														: 'Mark Complete'
												}}
											</button>
										</div>

										<div class="pt-2">
											<label
												class="block mb-2 text-xs font-semibold uppercase tracking-wide text-ink/50"
												>Visibility</label
											>
											<div class="flex flex-col gap-2">
												<FormControl
													type="checkbox"
													label="Visible to Student"
													:model-value="
														Boolean(studentStates[student.task_student]?.visible_to_student)
													"
													@update:modelValue="
														value =>
															setVisibility(student.task_student, 'visible_to_student', value)
													"
												/>
												<FormControl
													type="checkbox"
													label="Visible to Guardian"
													:model-value="
														Boolean(studentStates[student.task_student]?.visible_to_guardian)
													"
													@update:modelValue="
														value =>
															setVisibility(student.task_student, 'visible_to_guardian', value)
													"
												/>
											</div>
										</div>
									</div>

									<!-- Feedback Column -->
									<div class="space-y-1.5 md:col-span-1 lg:col-span-2">
										<label class="block text-xs font-semibold uppercase tracking-wide text-ink/50"
											>Feedback</label
										>
										<FormControl
											type="textarea"
											rows="5"
											placeholder="Positive reinforcement, areas for improvement..."
											class="!h-full"
											:model-value="studentStates[student.task_student]?.feedback || ''"
											@update:modelValue="onFeedbackChanged(student.task_student, $event)"
										/>
									</div>
								</div>

								<!-- Criteria Section -->
								<div
									v-if="gradebook.task?.criteria && gradebook.criteria.length"
									class="mt-6 rounded-lg border border-border/60 bg-white p-4 shadow-sm"
								>
									<div class="mb-4 flex items-center justify-between">
										<h4 class="text-sm font-bold text-ink">Criteria Breakdown</h4>
										<Badge
											v-if="studentStates[student.task_student]?.dirtyCriteria"
											variant="subtle"
											theme="orange"
										>
											Unsaved Changes
										</Badge>
									</div>
									<div class="grid gap-4 md:grid-cols-2">
										<div
											v-for="criterion in gradebook.criteria"
											:key="criterion.assessment_criteria"
											class="space-y-2 rounded-md bg-gray-50/50 p-3 ring-1 ring-border/40"
										>
											<div class="flex justify-between">
												<span class="text-sm font-medium text-ink">{{
													criterion.criteria_name
												}}</span>
												<span v-if="criterion.criteria_weighting" class="text-xs text-ink/50"
													>{{ criterion.criteria_weighting }}%</span
												>
											</div>
											<FormControl
												v-if="criterion.levels && criterion.levels.length"
												type="select"
												size="sm"
												:options="criterionLevelOptions(criterion)"
												placeholder="Level Achieved"
												:model-value="
													getCriterionState(student.task_student, criterion.assessment_criteria)
														?.level ?? null
												"
												@update:modelValue="
													level => onCriterionLevelChanged(student.task_student, criterion, level)
												"
											/>
											<FormControl
												v-else
												type="text"
												size="sm"
												placeholder="Level"
												:model-value="
													getCriterionState(student.task_student, criterion.assessment_criteria)
														?.level ?? ''
												"
												@update:modelValue="
													level => onCriterionLevelChanged(student.task_student, criterion, level)
												"
											/>
											<FormControl
												type="number"
												size="sm"
												:step="0.1"
												:min="0"
												placeholder="Points"
												:model-value="
													getCriterionState(student.task_student, criterion.assessment_criteria)
														?.level_points ?? 0
												"
												@update:modelValue="
													value =>
														onCriterionPointsChanged(
															student.task_student,
															criterion.assessment_criteria,
															value
														)
												"
											/>
											<FormControl
												type="textarea"
												rows="2"
												size="sm"
												placeholder="Criterion feedback"
												:model-value="
													getCriterionState(student.task_student, criterion.assessment_criteria)
														?.feedback || ''
												"
												@update:modelValue="
													value =>
														onCriterionFeedbackChanged(
															student.task_student,
															criterion.assessment_criteria,
															value
														)
												"
											/>
											<div class="flex items-center justify-between text-xs">
												<span class="text-ink/60">Score:</span>
												<span class="font-bold text-ink">
													{{
														formatPoints(
															getCriterionState(
																student.task_student,
																criterion.assessment_criteria
															)?.level_points
														)
													}}
												</span>
											</div>
										</div>
									</div>
								</div>

								<!-- Action Footer for Student Card -->
								<div class="mt-4 flex items-center justify-between border-t border-border/40 pt-4">
									<p class="text-xs text-ink/40">
										Last updated
										{{
											formatDateTime(studentStates[student.task_student]?.updated_on) || 'Never'
										}}
									</p>
									<div class="flex gap-2">
										<Button
											v-if="gradebook.task?.criteria && gradebook.criteria.length"
											size="sm"
											appearance="white"
											:loading="studentStates[student.task_student]?.savingCriteria"
											:disabled="!studentStates[student.task_student]?.dirtyCriteria"
											@click="saveCriteria(student.task_student)"
										>
											Save Criteria
										</Button>
										<Button
											size="sm"
											appearance="primary"
											:loading="studentStates[student.task_student]?.saving"
											:disabled="!studentStates[student.task_student]?.dirty"
											@click="saveStudent(student.task_student)"
										>
											Save Grade
										</Button>
									</div>
								</div>
							</article>
						</div>
					</div>
				</section>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Button, FormControl, Badge, FeatherIcon, Spinner, toast } from 'frappe-ui';
import { createGradebookService } from '@/lib/services/gradebook/gradebookService';
import { createStudentAttendanceService } from '@/lib/services/studentAttendance/studentAttendanceService';
import type { FetchSchoolFilterContextResponse } from '@/types/contracts/studentAttendance';
import type { GroupSummary as GradebookGroupSummary } from '@/types/contracts/gradebook/fetch_groups';
import type { TaskSummary as GradebookTaskSummary } from '@/types/contracts/gradebook/fetch_group_tasks';
import type {
	TaskPayload as GradebookTaskPayload,
	CriterionPayload as GradebookCriterionPayload,
	StudentRow as GradebookStudentRow,
} from '@/types/contracts/gradebook/get_task_gradebook';
import type { Response as UpdateTaskStudentResponse } from '@/types/contracts/gradebook/update_task_student';

/* TYPE DEFINITIONS ------------------------------------------------ */

type GroupSummary = GradebookGroupSummary;
type TaskSummary = GradebookTaskSummary;
type TaskPayload = GradebookTaskPayload;
type CriterionPayload = GradebookCriterionPayload;

interface StudentCriterionState {
	assessment_criteria: string;
	level: string | number | null;
	level_points: number;
	feedback: string;
}

type StudentRow = GradebookStudentRow;

interface StudentState {
	status: string;
	mark_awarded: number | null;
	feedback: string;
	visible_to_student: boolean;
	visible_to_guardian: boolean;
	complete: boolean;
	criteria: StudentCriterionState[];
	updated_on?: string | null;
	dirty: boolean;
	dirtyCriteria: boolean;
	saving: boolean;
	savingCriteria: boolean;
}

/* STATE --------------------------------------------------------- */
const route = useRoute();
const router = useRouter();
const gradebookService = createGradebookService();
const studentAttendanceService = createStudentAttendanceService();

// Filtering state
const filters = reactive({
	school: null as string | null,
	academic_year: null as string | null,
	program: null as string | null,
	course: null as string | null,
	// Task filters
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
const gradebookLoading = ref(false);
const rosterSyncing = ref(false);

const gradebook = reactive<{
	task: TaskPayload | null;
	criteria: CriterionPayload[];
	students: StudentRow[];
}>({
	task: null,
	criteria: [],
	students: [],
});

const studentStates = reactive<Record<string, StudentState>>({});
const statusOptions = [
	{ label: 'Not Started', value: 'Not Started' },
	{ label: 'In Progress', value: 'In Progress' },
	{ label: 'Needs Review', value: 'Needs Review' },
	{ label: 'Moderated', value: 'Moderated' },
	{ label: 'Finalized', value: 'Finalized' },
	{ label: 'Released', value: 'Released' },
	{ label: 'Not Applicable', value: 'Not Applicable' },
];

const AUTOSAVE_DELAY = 2500;
const studentSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {};
const criteriaSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {};

/* SERVICES ----------------------------------------------------- */

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

function showSuccessToast(title: string) {
	showToast(title, 'success');
}

function onSchoolsLoaded(data: FetchSchoolFilterContextResponse) {
	const rows = Array.isArray(data.schools) ? data.schools : [];
	schools.value = rows;
	const def = data.default_school || null;
	if (def) {
		defaultSchool.value = def;
		// Only set filter if not already set (e.g. via persistence? not implementing persistence for now)
		if (!filters.school) {
			filters.school = def;
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

// 2. Groups Loader
async function loadGroups(options: { skipRouteGroupSync?: boolean } = {}) {
	groupsLoading.value = true;
	try {
		const rows = await gradebookService.fetchGroups({
			school: filters.school,
		});

		// If currently selected group is not in list, add it (edge case)
		if (
			selectedGroup.value &&
			selectedGroup.value.name &&
			!rows.find(row => row.name === selectedGroup.value?.name)
		) {
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

// 3. Tasks Loader
async function loadTasks(groupName: string) {
	tasksLoading.value = true;
	try {
		const payload = await gradebookService.fetchGroupTasks({
			student_group: groupName,
		});
		taskSummaries.value = payload?.tasks ?? [];
	} catch (error) {
		console.error('Failed to load tasks', error);
		showDangerToast('Could not load tasks');
	} finally {
		tasksLoading.value = false;
	}
}

// 4. Gradebook Loader
async function loadGradebook(taskName: string) {
	gradebookLoading.value = true;
	try {
		const payload = await gradebookService.getTaskGradebook({
			task: taskName,
		});
		if (payload) {
			gradebook.task = payload.task;
			gradebook.criteria = payload.criteria || [];
			gradebook.students = payload.students || [];
			initializeStudentStates();
		}
	} catch (error) {
		console.error('Failed to load gradebook', error);
		showDangerToast('Could not load gradebook');
	} finally {
		gradebookLoading.value = false;
	}
}

async function syncRoster() {
	if (!selectedTask.value?.name) {
		showToast('Select a task first.', 'warning');
		return;
	}

	rosterSyncing.value = true;
	try {
		const payload = await gradebookService.repairTaskRoster({
			task: selectedTask.value.name,
		});
		showSuccessToast(payload.message || 'Roster synced.');
		await loadGradebook(selectedTask.value.name);
	} catch (error) {
		console.error('Failed to sync task roster', error);
		showDangerToast('Could not sync the task roster');
	} finally {
		rosterSyncing.value = false;
	}
}

/* COMPUTED - FILTER OPTIONS & DERIVED DATA ---------------------- */

const schoolOptions = computed(() => {
	const base = schools.value.map(s => ({
		label: s.school_name || s.name,
		value: s.name,
	}));
	if (defaultSchool.value) return base;
	// If no default school (admin global), add All option
	return [{ label: 'All Schools', value: null }, ...base];
});

function criterionLevelOptions(criterion: CriterionPayload) {
	return (criterion.levels || []).map(level => ({
		label: level.level,
		value: level.level,
	}));
}

// Derived Groups: Filter raw groups list by top bar selections
const derivedGroups = computed(() => {
	let list = groups.value;
	const f = filters;

	// 1. School Filter
	// Note: instructor with restricted scope might only see 1 school in list.
	// But if they have access to multiple (e.g. descendants), we filter here.
	if (f.school) {
		list = list.filter(g => g.school === f.school);
	}
	// 2. Year Filter
	if (f.academic_year) {
		list = list.filter(g => g.academic_year === f.academic_year);
	}
	// 3. Program Filter
	if (f.program) {
		list = list.filter(g => g.program === f.program);
	}
	// 4. Course Filter
	if (f.course) {
		list = list.filter(g => g.course === f.course);
	}
	return list;
});

const groupPickerOptions = computed(() =>
	derivedGroups.value.map(group => ({
		label: group.label,
		value: group.name,
	}))
);

// Options derived from CURRENT visible groups (after school filter applied)
// This ensures cascading logic: selecting a school reduces available years/programs.
const availableGroupsForOptions = computed(() => {
	let list = groups.value;
	if (filters.school) {
		list = list.filter(g => g.school === filters.school);
	}
	return list;
});

const yearOptions = computed(() => {
	// Unique academic years from available groups
	const years = new Set(availableGroupsForOptions.value.map(g => g.academic_year).filter(Boolean));
	return Array.from(years)
		.sort()
		.reverse()
		.map(y => ({ label: y, value: y }));
});

const programOptions = computed(() => {
	// Filter by year if selected
	let list = availableGroupsForOptions.value;
	if (filters.academic_year) {
		list = list.filter(g => g.academic_year === filters.academic_year);
	}
	const progs = new Set(list.map(g => g.program).filter(Boolean));
	return Array.from(progs)
		.sort()
		.map(p => ({ label: p, value: p }));
});

const courseOptions = computed(() => {
	let list = availableGroupsForOptions.value;
	if (filters.academic_year) {
		list = list.filter(g => g.academic_year === filters.academic_year);
	}
	if (filters.program) {
		list = list.filter(g => g.program === filters.program);
	}
	const courses = new Set(list.map(g => g.course).filter(Boolean));
	return Array.from(courses)
		.sort()
		.map(c => ({ label: c, value: c }));
});

const hasActiveFilters = computed(() => {
	return !!(filters.school || filters.academic_year || filters.program || filters.course);
});

/* TASK FILTERING ------------------------------------------------ */

const derivedTasks = computed(() => {
	let list = taskSummaries.value;
	if (filters.task_type) {
		list = list.filter(t => t.task_type === filters.task_type);
	}
	if (filters.delivery_type) {
		list = list.filter(t => t.delivery_type === filters.delivery_type);
	}
	return list;
});

const taskTypeOptions = computed(() => {
	const types = new Set(taskSummaries.value.map(t => t.task_type).filter(Boolean));
	return [
		{ label: 'All Types', value: null },
		...Array.from(types)
			.sort()
			.map(t => ({ label: t, value: t })),
	];
});

const deliveryTypeOptions = computed(() => {
	const types = new Set(taskSummaries.value.map(t => t.delivery_type).filter(Boolean));
	return [
		{ label: 'All Modes', value: null },
		...Array.from(types)
			.sort()
			.map(t => ({ label: t, value: t })),
	];
});

/* FILTER ACTIONS ------------------------------------------------ */

function onSchoolSelected(val: string | null) {
	filters.school = val;
	// Cascade reset
	filters.academic_year = null;
	filters.program = null;
	filters.course = null;
	void loadGroups();
}

function onYearSelected(val: string | null) {
	filters.academic_year = val;
	filters.program = null;
	filters.course = null;
}

function onProgramSelected(val: string | null) {
	filters.program = val;
	filters.course = null;
}

function onCourseSelected(val: string | null) {
	filters.course = val;
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

// Downstream Clearing Logic
// Watch derivedGroups: if selectedGroup is no longer in it, deselect.
watch(derivedGroups, newList => {
	if (selectedGroup.value) {
		const stillVisible = newList.find(g => g.name === selectedGroup.value?.name);
		if (!stillVisible) {
			selectGroup(null); // Clear selection
		}
	}
});

// Watch derivedTasks
watch(derivedTasks, newList => {
	if (selectedTask.value) {
		const stillVisible = newList.find(t => t.name === selectedTask.value?.name);
		if (!stillVisible) {
			selectTask(null); // Clear task selection
		}
	}
});

/* OTHER LOGIC (UNCHANGED MOSTLY) -------------------------------- */

function selectGroup(group: GroupSummary | null) {
	selectedGroup.value = group;
	if (group) {
		// Reset task filters when switching group? Only if desired.
		// Let's keep them as sticky filters might be useful.
		updateRouteStudentGroup(group.name);
	} else {
		updateRouteStudentGroup(null);
	}
}

function selectTask(task: TaskSummary | null) {
	selectedTask.value = task;
}

/* FORMATTERS & UTILS -------------------------------------------- */

function formatDate(dateStr?: string | null) {
	if (!dateStr) return '';
	return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDateTime(val?: string | null) {
	if (!val) return '';
	return new Date(val).toLocaleString(undefined, {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	});
}

function formatPoints(val: number | null | undefined) {
	return typeof val === 'number' ? val : '—';
}

const hasCriterionFeedback = computed(() => gradebook.criteria.length > 0);
const allStudentsVisible = computed(() => {
	if (!gradebook.students.length) return false;
	return gradebook.students.every(student => {
		const state = studentStates[student.task_student];
		return Boolean(state?.visible_to_student);
	});
});
const allGuardiansVisible = computed(() => {
	if (!gradebook.students.length) return false;
	return gradebook.students.every(student => {
		const state = studentStates[student.task_student];
		return Boolean(state?.visible_to_guardian);
	});
});

const DEFAULT_STUDENT_IMAGE = '/assets/ifitwala_ed/images/default_student_image.png';

function currentRouteStudentGroup(): string | null {
	const value = route.query.student_group;
	return typeof value === 'string' && value ? value : null;
}

const pendingRouteGroup = ref<string | null>(currentRouteStudentGroup());

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

function updateRouteStudentGroup(groupName: string | null) {
	const current = currentRouteStudentGroup();
	if (current === groupName || (!current && !groupName)) {
		return;
	}
	const nextQuery = { ...route.query };
	if (groupName) {
		nextQuery.student_group = groupName;
	} else {
		delete nextQuery.student_group;
	}
	router.replace({ query: nextQuery }).catch(() => {});
}

function onImgError(event: Event, fallback?: string) {
	const element = event.target as HTMLImageElement;
	element.onerror = null;
	element.src = fallback || DEFAULT_STUDENT_IMAGE;
}

function normalizeFeedback(value?: string | null) {
	if (!value) return '';
	try {
		if (typeof DOMParser !== 'undefined') {
			const parser = new DOMParser();
			const doc = parser.parseFromString(value, 'text/html');
			const text = doc.body.innerText || doc.body.textContent || '';
			return text.replace(/\u00a0/g, ' ').trim();
		}
	} catch {
		/* fall through to regex cleanup */
	}
	return value
		.replace(/<br\s*\/?>/gi, '\n')
		.replace(/<\/p>/gi, '\n')
		.replace(/<[^>]*>/g, '')
		.replace(/\u00a0/g, ' ')
		.replace(/\n{3,}/g, '\n\n')
		.trim();
}

function clearAllAutosaveTimers() {
	for (const key of Object.keys(studentSaveTimers)) {
		const handle = studentSaveTimers[key];
		if (handle) {
			clearTimeout(handle);
		}
		delete studentSaveTimers[key];
	}
	for (const key of Object.keys(criteriaSaveTimers)) {
		const handle = criteriaSaveTimers[key];
		if (handle) {
			clearTimeout(handle);
		}
		delete criteriaSaveTimers[key];
	}
}

function scheduleStudentSave(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;

	const existing = studentSaveTimers[taskStudent];
	if (existing) {
		clearTimeout(existing);
	}

	studentSaveTimers[taskStudent] = setTimeout(() => {
		studentSaveTimers[taskStudent] = null;
		if (!state.dirty) {
			return;
		}
		if (state.saving) {
			scheduleStudentSave(taskStudent);
			return;
		}
		void saveStudent(taskStudent);
	}, AUTOSAVE_DELAY);
}

function scheduleCriteriaSave(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;

	const existing = criteriaSaveTimers[taskStudent];
	if (existing) {
		clearTimeout(existing);
	}

	criteriaSaveTimers[taskStudent] = setTimeout(() => {
		criteriaSaveTimers[taskStudent] = null;
		if (!state.dirtyCriteria) {
			return;
		}
		if (state.savingCriteria) {
			scheduleCriteriaSave(taskStudent);
			return;
		}
		void saveCriteria(taskStudent);
	}, AUTOSAVE_DELAY);
}

watch(
	() => route.query.student_group,
	() => {
		pendingRouteGroup.value = currentRouteStudentGroup();
		if (pendingRouteGroup.value) {
			void applyRouteGroupFromQuery();
		}
	}
);

watch(
	() => selectedGroup.value?.name,
	groupName => {
		taskSummaries.value = [];
		selectedTask.value = null;
		gradebook.task = null;
		gradebook.criteria = [];
		gradebook.students = [];
		if (groupName) {
			void loadTasks(groupName);
		} else {
			updateRouteStudentGroup(null);
		}
	}
);

watch(
	() => selectedTask.value?.name,
	taskName => {
		gradebook.task = null;
		gradebook.criteria = [];
		gradebook.students = [];
		if (taskName) {
			void loadGradebook(taskName);
		}
	}
);

onMounted(() => {
	void (async () => {
		await loadSchoolContext();
		await loadGroups();
	})();
});

onBeforeUnmount(() => {
	clearAllAutosaveTimers();
});

function initializeStudentStates() {
	clearAllAutosaveTimers();
	for (const key of Object.keys(studentStates)) {
		delete studentStates[key];
	}

	for (const student of gradebook.students) {
		studentStates[student.task_student] = {
			status: student.status || 'Not Started',
			mark_awarded: student.mark_awarded,
			feedback: normalizeFeedback(student.feedback),
			visible_to_student: Boolean(student.visible_to_student),
			visible_to_guardian: Boolean(student.visible_to_guardian),
			complete: Boolean(student.complete),
			updated_on: student.updated_on,
			dirty: false,
			dirtyCriteria: false,
			saving: false,
			savingCriteria: false,
			criteria: student.criteria_scores.map(c => ({
				assessment_criteria: c.assessment_criteria,
				level: c.level,
				level_points: c.level_points ?? 0,
				feedback: normalizeFeedback(c.feedback),
			})),
		};
	}
}

function onStatusChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent];
	if (!state || state.status === value) return;
	state.status = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function onPointsChanged(taskStudent: string, value: number | null) {
	const state = studentStates[taskStudent];
	if (!state || state.mark_awarded === value) return;
	state.mark_awarded = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function toggleComplete(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;
	state.complete = !state.complete;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function setVisibility(
	taskStudent: string,
	field: 'visible_to_student' | 'visible_to_guardian',
	value: boolean
) {
	const state = studentStates[taskStudent];
	if (!state || state[field] === value) return;
	state[field] = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function onFeedbackChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent];
	if (!state || state.feedback === value) return;
	state.feedback = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function getCriterionState(taskStudent: string, criteriaName: string) {
	const state = studentStates[taskStudent];
	return state?.criteria.find(c => c.assessment_criteria === criteriaName);
}

function onCriterionLevelChanged(
	taskStudent: string,
	criterionRow: CriterionPayload,
	levelValue: string | number | null
) {
	const state = studentStates[taskStudent];
	if (!state) return;
	const item = state.criteria.find(
		c => c.assessment_criteria === criterionRow.assessment_criteria
	);
	if (!item) return;

	if (item.level === levelValue) return;

	const levelDef = criterionRow.levels.find(l => l.level === levelValue);
	item.level = levelValue;
	item.level_points = levelDef ? levelDef.points : item.level_points;
	state.dirtyCriteria = true;
	scheduleCriteriaSave(taskStudent);
}

function onCriterionPointsChanged(
	taskStudent: string,
	criteriaName: string,
	value: number | null
) {
	const state = studentStates[taskStudent];
	if (!state) return;
	const item = state.criteria.find(c => c.assessment_criteria === criteriaName);
	if (!item) return;
	const nextValue = typeof value === 'number' ? value : 0;
	if (item.level_points === nextValue) return;
	item.level_points = nextValue;
	state.dirtyCriteria = true;
	scheduleCriteriaSave(taskStudent);
}

function onCriterionFeedbackChanged(taskStudent: string, criteriaName: string, value: string) {
	const state = studentStates[taskStudent];
	if (!state) return;
	const item = state.criteria.find(c => c.assessment_criteria === criteriaName);
	if (!item || item.feedback === value) return;
	item.feedback = value;
	state.dirtyCriteria = true;
	scheduleCriteriaSave(taskStudent);
}

async function saveStudent(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;

	state.saving = true;
	try {
		const payload = {
			status: state.status,
			mark_awarded: state.mark_awarded,
			feedback: state.feedback,
			visible_to_student: state.visible_to_student,
			visible_to_guardian: state.visible_to_guardian,
			complete: state.complete,
		};
		const doc: UpdateTaskStudentResponse = await gradebookService.updateTaskStudent({
			task_student: taskStudent,
			updates: payload,
		});
		state.dirty = false;
		state.updated_on = doc.updated_on;
	} catch (error) {
		console.error('Save failed', error);
		showDangerToast('Failed to save grade');
	} finally {
		state.saving = false;
		if (state.dirty) {
			scheduleStudentSave(taskStudent);
		}
	}
}

async function saveCriteria(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;
	state.savingCriteria = true;
	try {
		const criteriaScores = state.criteria
			.map(c => ({
				assessment_criteria: c.assessment_criteria,
				level: c.level,
				level_points: c.level_points ?? 0,
				feedback: c.feedback,
			}))
			.filter(row => row.assessment_criteria && row.level !== null && row.level !== '');

		if (criteriaScores.length) {
			const doc: UpdateTaskStudentResponse = await gradebookService.updateTaskStudent({
				task_student: taskStudent,
				updates: {
					criteria_scores: criteriaScores,
				},
			});
			if (doc?.updated_on) {
				state.updated_on = doc.updated_on;
			}
		}
		state.dirtyCriteria = false;
	} catch (err) {
		console.error(err);
		showDangerToast('Error saving criteria');
	} finally {
		state.savingCriteria = false;
	}
}

function toggleVisibilityGroup(type: 'student' | 'guardian') {
	const field = type === 'student' ? 'visible_to_student' : 'visible_to_guardian';
	const targetVal = type === 'student' ? !allStudentsVisible.value : !allGuardiansVisible.value;

	gradebook.students.forEach(student => {
		setVisibility(student.task_student, field, targetVal);
	});
}
</script>
