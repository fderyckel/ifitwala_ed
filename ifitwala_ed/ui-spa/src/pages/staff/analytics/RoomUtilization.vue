<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/RoomUtilization.vue -->
<template>
	<div class="analytics-shell">
		<header class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
			<div class="text-left">
				<h1 class="type-h2 text-canopy">Room Utilization</h1>
				<p class="type-body text-slate-500 mt-1">
					Find free rooms across your campus and book spaces.
				</p>
			</div>
			<button
				v-if="canViewAnalytics"
				class="rounded-full bg-canopy px-5 py-2 text-sm font-medium text-white transition-all hover:bg-leaf hover:shadow-md active:scale-95"
				@click="refreshMetrics"
			>
				Refresh Data
			</button>
		</header>

		<KpiRow v-if="canViewAnalytics" :items="kpiItems" class="mb-2" />

		<section class="analytics-card relative overflow-hidden">
			<!-- Decorative background blur -->
			<div
				class="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-leaf/5 blur-3xl pointer-events-none"
			></div>

			<div
				class="relative z-10 flex flex-wrap items-end justify-between gap-4 border-b border-slate-100 pb-5 mb-5"
			>
				<div>
					<h3 class="analytics-card__title">Free Rooms Finder</h3>
					<p class="analytics-card__meta mt-1 max-w-2xl">
						Locate available spaces by checking against all meetings, school events, and teaching
						bookings.
					</p>
				</div>
				<div class="flex flex-wrap items-center gap-3">
					<button
						v-if="canOpenCreateEvent"
						class="rounded-full border border-slate-200 bg-white px-5 py-2 text-sm font-medium text-ink transition-all hover:border-canopy/40 hover:text-canopy hover:shadow-sm active:scale-95"
						@click="openCreateEvent"
					>
						{{ eventQuickActionTitle }}
					</button>
					<button
						class="fui-btn-primary rounded-full px-5 py-2 text-sm font-medium transition-all hover:shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
						:disabled="
							freeRoomsLoading ||
							!availabilityFilters.date ||
							!availabilityFilters.start_time ||
							!availabilityFilters.end_time
						"
						@click="loadFreeRooms"
					>
						Find Free Rooms
					</button>
				</div>
			</div>

			<div class="grid gap-6 lg:grid-cols-[280px_1fr]">
				<!-- Search Controls -->
				<div class="p-4 rounded-xl bg-slate-50 border border-slate-200/60 h-fit">
					<div class="space-y-4">
						<div class="flex flex-col gap-1.5">
							<label class="type-label">School Context</label>
							<select
								v-model="selectedSchool"
								class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-leaf focus:ring-leaf/20"
							>
								<option value="">Select School</option>
								<option v-for="s in schools" :key="s.name" :value="s.name">{{ s.label }}</option>
							</select>
						</div>

						<div class="flex flex-col gap-1.5">
							<label class="type-label">Target Date</label>
							<input
								type="date"
								v-model="availabilityFilters.date"
								class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-leaf focus:ring-leaf/20"
							/>
						</div>

						<div class="grid grid-cols-2 gap-3">
							<div class="flex flex-col gap-1.5">
								<label class="type-label">Start Time</label>
								<input
									type="time"
									v-model="availabilityFilters.start_time"
									class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-leaf focus:ring-leaf/20"
								/>
							</div>
							<div class="flex flex-col gap-1.5">
								<label class="type-label">End Time</label>
								<input
									type="time"
									v-model="availabilityFilters.end_time"
									class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-leaf focus:ring-leaf/20"
								/>
							</div>
						</div>

						<div class="flex flex-col gap-1.5">
							<label class="type-label">Min Capacity</label>
							<input
								type="number"
								min="1"
								step="1"
								v-model="availabilityFilters.capacity_needed"
								placeholder="Optional"
								class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-leaf focus:ring-leaf/20"
							/>
						</div>

						<div class="flex flex-col gap-1.5">
							<label class="type-label">Room Type</label>
							<select
								v-model="selectedLocationType"
								class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-leaf focus:ring-leaf/20"
							>
								<option value="">All schedulable rooms</option>
								<option v-for="option in locationTypes" :key="option.value" :value="option.value">
									{{ option.label }}
								</option>
							</select>
						</div>
					</div>
				</div>

				<!-- Results Area -->
				<div class="min-h-[200px] relative">
					<div class="flex items-center gap-3 mb-4">
						<StatsTile
							label="Available Rooms"
							:value="freeRooms.length"
							:tone="freeRooms.length ? 'success' : 'warning'"
							class="!bg-white !border-slate-100"
						/>
						<div class="h-8 w-px bg-slate-200"></div>
						<div class="text-xs text-slate-500">
							<span class="font-medium text-slate-700">Search Window:</span>
							{{ freeWindowLabel }}
						</div>
					</div>

					<div
						v-if="freeRoomsLoading"
						class="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-sm z-10"
					>
						<div class="flex flex-col items-center gap-2">
							<div
								class="h-6 w-6 animate-spin rounded-full border-2 border-leaf border-t-transparent"
							></div>
							<span class="text-sm text-slate-500 font-medium">Checking availability...</span>
						</div>
					</div>

					<div
						v-if="!freeRoomsLoading && !freeRooms.length"
						class="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed border-slate-100 rounded-xl bg-slate-50/50"
					>
						<div class="h-10 w-10 text-slate-300 mb-2">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-full h-full"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
								/>
							</svg>
						</div>
						<p class="text-sm font-medium text-slate-600">No free rooms found</p>
						<p class="text-xs text-slate-400 mt-1">Try adjusting the time window or capacity.</p>
					</div>

					<div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
						<article
							v-for="room in freeRooms"
							:key="room.room"
							class="group relative rounded-xl border border-slate-200 bg-white p-4 transition-all hover:border-leaf/50 hover:shadow-md"
						>
							<div class="flex items-start justify-between">
								<div>
									<div class="text-sm font-bold text-ink group-hover:text-leaf transition-colors">
										{{ room.room_name }}
									</div>
									<div class="text-xs text-slate-500 mt-0.5">
										{{ room.building || 'Main Building' }}
										<span v-if="room.location_type_name"> · {{ room.location_type_name }}</span>
									</div>
								</div>
								<div
									class="flex h-6 items-center justify-center rounded-full bg-slate-100 px-2 text-[10px] font-bold text-slate-600"
								>
									{{ room.max_capacity ? `${room.max_capacity} pax` : '—' }}
								</div>
							</div>
						</article>
					</div>
				</div>
			</div>
		</section>

		<!-- Unified Analytics Grid -->
		<div v-if="canViewAnalytics" class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<!-- Time Utilization Section -->
			<section class="analytics-card h-full">
				<div class="flex flex-wrap items-start justify-between gap-3 mb-4">
					<div>
						<h3 class="analytics-card__title text-jacaranda">Time Utilization</h3>
						<p class="analytics-card__meta mt-1">Booked minutes vs available minutes per day.</p>
					</div>
					<StatsTile
						label="Avg Utilization"
						:value="avgUtilizationLabel"
						tone="info"
						class="!bg-white"
					/>
				</div>

				<div class="bg-slate-50/80 rounded-xl p-3 border border-slate-100 mb-4">
					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
						<div class="space-y-1">
							<label class="text-[10px] uppercase tracking-wider font-semibold text-slate-400"
								>Date Range</label
							>
							<div class="flex items-center gap-2">
								<input
									type="date"
									v-model="timeUtilFilters.from_date"
									class="h-8 w-full rounded border-slate-200 text-xs shadow-sm focus:border-jacaranda focus:ring-jacaranda/20"
								/>
								<span class="text-slate-300">-</span>
								<input
									type="date"
									v-model="timeUtilFilters.to_date"
									class="h-8 w-full rounded border-slate-200 text-xs shadow-sm focus:border-jacaranda focus:ring-jacaranda/20"
								/>
							</div>
						</div>
						<div class="space-y-1">
							<label class="text-[10px] uppercase tracking-wider font-semibold text-slate-400"
								>Day Window</label
							>
							<div class="flex items-center gap-2">
								<input
									type="time"
									v-model="timeUtilFilters.day_start_time"
									class="h-8 w-full rounded border-slate-200 text-xs shadow-sm focus:border-jacaranda focus:ring-jacaranda/20"
								/>
								<span class="text-slate-300">-</span>
								<input
									type="time"
									v-model="timeUtilFilters.day_end_time"
									class="h-8 w-full rounded border-slate-200 text-xs shadow-sm focus:border-jacaranda focus:ring-jacaranda/20"
								/>
							</div>
						</div>
					</div>
					<label
						class="mt-3 flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600"
					>
						<input
							v-model="timeUtilFilters.include_non_instructional_days"
							type="checkbox"
							class="h-4 w-4 rounded border-slate-300 text-jacaranda focus:ring-jacaranda/30"
						/>
						<span>Include weekends and holidays</span>
					</label>
				</div>

				<div v-if="timeUtilLoading" class="flex-1 flex flex-col items-center justify-center py-12">
					<div
						class="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-jacaranda"
					></div>
				</div>

				<div
					v-else-if="!timeRooms.length"
					class="flex-1 flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-xl border border-slate-100 border-dashed"
				>
					<p class="text-sm text-slate-500">No utilization data.</p>
					<p class="text-xs text-slate-400">Check the school or date range.</p>
				</div>

				<div v-else class="flex-1 overflow-auto custom-scrollbar relative">
					<table class="w-full text-sm text-left">
						<thead
							class="text-xs text-slate-500 uppercase bg-slate-50/50 sticky top-0 backdrop-blur-sm z-10"
						>
							<tr>
								<th class="px-3 py-2 font-semibold">Room</th>
								<th class="px-3 py-2 font-semibold text-right">Booked</th>
								<th class="px-3 py-2 font-semibold text-right">Avail</th>
								<th class="px-3 py-2 font-semibold text-right">Util %</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr
								v-for="room in timeRooms"
								:key="room.room"
								class="group hover:bg-slate-50 transition-colors"
							>
								<td
									class="px-3 py-2.5 font-medium text-ink group-hover:text-jacaranda transition-colors"
								>
									<div class="leading-tight">{{ room.room_name }}</div>
									<div
										v-if="room.location_type_name"
										class="text-[11px] font-normal text-slate-400"
									>
										{{ room.location_type_name }}
									</div>
								</td>
								<td class="px-3 py-2.5 text-right text-slate-600 font-mono text-xs">
									{{ minutesToHours(room.booked_minutes) }}
								</td>
								<td class="px-3 py-2.5 text-right text-slate-400 font-mono text-xs">
									{{ minutesToHours(room.available_minutes) }}
								</td>
								<td class="px-3 py-2.5 text-right">
									<span
										class="inline-flex items-center justify-center rounded-full px-2 py-0.5 text-[10px] font-bold min-w-[3rem]"
										:class="utilizationBadge(room.utilization_pct)"
									>
										{{ room.utilization_pct.toFixed(1) }}%
									</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- Capacity Utilization Section -->
			<section class="analytics-card h-full">
				<div class="flex flex-wrap items-start justify-between gap-3 mb-4">
					<div>
						<h3 class="analytics-card__title text-flame">Capacity Utilization</h3>
						<p class="analytics-card__meta mt-1">Participants vs room capacity.</p>
					</div>
					<StatsTile
						label="Over-Cap Rooms"
						:value="overCapRooms"
						tone="warning"
						class="!bg-white"
					/>
				</div>

				<div class="bg-slate-50/80 rounded-xl p-3 border border-slate-100 mb-4">
					<div class="space-y-1">
						<label class="text-[10px] uppercase tracking-wider font-semibold text-slate-400"
							>Date Range</label
						>
						<div class="flex items-center gap-2">
							<input
								type="date"
								v-model="capacityFilters.from_date"
								class="h-8 w-full rounded border-slate-200 text-xs shadow-sm focus:border-flame focus:ring-flame/20"
							/>
							<span class="text-slate-300">-</span>
							<input
								type="date"
								v-model="capacityFilters.to_date"
								class="h-8 w-full rounded border-slate-200 text-xs shadow-sm focus:border-flame focus:ring-flame/20"
							/>
						</div>
					</div>
				</div>

				<div v-if="capacityLoading" class="flex-1 flex flex-col items-center justify-center py-12">
					<div
						class="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-flame"
					></div>
				</div>

				<div
					v-else-if="!capacityRooms.length"
					class="flex-1 flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-xl border border-slate-100 border-dashed"
				>
					<p class="text-sm text-slate-500">No capacity data.</p>
					<p class="text-xs text-slate-400">Check the school or date range.</p>
				</div>

				<div v-else class="flex-1 overflow-auto custom-scrollbar relative">
					<table class="w-full text-sm text-left">
						<thead
							class="text-xs text-slate-500 uppercase bg-slate-50/50 sticky top-0 backdrop-blur-sm z-10"
						>
							<tr>
								<th class="px-3 py-2 font-semibold">Room</th>
								<th class="px-3 py-2 font-semibold text-center">Cap</th>
								<th class="px-3 py-2 font-semibold text-center">Avg/Peak</th>
								<th class="px-3 py-2 font-semibold text-right">Avg %</th>
								<th class="px-3 py-2 font-semibold text-right">Count</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr
								v-for="room in capacityRooms"
								:key="room.room"
								class="group hover:bg-slate-50 transition-colors"
							>
								<td
									class="px-3 py-2.5 font-medium text-ink group-hover:text-flame transition-colors"
								>
									<div class="leading-tight">{{ room.room_name }}</div>
									<div
										v-if="room.location_type_name"
										class="text-[11px] font-normal text-slate-400"
									>
										{{ room.location_type_name }}
									</div>
								</td>
								<td class="px-3 py-2.5 text-center text-slate-400 text-xs">
									{{ room.max_capacity ?? '—' }}
								</td>
								<td class="px-3 py-2.5 text-center text-slate-600 text-xs">
									<span class="font-medium">{{ room.avg_attendees }}</span>
									<span class="text-slate-300 mx-1">/</span>
									<span>{{ room.peak_attendees }}</span>
								</td>
								<td class="px-3 py-2.5 text-right text-slate-600 text-xs font-mono">
									{{ formatPct(room.avg_capacity_pct) }}
								</td>
								<td class="px-3 py-2.5 text-right">
									<span
										class="inline-flex items-center justify-center rounded-full px-2 py-0.5 text-[10px] font-bold"
										:class="overCapBadge(room.over_capacity_count)"
									>
										{{ room.over_capacity_count }}
									</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		</div>

		<section class="analytics-card mt-6">
			<div
				class="mb-5 flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5"
			>
				<div>
					<h3 class="analytics-card__title text-canopy">Location Calendar</h3>
					<p class="analytics-card__meta mt-1 max-w-2xl">
						Read-only timeline of everything booked into a shared room or building, including
						teaching, meetings, and school events.
					</p>
				</div>
				<div class="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">
					{{ locationCalendarSummary }}
				</div>
			</div>

			<div class="grid gap-6 lg:grid-cols-[300px_1fr]">
				<div class="h-fit rounded-xl border border-slate-200/60 bg-slate-50 p-4">
					<div class="space-y-4">
						<div class="flex flex-col gap-1.5">
							<label class="type-label">School Context</label>
							<select
								v-model="selectedSchool"
								class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-canopy focus:ring-canopy/20"
							>
								<option value="">Select School</option>
								<option v-for="s in schools" :key="s.name" :value="s.name">{{ s.label }}</option>
							</select>
						</div>

						<div class="grid grid-cols-2 gap-3">
							<div class="flex flex-col gap-1.5">
								<label class="type-label">From</label>
								<input
									type="date"
									v-model="locationCalendarFilters.from_date"
									class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-canopy focus:ring-canopy/20"
								/>
							</div>
							<div class="flex flex-col gap-1.5">
								<label class="type-label">To</label>
								<input
									type="date"
									v-model="locationCalendarFilters.to_date"
									class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-canopy focus:ring-canopy/20"
								/>
							</div>
						</div>

						<div class="flex flex-col gap-1.5">
							<label class="type-label">Location or Building</label>
							<select
								v-model="locationCalendarFilters.location"
								class="h-10 w-full rounded-md border-slate-300 bg-white px-3 text-sm focus:border-canopy focus:ring-canopy/20"
							>
								<option value="">Select Location</option>
								<option
									v-for="option in locationCalendarLocationOptions"
									:key="option.value"
									:value="option.value"
								>
									{{ option.label }}
								</option>
							</select>
						</div>

						<p class="text-xs leading-5 text-slate-500">
							{{ locationCalendarNote }}
						</p>
					</div>
				</div>

				<div class="relative min-h-[240px]">
					<div
						v-if="locationCalendarLoading"
						class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-white/70 backdrop-blur-sm"
					>
						<div class="flex flex-col items-center gap-2">
							<div
								class="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-canopy"
							></div>
							<span class="text-sm font-medium text-slate-500">Loading location calendar...</span>
						</div>
					</div>

					<div
						v-if="!selectedSchool"
						class="flex h-full min-h-[240px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 text-center text-sm text-slate-500"
					>
						Select a school to load shared facilities and their booking timeline.
					</div>

					<div
						v-else-if="!locationCalendarFilters.location"
						class="flex h-full min-h-[240px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 text-center text-sm text-slate-500"
					>
						{{ locationCalendarNote }}
					</div>

					<div
						v-else-if="!locationCalendarEvents.length"
						class="flex h-full min-h-[240px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 text-center text-sm text-slate-500"
					>
						No bookings were found for {{ selectedLocationCalendarLabel || 'this selection' }} in
						the chosen date range.
					</div>

					<div v-else class="space-y-5">
						<div class="rounded-xl border border-slate-200/70 bg-slate-50 px-4 py-3">
							<p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
								Current Selection
							</p>
							<p class="mt-1 text-base font-semibold text-ink">
								{{ selectedLocationCalendarLabel }}
							</p>
						</div>

						<div
							v-for="day in groupedLocationCalendarEvents"
							:key="day.date"
							class="rounded-xl border border-slate-200/70 bg-white p-4"
						>
							<div class="mb-3 flex items-center justify-between gap-3">
								<h4 class="text-sm font-semibold text-ink">{{ day.label }}</h4>
								<span class="text-xs text-slate-400">
									{{ day.events.length }} booking{{ day.events.length === 1 ? '' : 's' }}
								</span>
							</div>

							<div class="space-y-3">
								<article
									v-for="event in day.events"
									:key="event.id"
									class="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-3"
								>
									<div
										class="mt-0.5 h-12 w-1.5 flex-none rounded-full"
										:style="{ backgroundColor: event.color || '#475569' }"
									></div>
									<div class="min-w-0 flex-1">
										<div class="flex flex-wrap items-start justify-between gap-3">
											<div class="min-w-0">
												<p class="text-sm font-semibold text-ink">{{ event.title }}</p>
												<p class="mt-1 text-xs text-slate-500">
													{{ eventTimeLabel(event.start, event.end) }}
												</p>
											</div>
											<span
												class="rounded-full bg-white px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500"
											>
												{{ event.meta?.occupancy_type || 'Busy' }}
											</span>
										</div>
										<p
											v-if="event.meta?.teaching_context_label"
											class="mt-2 text-xs font-medium text-slate-600"
										>
											{{ event.meta.teaching_context_label }}
										</p>
										<p v-if="event.meta?.location_label" class="mt-2 text-xs text-slate-500">
											{{ event.meta.location_label }}
										</p>
									</div>
								</article>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { createResource } from 'frappe-ui';

import StatsTile from '@/components/analytics/StatsTile.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';

type SchoolOption = { name: string; label: string };
type LocationTypeOption = { value: string; label: string };
type TimeUtilDefaults = { day_start_time: string; day_end_time: string };

type FreeRoom = {
	room: string;
	room_name: string;
	building?: string;
	location_type?: string | null;
	location_type_name?: string | null;
	max_capacity?: number | null;
};

type TimeRoom = {
	room: string;
	room_name: string;
	location_type?: string | null;
	location_type_name?: string | null;
	booked_minutes: number;
	available_minutes: number;
	utilization_pct: number;
};

type CapacityRoom = {
	room: string;
	room_name: string;
	location_type?: string | null;
	location_type_name?: string | null;
	max_capacity?: number | null;
	meetings: number;
	avg_attendees: number;
	peak_attendees: number;
	avg_capacity_pct?: number | null;
	peak_capacity_pct?: number | null;
	over_capacity_count: number;
};

type CalendarLocationOption = {
	value: string;
	label: string;
	is_group?: number;
	parent_location?: string | null;
	location_type?: string | null;
	location_type_name?: string | null;
};

type LocationCalendarEvent = {
	id: string;
	title: string;
	start: string;
	end: string;
	allDay: boolean;
	color?: string | null;
	meta?: {
		occupancy_type?: string | null;
		location?: string | null;
		location_label?: string | null;
		student_group?: string | null;
		student_group_label?: string | null;
		course?: string | null;
		course_name?: string | null;
		teaching_context_label?: string | null;
	};
};

const today = new Date().toISOString().slice(0, 10);

function addDaysIso(baseDate: string, days: number) {
	const base = new Date(`${baseDate}T00:00:00`);
	if (Number.isNaN(base.getTime())) return baseDate;
	base.setDate(base.getDate() + days);
	return base.toISOString().slice(0, 10);
}

function normalizeDateTime(value: string | null | undefined) {
	return String(value || '').replace(' ', 'T');
}

function extractDateKey(value: string | null | undefined) {
	return normalizeDateTime(value).slice(0, 10);
}

function extractTimeValue(value: string | null | undefined) {
	const normalized = normalizeDateTime(value);
	return normalized.length >= 16 ? normalized.slice(11, 16) : '—';
}

function formatDateKeyLabel(dateKey: string) {
	if (!dateKey) return 'Unknown day';
	const date = new Date(`${dateKey}T00:00:00`);
	if (Number.isNaN(date.getTime())) return dateKey;
	return date.toLocaleDateString(undefined, {
		weekday: 'short',
		month: 'short',
		day: 'numeric',
	});
}

const selectedSchool = ref('');
const selectedLocationType = ref('');
const overlay = useOverlayStack();

const availabilityFilters = ref({
	date: today,
	start_time: '09:00',
	end_time: '10:15',
	capacity_needed: '',
});

const timeUtilFilters = ref({
	from_date: today,
	to_date: today,
	day_start_time: '07:00',
	day_end_time: '16:00',
	include_non_instructional_days: false,
});

const capacityFilters = ref({
	from_date: today,
	to_date: today,
});

const locationCalendarFilters = ref({
	from_date: today,
	to_date: addDaysIso(today, 6),
	location: '',
});

const filterMetaResource = createResource({
	url: 'ifitwala_ed.api.room_utilization.get_room_utilization_filter_meta',
	method: 'GET',
	auto: true,
});

const filterMeta = computed(() => (filterMetaResource.data as any) || {});
const schools = computed<SchoolOption[]>(() => filterMeta.value.schools || []);
const locationTypes = computed<LocationTypeOption[]>(() => filterMeta.value.location_types || []);
const timeUtilDefaultsBySchool = computed<Record<string, TimeUtilDefaults>>(
	() => filterMeta.value.time_util_defaults_by_school || {}
);

watch(
	filterMeta,
	data => {
		if (!data) return;
		if (data.default_school && !selectedSchool.value) {
			selectedSchool.value = data.default_school;
		}
	},
	{ immediate: true }
);

watch(
	() => [selectedSchool.value, timeUtilDefaultsBySchool.value],
	([schoolName, defaultsBySchool]) => {
		const schoolDefaults = schoolName ? defaultsBySchool?.[schoolName] : null;
		if (!schoolDefaults) return;
		timeUtilFilters.value.day_start_time = String(
			schoolDefaults.day_start_time || '07:00:00'
		).slice(0, 5);
		timeUtilFilters.value.day_end_time = String(schoolDefaults.day_end_time || '16:00:00').slice(
			0,
			5
		);
	},
	{ immediate: true }
);

const freeRoomsResource = createResource({
	url: 'ifitwala_ed.api.room_utilization.get_free_rooms',
	method: 'POST',
	auto: false,
});

const analyticsAccessResource = createResource({
	url: 'ifitwala_ed.api.room_utilization.can_view_room_utilization_analytics',
	method: 'POST',
	auto: false,
});

const staffHomeHeaderResource = createResource({
	url: 'ifitwala_ed.api.portal.get_staff_home_header',
	method: 'POST',
	auto: false,
});

const canViewAnalytics = ref(false);
const roomUtilizationCapabilities = computed(
	() => staffHomeHeaderResource.data?.capabilities || {}
);
const canCreateMeeting = computed(() =>
	Boolean(roomUtilizationCapabilities.value.quick_action_create_meeting)
);
const canCreateSchoolEvent = computed(() =>
	Boolean(roomUtilizationCapabilities.value.quick_action_create_school_event)
);
const canOpenCreateEvent = computed(() => canCreateMeeting.value || canCreateSchoolEvent.value);
const eventQuickActionTitle = computed(() => {
	if (canCreateMeeting.value && !canCreateSchoolEvent.value) return 'Schedule meeting';
	return 'Create event';
});

const timeUtilResource = createResource({
	url: 'ifitwala_ed.api.room_utilization.get_room_time_utilization',
	method: 'POST',
	auto: false,
});

const capacityResource = createResource({
	url: 'ifitwala_ed.api.room_utilization.get_room_capacity_utilization',
	method: 'POST',
	auto: false,
});

const locationCalendarResource = createResource({
	url: 'ifitwala_ed.api.room_utilization.get_location_calendar',
	method: 'POST',
	auto: false,
});

const freeRooms = computed<FreeRoom[]>(() => freeRoomsResource.data?.rooms || []);
const timeRooms = computed<TimeRoom[]>(() => timeUtilResource.data?.rooms || []);
const capacityRooms = computed<CapacityRoom[]>(() => capacityResource.data?.rooms || []);
const locationCalendarLocations = computed<CalendarLocationOption[]>(
	() => locationCalendarResource.data?.locations || []
);
const locationCalendarEvents = computed<LocationCalendarEvent[]>(
	() => locationCalendarResource.data?.events || []
);

const freeRoomsLoading = computed(() => freeRoomsResource.loading);
const timeUtilLoading = computed(() => timeUtilResource.loading);
const capacityLoading = computed(() => capacityResource.loading);
const locationCalendarLoading = computed(() => locationCalendarResource.loading);

const freeWindowLabel = computed(() => {
	if (
		!availabilityFilters.value.date ||
		!availabilityFilters.value.start_time ||
		!availabilityFilters.value.end_time
	)
		return '—';
	return `${availabilityFilters.value.date} ${availabilityFilters.value.start_time}–${availabilityFilters.value.end_time}`;
});

const avgUtilizationLabel = computed(() => {
	if (!timeRooms.value.length) return '—';
	const total = timeRooms.value.reduce((sum, room) => sum + room.utilization_pct, 0);
	const avg = total / timeRooms.value.length;
	return `${avg.toFixed(1)}%`;
});

const overCapRooms = computed(() => {
	if (!capacityRooms.value.length) return 0;
	return capacityRooms.value.filter(room => room.over_capacity_count > 0).length;
});

const locationCalendarLocationOptions = computed<CalendarLocationOption[]>(
	() => locationCalendarLocations.value
);

const selectedLocationCalendarLabel = computed(
	() => locationCalendarResource.data?.selected_location_label || ''
);

const locationCalendarNote = computed(
	() =>
		locationCalendarResource.data?.note || 'Select a location or building to load its calendar.'
);

const locationCalendarSummary = computed(() => {
	if (!selectedSchool.value) return 'Select a school';
	if (!locationCalendarFilters.value.location) {
		return `${locationCalendarLocationOptions.value.length} locations in scope`;
	}
	return `${locationCalendarEvents.value.length} booking${locationCalendarEvents.value.length === 1 ? '' : 's'}`;
});

const groupedLocationCalendarEvents = computed(() => {
	const groups = new Map<string, LocationCalendarEvent[]>();

	for (const event of locationCalendarEvents.value) {
		const dateKey = extractDateKey(event.start);
		const bucket = groups.get(dateKey) || [];
		bucket.push(event);
		groups.set(dateKey, bucket);
	}

	return Array.from(groups.entries())
		.sort(([left], [right]) => left.localeCompare(right))
		.map(([dateKey, events]) => ({
			date: dateKey,
			label: formatDateKeyLabel(dateKey),
			events: [...events].sort((left, right) => left.start.localeCompare(right.start)),
		}));
});

const kpiItems = computed(() => [
	{
		id: 'free_rooms',
		label: 'Free Rooms (last search)',
		value: freeRooms.value.length,
	},
	{
		id: 'total_rooms',
		label: 'Rooms in Scope',
		value: Array.isArray(timeUtilResource.data?.rooms) ? timeRooms.value.length : '—',
	},
	{
		id: 'avg_util',
		label: 'Average Utilization',
		value: avgUtilizationLabel.value,
	},
	{
		id: 'over_cap',
		label: 'Over-Cap Rooms',
		value: overCapRooms.value,
	},
]);

function minutesToHours(minutes: number) {
	const hours = minutes / 60;
	return `${hours.toFixed(1)}h`;
}

function formatPct(value?: number | null) {
	if (value === null || value === undefined) return '—';
	return `${value.toFixed(1)}%`;
}

function utilizationBadge(value: number) {
	if (value >= 70) {
		return 'bg-[rgb(var(--flame-rgb)/0.12)] text-[rgb(var(--flame-rgb))]';
	}
	if (value >= 40) {
		return 'bg-[rgb(var(--jacaranda-rgb)/0.12)] text-[rgb(var(--jacaranda-rgb))]';
	}
	return 'bg-[rgb(var(--canopy-rgb)/0.08)] text-[rgb(var(--canopy-rgb))]';
}

function overCapBadge(count: number) {
	if (count > 0) {
		return 'bg-[rgb(var(--flame-rgb)/0.12)] text-[rgb(var(--flame-rgb))]';
	}
	return 'bg-[rgb(var(--canopy-rgb)/0.08)] text-[rgb(var(--canopy-rgb))]';
}

function eventTimeLabel(start: string, end: string) {
	return `${extractTimeValue(start)} - ${extractTimeValue(end)}`;
}

async function loadFreeRooms() {
	await freeRoomsResource.submit({
		filters: {
			school: selectedSchool.value,
			date: availabilityFilters.value.date,
			start_time: availabilityFilters.value.start_time,
			end_time: availabilityFilters.value.end_time,
			location_type: selectedLocationType.value || null,
			capacity_needed: availabilityFilters.value.capacity_needed,
		},
	});
}

async function loadTimeUtil() {
	if (!canViewAnalytics.value) return;
	if (!selectedSchool.value || !timeUtilFilters.value.from_date || !timeUtilFilters.value.to_date)
		return;
	await timeUtilResource.submit({
		filters: {
			school: selectedSchool.value,
			from_date: timeUtilFilters.value.from_date,
			to_date: timeUtilFilters.value.to_date,
			day_start_time: timeUtilFilters.value.day_start_time,
			day_end_time: timeUtilFilters.value.day_end_time,
			include_non_instructional_days: timeUtilFilters.value.include_non_instructional_days ? 1 : 0,
			location_type: selectedLocationType.value || null,
		},
	});
}

async function loadCapacityUtil() {
	if (!canViewAnalytics.value) return;
	if (!selectedSchool.value || !capacityFilters.value.from_date || !capacityFilters.value.to_date)
		return;
	await capacityResource.submit({
		filters: {
			school: selectedSchool.value,
			from_date: capacityFilters.value.from_date,
			to_date: capacityFilters.value.to_date,
			location_type: selectedLocationType.value || null,
		},
	});
}

let timeDebounce: number | undefined;
let capacityDebounce: number | undefined;
let locationCalendarDebounce: number | undefined;

function debounceTimeUtil() {
	if (!canViewAnalytics.value) return;
	window.clearTimeout(timeDebounce);
	timeDebounce = window.setTimeout(() => {
		loadTimeUtil();
	}, 400);
}

function debounceCapacityUtil() {
	if (!canViewAnalytics.value) return;
	window.clearTimeout(capacityDebounce);
	capacityDebounce = window.setTimeout(() => {
		loadCapacityUtil();
	}, 400);
}

async function loadLocationCalendar() {
	if (!selectedSchool.value) return;
	if (!locationCalendarFilters.value.from_date || !locationCalendarFilters.value.to_date) return;
	await locationCalendarResource.submit({
		filters: {
			school: selectedSchool.value,
			from_date: locationCalendarFilters.value.from_date,
			to_date: locationCalendarFilters.value.to_date,
			location: locationCalendarFilters.value.location || null,
		},
	});
}

function debounceLocationCalendar() {
	window.clearTimeout(locationCalendarDebounce);
	locationCalendarDebounce = window.setTimeout(() => {
		void loadLocationCalendar();
	}, 350);
}

watch(
	() => [
		selectedSchool.value,
		selectedLocationType.value,
		timeUtilFilters.value.from_date,
		timeUtilFilters.value.to_date,
		timeUtilFilters.value.day_start_time,
		timeUtilFilters.value.day_end_time,
		timeUtilFilters.value.include_non_instructional_days,
	],
	() => {
		if (!canViewAnalytics.value) return;
		debounceTimeUtil();
	}
);

watch(
	() => [
		selectedSchool.value,
		selectedLocationType.value,
		capacityFilters.value.from_date,
		capacityFilters.value.to_date,
	],
	() => {
		if (!canViewAnalytics.value) return;
		debounceCapacityUtil();
	}
);

watch(
	() => [timeUtilFilters.value.from_date, timeUtilFilters.value.to_date],
	([fromDate, toDate]) => {
		capacityFilters.value.from_date = fromDate;
		capacityFilters.value.to_date = toDate;
	},
	{ immediate: true }
);

watch(
	() => [
		selectedSchool.value,
		locationCalendarFilters.value.from_date,
		locationCalendarFilters.value.to_date,
		locationCalendarFilters.value.location,
	],
	() => {
		if (!selectedSchool.value) return;
		debounceLocationCalendar();
	},
	{ immediate: true }
);

watch(
	() => selectedSchool.value,
	(nextSchool, previousSchool) => {
		if (nextSchool === previousSchool) return;
		locationCalendarFilters.value.location = '';
	}
);

watch(
	() => locationCalendarLocationOptions.value,
	optionsList => {
		const allowed = new Set(optionsList.map(option => option.value));
		if (
			locationCalendarFilters.value.location &&
			!allowed.has(locationCalendarFilters.value.location)
		) {
			locationCalendarFilters.value.location = '';
		}
	},
	{ deep: true }
);

function refreshMetrics() {
	if (!canViewAnalytics.value) return;
	loadTimeUtil();
	loadCapacityUtil();
}

async function loadAnalyticsAccess() {
	const result = await analyticsAccessResource.submit();
	const allowed = result?.allowed ?? analyticsAccessResource.data?.allowed ?? 0;
	canViewAnalytics.value = Boolean(allowed);
}

async function loadRoomUtilizationCapabilities() {
	try {
		await staffHomeHeaderResource.submit({});
	} catch (error) {
		console.error('[RoomUtilization] Failed to load event quick create capabilities:', error);
	}
}

function openCreateEvent() {
	if (!canOpenCreateEvent.value) return;

	const lockEventType = canCreateMeeting.value !== canCreateSchoolEvent.value;
	const eventType = canCreateMeeting.value ? 'meeting' : 'school_event';

	overlay.open('event-quick-create', {
		eventType: lockEventType ? eventType : null,
		lockEventType,
		meetingMode: 'ad_hoc',
		prefillSchool: selectedSchool.value || null,
	});
}

onMounted(async () => {
	await Promise.all([loadAnalyticsAccess(), loadRoomUtilizationCapabilities()]);
	refreshMetrics();
});
</script>
