<!-- ifitwala_ed/ui-spa/src/pages/staff/MorningBriefing.vue -->
<template>
	<div class="min-h-screen bg-transparent p-4 sm:p-6 space-y-8">
		<!-- HEADER -->
		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="type-h1">Morning Briefing</h1>
				<p class="type-meta mt-1 text-slate-token/80">Daily Operational &amp; Academic Pulse</p>
			</div>

			<div class="flex items-center gap-3">
				<div class="text-right">
					<span class="section-header block mb-0.5">Today</span>
					<span class="type-h3 text-ink">
						{{ formattedDate }}
					</span>
				</div>
				<button @click="widgets.reload()" class="remark-btn ml-2 flex items-center justify-center">
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
			<div class="h-32 w-full rounded-2xl bg-surface-soft"></div>
			<div class="grid grid-cols-2 gap-6">
				<div class="h-64 rounded-2xl bg-surface-soft"></div>
				<div class="h-64 rounded-2xl bg-surface-soft"></div>
			</div>
		</div>

		<!-- CONTENT -->
		<div v-else class="space-y-8">
			<!-- ANNOUNCEMENTS -->
			<section v-if="hasArrayData('announcements')" class="space-y-3">
				<!-- Header strip -->
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex items-center gap-2">
						<h2 class="section-header text-slate-token/80">Organizational Announcements</h2>
						<span
							class="inline-flex items-center rounded-full bg-surface-soft px-2 py-0.5 text-[10px] font-medium text-slate-token/80"
						>
							{{ widgets.data.announcements.length }} today
						</span>
					</div>

					<div class="flex items-center gap-2">
						<button
							v-for="mode in viewModes"
							:key="mode.value"
							class="rounded-full border px-3 py-1 text-xs font-semibold transition-all"
							:class="
								viewMode === mode.value
									? 'border-jacaranda bg-jacaranda/5 text-jacaranda shadow-sm'
									: 'border-border/60 text-slate-token/80 hover:bg-surface-soft'
							"
							@click="viewMode = mode.value"
						>
							{{ mode.label }}
						</button>

						<div class="hidden items-center gap-2 text-[11px] text-slate-token/70 sm:flex">
							<span class="inline-flex items-center gap-1">
								<span class="h-2 w-2 rounded-full bg-flame"></span>
								{{ criticalCount }} Critical
							</span>
							<span class="inline-flex items-center gap-1">
								<span class="h-2 w-2 rounded-full bg-jacaranda"></span>
								{{ highCount }} High
							</span>
						</div>
					</div>
				</div>

				<!-- Spotlight -->
				<div
					v-if="spotlightAnnouncements.length"
					class="relative overflow-hidden rounded-2xl bg-surface-soft/80 p-5 ring-1 ring-border/60"
				>
					<div class="flex items-start justify-between gap-4">
						<div v-if="currentSpotlight" class="flex-1">
							<div class="mb-2 flex flex-wrap items-center gap-2">
								<span
									class="inline-flex items-center gap-1 rounded-md bg-surface-soft px-2 py-1 text-[11px] font-semibold text-slate-token/80"
								>
									{{ currentSpotlight.type }}
								</span>
								<span
									v-if="currentSpotlight.priority === 'Critical'"
									class="inline-flex items-center gap-1 rounded-md bg-flame/10 px-2 py-1 text-[11px] font-semibold text-flame"
								>
									Critical
								</span>
								<span
									v-else-if="currentSpotlight.priority === 'High'"
									class="inline-flex items-center gap-1 rounded-md bg-jacaranda/10 px-2 py-1 text-[11px] font-semibold text-jacaranda"
								>
									High priority
								</span>
							</div>

							<h3 class="mb-2 type-h3 text-ink">
								{{ currentSpotlight.title }}
							</h3>

							<div
								class="prose prose-sm max-w-none text-slate-token/85 line-clamp-3"
								v-html="currentSpotlight.content"
							></div>

							<button
								@click="openAnnouncement(currentSpotlight)"
								class="mt-3 flex items-center gap-1 type-button-label text-jacaranda hover:text-jacaranda/80"
							>
								Read full announcement
								<FeatherIcon name="arrow-right" class="h-4 w-4" />
							</button>

							<!-- Interaction strip for spotlight (staff comments mode only) -->
							<div
								v-if="canShowInteractions(currentSpotlight)"
								class="mt-3 flex items-center justify-between border-t border-border/40 pt-2 text-[11px] text-slate-token/70"
							>
								<div class="flex items-center gap-3">
									<button
										type="button"
										class="inline-flex items-center gap-1 rounded-full bg-surface-soft px-2 py-1 hover:bg-surface-soft/80"
										@click.stop="acknowledgeAnnouncement(currentSpotlight)"
									>
										<FeatherIcon name="thumbs-up" class="h-3 w-3 text-canopy" />
										<span>
											Reactions
											<span class="ml-1 text-[10px] text-slate-token/60">
												({{ getInteractionStatsFor(currentSpotlight).reactions_total }})
											</span>
										</span>
									</button>

									<button
										type="button"
										class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-slate-token/70 hover:bg-surface-soft"
										@click.stop="openInteractionThread(currentSpotlight)"
									>
										<FeatherIcon name="message-circle" class="h-3 w-3" />
										<span>Comments</span>
										<span class="text-[10px] text-slate-token/60">
											({{ getInteractionStatsFor(currentSpotlight).comments_total }})
										</span>
									</button>
								</div>

								<div
									v-if="getInteractionFor(currentSpotlight).self"
									class="hidden text-[10px] text-jacaranda md:block"
								>
									You responded:
									{{ getInteractionFor(currentSpotlight).self.intent_type || 'Commented' }}
								</div>
							</div>
						</div>

						<div v-if="spotlightAnnouncements.length > 1" class="flex flex-col items-center gap-2">
							<button
								class="rounded-full p-1 text-slate-token/60 transition-colors hover:bg-surface-soft hover:text-ink"
								@click="prevSpotlight"
							>
								<FeatherIcon name="chevron-up" class="h-4 w-4" />
							</button>
							<div class="flex flex-col gap-1">
								<span
									v-for="(a, idx) in spotlightAnnouncements"
									:key="idx"
									class="h-1.5 w-1.5 rounded-full"
									:class="idx === spotlightIndex ? 'bg-jacaranda' : 'bg-border'"
								></span>
							</div>
							<button
								class="rounded-full p-1 text-slate-token/60 transition-colors hover:bg-surface-soft hover:text-ink"
								@click="nextSpotlight"
							>
								<FeatherIcon name="chevron-down" class="h-4 w-4" />
							</button>
						</div>
					</div>
				</div>

				<!-- Compact list -->
				<div class="paper-card mt-3">
					<div class="flex items-center justify-between border-b border-border/60 px-4 py-2">
						<p class="text-xs font-semibold uppercase tracking-wide text-slate-token/70">
							All announcements
						</p>
						<button
							v-if="widgets.data.announcements.length > MAX_INLINE_ANNOUNCEMENTS"
							class="text-[11px] font-medium text-jacaranda hover:text-jacaranda/80"
							@click="openAnnouncementsDialog"
						>
							Open announcement center
						</button>
					</div>

					<div class="divide-y divide-border/40">
						<button
							v-for="(item, idx) in limitedAnnouncements"
							:key="idx"
							class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-soft"
							@click="openAnnouncement(item)"
						>
							<div
								class="mt-1 h-2 w-2 flex-shrink-0 rounded-full"
								:class="
									item.priority === 'Critical'
										? 'bg-flame'
										: item.priority === 'High'
											? 'bg-jacaranda'
											: 'bg-border'
								"
							></div>

							<div class="min-w-0 flex-1">
								<div class="flex items-center justify-between gap-2">
									<p class="truncate text-sm font-semibold text-ink">
										{{ item.title }}
									</p>
									<span class="text-[10px] uppercase text-slate-token/60">
										{{ item.type }}
									</span>
								</div>
								<p
									class="mt-1 text-xs text-slate-token/80 line-clamp-4 md:line-clamp-5"
									v-html="item.content"
								></p>

								<!-- Interaction summary for each announcement (staff comments only) -->
								<div
									v-if="canShowInteractions(item)"
									class="mt-2 flex items-center justify-between text-[10px] text-slate-token/65"
								>
									<div class="flex items-center gap-2">
										<button
											type="button"
											class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 hover:bg-surface-soft"
											@click.stop="acknowledgeAnnouncement(item)"
										>
											<FeatherIcon name="thumbs-up" class="h-3 w-3 text-canopy" />
											<span>{{ getInteractionStatsFor(item).reactions_total }}</span>
										</button>

										<button
											type="button"
											class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 hover:bg-surface-soft"
											@click.stop="openInteractionThread(item)"
										>
											<FeatherIcon name="message-circle" class="h-3 w-3" />
											<span>Comments</span>
											<span>({{ getInteractionStatsFor(item).comments_total }})</span>
										</button>
									</div>

									<span
										v-if="getInteractionFor(item).self"
										class="ml-2 text-[10px] text-jacaranda"
									>
										You responded
									</span>
								</div>
							</div>
						</button>
					</div>
				</div>
			</section>

			<div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
				<!-- LEFT COLUMN -->
				<div class="space-y-6">
					<div
						v-if="hasArrayData('clinic_volume') || widgets.data?.critical_incidents !== undefined"
						class="grid grid-cols-2 gap-6"
					>
						<!-- Attendance Trend (Admin) -->
						<div v-if="hasArrayData('attendance_trend')" class="col-span-2">
							<AttendanceTrend :data="widgets.data.attendance_trend" />
						</div>

						<!-- Critical Incidents card -->
						<div
							v-if="widgets.data?.critical_incidents !== undefined"
							class="paper-card cursor-pointer border-l-4 border-l-flame p-5 transition-shadow hover:shadow-md"
							@click="openCriticalIncidents"
						>
							<h3 class="section-header mb-1 text-flame/80">Critical Incidents</h3>
							<div class="text-3xl font-bold text-ink">
								{{ widgets.data.critical_incidents }}
							</div>
							<p class="mt-1 flex items-center gap-1 text-xs font-medium text-flame">
								<FeatherIcon name="alert-circle" class="h-3 w-3" />
								Open Follow-ups
							</p>
						</div>

						<!-- Clinic Volume -->
						<div
							v-if="hasArrayData('clinic_volume')"
							class="paper-card cursor-pointer p-5 transition-shadow hover:shadow-md"
							@click="showClinicHistory = true"
						>
							<div class="mb-3 flex items-center gap-2">
								<div
									class="flex h-8 w-8 items-center justify-center rounded-full bg-sky/15 text-sky"
								>
									<FeatherIcon name="thermometer" class="h-4 w-4" />
								</div>
								<h3 class="text-sm font-semibold text-canopy">Clinic Volume</h3>
							</div>
							<div class="space-y-2">
								<div
									v-for="day in widgets.data.clinic_volume"
									:key="day.date"
									class="flex items-center justify-between text-sm"
								>
									<span class="text-slate-token/80">
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
									class="flex h-8 w-8 items-center justify-center rounded-full bg-jacaranda/10 text-jacaranda"
								>
									<FeatherIcon name="users" class="h-4 w-4" />
								</div>
								<h3 class="text-sm font-semibold text-canopy">Admissions (Last 7 Days)</h3>
							</div>
							<span class="text-2xl font-bold text-ink">
								{{ widgets.data.admissions_pulse.total_new_weekly }}
							</span>
						</div>
						<div class="flex flex-wrap gap-2">
							<div
								v-for="stat in widgets.data.admissions_pulse.breakdown"
								:key="stat.application_status"
								class="inline-chip border border-border/40 bg-surface-soft text-slate-token/90"
							>
								{{ stat.application_status }}: {{ stat.count }}
							</div>
						</div>
					</div>

					<!-- Absent Student List (Instructor) -->
					<div v-if="hasArrayData('my_absent_students')">
						<AbsentStudentList :students="widgets.data.my_absent_students" />
					</div>
				</div>

				<!-- RIGHT COLUMN: RECENT LOGS -->
				<div v-if="hasArrayData('student_logs')">
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
								class="group border-b border-border/50 p-5 last:border-0 transition-colors hover:bg-surface-soft"
							>
								<div class="flex gap-4">
									<div class="relative flex-shrink-0">
										<div class="h-12 w-12 overflow-hidden rounded-xl bg-surface-soft">
											<img
												v-if="log.student_image"
												:src="log.student_image"
												class="h-full w-full object-cover"
											/>
											<div
												v-else
												class="flex h-full w-full items-center justify-center text-xs font-bold text-slate-token/75"
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
											<span class="text-[10px] text-slate-token/65">
												{{ log.date_display }}
											</span>
										</div>

										<div class="mt-1 mb-2 flex items-center gap-2">
											<span
												class="rounded bg-surface-soft px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-token/80"
											>
												{{ log.log_type }}
											</span>
										</div>

										<p class="mb-2 text-xs leading-relaxed text-slate-token/90">
											{{ log.snippet }}
										</p>

										<button
											@click="openLog(log)"
											class="mt-1 flex items-center gap-1 text-[11px] font-medium text-jacaranda transition-colors hover:text-jacaranda/80"
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

			<!-- COMMUNITY PULSE: BIRTHDAYS -->
			<section v-if="hasArrayData('staff_birthdays') || hasArrayData('my_student_birthdays')">
				<div class="border-t border-border/60 pt-6">
					<!-- Section header -->
					<div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
						<div>
							<h2 class="section-header flex items-center gap-2 text-slate-token/70">
								<FeatherIcon name="gift" class="h-3 w-3" />
								Community Pulse
							</h2>
							<p class="type-meta mt-0.5 text-slate-token/80">
								Birthdays from our staff and your groups this week
							</p>
						</div>
						<span class="text-xs font-medium italic text-jacaranda">
							Small moments that keep the community connected 🎂
						</span>
					</div>

					<!-- Card with two columns -->
					<div class="paper-card p-5">
						<div class="grid gap-6 md:grid-cols-2">
							<!-- Staff birthdays -->
							<div v-if="hasArrayData('staff_birthdays')" class="space-y-3">
								<div class="flex items-center justify-between">
									<h3 class="text-xs font-semibold uppercase tracking-wide text-slate-token/70">
										Staff Birthdays
									</h3>
									<span
										class="inline-flex items-center rounded-full bg-surface-soft px-2 py-0.5 text-[10px] font-medium text-slate-token/70"
									>
										{{ widgets.data.staff_birthdays.length }} this week
									</span>
								</div>

								<ul class="space-y-2">
									<li
										v-for="emp in widgets.data.staff_birthdays"
										:key="emp.name"
										class="flex items-center gap-3 rounded-xl bg-surface-soft/60 px-3 py-2"
									>
										<div
											class="h-9 w-9 overflow-hidden rounded-full bg-white shadow-[var(--shadow-soft)]"
										>
											<img v-if="emp.image" :src="emp.image" class="h-full w-full object-cover" />
											<div
												v-else
												class="flex h-full w-full items-center justify-center text-xs font-semibold text-slate-token/70"
											>
												{{ emp.name.substring(0, 1) }}
											</div>
										</div>
										<div class="min-w-0 flex-1">
											<p class="truncate text-sm font-semibold text-ink">
												{{ emp.name }}
											</p>
											<p class="text-[11px] font-medium uppercase tracking-wide text-flame">
												{{ formatBirthday(emp.date_of_birth) }}
											</p>
										</div>
									</li>
								</ul>
							</div>

							<!-- Student birthdays (my groups) -->
							<div v-if="hasArrayData('my_student_birthdays')" class="space-y-3">
								<div class="flex items-center justify-between">
									<h3 class="text-xs font-semibold uppercase tracking-wide text-slate-token/70">
										Student Birthdays (My Groups)
									</h3>
									<span
										class="inline-flex items-center rounded-full bg-surface-soft px-2 py-0.5 text-[10px] font-medium text-slate-token/70"
									>
										{{ widgets.data.my_student_birthdays.length }} this week
									</span>
								</div>

								<ul class="space-y-2">
									<li
										v-for="stu in widgets.data.my_student_birthdays"
										:key="stu.first_name + stu.last_name"
										class="flex items-center gap-3 rounded-xl bg-surface-soft/60 px-3 py-2"
									>
										<div
											class="h-9 w-9 overflow-hidden rounded-full bg-white shadow-[var(--shadow-soft)]"
										>
											<img v-if="stu.image" :src="stu.image" class="h-full w-full object-cover" />
											<div
												v-else
												class="flex h-full w-full items-center justify-center text-xs font-semibold text-slate-token/70"
											>
												{{ stu.first_name.substring(0, 1) }}
											</div>
										</div>
										<div class="min-w-0 flex-1">
											<p class="truncate text-sm font-semibold text-ink">
												{{ stu.first_name }} {{ stu.last_name }}
											</p>
											<p class="text-[11px] font-medium uppercase tracking-wide text-flame">
												{{ formatBirthday(stu.date_of_birth) }}
											</p>
										</div>
									</li>
								</ul>
							</div>
						</div>

						<!-- Empty-state text if only one side exists -->
						<p
							v-if="hasArrayData('staff_birthdays') && !hasArrayData('my_student_birthdays')"
							class="mt-4 text-[11px] text-slate-token/70"
						>
							No student birthdays in your groups for this window.
						</p>
						<p
							v-else-if="hasArrayData('my_student_birthdays') && !hasArrayData('staff_birthdays')"
							class="mt-4 text-[11px] text-slate-token/70"
						>
							No staff birthdays in this window.
						</p>
					</div>
				</div>
			</section>
		</div>

		<!-- CONTENT DIALOG -->
		<ContentDialog
			v-model="isContentDialogOpen"
			:subtitle="dialogContent.subtitle"
			:content="dialogContent.content"
			:image="dialogContent.image"
			:image-fallback="dialogContent.imageFallback"
			:badge="dialogContent.badge"
			:show-interactions="showInteractionsForActive"
			:interaction="
				activeCommunication ? getInteractionFor(activeCommunication) : { counts: {}, self: null }
			"
			@acknowledge="activeCommunication && acknowledgeAnnouncement(activeCommunication)"
			@open-comments="activeCommunication && openInteractionThread(activeCommunication)"
			@react="activeCommunication && reactToAnnouncement(activeCommunication, $event)"
		/>

		<!-- ANNOUNCEMENT CENTER DIALOG -->
		<GenericListDialog
			v-model="showAnnouncementCenter"
			title="Announcement Center"
			subtitle="Full list of announcements"
			:items="widgets.data?.announcements || []"
		>
			<template #item="{ item }">
				<div class="flex gap-3 p-4">
					<div
						class="mt-1 h-2.5 w-2.5 flex-shrink-0 rounded-full"
						:class="
							item.priority === 'Critical'
								? 'bg-flame ring-2 ring-flame/30'
								: item.priority === 'High'
									? 'bg-jacaranda ring-2 ring-jacaranda/30'
									: 'bg-border'
						"
					></div>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between gap-2">
							<div class="flex flex-wrap items-center gap-2">
								<p class="text-sm font-semibold text-ink">
									{{ item.title }}
								</p>
								<span
									class="inline-flex items-center rounded-full bg-surface-soft px-2 py-0.5 text-[11px] font-semibold text-slate-token/80"
								>
									{{ item.type }}
								</span>
								<span
									class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
									:class="getPriorityClasses(item.priority)"
								>
									{{ item.priority || 'Info' }}
								</span>
							</div>
							<button
								class="text-[11px] font-medium text-jacaranda transition-colors hover:text-jacaranda/80"
								@click="openAnnouncement(item)"
							>
								Open
							</button>
						</div>
						<div class="mt-1 text-xs text-slate-token/80 line-clamp-3" v-html="item.content"></div>
					</div>
				</div>
			</template>
		</GenericListDialog>

		<!-- CRITICAL INCIDENTS DIALOG -->
		<GenericListDialog
			v-model="showCriticalIncidents"
			title="Critical Incidents"
			subtitle="Open logs requiring follow-up"
			:items="criticalIncidentsList.data || []"
			:loading="criticalIncidentsList.loading"
		>
			<template #item="{ item }">
				<div class="flex gap-4 p-4">
					<div class="h-10 w-10 shrink-0 overflow-hidden rounded-full bg-surface-soft">
						<img
							v-if="item.student_image"
							:src="item.student_image"
							class="h-full w-full object-cover"
						/>
						<div
							v-else
							class="flex h-full w-full items-center justify-center text-xs font-bold text-slate-token/65"
						>
							{{ item.student_name.substring(0, 2) }}
						</div>
					</div>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between">
							<h4 class="text-sm font-bold text-ink">
								{{ item.student_name }}
							</h4>
							<span class="text-xs text-slate-token/80">
								{{ item.date_display }}
							</span>
						</div>
						<span
							class="mt-1 mb-2 inline-block rounded bg-surface-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-token/80"
						>
							{{ item.log_type }}
						</span>
						<p class="text-sm text-slate-token/90 line-clamp-2">
							{{ item.snippet }}
						</p>
						<button
							@click="openLog(item)"
							class="mt-2 text-xs font-medium text-jacaranda hover:text-jacaranda/80"
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

		<CommentThreadDrawer
			:open="showInteractionDrawer"
			title="Announcement Comments"
			:rows="interactionThread.data || []"
			:loading="interactionThread.loading"
			v-model:comment="newComment"
			submit-label="Send"
			placeholder="Add a short comment (max 300 characters)"
			:format-timestamp="formatThreadTimestamp"
			@close="showInteractionDrawer = false"
			@submit="submitComment"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { createResource, FeatherIcon, call, toast } from 'frappe-ui';
import ContentDialog from '@/components/ContentDialog.vue';
import GenericListDialog from '@/components/analytics/GenericListDialog.vue';
import HistoryDialog from '@/components/analytics/HistoryDialog.vue';
import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue';
import AttendanceTrend from './components/AttendanceTrend.vue';
import AbsentStudentList from './components/AbsentStudentList.vue';
import {
	ORG_SURFACES,
	type Announcement,
	type WidgetsPayload,
	type InteractionSummaryMap,
	type InteractionThreadRow,
	type StudentLogItem,
	type OrgPriority,
	type StudentLogDetail,
} from '@/types/morning_brief';
import type {
	InteractionSummary,
	InteractionIntentType,
	ReactionCode,
} from '@/types/morning_brief';
import { canShowPublicInteractions } from '@/utils/orgCommunication';
import type { OrgCommunicationListItem } from '@/types/orgCommunication';
import { getInteractionStats } from '@/utils/interactionStats';

interface DialogContent {
	title: string;
	subtitle: string;
	content: string;
	image: string;
	imageFallback: string;
	badge: string;
}

type ArrayWidgetKey =
	| 'announcements'
	| 'staff_birthdays'
	| 'clinic_volume'
	| 'my_student_birthdays'
	| 'student_logs'
	| 'attendance_trend'
	| 'my_absent_students';

// State for Dialog
const isContentDialogOpen = ref<boolean>(false);
const dialogContent = ref<DialogContent>({
	title: '',
	subtitle: '',
	content: '',
	image: '',
	imageFallback: '',
	badge: '',
});

// State for new dialogs
const showAnnouncementCenter = ref<boolean>(false);
const showCriticalIncidents = ref<boolean>(false);
const showClinicHistory = ref<boolean>(false);
const showInteractionDrawer = ref<boolean>(false);
const activeCommunication = ref<Announcement | null>(null);
const showInteractionsForActive = computed(() => canShowInteractions(activeCommunication.value));
const newComment = ref<string>('');

const criticalIncidentsList = createResource<StudentLogDetail[]>({
	url: 'ifitwala_ed.api.morning_brief.get_critical_incidents_details',
	auto: false,
});

const widgets = createResource<WidgetsPayload>({
	url: 'ifitwala_ed.api.morning_brief.get_briefing_widgets',
	auto: true,
});

const interactionSummary = createResource<InteractionSummaryMap>({
	url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_org_comm_interaction_summary',
	method: 'POST',
	auto: false,
});

const interactionThread = createResource<InteractionThreadRow[]>({
	url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_communication_thread',
	method: 'POST',
	auto: false,
});

const viewModes = [
	{ value: 'focus', label: 'Focus' },
	{ value: 'all', label: 'All' },
] as const;
type ViewMode = (typeof viewModes)[number]['value'];
const MAX_INLINE_ANNOUNCEMENTS = 5;
const viewMode = ref<ViewMode>('all');
const spotlightIndex = ref(0);
const spotlightAnnouncements = computed<Announcement[]>(() =>
	(widgets.data?.announcements || []).filter(a => ['Critical', 'High'].includes(a.priority ?? ''))
);
const currentSpotlight = computed<Announcement | null>(
	() => spotlightAnnouncements.value[spotlightIndex.value] || null
);

watch(spotlightAnnouncements, (list: Announcement[]) => {
	if (!list.length) {
		spotlightIndex.value = 0;
		return;
	}
	if (spotlightIndex.value >= list.length) {
		spotlightIndex.value = 0;
	}
});

const criticalCount = computed(
	() => (widgets.data?.announcements || []).filter(a => a.priority === 'Critical').length
);
const highCount = computed(
	() => (widgets.data?.announcements || []).filter(a => a.priority === 'High').length
);

const filteredAnnouncements = computed<Announcement[]>(() => {
	const all = widgets.data?.announcements || [];

	if (viewMode.value === 'focus') {
		return all.filter(a => a.priority === 'Critical' || a.priority === 'High');
	}

	return all;
});

const limitedAnnouncements = computed<Announcement[]>(() => filteredAnnouncements.value);

// Adapter because the shared helper is typed for org communication list items
function canShowInteractions(item: Announcement | null | undefined): boolean {
	return canShowPublicInteractions(item as unknown as OrgCommunicationListItem | null | undefined);
}

watch(
	() => widgets.data?.announcements,
	(list: Announcement[] | undefined) => {
		if (!list || !list.length) return;

		const comm_names = list.map(a => a.name).filter(Boolean);
		if (!comm_names.length) return;

		interactionSummary.submit({ comm_names });
	},
	{ immediate: true }
);

function nextSpotlight(): void {
	if (!spotlightAnnouncements.value.length) return;
	spotlightIndex.value = (spotlightIndex.value + 1) % spotlightAnnouncements.value.length;
}

function prevSpotlight(): void {
	if (!spotlightAnnouncements.value.length) return;
	spotlightIndex.value =
		(spotlightIndex.value - 1 + spotlightAnnouncements.value.length) %
		spotlightAnnouncements.value.length;
}

function hasArrayData(key: ArrayWidgetKey): boolean {
	const list = widgets.data?.[key];
	return Array.isArray(list) && list.length > 0;
}

function openLog(log: StudentLogItem): void {
	activeCommunication.value = null;
	dialogContent.value = {
		title: log.student_name,
		subtitle: log.date_display,
		content: log.full_content,
		image: log.student_image || '',
		imageFallback: log.student_name.substring(0, 2),
		badge: log.log_type,
	};
	isContentDialogOpen.value = true;
}

function openAnnouncement(news: Announcement): void {
	activeCommunication.value = news;
	dialogContent.value = {
		title: news.title,
		subtitle: formattedDate.value,
		content: news.content,
		image: '',
		imageFallback: '',
		badge: news.type,
	};
	isContentDialogOpen.value = true;
}

function getInteractionFor(item: Announcement): InteractionSummary {
	const summary = interactionSummary.data?.[item.name];
	if (!summary) {
		return {
			counts: {},
			self: null,
		};
	}
	return summary;
}

function getInteractionStatsFor(item: Announcement) {
	return getInteractionStats(getInteractionFor(item));
}

function openInteractionThread(item: Announcement): void {
	if (!canShowInteractions(item)) {
		toast.create({
			appearance: 'warning',
			message: 'Comments are disabled for this announcement.',
		});
		return;
	}
	activeCommunication.value = item;
	showInteractionDrawer.value = true;

	interactionThread.submit({
		org_communication: item.name,
		limit_start: 0,
		limit_page_length: 30,
	});
}

function formatThreadTimestamp(value?: string | null): string {
	if (!value) return '';
	const d = new Date(value);
	if (isNaN(d.getTime())) return value;

	return d.toLocaleDateString('en-GB', {
		day: '2-digit',
		month: 'short',
		hour: '2-digit',
		minute: '2-digit',
		hour12: false,
	});
}

function acknowledgeAnnouncement(item: Announcement): void {
	if (!item?.name || !canShowInteractions(item)) return;

	call(
		'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.upsert_communication_interaction',
		{
			org_communication: item.name,
			intent_type: 'Acknowledged',
			surface: ORG_SURFACES.MORNING_BRIEF,
		}
	).then(() => {
		const list = widgets.data?.announcements || [];
		const comm_names = list.map(a => a.name).filter(Boolean);
		if (comm_names.length) {
			interactionSummary.submit({ comm_names });
		}
	});
}

function submitComment(): void {
	if (!activeCommunication.value || !canShowInteractions(activeCommunication.value)) return;
	if (!newComment.value.trim()) return;

	const note = newComment.value.trim();

	call(
		'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.upsert_communication_interaction',
		{
			org_communication: activeCommunication.value.name,
			note,
			intent_type: 'Comment',
			surface: ORG_SURFACES.MORNING_BRIEF,
		}
	).then(() => {
		newComment.value = '';
		interactionThread.submit({
			org_communication: activeCommunication.value.name,
			limit_start: 0,
			limit_page_length: 30,
		});

		const list = widgets.data?.announcements || [];
		const comm_names = list.map(a => a.name).filter(Boolean);
		if (comm_names.length) {
			interactionSummary.submit({ comm_names });
		}
	});
}

function reactToAnnouncement(item: Announcement, reaction: ReactionCode): void {
	if (!item?.name || !canShowInteractions(item)) return;

	if (reaction === 'question') {
		openInteractionThread(item);
		return;
	}

	const reactionIntentMap: Record<ReactionCode, InteractionIntentType> = {
		like: 'Acknowledged',
		thank: 'Appreciated',
		heart: 'Support',
		smile: 'Positive',
		applause: 'Celebration',
		question: 'Question',
		concern: 'Concern',
		other: 'Other',
	};

	const intent_type = reactionIntentMap[reaction] || 'Other';

	call(
		'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.upsert_communication_interaction',
		{
			org_communication: item.name,
			reaction_code: reaction,
			intent_type,
			surface: ORG_SURFACES.MORNING_BRIEF,
		}
	).then(() => {
		const list = widgets.data?.announcements || [];
		const comm_names = list.map(a => a.name).filter(Boolean);
		if (comm_names.length) {
			interactionSummary.submit({ comm_names });
		}
	});
}

function openAnnouncementsDialog(): void {
	showAnnouncementCenter.value = true;
}

function openCriticalIncidents(): void {
	showCriticalIncidents.value = true;
	criticalIncidentsList.fetch();
}

const formattedDate = computed<string>(() => widgets.data?.today_label ?? '');

function getPriorityClasses(priority: OrgPriority): string {
	switch (priority) {
		case 'Critical':
			return 'bg-flame text-white ring-2 ring-flame/30';
		case 'High':
			return 'bg-jacaranda/5 ring-1 ring-jacaranda/30';
		case 'Low':
			return 'bg-surface-soft text-slate-token/80';
		default:
			return 'bg-surface-soft text-ink';
	}
}

function formatBirthday(dateStr: string | null | undefined): string {
	if (!dateStr) return '';

	// Parsed in local time; we only care about day + month, not year
	const date = new Date(dateStr);
	const day = date.getDate();

	// Force Gregorian month names, ignore Thai/Buddhist locale
	const month = date.toLocaleString('en-US', { month: 'long' });

	const suffix = (value: number) => {
		if (value > 3 && value < 21) return 'th';
		switch (value % 10) {
			case 1:
				return 'st';
			case 2:
				return 'nd';
			case 3:
				return 'rd';
			default:
				return 'th';
		}
	};

	return `${day}${suffix(day)} ${month}`;
}
</script>
