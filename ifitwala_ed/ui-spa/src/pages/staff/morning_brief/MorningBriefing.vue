<!-- ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue -->
<template>
	<div class="staff-shell min-w-0 space-y-8">
		<!-- HEADER -->
		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="type-h1">Morning Briefing</h1>
				<p class="type-meta mt-1 text-slate-token/80">Daily Operational &amp; Academic Pulse</p>
			</div>

			<div class="flex items-center gap-3 self-start sm:self-auto">
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
			<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
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

					<div class="flex flex-wrap items-center justify-start gap-2 sm:justify-end">
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
					<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
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
								class="mt-3 flex flex-col gap-2 border-t border-border/40 pt-2 text-[11px] text-slate-token/70 sm:flex-row sm:items-center sm:justify-between"
							>
								<div class="flex flex-wrap items-center gap-2 sm:gap-3">
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

						<div
							v-if="spotlightAnnouncements.length > 1"
							class="flex flex-row items-center justify-start gap-3 lg:flex-col"
						>
							<button
								class="rounded-full p-1 text-slate-token/60 transition-colors hover:bg-surface-soft hover:text-ink"
								@click="prevSpotlight"
							>
								<FeatherIcon name="chevron-up" class="h-4 w-4" />
							</button>
							<div class="flex flex-row gap-1 lg:flex-col">
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
					<div
						class="flex flex-col gap-2 border-b border-border/60 px-4 py-2 sm:flex-row sm:items-center sm:justify-between"
					>
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
								<div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
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
									class="mt-2 flex flex-col gap-2 text-[10px] text-slate-token/65 sm:flex-row sm:items-center sm:justify-between"
								>
									<div class="flex flex-wrap items-center gap-2">
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

			<div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
				<!-- LEFT COLUMN -->
				<div class="space-y-6">
					<div
						v-if="hasClinicVolumeCard || widgets.data?.critical_incidents !== undefined"
						class="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6"
					>
						<!-- Attendance Trend (Admin) -->
						<div v-if="hasArrayData('attendance_trend')" class="sm:col-span-2">
							<AttendanceTrend :data="widgets.data.attendance_trend" />
						</div>

						<!-- Critical Incidents card -->
						<div
							v-if="widgets.data?.critical_incidents !== undefined"
							class="paper-card cursor-pointer border-l-4 border-l-flame p-5 transition-shadow hover:shadow-md"
							@click="openCriticalIncidentsOverlay"
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
							v-if="hasClinicVolumeCard"
							class="paper-card p-5 transition-shadow"
							:class="clinicVolumeIsInteractive ? 'cursor-pointer hover:shadow-md' : ''"
							@click="openClinicHistory"
						>
							<div class="mb-3 flex items-start justify-between gap-3">
								<div class="flex items-center gap-2">
									<div
										class="flex h-8 w-8 items-center justify-center rounded-full bg-sky/15 text-sky"
									>
										<FeatherIcon name="thermometer" class="h-4 w-4" />
									</div>
									<div>
										<h3 class="text-sm font-semibold text-canopy">Clinic Volume</h3>
										<p class="mt-0.5 text-[11px] text-slate-token/70">
											{{ clinicVolume?.school || 'School context' }}
										</p>
									</div>
								</div>
								<DateRangePills
									v-if="!clinicVolume?.error"
									v-model="clinicVolumeView"
									:items="clinicVolumeViewOptions"
									size="sm"
									wrap-class="bg-white/70"
									@click.stop
								/>
							</div>
							<p
								v-if="clinicVolume?.error"
								class="rounded-xl border border-dashed border-border/70 bg-surface-soft px-3 py-2 text-xs text-slate-token/82"
							>
								{{ clinicVolume.error }}
							</p>
							<div v-else-if="clinicVolumePoints.length" class="space-y-2">
								<div
									v-for="point in clinicVolumePoints"
									:key="point.label"
									class="flex items-center justify-between text-sm"
								>
									<span class="text-slate-token/80">
										{{ point.label }}
									</span>
									<span
										class="font-mono font-medium"
										:class="point.count > 10 ? 'text-flame' : 'text-ink'"
									>
										{{ point.count }}
									</span>
								</div>
							</div>
							<p v-else class="text-xs text-slate-token/75">
								No clinic visits in this business window.
							</p>
						</div>
					</div>

					<!-- Admissions pulse -->
					<div v-if="widgets.data?.admissions_pulse" class="paper-card p-5">
						<div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
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

					<div
						class="paper-card relative flex min-h-[24rem] max-h-[65vh] flex-col md:h-[600px] md:max-h-none"
					>
						<div class="custom-scrollbar flex-1 overflow-y-auto p-0">
							<div
								v-for="(log, i) in widgets.data.student_logs"
								:key="log.name"
								class="group border-b border-border/50 p-4 last:border-0 transition-colors hover:bg-surface-soft sm:p-5"
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
										<div class="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
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
								<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
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
								<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
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
			@policy-inform="openPolicyInformOverlay"
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

		<!-- CLINIC HISTORY DIALOG -->
		<HistoryDialog
			v-model="showClinicHistory"
			title="Clinic Volume"
			subtitle="Student patient visits over time"
			method="ifitwala_ed.api.morning_brief.get_clinic_visits_trend"
			:range-options="clinicHistoryRangeOptions"
			:default-range="clinicVolumeView"
		/>

		<CommentThreadDrawer
			:open="showInteractionDrawer"
			title="Announcement Comments"
			:rows="interactionThreadRows"
			:loading="interactionThreadLoading"
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { createResource, FeatherIcon, toast } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { formatLocalizedDateTime } from '@/lib/datetime';
import { createCommunicationInteractionService } from '@/lib/services/communicationInteraction/communicationInteractionService';
import { SIGNAL_ORG_COMMUNICATION_INVALIDATE, uiSignals } from '@/lib/uiSignals';
import ContentDialog from '@/components/ContentDialog.vue';
import GenericListDialog from '@/components/analytics/GenericListDialog.vue';
import HistoryDialog from '@/components/analytics/HistoryDialog.vue';
import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue';
import DateRangePills from '@/components/filters/DateRangePills.vue';
import AttendanceTrend from './components/AttendanceTrend.vue';
import AbsentStudentList from './components/AbsentStudentList.vue';
import {
	ORG_SURFACES,
	type Announcement,
	type ClinicVolumeSummary,
	type InteractionSummaryMap,
	type InteractionThreadRow,
	type WidgetsPayload,
	type StudentLogItem,
	type OrgPriority,
	type StudentLogDetail,
} from '@/types/morning_brief';
import type { InteractionSummary, ReactionCode } from '@/types/morning_brief';
import { canShowPublicInteractions } from '@/utils/orgCommunication';
import type { PolicyInformLinkPayload } from '@/utils/policyInformLink';
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
	| 'my_student_birthdays'
	| 'student_logs'
	| 'attendance_trend'
	| 'my_absent_students';

// State for Dialog
const isContentDialogOpen = ref<boolean>(false);
const overlay = useOverlayStack();
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
const showClinicHistory = ref<boolean>(false);
const showInteractionDrawer = ref<boolean>(false);
const activeCommunication = ref<Announcement | null>(null);
const showInteractionsForActive = computed(() => canShowInteractions(activeCommunication.value));
const newComment = ref<string>('');
const interactionService = createCommunicationInteractionService();
const interactionSummaryData = ref<InteractionSummaryMap>({});
const interactionThreadRows = ref<InteractionThreadRow[]>([]);
const interactionThreadLoading = ref(false);
let disposeOrgCommunicationInvalidate: (() => void) | null = null;

const criticalIncidentsList = createResource<StudentLogDetail[]>({
	url: 'ifitwala_ed.api.morning_brief.get_critical_incidents_details',
	auto: false,
});

const widgets = createResource<WidgetsPayload>({
	url: 'ifitwala_ed.api.morning_brief.get_briefing_widgets',
	auto: true,
});
const clinicVolumeViewOptions = [
	{ label: '3 days', value: '3D' },
	{ label: '3 weeks', value: '3W' },
] as const;
const clinicHistoryRangeOptions = [
	...clinicVolumeViewOptions,
	{ label: '1M', value: '1M' },
	{ label: '3M', value: '3M' },
	{ label: '6M', value: '6M' },
	{ label: 'YTD', value: 'YTD' },
] as const;
type ClinicVolumeView = (typeof clinicVolumeViewOptions)[number]['value'];
const clinicVolumeView = ref<ClinicVolumeView>('3D');

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
const clinicVolume = computed<ClinicVolumeSummary | null>(
	() => widgets.data?.clinic_volume || null
);
const clinicVolumePoints = computed(() => {
	const volume = clinicVolume.value;
	if (!volume) return [];
	return volume.views?.[clinicVolumeView.value] || [];
});
const hasClinicVolumeCard = computed(() => clinicVolume.value !== null);
const clinicVolumeIsInteractive = computed(
	() => !!clinicVolume.value && !clinicVolume.value.error && clinicVolumePoints.value.length > 0
);

watch(
	clinicVolume,
	volume => {
		const defaultView = volume?.default_view;
		if (defaultView === '3D' || defaultView === '3W') {
			clinicVolumeView.value = defaultView;
		}
	},
	{ immediate: true }
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
		if (!list || !list.length) {
			interactionSummaryData.value = {};
			return;
		}

		const commNames = list.map(a => a.name).filter(Boolean);
		if (!commNames.length) {
			interactionSummaryData.value = {};
			return;
		}

		void refreshInteractionSummary(commNames);
	},
	{ immediate: true }
);

async function refreshInteractionSummary(commNames: string[]) {
	const names = commNames.filter(name => typeof name === 'string' && !!name.trim());
	if (!names.length) {
		interactionSummaryData.value = {};
		return;
	}

	try {
		const nextSummary = await interactionService.getOrgCommInteractionSummary({
			comm_names: names,
		});
		interactionSummaryData.value = {
			...interactionSummaryData.value,
			...nextSummary,
		};
	} catch {
		if (!interactionSummaryData.value || !Object.keys(interactionSummaryData.value).length) {
			interactionSummaryData.value = {};
		}
	}
}

async function refreshInteractionThread(orgCommunication: string, opts?: { silent?: boolean }) {
	interactionThreadLoading.value = true;
	try {
		interactionThreadRows.value = await interactionService.getCommunicationThread({
			org_communication: orgCommunication,
			limit_start: 0,
			limit: 30,
		});
	} catch (err) {
		interactionThreadRows.value = [];
		if (!opts?.silent) {
			const message = err instanceof Error ? err.message : 'Unable to load announcement comments.';
			toast({
				title: 'Unable to load comments',
				text: message,
				icon: 'alert-circle',
				appearance: 'danger',
			});
		}
	} finally {
		interactionThreadLoading.value = false;
	}
}

function getAnnouncementNames(): string[] {
	return (widgets.data?.announcements || []).map(item => item.name).filter(Boolean);
}

function onOrgCommunicationInvalidated(payload?: { names?: string[] }) {
	const currentNames = getAnnouncementNames();
	if (!currentNames.length) {
		interactionSummaryData.value = {};
		return;
	}

	const invalidatedNames = (payload?.names || [])
		.filter(name => typeof name === 'string' && !!name.trim())
		.filter(name => currentNames.includes(name));
	const namesToRefresh = invalidatedNames.length ? invalidatedNames : currentNames;

	void refreshInteractionSummary(namesToRefresh);

	const activeName = activeCommunication.value?.name || null;
	if (showInteractionDrawer.value && activeName && namesToRefresh.includes(activeName)) {
		void refreshInteractionThread(activeName, { silent: true });
	}
}

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

function openClinicHistory(): void {
	if (!clinicVolumeIsInteractive.value) {
		return;
	}
	showClinicHistory.value = true;
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
	const summary = interactionSummaryData.value?.[item.name];
	if (!summary) {
		return {
			counts: {},
			reaction_counts: {},
			reactions_total: 0,
			comments_total: 0,
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
		toast({
			title: 'Comments unavailable',
			text: 'Comments are disabled for this announcement.',
			icon: 'info',
		});
		return;
	}

	activeCommunication.value = item;
	showInteractionDrawer.value = true;
	void refreshInteractionThread(item.name);
}

function formatThreadTimestamp(value?: string | null): string {
	if (!value) return '';
	return formatLocalizedDateTime(value, {
		day: '2-digit',
		month: 'short',
		fallback: value,
	});
}

async function acknowledgeAnnouncement(item: Announcement): Promise<void> {
	if (!item?.name) {
		toast({
			title: 'Unable to save acknowledgement',
			text: 'Please try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
		return;
	}
	if (!canShowInteractions(item)) {
		toast({
			title: 'Reactions unavailable',
			text: 'Reactions are disabled for this announcement.',
			icon: 'info',
		});
		return;
	}

	try {
		await interactionService.reactToOrgCommunication({
			org_communication: item.name,
			reaction_code: 'like',
			surface: ORG_SURFACES.MORNING_BRIEF,
		});
	} catch (err) {
		const message = err instanceof Error ? err.message : 'Unable to save acknowledgement.';
		toast({
			title: 'Unable to save acknowledgement',
			text: message,
			icon: 'alert-circle',
			appearance: 'danger',
		});
	}
}

async function submitComment(): Promise<void> {
	if (!activeCommunication.value?.name) {
		toast({
			title: 'Select an announcement',
			text: 'Choose an announcement before posting a comment.',
			icon: 'info',
		});
		return;
	}
	if (!canShowInteractions(activeCommunication.value)) {
		toast({
			title: 'Comments unavailable',
			text: 'Comments are disabled for this announcement.',
			icon: 'info',
		});
		return;
	}

	const note = newComment.value.trim();
	if (!note) {
		toast({
			title: 'Comment required',
			text: 'Write a comment before posting.',
			icon: 'info',
		});
		return;
	}

	try {
		await interactionService.postOrgCommunicationComment({
			org_communication: activeCommunication.value.name,
			note,
			surface: ORG_SURFACES.MORNING_BRIEF,
		});
		newComment.value = '';
	} catch (err) {
		const message = err instanceof Error ? err.message : 'Unable to post comment.';
		toast({
			title: 'Unable to post comment',
			text: message,
			icon: 'alert-circle',
			appearance: 'danger',
		});
	}
}

async function reactToAnnouncement(item: Announcement, reaction: ReactionCode): Promise<void> {
	if (!item?.name) {
		toast({
			title: 'Unable to save reaction',
			text: 'Please try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
		return;
	}
	if (!canShowInteractions(item)) {
		toast({
			title: 'Reactions unavailable',
			text: 'Reactions are disabled for this announcement.',
			icon: 'info',
		});
		return;
	}

	if (reaction === 'question') {
		openInteractionThread(item);
		return;
	}

	try {
		await interactionService.reactToOrgCommunication({
			org_communication: item.name,
			reaction_code: reaction,
			surface: ORG_SURFACES.MORNING_BRIEF,
		});
	} catch (err) {
		const message = err instanceof Error ? err.message : 'Unable to save reaction.';
		toast({
			title: 'Unable to save reaction',
			text: message,
			icon: 'alert-circle',
			appearance: 'danger',
		});
	}
}

function openAnnouncementsDialog(): void {
	showAnnouncementCenter.value = true;
}

function openPolicyInformOverlay(payload: PolicyInformLinkPayload): void {
	const policyVersion = String(payload?.policyVersion || '').trim();
	if (!policyVersion) return;
	const communicationName =
		String(payload?.orgCommunication || '').trim() ||
		String(activeCommunication.value?.name || '').trim() ||
		null;
	isContentDialogOpen.value = false;
	overlay.open('staff-policy-inform', {
		policyVersion,
		orgCommunication: communicationName,
	});
}

function openCriticalIncidentsOverlay(): void {
	// Fetch data if not already loaded
	if (!criticalIncidentsList.data && !criticalIncidentsList.loading) {
		criticalIncidentsList.fetch();
	}

	overlay.open('critical-incidents-list', {
		items: criticalIncidentsList.data || [],
		loading: criticalIncidentsList.loading,
	});
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

onMounted(() => {
	disposeOrgCommunicationInvalidate = uiSignals.subscribe(
		SIGNAL_ORG_COMMUNICATION_INVALIDATE,
		onOrgCommunicationInvalidated
	);
});

onBeforeUnmount(() => {
	if (disposeOrgCommunicationInvalidate) disposeOrgCommunicationInvalidate();
});
</script>
