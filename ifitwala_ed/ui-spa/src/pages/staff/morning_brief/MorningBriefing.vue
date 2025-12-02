<!-- ifitwala_ed/ui-spa/src/pages/staff/MorningBriefing.vue -->
<template>
	<div class="min-h-screen bg-transparent p-4 sm:p-6 space-y-8">

		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="text-3xl font-bold tracking-tight text-heading">Morning Briefing</h1>
				<p class="text-slate-500 mt-1 font-medium">Daily Operational & Academic Pulse</p>
			</div>
			<div class="flex items-center gap-3">
				<div class="text-right">
					<span class="section-header block mb-0.5">Today</span>
					<span class="text-lg font-semibold text-ink">{{ formattedDate }}</span>
				</div>
				<button @click="widgets.reload()" class="remark-btn flex items-center justify-center ml-2">
					<FeatherIcon name="refresh-cw" class="h-4 w-4" :class="{ 'animate-spin': widgets.loading }" />
				</button>
			</div>
		</header>

		<div v-if="widgets.loading" class="animate-pulse space-y-6">
			<div class="h-32 bg-slate-100 rounded-2xl w-full"></div>
			<div class="grid grid-cols-2 gap-6">
				<div class="h-64 bg-slate-100 rounded-2xl"></div>
				<div class="h-64 bg-slate-100 rounded-2xl"></div>
			</div>
		</div>

		<div v-else class="space-y-8">

			<section v-if="hasData('announcements')" class="space-y-4">
				<div v-for="(news, idx) in widgets.data.announcements" :key="idx"
					class="relative overflow-hidden rounded-2xl p-6 shadow-sm transition-all mb-4 last:mb-0"
					:class="getPriorityClasses(news.priority)">
					<div v-if="news.priority !== 'Critical'" class="absolute inset-0 bg-purple-50 opacity-100 z-0"></div>
					<div class="relative z-0" :class="news.priority === 'Critical' ? 'text-white' : 'text-ink'">
						<div class="flex gap-2 mb-2">
							<span class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium border"
								:class="news.priority === 'Critical' ? 'bg-white/20 border-white/30 text-white' : 'bg-white border-purple-100 text-purple-700'">
								{{ news.type }}
							</span>
							<span v-if="news.priority === 'Critical'"
								class="inline-flex items-center gap-1 rounded-md bg-red-100 text-red-700 px-2 py-1 text-xs font-bold">
								CRITICAL
							</span>
						</div>
						<h3 class="text-lg font-bold mb-2">{{ news.title }}</h3>
						<div class="prose prose-sm max-w-none opacity-90 line-clamp-3"
							:class="news.priority === 'Critical' ? 'prose-invert' : 'text-slate-600'" v-html="news.content"></div>

						<button @click="openAnnouncement(news)"
							class="mt-3 text-sm font-semibold flex items-center gap-1 hover:underline focus:outline-none"
							:class="news.priority === 'Critical' ? 'text-white' : 'text-purple-700'">
							Read full announcement
							<FeatherIcon name="arrow-right" class="h-4 w-4" />
						</button>
					</div>
				</div>
			</section>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

				<div class="space-y-6">

					<div class="grid grid-cols-2 gap-6"
						v-if="hasData('clinic_volume') || widgets.data?.critical_incidents !== undefined">
						<!-- Attendance Trend (Admin) -->
						<div v-if="hasData('attendance_trend')" class="col-span-2">
							<AttendanceTrend :data="widgets.data.attendance_trend" />
						</div>

						<div v-if="widgets.data?.critical_incidents !== undefined"
							class="paper-card p-5 border-l-4 border-l-flame cursor-pointer hover:shadow-md transition-shadow"
							@click="openCriticalIncidents">
							<h3 class="section-header !text-flame/80 mb-1">Critical Incidents</h3>
							<div class="text-3xl font-bold text-ink">{{ widgets.data.critical_incidents }}</div>
							<p class="text-xs text-flame mt-1 font-medium flex items-center gap-1">
								<FeatherIcon name="alert-circle" class="h-3 w-3" /> Open Follow-ups
							</p>
						</div>

						<div v-if="hasData('clinic_volume')" class="paper-card p-5 cursor-pointer hover:shadow-md transition-shadow"
							@click="showClinicHistory = true">
							<div class="flex items-center gap-2 mb-3">
								<div class="h-8 w-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
									<FeatherIcon name="thermometer" class="h-4 w-4" />
								</div>
								<h3 class="font-semibold text-canopy text-sm">Clinic Volume</h3>
							</div>
							<div class="space-y-2">
								<div v-for="day in widgets.data.clinic_volume" :key="day.date"
									class="flex justify-between items-center text-sm">
									<span class="text-slate-500">{{ day.date }}</span>
									<span class="font-mono font-medium" :class="day.count > 10 ? 'text-flame' : 'text-ink'">{{ day.count
									}}</span>
								</div>
							</div>
						</div>
					</div>

					<div v-if="widgets.data?.admissions_pulse" class="paper-card p-5">
						<div class="flex items-center justify-between mb-3">
							<div class="flex items-center gap-2">
								<div class="h-8 w-8 rounded-full bg-purple-50 text-purple-600 flex items-center justify-center">
									<FeatherIcon name="users" class="h-4 w-4" />
								</div>
								<h3 class="font-semibold text-canopy text-sm">Admissions (Last 7 Days)</h3>
							</div>
							<span class="text-2xl font-bold text-ink">{{ widgets.data.admissions_pulse.total_new_weekly }}</span>
						</div>
						<div class="flex flex-wrap gap-2">
							<div v-for="stat in widgets.data.admissions_pulse.breakdown" :key="stat.application_status"
								class="inline-chip bg-slate-100 text-slate-600 border border-slate-200">
								{{ stat.application_status }}: {{ stat.count }}
							</div>
						</div>
					</div>

					<div v-if="hasData('medical_context')" class="paper-card p-5 border-l-4 border-l-sky">
						<h3 class="font-semibold text-canopy text-sm mb-3">Medical Alerts (My Classes)</h3>
						<div class="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
							<div v-for="med in widgets.data.medical_context" :key="med.first_name"
								class="text-sm p-2 bg-sky/30 rounded">
								<span class="font-bold text-ink">{{ med.first_name }}:</span>
								<span class="text-slate-600 ml-1">{{ med.food_allergies }}</span>
							</div>
						</div>
					</div>

					<!-- Absent Student List (Instructor) -->
					<div v-if="hasData('my_absent_students')">
						<AbsentStudentList :students="widgets.data.my_absent_students" />
					</div>
				</div>

				<div v-if="hasData('student_logs')">
					<div class="flex items-center justify-between mb-4">
						<h2 class="section-header flex items-center gap-2 text-flame">
							<FeatherIcon name="clipboard" class="h-3 w-3" /> Recent Logs (48h)
						</h2>
					</div>

					<div class="paper-card flex flex-col h-[600px] relative">
						<div class="overflow-y-auto p-0 custom-scrollbar flex-1">
							<div v-for="(log, i) in widgets.data.student_logs" :key="log.name"
								class="p-5 border-b border-border/50 last:border-0 hover:bg-slate-50 transition-colors group">

								<div class="flex gap-4">
									<div class="flex-shrink-0 relative">
										<div class="h-12 w-12 rounded-xl bg-slate-200 overflow-hidden">
											<img v-if="log.student_photo" :src="log.student_photo" class="h-full w-full object-cover">
											<div v-else
												class="h-full w-full flex items-center justify-center text-xs font-bold text-slate-500">
												{{ log.student_name.substring(0, 2) }}
											</div>
										</div>
										<div v-if="log.status_color === 'red'"
											class="absolute -top-1 -right-1 h-3 w-3 bg-flame rounded-full ring-2 ring-white"></div>
									</div>

									<div class="flex-1 min-w-0">
										<div class="flex justify-between items-start">
											<h4 class="text-sm font-bold text-ink">{{ log.student_name }}</h4>
											<span class="text-[10px] text-slate-400">{{ log.date_display }}</span>
										</div>

										<div class="flex items-center gap-2 mt-1 mb-2">
											<span class="text-[10px] uppercase font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
												{{ log.log_type }}
											</span>
										</div>

										<p class="text-xs text-slate-600 leading-relaxed mb-2">
											{{ log.snippet }}
										</p>

										<button @click="openLog(log)"
											class="text-[11px] font-medium text-jacaranda hover:text-purple-700 flex items-center gap-1 mt-1 transition-colors">
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

			<section v-if="hasData('staff_birthdays')">
				<div class="border-t border-border/60 pt-6">
					<div class="flex items-center justify-between mb-4">
						<h2 class="section-header flex items-center gap-2 text-slate-400">
							<FeatherIcon name="gift" class="h-3 w-3" /> Community Pulse
						</h2>
						<span class="text-xs font-medium text-purple-600 italic">
							Let's celebrate our amazing team! 🎂
						</span>
					</div>
					<div class="flex flex-wrap gap-4 items-center">
						<div v-for="emp in widgets.data.staff_birthdays" :key="emp.name"
							class="flex items-center gap-3 bg-white border border-border/80 rounded-full pr-5 pl-2 py-2 shadow-sm hover:shadow-md transition-shadow">
							<div class="h-10 w-10 rounded-full bg-slate-100 overflow-hidden ring-2 ring-white">
								<img v-if="emp.image" :src="emp.image" class="h-full w-full object-cover" />
								<div v-else class="h-full w-full flex items-center justify-center text-sm font-bold text-slate-400">{{
									emp.name.substring(0, 1) }}</div>
							</div>
							<div class="flex flex-col">
								<span class="text-sm font-bold text-ink">{{ emp.name }}</span>
								<span class="text-xs text-amber-600 font-medium uppercase">{{ formatBirthday(emp.date_of_birth)
								}}</span>
							</div>
						</div>
					</div>
				</div>
			</section>

			<section v-if="hasData('my_student_birthdays')">
				<div class="border-t border-border/60 pt-6">
					<h2 class="section-header mb-4 flex items-center gap-2 text-slate-400">
						<FeatherIcon name="gift" class="h-3 w-3" /> Student Birthdays (My Groups)
					</h2>
					<div class="flex flex-wrap gap-4 items-center">
						<div v-for="stu in widgets.data.my_student_birthdays" :key="stu.first_name + stu.last_name"
							class="flex items-center gap-3 bg-white border border-border/80 rounded-full pr-5 pl-2 py-2 shadow-sm hover:shadow-md transition-shadow">
							<div class="h-10 w-10 rounded-full bg-slate-100 overflow-hidden ring-2 ring-white">
								<img v-if="stu.image" :src="stu.image" class="h-full w-full object-cover" />
								<div v-else class="h-full w-full flex items-center justify-center text-sm font-bold text-slate-400">{{
									stu.first_name.substring(0, 1) }}</div>
							</div>
							<div class="flex flex-col">
								<span class="text-sm font-bold text-ink">{{ stu.first_name }} {{ stu.last_name }}</span>
								<span class="text-xs text-amber-600 font-medium uppercase">{{ formatBirthday(stu.date_of_birth)
								}}</span>
							</div>
						</div>
					</div>
				</div>
			</section>

		</div>

		<ContentDialog v-model="isContentDialogOpen" :title="dialogContent.title" :subtitle="dialogContent.subtitle"
			:content="dialogContent.content" :image="dialogContent.image" :image-fallback="dialogContent.imageFallback"
			:badge="dialogContent.badge" />

		<!-- New Dialogs -->
		<GenericListDialog v-model="showCriticalIncidents" title="Critical Incidents"
			subtitle="Open logs requiring follow-up" :items="criticalIncidentsList.data"
			:loading="criticalIncidentsList.loading">
			<template #item="{ item }">
				<div class="p-4 flex gap-4">
					<div class="h-10 w-10 shrink-0 rounded-full bg-slate-100 overflow-hidden">
						<img v-if="item.student_photo" :src="item.student_photo" class="h-full w-full object-cover">
						<div v-else class="h-full w-full flex items-center justify-center text-xs font-bold text-slate-400">
							{{ item.student_name.substring(0, 2) }}
						</div>
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex justify-between items-start">
							<h4 class="text-sm font-bold text-ink">{{ item.student_name }}</h4>
							<span class="text-xs text-slate-500">{{ item.date_display }}</span>
						</div>
						<span
							class="inline-block mt-1 mb-2 text-[10px] font-semibold uppercase text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
							{{ item.log_type }}
						</span>
						<p class="text-sm text-slate-600 line-clamp-2">{{ item.snippet }}</p>
						<button @click="openLog(item)" class="mt-2 text-xs font-medium text-jacaranda hover:underline">
							View Full Log
						</button>
					</div>
				</div>
			</template>
		</GenericListDialog>

		<HistoryDialog v-model="showClinicHistory" title="Clinic Volume History" subtitle="Student patient visits over time"
			method="ifitwala_ed.api.morning_brief.get_clinic_visits_trend" />

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
