<template>
	<div class="min-h-screen bg-gray-50 p-6">
		<header class="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="text-3xl font-bold text-gray-900">Morning Briefing</h1>
				<p class="text-gray-500 mt-1">
					Student well-being & attendance intelligence
				</p>
			</div>
			<div class="flex items-center gap-3">
				<div class="text-right">
					<span class="block text-xs font-bold uppercase tracking-wider text-gray-400">Today</span>
					<span class="text-lg font-semibold text-gray-900">{{ formattedDate }}</span>
				</div>
				<button
					@click="refreshData"
					class="ml-4 rounded-full p-2 text-gray-400 hover:bg-gray-200 hover:text-gray-600 transition-colors"
					title="Refresh Data"
				>
					<FeatherIcon name="refresh-cw" class="h-5 w-5" :class="{ 'animate-spin': isLoading }" />
				</button>
			</div>
		</header>

		<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">

			<div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-blue-500 relative overflow-hidden">
				<h3 class="text-xs font-bold tracking-wider text-gray-400 uppercase">Absent Today</h3>
				<div class="mt-2 flex items-baseline gap-2">
					<span v-if="stats.loading" class="h-8 w-16 bg-gray-100 rounded animate-pulse"></span>
					<span v-else class="text-3xl font-bold text-gray-900">
						{{ stats.data?.absent_today || 0 }}
					</span>
					<span class="text-sm text-gray-500">students</span>
				</div>
				<div class="mt-4 flex items-center text-xs text-blue-600 font-medium">
					<FeatherIcon name="clock" class="h-3 w-3 mr-1" />
					<span>{{ stats.data?.late_today || 0 }} Late arrivals</span>
				</div>
			</div>

			<div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-red-500 relative overflow-hidden">
				<h3 class="text-xs font-bold tracking-wider text-gray-400 uppercase">Critical Flags</h3>
				<div class="mt-2 flex items-baseline gap-2">
					<span v-if="stats.loading" class="h-8 w-16 bg-gray-100 rounded animate-pulse"></span>
					<span v-else class="text-3xl font-bold text-gray-900">
						{{ stats.data?.critical_logs || 0 }}
					</span>
					<span class="text-sm text-gray-500">unresolved</span>
				</div>
				<p class="mt-4 text-xs text-red-600 font-medium">
					High severity incidents (7 days)
				</p>
			</div>

			<div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-orange-500 relative overflow-hidden">
				<h3 class="text-xs font-bold tracking-wider text-gray-400 uppercase">At Risk Watchlist</h3>
				<div class="mt-2 flex items-baseline gap-2">
					<span v-if="watchlist.loading" class="h-8 w-16 bg-gray-100 rounded animate-pulse"></span>
					<span v-else class="text-3xl font-bold text-gray-900">
						{{ watchlist.data?.length || 0 }}
					</span>
					<span class="text-sm text-gray-500">patterns detected</span>
				</div>
				<p class="mt-4 text-xs text-orange-600 font-medium">
					Velocity & Ghosting checks
				</p>
			</div>
		</div>

		<div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
			<div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
				<h2 class="text-lg font-bold text-gray-900 flex items-center gap-2">
					<FeatherIcon name="radar" class="h-5 w-5 text-jacaranda" />
					Early Warning Radar
				</h2>
				<span class="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">
					Auto-generated based on velocity
				</span>
			</div>

			<div class="min-h-[300px]">

				<div v-if="watchlist.loading" class="p-6 space-y-4">
					<div v-for="i in 3" :key="i" class="flex items-center gap-4 animate-pulse">
						<div class="h-10 w-10 bg-gray-100 rounded-full"></div>
						<div class="h-4 bg-gray-100 rounded w-1/3"></div>
						<div class="h-4 bg-gray-100 rounded w-1/4"></div>
					</div>
				</div>

				<div v-else-if="!watchlist.data || watchlist.data.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
					<div class="h-12 w-12 rounded-full bg-green-50 flex items-center justify-center mb-3">
						<FeatherIcon name="check" class="h-6 w-6 text-green-600" />
					</div>
					<h3 class="text-gray-900 font-medium">All clear</h3>
					<p class="text-gray-500 text-sm mt-1 max-w-xs">
						No students triggered the velocity or ghosting algorithms today.
					</p>
				</div>

				<table v-else class="w-full text-left text-sm">
					<thead class="bg-gray-50 text-gray-500 font-medium border-b border-gray-100">
						<tr>
							<th class="px-6 py-3">Student</th>
							<th class="px-6 py-3">Grade</th>
							<th class="px-6 py-3">Risk Vector</th>
							<th class="px-6 py-3 text-right">Action</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-100">
						<tr v-for="student in watchlist.data" :key="student.student" class="group hover:bg-gray-50 transition-colors">
							<td class="px-6 py-4">
								<div class="flex items-center gap-3">
									<div class="h-10 w-10 rounded-full bg-gray-200 overflow-hidden flex items-center justify-center text-gray-500">
										<img v-if="student.image" :src="student.image" class="h-full w-full object-cover" />
										<FeatherIcon v-else name="user" class="h-5 w-5" />
									</div>
									<div class="font-medium text-gray-900">
										{{ student.student_name }}
									</div>
								</div>
							</td>
							<td class="px-6 py-4 text-gray-500">
								{{ student.grade }}
							</td>
							<td class="px-6 py-4">
								<div class="flex flex-wrap gap-2">
									<span
										v-for="risk in student.risks"
										:key="risk"
										class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border"
										:class="getRiskBadgeColor(risk)"
									>
										{{ risk }}
									</span>
								</div>
							</td>
							<td class="px-6 py-4 text-right">
								<button class="text-gray-400 hover:text-jacaranda transition-colors">
									<FeatherIcon name="chevron-right" class="h-5 w-5" />
								</button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource, FeatherIcon } from 'frappe-ui'

// 1. Fetch Summary Stats
const stats = createResource({
	url: 'ifitwala_ed.ifitwala_ed.api.morning_brief.get_morning_briefing_stats',
	auto: true
})

// 2. Fetch Detailed Watchlist
const watchlist = createResource({
	url: 'ifitwala_ed.ifitwala_ed.api.morning_brief.get_risk_watchlist',
	auto: true
})

const isLoading = computed(() => stats.loading || watchlist.loading)

// 3. Formatting
const formattedDate = computed(() => {
	const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
	return new Date().toLocaleDateString('en-GB', options);
})

function refreshData() {
	stats.reload()
	watchlist.reload()
}

function getRiskBadgeColor(riskType) {
	if (riskType.includes('Ghosting')) {
		return 'bg-gray-100 text-gray-700 border-gray-200'
	}
	if (riskType.includes('Velocity')) {
		return 'bg-orange-50 text-orange-700 border-orange-200'
	}
	return 'bg-red-50 text-red-700 border-red-200'
}
</script>
