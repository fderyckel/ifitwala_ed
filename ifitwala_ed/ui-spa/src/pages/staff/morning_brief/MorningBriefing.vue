<!-- ifitwala_ed/ui-spa/src/pages/staff/MorningBriefing.vue -->
<template>
	<div class="min-h-screen bg-transparent p-4 sm:p-6 space-y-8">
		<!-- HEADER -->
		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="type-h1">
					Morning Briefing
				</h1>
				<p class="type-meta mt-1 text-slate-token/80">
					Daily Operational &amp; Academic Pulse
				</p>
			</div>

			<div class="flex items-center gap-3">
				<div class="text-right">
					<span class="section-header block mb-0.5">Today</span>
					<span class="type-h3 text-ink">
						{{ formattedDate }}
					</span>
				</div>
				<button
					@click="widgets.reload()"
					class="remark-btn ml-2 flex items-center justify-center"
				>
					<FeatherIcon
						name="refresh-cw"
						class="h-4 w-4"
						:class="{ 'animate-spin': widgets.loading }"
					/>
				</button>
			</div>
		</header>

		<!-- SKELETON STATE -->
		<div v-if="widgets.loading" class="space-y-6 animate-pulse">
			<div class="h-32 w-full rounded-2xl bg-slate-100"></div>
			<div class="grid grid-cols-2 gap-6">
				<div class="h-64 rounded-2xl bg-slate-100"></div>
				<div class="h-64 rounded-2xl bg-slate-100"></div>
			</div>
		</div>

		<!-- CONTENT -->
		<div v-else class="space-y-8">
			<!-- ANNOUNCEMENTS -->
			<section v-if="hasData('announcements')" class="space-y-4">
				<div
					v-for="(news, idx) in widgets.data.announcements"
					:key="idx"
					class="relative mb-4 overflow-hidden rounded-2xl p-6 shadow-sm transition-all last:mb-0"
					:class="getPriorityClasses(news.priority)"
				>
					<div
						v-if="news.priority !== 'Critical'"
						class="absolute inset-0 z-0 bg-purple-50 opacity-100"
					></div>

					<div
						class="relative z-0"
						:class="news.priority === 'Critical' ? 'text-white' : 'text-ink'"
					>
						<div class="mb-2 flex gap-2">
							<span
								class="inline-flex items-center gap-1 rounded-md border px-2 py-1 type-badge-label"
								:class="news.priority === 'Critical'
									? 'bg-white/20 border-white/30 text-white'
									: 'bg-white border-purple-100 text-purple-700'"
							>
								{{ news.type }}
							</span>

							<span
								v-if="news.priority === 'Critical'"
								class="inline-flex items-center gap-1 rounded-md bg-red-100 px-2 py-1 type-badge-label text-red-700"
							>
								CRITICAL
							</span>
						</div>

						<h3 class="mb-2 type-h3">
							{{ news.title }}
						</h3>

						<div
							class="prose prose-sm max-w-none opacity-90 line-clamp-3"
							:class="news.priority === 'Critical' ? 'prose-invert' : 'text-slate-600'"
							v-html="news.content"
						></div>

						<button
							@click="openAnnouncement(news)"
							class="mt-3 flex items-center gap-1 type-button-label hover:underline focus:outline-none"
							:class="news.priority === 'Critical' ? 'text-white' : 'text-purple-700'"
						>
							Read full announcement
							<FeatherIcon name="arrow-right" class="h-4 w-4" />
						</button>
					</div>
				</div>
			</section>

			<div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
				<!-- LEFT COLUMN -->
				<div class="space-y-6">
					<div
						v-if="hasData('clinic_volume') || widgets.data?.critical_incidents !== undefined"
						class="grid grid-cols-2 gap-6"
					>
						<!-- Attendance Trend (Admin) -->
						<div v-if="hasData('attendance_trend')" class="col-span-2">
							<AttendanceTrend :data="widgets.data.attendance_trend" />
						</div>

						<!-- Critical Incidents card -->
						<div
							v-if="widgets.data?.critical_incidents !== undefined"
							class="paper-card cursor-pointer border-l-4 border-l-flame p-5 transition-shadow hover:shadow-md"
							@click="openCriticalIncidents"
						>
							<h3 class="section-header mb-1 text-flame/80">
								Critical Incidents
							</h3>
							<div class="text-3xl font-bold text-ink">
								{{ widgets.data.critical_incidents }}
							</div>
							<p
								class="mt-1 flex items-center gap-1 text-xs font-medium text-flame"
							>
								<FeatherIcon name="alert-circle" class="h-3 w-3" />
								Open Follow-ups
							</p>
						</div>

						<!-- Clinic Volume -->
						<div
							v-if="hasData('clinic_volume')"
							class="paper-card cursor-pointer p-5 transition-shadow hover:shadow-md"
							@click="showClinicHistory = true"
						>
							<div class="mb-3 flex items-center gap-2">
								<div
									class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-blue-600"
                                >
									<FeatherIcon name="thermometer" class="h-4 w-4" />
								</div>
								<h3 class="text-sm font-semibold text-canopy">
									Clinic Volume
								</h3>
							</div>
							<div class="space-y-2">
								<div
									v-for="day in widgets.data.clinic_volume"
									:key="day.date"
									class="flex items-center justify-between text-sm"
								>
									<span class="text-slate-500">
										{{ day.date }}
									</span>
									<span
										class="font-mono font-medium"
										:class="day.count > 10 ? 'text-flame' : 'text-ink'"
									>
										{{ day.count }}
									</span>
								</div>
							</div>
						</div>
					</div>

					<!-- Admissions pulse -->
					<div v-if="widgets.data?.admissions_pulse" class="paper-card p-5">
						<div class="mb-3 flex items-center justify-between">
							<div class="flex items-center gap-2">
								<div
									class="flex h-8 w-8 items-center justify-center rounded-full bg-purple-50 text-purple-600"
								>
									<FeatherIcon name="users" class="h-4 w-4" />
								</div>
								<h3 class="text-sm font-semibold text-canopy">
									Admissions (Last 7 Days)
								</h3>
							</div>
							<span class="text-2xl font-bold text-ink">
								{{ widgets.data.admissions_pulse.total_new_weekly }}
							</span>
						</div>
						<div class="flex flex-wrap gap-2">
							<div
								v-for="stat in widgets.data.admissions_pulse.breakdown"
								:key="stat.application_status"
								class="inline-chip border border-slate-200 bg-slate-100 text-slate-600"
							>
								{{ stat.application_status }}: {{ stat.count }}
							</div>
						</div>
					</div>

					<!-- Medical Alerts -->
					<div
						v-if="hasData('medical_context')"
						class="paper-card border-l-4 border-l-sky p-5"
					>
						<h3 class="mb-3 text-sm font-semibold text-canopy">
							Medical Alerts (My Classes)
						</h3>
						<div class="custom-scrollbar max-h-48 space-y-2 overflow-y-auto">
							<div
								v-for="med in widgets.data.medical_context"
								:key="med.first_name"
								class="rounded bg-sky/30 p-2 text-sm"
							>
								<span class="font-bold text-ink">
									{{ med.first_name }}:
								</span>
								<span class="ml-1 text-slate-600">
									{{ med.food_allergies }}
								</span>
							</div>
						</div>
					</div>

					<!-- Absent Student List (Instructor) -->
					<div v-if="hasData('my_absent_students')">
						<AbsentStudentList :students="widgets.data.my_absent_students" />
					</div>
				</div>

				<!-- RIGHT COLUMN: RECENT LOGS -->
				<div v-if="hasData('student_logs')">
					<div class="mb-4 flex items-center justify-between">
						<h2 class="section-header flex items-center gap-2 text-flame">
							<FeatherIcon name="clipboard" class="h-3 w-3" />
							Recent Logs (48h)
						</h2>
					</div>

					<div class="paper-card relative flex h-[600px] flex-col">
						<div class="custom-scrollbar flex-1 overflow-y-auto p-0">
							<div
								v-for="(log, i) in widgets.data.student_logs"
								:key="log.name"
								class="group border-b border-border/50 p-5 last:border-0 transition-colors hover:bg-slate-50"
							>
								<div class="flex gap-4">
									<div class="relative flex-shrink-0">
										<div class="h-12 w-12 overflow-hidden rounded-xl bg-slate-200">
											<img
												v-if="log.student_photo"
												:src="log.student_photo"
												class="h-full w-full object-cover"
											/>
											<div
												v-else
												class="flex h-full w-full items-center justify-center text-xs font-bold text-slate-500"
											>
												{{ log.student_name.substring(0, 2) }}
											</div>
										</div>
										<div
											v-if="log.status_color === 'red'"
											class="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-flame ring-2 ring-white"
										></div>
									</div>

									<div class="min-w-0 flex-1">
										<div class="flex items-start justify-between">
											<h4 class="text-sm font-bold text-ink">
												{{ log.student_name }}
											</h4>
											<span class="text-[10px] text-slate-400">
												{{ log.date_display }}
											</span>
										</div>

										<div class="mt-1 mb-2 flex items-center gap-2">
											<span
												class="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-500"
											>
												{{ log.log_type }}
											</span>
										</div>

										<p class="mb-2 text-xs leading-relaxed text-slate-600">
											{{ log.snippet }}
										</p>

										<button
											@click="openLog(log)"
											class="mt-1 flex items-center gap-1 text-[11px] font-medium text-jacaranda transition-colors hover:text-purple-700"
										>
											Read Full Log
											<FeatherIcon name="maximize-2" class="h-3 w-3" />
										</button>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- STAFF BIRTHDAYS -->
			<section v-if="hasData('staff_birthdays')">
				<div class="border-t border-border/60 pt-6">
					<div class="mb-4 flex items-center justify-between">
						<h2 class="section-header flex items-center gap-2 text-slate-400">
							<FeatherIcon name="gift" class="h-3 w-3" />
							Community Pulse
						</h2>
						<span class="text-xs font-medium italic text-purple-600">
							Let's celebrate our amazing team! 🎂
						</span>
					</div>
					<div class="flex flex-wrap items-center gap-4">
						<div
							v-for="emp in widgets.data.staff_birthdays"
							:key="emp.name"
							class="flex items-center gap-3 rounded-full border border-border/80 bg-white py-2 pl-2 pr-5 shadow-sm transition-shadow hover:shadow-md"
						>
							<div class="h-10 w-10 overflow-hidden rounded-full bg-slate-100 ring-2 ring-white">
								<img
									v-if="emp.image"
									:src="emp.image"
									class="h-full w-full object-cover"
								/>
								<div
									v-else
									class="flex h-full w-full items-center justify-center text-sm font-bold text-slate-400"
								>
									{{ emp.name.substring(0, 1) }}
								</div>
							</div>
							<div class="flex flex-col">
								<span class="text-sm font-bold text-ink">
									{{ emp.name }}
								</span>
								<span class="text-xs font-medium uppercase text-amber-600">
									{{ formatBirthday(emp.date_of_birth) }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</section>

			<!-- STUDENT BIRTHDAYS -->
			<section v-if="hasData('my_student_birthdays')">
				<div class="border-t border-border/60 pt-6">
					<h2 class="mb-4 flex items-center gap-2 section-header text-slate-400">
						<FeatherIcon name="gift" class="h-3 w-3" />
						Student Birthdays (My Groups)
					</h2>
					<div class="flex flex-wrap items-center gap-4">
						<div
							v-for="stu in widgets.data.my_student_birthdays"
							:key="stu.first_name + stu.last_name"
							class="flex items-center gap-3 rounded-full border border-border/80 bg-white py-2 pl-2 pr-5 shadow-sm transition-shadow hover:shadow-md"
						>
							<div class="h-10 w-10 overflow-hidden rounded-full bg-slate-100 ring-2 ring-white">
								<img
									v-if="stu.image"
									:src="stu.image"
									class="h-full w-full object-cover"
								/>
								<div
									v-else
									class="flex h-full w-full items-center justify-center text-sm font-bold text-slate-400"
								>
									{{ stu.first_name.substring(0, 1) }}
								</div>
							</div>
							<div class="flex flex-col">
								<span class="text-sm font-bold text-ink">
									{{ stu.first_name }} {{ stu.last_name }}
								</span>
								<span class="text-xs font-medium uppercase text-amber-600">
									{{ formatBirthday(stu.date_of_birth) }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</section>
		</div>

		<!-- CONTENT DIALOG -->
		<ContentDialog
			v-model="isContentDialogOpen"
			:title="dialogContent.title"
			:subtitle="dialogContent.subtitle"
			:content="dialogContent.content"
			:image="dialogContent.image"
			:image-fallback="dialogContent.imageFallback"
			:badge="dialogContent.badge"
		/>

		<!-- CRITICAL INCIDENTS DIALOG -->
		<GenericListDialog
			v-model="showCriticalIncidents"
			title="Critical Incidents"
			subtitle="Open logs requiring follow-up"
			:items="criticalIncidentsList.data"
			:loading="criticalIncidentsList.loading"
		>
			<template #item="{ item }">
				<div class="flex gap-4 p-4">
					<div class="h-10 w-10 shrink-0 overflow-hidden rounded-full bg-slate-100">
						<img
							v-if="item.student_photo"
							:src="item.student_photo"
							class="h-full w-full object-cover"
						/>
						<div
							v-else
							class="flex h-full w-full items-center justify-center text-xs font-bold text-slate-400"
						>
							{{ item.student_name.substring(0, 2) }}
						</div>
					</div>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between">
							<h4 class="text-sm font-bold text-ink">
								{{ item.student_name }}
							</h4>
							<span class="text-xs text-slate-500">
								{{ item.date_display }}
							</span>
						</div>
						<span
							class="mt-1 mb-2 inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-500"
						>
							{{ item.log_type }}
						</span>
						<p class="line-clamp-2 text-sm text-slate-600">
							{{ item.snippet }}
						</p>
						<button
							@click="openLog(item)"
							class="mt-2 text-xs font-medium text-jacaranda hover:underline"
						>
							View Full Log
						</button>
					</div>
				</div>
			</template>
		</GenericListDialog>

		<!-- CLINIC HISTORY DIALOG -->
		<HistoryDialog
			v-model="showClinicHistory"
			subtitle="Student patient visits over time"
			method="ifitwala_ed.api.morning_brief.get_clinic_visits_trend"
		/>
	</div>
</template>


<script setup>
import { ref, computed } from 'vue'
import { createResource, FeatherIcon } from 'frappe-ui'
import ContentDialog from '@/components/ContentDialog.vue'
import GenericListDialog from '@/components/GenericListDialog.vue'
import HistoryDialog from '@/components/HistoryDialog.vue'
import AttendanceTrend from './components/AttendanceTrend.vue'
import AbsentStudentList from './components/AbsentStudentList.vue'

// State for Dialog
const isContentDialogOpen = ref(false)
const dialogContent = ref({
	title: '',
	subtitle: '',
	content: '',
	image: '',
	imageFallback: '',
	badge: ''
})

// State for new dialogs
const showCriticalIncidents = ref(false)
const showClinicHistory = ref(false)

const criticalIncidentsList = createResource({
	url: 'ifitwala_ed.api.morning_brief.get_critical_incidents_details',
	auto: false
})

const widgets = createResource({
	url: 'ifitwala_ed.api.morning_brief.get_briefing_widgets',
	auto: true
})

function hasData(key) {
	return widgets.data && widgets.data[key] && Array.isArray(widgets.data[key]) && widgets.data[key].length > 0
}

function openLog(log) {
	dialogContent.value = {
		title: log.student_name,
		subtitle: log.date_display,
		content: log.full_content,
		image: log.student_photo,
		imageFallback: log.student_name.substring(0, 2),
		badge: log.log_type
	}
	isContentDialogOpen.value = true
}

function openAnnouncement(news) {
	dialogContent.value = {
		title: news.title,
		subtitle: formattedDate.value,
		content: news.content,
		image: '', // Or maybe an icon?
		imageFallback: '',
		badge: news.type
	}
	isContentDialogOpen.value = true
}

function openCriticalIncidents() {
	showCriticalIncidents.value = true
	criticalIncidentsList.fetch()
}

const formattedDate = computed(() => {
	const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
	return new Date().toLocaleDateString('en-GB', options);
})

function getPriorityClasses(priority) {
	if (priority === 'Critical') return 'bg-red-600 text-white ring-4 ring-red-100'
	return ''
}

function formatBirthday(dateStr) {
	if (!dateStr) return ''
	const date = new Date(dateStr)
	const day = date.getDate()
	const month = date.toLocaleString('default', { month: 'long' })

	const suffix = (day) => {
		if (day > 3 && day < 21) return 'th'
		switch (day % 10) {
			case 1: return "st"
			case 2: return "nd"
			case 3: return "rd"
			default: return "th"
		}
	}

	return `${day}${suffix(day)} ${month}`
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
	width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
	background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
	background-color: #cbd5e1;
	border-radius: 20px;
}
</style>
