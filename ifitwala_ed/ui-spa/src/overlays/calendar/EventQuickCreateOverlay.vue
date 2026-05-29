<!-- ifitwala_ed/ui-spa/src/overlays/calendar/EventQuickCreateOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--meeting"
			:style="{ zIndex: zIndex }"
			:initialFocus="initialFocus"
			@close="onDialogClose"
		>
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel">
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose('programmatic')"
						>
							{{ __('Close') }}
						</button>

						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">{{ overlayTitle }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{ overlayDescription }}
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								:aria-label="__('Close')"
								@click="emitClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body space-y-5 px-6 pb-6">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
									<div class="min-w-0">
										<p class="type-body-strong text-rose-900">{{ __('Action blocked') }}</p>
										<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">
											{{ errorMessage }}
										</p>
										<p
											v-if="showStudentConflictRecovery"
											class="mt-2 type-caption text-rose-900/70"
										>
											{{
												__(
													'The form is still open. Use the common time finder to pick the next free slot for this group.'
												)
											}}
										</p>
										<p
											v-else-if="showRoomConflictRecovery"
											class="mt-2 type-caption text-rose-900/70"
										>
											{{
												__(
													'The form is still open. Use room suggestions to replace the booked room without losing this draft.'
												)
											}}
										</p>
									</div>
									<button
										v-if="showStudentConflictRecovery"
										type="button"
										class="inline-flex items-center justify-center rounded-full bg-rose-900 px-4 py-2 type-button-label text-white transition hover:bg-rose-950 disabled:cursor-not-allowed disabled:bg-rose-300"
										:disabled="submitting || slotLoading"
										@click="recoverFromStudentConflict"
									>
										{{ __('Find common times') }}
									</button>
									<button
										v-else-if="showRoomConflictRecovery"
										type="button"
										class="inline-flex items-center justify-center rounded-full bg-rose-900 px-4 py-2 type-button-label text-white transition hover:bg-rose-950 disabled:cursor-not-allowed disabled:bg-rose-300"
										:disabled="submitting || roomLoading"
										@click="recoverFromRoomConflict"
									>
										{{ __('Suggest rooms') }}
									</button>
								</div>
							</div>

							<div class="rounded-2xl border border-border/70 bg-white p-3 shadow-soft">
								<div class="flex flex-wrap items-center gap-2">
									<button
										v-for="type in typeOptions"
										:key="type.value"
										type="button"
										class="rounded-full px-3 py-1.5 type-button-label transition"
										:class="
											activeType === type.value
												? 'bg-jacaranda text-white'
												: 'bg-slate-100 text-slate-token hover:bg-slate-200'
										"
										:disabled="!canSwitchType || !type.enabled"
										@click="setActiveType(type.value)"
									>
										{{ type.label }}
									</button>
									<span
										v-if="typeLocked"
										class="rounded-full bg-sky/25 px-2.5 py-1 type-caption text-canopy"
									>
										{{ __('Mode locked by entry context') }}
									</span>
								</div>
							</div>

							<div
								v-if="optionsLoading"
								class="flex items-center gap-2 rounded-2xl border border-border/70 bg-white px-4 py-3 text-ink/70"
							>
								<Spinner class="h-4 w-4" />
								<span class="type-caption">Loading event options...</span>
							</div>

							<form v-else class="space-y-4" @submit.prevent="submit">
								<section v-if="activeType === 'meeting'" class="space-y-4">
									<div class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft">
										<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
											<div class="space-y-1">
												<p class="type-overline text-ink/55">{{ __('Meeting workflow') }}</p>
												<h3 class="type-h3 text-ink">{{ meetingModeTitle }}</h3>
												<p class="type-caption text-ink/70">
													{{ meetingModeDescription }}
												</p>
											</div>
											<span class="rounded-full bg-sky/25 px-3 py-1.5 type-caption text-canopy">
												{{ meetingModeBadge }}
											</span>
										</div>

										<div
											class="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,2fr),minmax(0,1fr)]"
										>
											<div class="space-y-1">
												<label class="type-label">{{ __('Meeting name') }}</label>
												<FormControl
													type="text"
													:model-value="meetingForm.meeting_name"
													:placeholder="__('Family support meeting')"
													:disabled="submitting"
													@update:modelValue="value => updateMeetingField('meeting_name', value)"
												/>
											</div>

											<div class="space-y-1">
												<label class="type-label">{{ __('Host school') }}</label>
												<FormControl
													type="select"
													:options="schoolSelectOptions"
													option-label="label"
													option-value="value"
													:model-value="meetingForm.school"
													:disabled="submitting || schoolLocked"
													@update:modelValue="value => updateMeetingField('school', value)"
												/>
											</div>
										</div>

										<div class="mt-4 space-y-2">
											<label class="type-label">{{ __('Planning format') }}</label>
											<div class="flex flex-wrap gap-2">
												<button
													v-for="format in meetingFormatOptions"
													:key="format.value"
													type="button"
													class="rounded-full px-3 py-1.5 type-button-label transition"
													:class="
														meetingForm.meeting_format === format.value
															? 'bg-ink text-white'
															: 'bg-slate-100 text-slate-token hover:bg-slate-200'
													"
													:disabled="submitting"
													@click="setMeetingFormat(format.value)"
												>
													{{ format.label }}
												</button>
											</div>
											<p class="type-caption text-ink/60">
												{{
													__(
														'Virtual meetings skip room suggestions. Hybrid keeps both room and link fields available.'
													)
												}}
											</p>
										</div>
									</div>

									<div class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft">
										<div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
											<div class="space-y-1">
												<h3 class="type-h3 text-ink">{{ __('Attendees') }}</h3>
												<p class="type-caption text-ink/70">
													{{
														__(
															'Add colleagues, students, and guardians directly. The organizer is always included automatically.'
														)
													}}
												</p>
											</div>
											<span
												class="rounded-full bg-slate-100 px-3 py-1 type-caption text-slate-token"
											>
												{{ selectedAttendeeCountLabel }}
											</span>
										</div>

										<div class="mt-4 flex flex-wrap gap-2">
											<div
												v-for="attendee in selectedAttendees"
												:key="attendee.value"
												class="inline-flex items-center gap-2 rounded-full border border-border/70 bg-slate-50 px-3 py-1.5"
											>
												<div class="min-w-0">
													<p class="truncate type-caption text-ink">{{ attendee.label }}</p>
													<p class="truncate text-[11px] text-ink/55">
														{{ attendeeKindLabel(attendee.kind) }}
														<span v-if="attendee.meta"> · {{ attendee.meta }}</span>
														<span v-if="isLockedTeamAttendee(attendee.value)">
															{{ __('· Team context') }}</span
														>
													</p>
												</div>
												<button
													v-if="!isLockedTeamAttendee(attendee.value)"
													type="button"
													class="rounded-full p-1 text-slate-token/60 transition hover:bg-slate-200 hover:text-ink"
													:disabled="submitting"
													@click="removeAttendee(attendee.value)"
												>
													<FeatherIcon name="x" class="h-3.5 w-3.5" />
												</button>
											</div>
											<div
												v-if="!selectedAttendees.length"
												class="rounded-2xl border border-dashed border-slate-300 px-4 py-3 type-caption text-slate-token/75"
											>
												No invitees selected yet.
											</div>
										</div>

										<div class="mt-4 space-y-2">
											<label class="type-label">{{ __('Invite scope') }}</label>
											<div class="flex flex-wrap gap-2">
												<label
													v-if="employeeAttendeeKindOption"
													class="inline-flex items-center gap-2 rounded-full border border-canopy/30 bg-canopy/10 px-3 py-1.5 type-button-label text-canopy"
												>
													<input type="checkbox" checked disabled class="h-4 w-4 accent-canopy" />
													<span>{{ employeeAttendeeKindOption.label }}</span>
												</label>
												<label
													v-for="kind in nonEmployeeInviteScopeOptions"
													:key="kind.value"
													class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 type-button-label transition"
													:class="
														isAttendeeKindSelected(kind.value)
															? 'border-canopy/40 bg-canopy/10 text-canopy'
															: 'border-border/70 bg-slate-100 text-slate-token'
													"
												>
													<input
														type="checkbox"
														class="h-4 w-4 accent-canopy"
														:checked="isAttendeeKindSelected(kind.value)"
														:disabled="submitting"
														@change="toggleNonEmployeeInviteScope(kind.value)"
													/>
													<span>{{ kind.label }}</span>
												</label>
											</div>
											<p v-if="attendeeScopeSafetyMessage" class="type-caption text-amber-700">
												{{ attendeeScopeSafetyMessage }}
											</p>
											<p v-if="inviteScopeMismatchMessage" class="type-caption text-rose-700">
												{{ inviteScopeMismatchMessage }}
											</p>
										</div>

										<div class="mt-3 space-y-2">
											<label class="type-label">{{ __('Search people') }}</label>
											<FormControl
												type="text"
												:model-value="attendeeSearchQuery"
												:placeholder="__('Search by name or email')"
												:disabled="submitting"
												@update:modelValue="value => updateAttendeeSearchQuery(value)"
											/>
											<div
												v-if="attendeeSearchLoading"
												class="flex items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-ink/70"
											>
												<Spinner class="h-4 w-4" />
												<span class="type-caption">{{ __('Searching people...') }}</span>
											</div>
											<div
												v-else-if="
													attendeeSearchQuery.trim().length >= 2 && availableSearchResults.length
												"
												class="max-h-56 space-y-2 overflow-y-auto rounded-2xl border border-border/70 bg-slate-50 p-2"
											>
												<button
													v-for="attendee in availableSearchResults"
													:key="`${attendee.kind}:${attendee.value}`"
													type="button"
													class="flex w-full items-center justify-between gap-3 rounded-xl bg-white px-3 py-2 text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-md"
													:disabled="submitting"
													@click="addAttendee(attendee)"
												>
													<div class="min-w-0">
														<p class="truncate type-body-strong text-ink">
															{{ attendee.label }}
														</p>
														<p class="truncate type-caption text-ink/65">
															{{ attendeeKindLabel(attendee.kind) }}
															<span v-if="attendee.meta"> · {{ attendee.meta }}</span>
														</p>
													</div>
													<span
														class="rounded-full bg-jacaranda px-3 py-1.5 type-button-label text-white"
													>
														{{ __('Add') }}
													</span>
												</button>
											</div>
											<p
												v-else-if="attendeeSearchQuery.trim().length >= 2"
												class="type-caption text-ink/60"
											>
												No matching people found in your scope.
											</p>
											<p v-if="attendeePanelMessage" class="type-caption text-canopy">
												{{ attendeePanelMessage }}
											</p>
											<p
												v-for="note in attendeeSearchNotes"
												:key="note"
												class="type-caption text-ink/60"
											>
												{{ note }}
											</p>
										</div>

										<div class="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr),auto]">
											<div class="space-y-1">
												<label class="type-label">
													{{
														effectiveMeetingMode === 'team'
															? __('Team context')
															: __('Bulk-add a team')
													}}
												</label>
												<FormControl
													type="select"
													:options="teamSelectOptions"
													option-label="label"
													option-value="value"
													:model-value="meetingForm.team"
													:disabled="submitting || teamFieldLocked || teamHydrating"
													@update:modelValue="value => updateMeetingField('team', value)"
												/>
											</div>
											<div class="flex items-end">
												<button
													type="button"
													class="inline-flex items-center gap-2 rounded-full bg-canopy px-4 py-2.5 type-button-label text-white transition hover:bg-canopy/90 disabled:cursor-not-allowed disabled:bg-slate-300"
													:disabled="submitting || teamHydrating || !meetingForm.team"
													@click="addTeamAttendees()"
												>
													<Spinner v-if="teamHydrating" class="h-4 w-4" />
													<span>
														{{
															effectiveMeetingMode === 'team'
																? __('Refresh team roster')
																: __('Add team')
														}}
													</span>
												</button>
											</div>
										</div>
										<p class="mt-2 type-caption text-ink/60">
											{{
												effectiveMeetingMode === 'team'
													? __(
															'Team attendees are locked because this workflow was opened from team context.'
														)
													: __(
															'Team bulk-add only affects the attendee list. This stays an ad-hoc meeting unless a dedicated team entry point opens it in team mode.'
														)
											}}
										</p>
									</div>

									<div
										ref="commonTimesSection"
										class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft"
									>
										<div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
											<div class="space-y-1">
												<h3 class="type-h3 text-ink">{{ __('Common time finder') }}</h3>
												<p class="type-caption text-ink/70">
													{{
														__(
															'Server-side suggestions use batched attendee availability checks and, for in-person or hybrid meetings, only keep exact matches that still have a free room in the selected school.'
														)
													}}
												</p>
											</div>
											<button
												type="button"
												class="inline-flex items-center gap-2 rounded-full bg-jacaranda px-4 py-2.5 type-button-label text-white transition hover:bg-jacaranda/90 disabled:cursor-not-allowed disabled:bg-slate-300"
												:disabled="submitting || slotLoading"
												@click="findCommonTimes"
											>
												<Spinner v-if="slotLoading" class="h-4 w-4" />
												<span>{{ __('Find common times') }}</span>
											</button>
										</div>

										<div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
											<div class="space-y-1">
												<label class="type-label">{{ __('Duration (minutes)') }}</label>
												<input
													v-model="meetingForm.duration_minutes"
													type="number"
													min="15"
													max="240"
													step="15"
													class="if-overlay__input"
													:disabled="submitting || slotLoading"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">{{ __('Search from') }}</label>
												<input
													v-model="meetingForm.date_from"
													type="date"
													class="if-overlay__input"
													:disabled="submitting || slotLoading"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">{{ __('Search to') }}</label>
												<input
													v-model="meetingForm.date_to"
													type="date"
													class="if-overlay__input"
													:disabled="submitting || slotLoading"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">{{ __('Earliest start') }}</label>
												<input
													v-model="meetingForm.day_start_time"
													type="time"
													class="if-overlay__input"
													:disabled="submitting || slotLoading"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">{{ __('Latest end') }}</label>
												<input
													v-model="meetingForm.day_end_time"
													type="time"
													class="if-overlay__input"
													:disabled="submitting || slotLoading"
												/>
											</div>
										</div>

										<div class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
											<div class="space-y-2">
												<div class="flex items-center justify-between gap-2">
													<h4 class="type-body-strong text-ink">{{ __('Best common times') }}</h4>
													<span class="type-caption text-ink/55">
														{{ exactMatchSummary }}
													</span>
												</div>
												<div
													v-if="slotSuggestions.length"
													class="space-y-2 rounded-2xl border border-border/70 bg-slate-50 p-3"
												>
													<button
														v-for="(slot, index) in slotSuggestions"
														:key="slot.start"
														type="button"
														class="flex w-full items-start justify-between gap-3 rounded-xl bg-white px-3 py-3 text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-md"
														:disabled="submitting"
														@click="applySuggestedSlot(slot)"
													>
														<div class="min-w-0">
															<p class="type-body-strong text-ink">
																{{ slotDisplayLabel(slot) }}
															</p>
															<p class="type-caption text-ink/60">
																{{
																	__('{0} · {1} to {2}', [
																		slot.date,
																		slot.start_time,
																		slot.end_time,
																	])
																}}
															</p>
															<p v-if="slot.suggested_room" class="type-caption text-canopy">
																{{ slotRoomSummary(slot) }}
															</p>
														</div>
														<span
															class="rounded-full px-2.5 py-1 type-caption"
															:class="
																index === 0
																	? 'bg-canopy/15 text-canopy'
																	: 'bg-slate-100 text-slate-token'
															"
														>
															{{ index === 0 ? __('Best match') : __('Apply') }}
														</span>
													</button>
												</div>
												<p
													v-else-if="slotSearchPerformed"
													class="rounded-2xl border border-dashed border-slate-300 px-4 py-3 type-caption text-slate-token/75"
												>
													No exact common slot was found in this window.
												</p>
											</div>

											<div class="space-y-2">
												<div class="flex items-center justify-between gap-2">
													<h4 class="type-body-strong text-ink">
														{{ __('Nearest alternatives') }}
													</h4>
													<span class="type-caption text-ink/55">
														{{ __('{0} partial matches', [fallbackSlotSuggestions.length]) }}
													</span>
												</div>
												<div
													v-if="fallbackSlotSuggestions.length"
													class="space-y-2 rounded-2xl border border-border/70 bg-slate-50 p-3"
												>
													<button
														v-for="slot in fallbackSlotSuggestions"
														:key="slot.start"
														type="button"
														class="flex w-full items-start justify-between gap-3 rounded-xl bg-white px-3 py-3 text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-md"
														:disabled="submitting"
														@click="applySuggestedSlot(slot)"
													>
														<div class="min-w-0">
															<p class="type-body-strong text-ink">
																{{ slotDisplayLabel(slot) }}
															</p>
															<p class="type-caption text-ink/60">
																{{
																	__('{0} · {1} to {2}', [
																		slot.date,
																		slot.start_time,
																		slot.end_time,
																	])
																}}
															</p>
															<p
																v-if="showRoomAssistant"
																class="type-caption"
																:class="slot.suggested_room ? 'text-canopy' : 'text-amber-700'"
															>
																{{ fallbackRoomSummary(slot) }}
															</p>
														</div>
														<span
															class="rounded-full bg-amber-100 px-2.5 py-1 type-caption text-amber-700"
														>
															{{
																slot.blocked_count === 1
																	? __('{0} conflict', [slot.blocked_count])
																	: __('{0} conflicts', [slot.blocked_count])
															}}
														</span>
													</button>
												</div>
												<p
													v-else-if="slotSearchPerformed"
													class="rounded-2xl border border-dashed border-slate-300 px-4 py-3 type-caption text-slate-token/75"
												>
													No fallback slots were ranked for this search.
												</p>
											</div>
										</div>

										<div v-if="slotNotes.length" class="mt-4 space-y-1">
											<p v-for="note in slotNotes" :key="note" class="type-caption text-ink/60">
												{{ note }}
											</p>
										</div>

										<div class="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
											<div class="space-y-1">
												<label class="type-label">{{ __('Meeting date') }}</label>
												<input
													v-model="meetingForm.date"
													type="date"
													class="if-overlay__input"
													:disabled="submitting"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">{{ __('Start time') }}</label>
												<input
													v-model="meetingForm.start_time"
													type="time"
													class="if-overlay__input"
													:disabled="submitting"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">{{ __('End time') }}</label>
												<input
													v-model="meetingForm.end_time"
													type="time"
													class="if-overlay__input"
													:disabled="submitting"
												/>
											</div>
										</div>
										<p class="mt-2 type-caption text-ink/60">
											{{
												__(
													'You can accept a suggestion above or set the final date and time manually.'
												)
											}}
										</p>
									</div>

									<div
										v-if="showRoomAssistant"
										ref="roomSuggestionsSection"
										class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft"
									>
										<div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
											<div class="space-y-1">
												<h3 class="type-h3 text-ink">{{ __('Room suggestions') }}</h3>
												<p class="type-caption text-ink/70">
													{{
														__(
															'Available rooms are ranked server-side from live location bookings. Applying a room-aware common time also prefills the best-ranked free room.'
														)
													}}
												</p>
											</div>
											<button
												type="button"
												class="inline-flex items-center gap-2 rounded-full bg-canopy px-4 py-2.5 type-button-label text-white transition hover:bg-canopy/90 disabled:cursor-not-allowed disabled:bg-slate-300"
												:disabled="submitting || roomLoading"
												@click="findRoomSuggestions"
											>
												<Spinner v-if="roomLoading" class="h-4 w-4" />
												<span>{{ __('Suggest rooms') }}</span>
											</button>
										</div>

										<div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
											<div
												v-if="roomSuggestions.length"
												class="space-y-2 rounded-2xl border border-border/70 bg-slate-50 p-3"
											>
												<button
													v-for="room in roomSuggestions"
													:key="room.value"
													type="button"
													class="flex w-full items-start justify-between gap-3 rounded-xl bg-white px-3 py-3 text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-md"
													:disabled="submitting"
													@click="applySuggestedRoom(room)"
												>
													<div class="min-w-0">
														<p class="type-body-strong text-ink">{{ room.label }}</p>
														<p class="type-caption text-ink/60">
															<span v-if="room.building">{{ room.building }}</span>
															<span
																v-if="
																	room.building && (room.location_type_name || room.max_capacity)
																"
															>
																·
															</span>
															<span v-if="room.location_type_name">
																{{ room.location_type_name }}
															</span>
															<span v-if="room.location_type_name && room.max_capacity"> · </span>
															<span v-if="room.max_capacity">
																{{ __('Capacity {0}', [room.max_capacity]) }}
															</span>
														</p>
													</div>
													<span
														class="rounded-full bg-slate-100 px-2.5 py-1 type-caption text-slate-token"
													>
														{{ __('Use room') }}
													</span>
												</button>
											</div>
											<p
												v-else-if="roomSearchPerformed"
												class="rounded-2xl border border-dashed border-slate-300 px-4 py-3 type-caption text-slate-token/75"
											>
												No free room matched the selected slot and school scope.
											</p>

											<div class="space-y-3">
												<div class="space-y-1">
													<label class="type-label">{{ __('Room type filter') }}</label>
													<FormControl
														type="select"
														:options="meetingLocationTypeSelectOptions"
														option-label="label"
														option-value="value"
														:model-value="meetingForm.location_type"
														:disabled="submitting"
														@update:modelValue="
															value => updateMeetingField('location_type', value)
														"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">{{ __('Location (optional)') }}</label>
													<FormControl
														type="select"
														:options="meetingLocationSelectOptions"
														option-label="label"
														option-value="value"
														:model-value="meetingForm.location"
														:disabled="submitting"
														@update:modelValue="value => updateMeetingField('location', value)"
													/>
												</div>
												<p class="type-caption text-ink/60">
													{{
														__('Capacity target: {0} people including organizer.', [
															roomCapacityTarget,
														])
													}}
												</p>
											</div>
										</div>

										<div v-if="roomNotes.length" class="mt-4 space-y-1">
											<p v-for="note in roomNotes" :key="note" class="type-caption text-ink/60">
												{{ note }}
											</p>
										</div>
									</div>

									<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
										<div class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft">
											<div class="space-y-3">
												<div class="space-y-1">
													<label class="type-label">{{ __('Meeting category (optional)') }}</label>
													<FormControl
														type="select"
														:options="meetingCategorySelectOptions"
														option-label="label"
														option-value="value"
														:model-value="meetingForm.meeting_category"
														:disabled="submitting"
														@update:modelValue="
															value => updateMeetingField('meeting_category', value)
														"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">{{ __('Virtual link (optional)') }}</label>
													<FormControl
														type="text"
														:model-value="meetingForm.virtual_meeting_link"
														:placeholder="__('https://...')"
														:disabled="submitting"
														@update:modelValue="
															value => updateMeetingField('virtual_meeting_link', value)
														"
													/>
												</div>
											</div>
										</div>

										<div class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft">
											<div class="space-y-1">
												<label class="type-label">{{ __('Agenda (optional)') }}</label>
												<FormControl
													type="textarea"
													:rows="6"
													:model-value="meetingForm.agenda"
													:disabled="submitting"
													:placeholder="__('Purpose, outcomes, or discussion points...')"
													@update:modelValue="value => updateMeetingField('agenda', value)"
												/>
											</div>
										</div>
									</div>
								</section>

								<section v-else class="space-y-4">
									<div class="space-y-1">
										<label class="type-label">{{ __('Event subject') }}</label>
										<FormControl
											type="text"
											:model-value="schoolEventForm.subject"
											:placeholder="__('Parent workshop: assessment reporting')"
											:disabled="submitting"
											@update:modelValue="value => updateSchoolEventField('subject', value)"
										/>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">{{ __('School') }}</label>
											<FormControl
												type="select"
												:options="schoolSelectOptions"
												option-label="label"
												option-value="value"
												:model-value="schoolEventForm.school"
												:disabled="submitting || schoolLocked"
												@update:modelValue="value => updateSchoolEventField('school', value)"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">{{ __('Event category') }}</label>
											<FormControl
												type="select"
												:options="schoolEventCategorySelectOptions"
												option-label="label"
												option-value="value"
												:model-value="schoolEventForm.event_category"
												:disabled="submitting"
												@update:modelValue="
													value => updateSchoolEventField('event_category', value)
												"
											/>
										</div>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">{{ __('Starts on') }}</label>
											<input
												v-model="schoolEventForm.starts_on"
												type="datetime-local"
												class="if-overlay__input"
												:disabled="submitting"
											/>
										</div>
										<div class="space-y-1">
											<label class="type-label">{{ __('Ends on') }}</label>
											<input
												v-model="schoolEventForm.ends_on"
												type="datetime-local"
												class="if-overlay__input"
												:disabled="submitting"
											/>
										</div>
									</div>

									<div class="space-y-1">
										<label class="type-label">{{ __('Audience type') }}</label>
										<FormControl
											type="select"
											:options="audienceTypeSelectOptions"
											option-label="label"
											option-value="value"
											:model-value="schoolEventForm.audience_type"
											:disabled="submitting"
											@update:modelValue="value => updateSchoolEventField('audience_type', value)"
										/>
									</div>

									<div
										v-if="schoolEventForm.audience_type === 'Employees in Team'"
										class="space-y-1"
									>
										<label class="type-label">{{ __('Audience team') }}</label>
										<FormControl
											type="select"
											:options="schoolEventTeamSelectOptions"
											option-label="label"
											option-value="value"
											:model-value="schoolEventForm.audience_team"
											:disabled="submitting"
											@update:modelValue="value => updateSchoolEventField('audience_team', value)"
										/>
									</div>

									<div
										v-if="schoolEventForm.audience_type === 'Students in Student Group'"
										class="space-y-1"
									>
										<label class="type-label">{{ __('Audience student group') }}</label>
										<FormControl
											type="select"
											:options="studentGroupSelectOptions"
											option-label="label"
											option-value="value"
											:model-value="schoolEventForm.audience_student_group"
											:disabled="submitting"
											@update:modelValue="
												value => updateSchoolEventField('audience_student_group', value)
											"
										/>
									</div>

									<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
										<div class="space-y-1">
											<label class="type-label">{{ __('Location (optional)') }}</label>
											<FormControl
												type="select"
												:options="schoolEventLocationSelectOptions"
												option-label="label"
												option-value="value"
												:model-value="schoolEventForm.location"
												:disabled="submitting"
												@update:modelValue="value => updateSchoolEventField('location', value)"
											/>
										</div>
										<div class="space-y-2 pt-6">
											<label class="flex items-center gap-2 type-caption text-ink/80">
												<input
													v-model="schoolEventForm.all_day"
													type="checkbox"
													class="rounded border-border/70"
													:disabled="submitting"
												/>
												{{ __('All-day event') }}
											</label>
											<label class="flex items-center gap-2 type-caption text-ink/80">
												<input
													v-model="schoolEventForm.include_guardians"
													type="checkbox"
													class="rounded border-border/70"
													:disabled="submitting"
												/>
												{{ __('Include guardians') }}
											</label>
											<label class="flex items-center gap-2 type-caption text-ink/80">
												<input
													v-model="schoolEventForm.include_students"
													type="checkbox"
													class="rounded border-border/70"
													:disabled="submitting"
												/>
												{{ __('Include students') }}
											</label>
										</div>
									</div>

									<div class="space-y-1">
										<label class="type-label">{{ __('Description (optional)') }}</label>
										<FormControl
											type="textarea"
											:rows="5"
											:model-value="schoolEventForm.description"
											:disabled="submitting"
											:placeholder="__('Share event details and expectations...')"
											@update:modelValue="value => updateSchoolEventField('description', value)"
										/>
									</div>

									<div class="rounded-2xl border border-border/70 bg-sand/20 p-4 shadow-soft">
										<div class="space-y-1">
											<p class="type-overline text-ink/55">{{ __('Communications') }}</p>
											<h3 class="type-h3 text-ink">{{ __('Calendar item vs announcement') }}</h3>
											<p class="type-caption text-ink/70">
												{{
													__(
														'This school event creates the calendar item. If families or students also need a portal announcement with read-state, publish it here in the same workflow.'
													)
												}}
											</p>
										</div>

										<label
											class="mt-4 flex items-start gap-3 rounded-2xl border border-border/70 bg-white px-4 py-3 type-caption text-ink/80"
											:class="
												canPublishAnnouncement ? 'cursor-pointer' : 'cursor-not-allowed opacity-70'
											"
										>
											<input
												v-model="schoolEventForm.publish_announcement"
												type="checkbox"
												class="mt-0.5 rounded border-border/70"
												:disabled="submitting || !canPublishAnnouncement"
											/>
											<span>
												<span class="block type-body-strong text-ink">
													{{ __('Also publish announcement') }}
												</span>
												<span class="mt-1 block type-caption text-ink/65">
													{{
														__(
															'Recommended when this event is for guardians or students and should appear in Communications as well as the calendar.'
														)
													}}
												</span>
											</span>
										</label>

										<p
											v-if="publishAnnouncementBlockedReason"
											class="mt-3 type-caption text-amber-800"
										>
											{{ publishAnnouncementBlockedReason }}
										</p>

										<div v-if="schoolEventForm.publish_announcement" class="mt-4 space-y-1">
											<label class="type-label">{{ __('Announcement message (optional)') }}</label>
											<FormControl
												type="textarea"
												:rows="5"
												:model-value="schoolEventForm.announcement_message"
												:disabled="submitting"
												:placeholder="
													__('What should families or students read in Communications?')
												"
												@update:modelValue="
													value => updateSchoolEventField('announcement_message', value)
												"
											/>
											<p class="type-caption text-ink/60">
												{{ __('If you leave this blank, the event description above is reused.') }}
											</p>
										</div>
									</div>

									<p
										v-if="schoolEventForm.audience_type === 'Custom Users'"
										class="type-caption text-ink/65"
									>
										{{ __('Custom Users audience will include you as the initial participant.') }}
									</p>
								</section>
							</form>
						</div>

						<footer
							class="if-overlay__footer flex flex-wrap items-center justify-end gap-2 px-6 pb-6"
						>
							<button
								type="button"
								class="if-button if-button--secondary"
								:disabled="submitting"
								@click="emitClose('programmatic')"
							>
								{{ __('Cancel') }}
							</button>
							<button
								type="button"
								class="if-button if-button--primary"
								:disabled="submitting"
								@click="submit"
							>
								{{ submitLabel }}
							</button>
						</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon, FormControl, Spinner } from 'frappe-ui';

import { formatHumanDateTimeFields } from '@/lib/datetime';
import { __ } from '@/lib/i18n';
import {
	createMeetingQuick,
	createSchoolEventQuick,
	getEventQuickCreateOptions,
	getMeetingTeamAttendees,
	searchMeetingAttendees,
	suggestMeetingRooms,
	suggestMeetingSlots,
} from '@/lib/services/calendar/eventQuickCreateService';

import type {
	AttendeeKindOption,
	LocationOption,
	Response as EventQuickCreateOptionsResponse,
	SelectOption,
} from '@/types/contracts/calendar/get_event_quick_create_options';
import type { MeetingAttendeeInput } from '@/types/contracts/calendar/meeting_quick_create_shared';
import type {
	MeetingAttendee,
	MeetingAttendeeKind,
	MeetingRoomSuggestion,
	MeetingSlotSuggestion,
} from '@/types/contracts/calendar/meeting_quick_create_shared';

type EventType = 'meeting' | 'school_event';
type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type MeetingMode = 'ad_hoc' | 'team';
type MeetingFormat = 'in_person' | 'virtual' | 'hybrid';
type MeetingFormatOption = { value: MeetingFormat; label: string };
type TypeOption = { value: EventType; label: string; enabled: boolean };

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	eventType?: EventType | null;
	lockEventType?: boolean;
	prefillSchool?: string | null;
	prefillTeam?: string | null;
	meetingMode?: MeetingMode | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
	(e: 'done', payload?: Record<string, unknown>): void;
}>();

const zIndex = computed(() => props.zIndex ?? 60);

const optionsLoading = ref(false);
const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const errorCode = ref<string | null>(null);
const attendeePanelMessage = ref<string | null>(null);

const options = ref<EventQuickCreateOptionsResponse | null>(null);
const activeType = ref<EventType>('meeting');
const initialFocus = ref<HTMLElement | null>(null);
const commonTimesSection = ref<HTMLElement | null>(null);
const roomSuggestionsSection = ref<HTMLElement | null>(null);

const attendeeSearchQuery = ref('');
const attendeeSearchLoading = ref(false);
const attendeeSearchResults = ref<MeetingAttendee[]>([]);
const attendeeSearchNotes = ref<string[]>([]);

const selectedAttendees = ref<MeetingAttendee[]>([]);
const selectedAttendeeKinds = ref<MeetingAttendeeKind[]>([]);
const lockedTeamAttendeeUsers = ref<string[]>([]);

const teamHydrating = ref(false);
const teamHydratedFor = ref<string | null>(null);

const slotLoading = ref(false);
const slotSearchPerformed = ref(false);
const slotSuggestions = ref<MeetingSlotSuggestion[]>([]);
const fallbackSlotSuggestions = ref<MeetingSlotSuggestion[]>([]);
const slotNotes = ref<string[]>([]);

const roomLoading = ref(false);
const roomSearchPerformed = ref(false);
const roomSuggestions = ref<MeetingRoomSuggestion[]>([]);
const roomNotes = ref<string[]>([]);

let attendeeSearchTimer: number | undefined;
let attendeeSearchRequestSeq = 0;
let slotRequestSeq = 0;
let roomRequestSeq = 0;
let applyingSlotResponse = false;

const meetingForm = reactive({
	meeting_name: '',
	school: '',
	team: '',
	date: '',
	start_time: '',
	end_time: '',
	date_from: '',
	date_to: '',
	day_start_time: '',
	day_end_time: '',
	duration_minutes: '60',
	location: '',
	location_type: '',
	meeting_category: '',
	virtual_meeting_link: '',
	agenda: '',
	meeting_format: 'in_person' as MeetingFormat,
});

const schoolEventForm = reactive({
	subject: '',
	school: '',
	starts_on: '',
	ends_on: '',
	audience_type: '',
	event_category: '',
	all_day: false,
	location: '',
	description: '',
	audience_team: '',
	audience_student_group: '',
	include_guardians: false,
	include_students: false,
	publish_announcement: false,
	announcement_message: '',
});

const meetingFormatOptions: MeetingFormatOption[] = [
	{ value: 'in_person', label: __('In person') },
	{ value: 'virtual', label: __('Virtual') },
	{ value: 'hybrid', label: __('Hybrid') },
];

const typeLocked = computed(() => Boolean(props.lockEventType && props.eventType));
const schoolLocked = computed(() => Boolean(typeLocked.value && props.prefillSchool));

const effectiveMeetingMode = computed<MeetingMode>(() => {
	if (props.meetingMode === 'team' || props.meetingMode === 'ad_hoc') return props.meetingMode;
	return props.prefillTeam ? 'team' : 'ad_hoc';
});

const teamFieldLocked = computed(
	() => effectiveMeetingMode.value === 'team' && Boolean(props.prefillTeam)
);

const hasMeetingAccess = computed(() => Boolean(options.value?.can_create_meeting));
const hasSchoolEventAccess = computed(() => Boolean(options.value?.can_create_school_event));

const overlayTitle = computed(() => {
	if (hasMeetingAccess.value && !hasSchoolEventAccess.value) return __('Schedule meeting');
	return __('Create event');
});

const overlayDescription = computed(() => {
	if (activeType.value === 'meeting') {
		return __(
			'Invite colleagues, students, or guardians, rank common free times, and pick an available room without leaving Staff Home.'
		);
	}
	return __(
		'Create a school event with the same validations and workflows as the core calendar DocTypes.'
	);
});

const meetingModeTitle = computed(() =>
	effectiveMeetingMode.value === 'team' ? __('Team scheduling') : __('Ad-hoc scheduling')
);

const meetingModeDescription = computed(() => {
	if (effectiveMeetingMode.value === 'team') {
		return __(
			'The team context owns the core attendee list. You can still add extra people around that team.'
		);
	}
	return __(
		'Start from the people you need, then let the system rank common times and free rooms.'
	);
});

const meetingModeBadge = computed(() =>
	effectiveMeetingMode.value === 'team' ? __('Team context') : __('Flexible attendee list')
);

const canSwitchType = computed(
	() => !typeLocked.value && !submitting.value && !optionsLoading.value
);

const typeOptions = computed<TypeOption[]>(() => [
	{ value: 'meeting', label: __('Meeting'), enabled: hasMeetingAccess.value },
	{ value: 'school_event', label: __('School event'), enabled: hasSchoolEventAccess.value },
]);

const attendeeKindOptions = computed<AttendeeKindOption[]>(
	() => options.value?.attendee_kinds || []
);
const employeeAttendeeKindOption = computed(
	() => attendeeKindOptions.value.find(option => option.value === 'employee') || null
);
const nonEmployeeInviteScopeOptions = computed(() =>
	attendeeKindOptions.value.filter(
		option => option.value === 'student' || option.value === 'guardian'
	)
);

const teamSelectOptions = computed<SelectOption[]>(() => [
	{
		value: '',
		label:
			effectiveMeetingMode.value === 'team' ? __('Select team') : __('Select team to bulk-add'),
	},
	...(options.value?.teams || []),
]);

const schoolEventTeamSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: __('Select team') },
	...(options.value?.teams || []),
]);

const schoolSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: __('Select school') },
	...(options.value?.schools || []),
]);

const locationsBySchool = computed<Record<string, LocationOption[]>>(
	() => options.value?.locations_by_school || {}
);

const locationTypesBySchool = computed<Record<string, SelectOption[]>>(
	() => options.value?.location_types_by_school || {}
);

function schoolScopedLocationRows(school: string, fallback: LocationOption[] = []) {
	const schoolKey = String(school || '').trim();
	if (!schoolKey) return fallback;
	return locationsBySchool.value[schoolKey] || fallback;
}

function schoolScopedLocationTypeRows(school: string, fallback: SelectOption[] = []) {
	const schoolKey = String(school || '').trim();
	if (!schoolKey) return fallback;
	return locationTypesBySchool.value[schoolKey] || fallback;
}

const studentGroupSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: __('Select student group') },
	...(options.value?.student_groups || []),
]);

const meetingLocationRows = computed<LocationOption[]>(() => {
	const schoolRows = schoolScopedLocationRows(meetingForm.school, options.value?.locations || []);
	const selectedType = String(meetingForm.location_type || '').trim();
	if (!selectedType) return schoolRows;
	return schoolRows.filter(row => row.location_type === selectedType);
});

const meetingLocationTypeSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: __('All room types') },
	...schoolScopedLocationTypeRows(meetingForm.school, options.value?.location_types || []),
]);

const meetingLocationSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: __('No location') },
	...meetingLocationRows.value.map(row => ({
		value: row.value,
		label: row.label,
	})),
]);

const schoolEventLocationSelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: __('No location') },
	...schoolScopedLocationRows(schoolEventForm.school, options.value?.locations || []).map(row => ({
		value: row.value,
		label: row.label,
	})),
]);

const meetingCategorySelectOptions = computed<SelectOption[]>(() => [
	{ value: '', label: __('No category') },
	...((options.value?.meeting_categories || []).map(value => ({
		value,
		label: value,
	})) as SelectOption[]),
]);

const schoolEventCategorySelectOptions = computed<SelectOption[]>(
	() =>
		(options.value?.school_event_categories || []).map(value => ({
			value,
			label: value,
		})) as SelectOption[]
);

const audienceTypeSelectOptions = computed<SelectOption[]>(
	() =>
		(options.value?.audience_types || []).map(value => ({
			value,
			label: value,
		})) as SelectOption[]
);

const announcementPublishCapability = computed(() => options.value?.announcement_publish);

const publishAnnouncementBlockedReason = computed(() => {
	if (!announcementPublishCapability.value?.enabled) {
		return (
			announcementPublishCapability.value?.blocked_reason ||
			__('You do not currently have access to publish org communications from this workflow.')
		);
	}
	if (schoolEventForm.audience_type === 'Custom Users') {
		return __(
			'Custom Users events can stay calendar-only here. Publish a separate communication if you need message history.'
		);
	}
	if (schoolEventForm.audience_type === 'Employees in Team' && schoolEventForm.include_students) {
		return __("Team announcements cannot mirror 'Include students' from this event audience.");
	}
	return '';
});

const canPublishAnnouncement = computed(
	() =>
		Boolean(announcementPublishCapability.value?.enabled) &&
		!publishAnnouncementBlockedReason.value
);

const submitLabel = computed(() => {
	if (activeType.value === 'meeting') return __('Create meeting');
	return schoolEventForm.publish_announcement
		? __('Create event and publish')
		: __('Create school event');
});

const selectedAttendeeCountLabel = computed(() => {
	const invitees = selectedAttendees.value.length;
	return invitees === 1
		? __('{0} invitee + organizer', [invitees])
		: __('{0} invitees + organizer', [invitees]);
});

const selectedAttendeeInputs = computed<MeetingAttendeeInput[]>(() =>
	selectedAttendees.value.map(attendee => ({
		user: attendee.value,
		kind: attendee.kind,
		label: attendee.label,
	}))
);
const includeStudentAttendees = computed(() => selectedAttendeeKinds.value.includes('student'));
const includeGuardianAttendees = computed(() => selectedAttendeeKinds.value.includes('guardian'));

function hasSelectedAttendeesOfKind(kind: MeetingAttendeeKind) {
	return selectedAttendees.value.some(attendee => attendee.kind === kind);
}

const attendeeScopeSafetyMessage = computed(() => {
	if (includeStudentAttendees.value && includeGuardianAttendees.value) {
		return __('Students and guardians will appear in search and can receive this meeting invite.');
	}
	if (includeStudentAttendees.value) {
		return __('Students will appear in search and can receive this meeting invite.');
	}
	if (includeGuardianAttendees.value) {
		return __('Guardians will appear in search and can receive this meeting invite.');
	}
	return '';
});

const inviteScopeMismatchMessage = computed(() => {
	if (!includeStudentAttendees.value && hasSelectedAttendeesOfKind('student')) {
		return __(
			'Remove selected student invitees or re-enable Students before creating the meeting.'
		);
	}
	if (!includeGuardianAttendees.value && hasSelectedAttendeesOfKind('guardian')) {
		return __(
			'Remove selected guardian invitees or re-enable Guardians before creating the meeting.'
		);
	}
	return '';
});

const availableSearchResults = computed(() =>
	attendeeSearchResults.value.filter(attendee => !isSelectedAttendee(attendee.value))
);

const roomCapacityTarget = computed(() => selectedAttendees.value.length + 1);
const showRoomAssistant = computed(() => meetingForm.meeting_format !== 'virtual');
const showStudentConflictRecovery = computed(
	() =>
		activeType.value === 'meeting' &&
		Boolean(errorMessage.value) &&
		errorCode.value === 'StudentAvailabilityConflictError'
);
const showRoomConflictRecovery = computed(
	() =>
		activeType.value === 'meeting' &&
		showRoomAssistant.value &&
		Boolean(errorMessage.value) &&
		errorCode.value === 'LocationConflictError'
);

const exactMatchSummary = computed(() => {
	if (!showRoomAssistant.value) {
		return slotSuggestions.value.length === 1
			? __('{0} exact match', [slotSuggestions.value.length])
			: __('{0} exact matches', [slotSuggestions.value.length]);
	}
	return slotSuggestions.value.length === 1
		? __('{0} room-safe match', [slotSuggestions.value.length])
		: __('{0} room-safe matches', [slotSuggestions.value.length]);
});

function emitAfterLeave() {
	emit('after-leave');
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

function cleanupTimers() {
	if (attendeeSearchTimer) {
		window.clearTimeout(attendeeSearchTimer);
		attendeeSearchTimer = undefined;
	}
}

function resolveSiteTimeZone(): string | undefined {
	if (typeof window === 'undefined') return undefined;
	const globalAny = window as unknown as Record<string, any>;
	const siteTz = String(globalAny.frappe?.boot?.sysdefaults?.time_zone || '').trim();
	return siteTz || Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
}

function zonedDateTimeParts(date: Date) {
	const formatter = new Intl.DateTimeFormat('en-CA', {
		timeZone: resolveSiteTimeZone(),
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
		hour12: false,
	});
	const parts = formatter.formatToParts(date);
	const lookup: Record<string, string> = {};
	for (const part of parts) {
		if (part.type === 'literal') continue;
		lookup[part.type] = part.value;
	}
	return lookup;
}

function dateInputWithOffsetDays(offsetDays = 0) {
	const date = new Date(Date.now() + offsetDays * 24 * 60 * 60 * 1000);
	const parts = zonedDateTimeParts(date);
	return `${parts.year}-${parts.month}-${parts.day}`;
}

function timeInputWithOffset(offsetMinutes = 0) {
	const date = new Date(Date.now() + offsetMinutes * 60 * 1000);
	const parts = zonedDateTimeParts(date);
	return `${parts.hour}:${parts.minute}`;
}

function addMinutesToTime(timeValue: string, minutesToAdd: number) {
	const match = String(timeValue || '')
		.trim()
		.match(/^(\d{2}):(\d{2})/);
	if (!match) return '';
	const hours = Number.parseInt(match[1] || '0', 10);
	const minutes = Number.parseInt(match[2] || '0', 10);
	if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return '';
	const total = (((hours * 60 + minutes + minutesToAdd) % (24 * 60)) + 24 * 60) % (24 * 60);
	const normalizedHours = String(Math.floor(total / 60)).padStart(2, '0');
	const normalizedMinutes = String(total % 60).padStart(2, '0');
	return `${normalizedHours}:${normalizedMinutes}`;
}

function makeClientRequestId() {
	if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
		return crypto.randomUUID();
	}
	return `evt_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function parseDateTime(value: string) {
	const normalized = String(value || '').trim();
	if (!normalized) return null;
	const date = new Date(normalized);
	if (Number.isNaN(date.getTime())) return null;
	return date;
}

function parseTimeToMinutes(value: string) {
	const match = String(value || '')
		.trim()
		.match(/^(\d{2}):(\d{2})/);
	if (!match) return null;
	const hours = Number.parseInt(match[1] || '0', 10);
	const minutes = Number.parseInt(match[2] || '0', 10);
	if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return null;
	return hours * 60 + minutes;
}

function coerceDurationMinutes(value: string | number) {
	const parsed = Number.parseInt(String(value || '').trim(), 10);
	if (!Number.isFinite(parsed) || parsed < 15 || parsed > 240) return null;
	return parsed;
}

function parseOverlayServerMessages(raw: unknown): string | null {
	if (typeof raw !== 'string' || !raw.trim()) {
		return null;
	}

	try {
		const entries = JSON.parse(raw);
		if (!Array.isArray(entries)) return raw.trim();
		const lines = entries
			.map(entry => {
				if (typeof entry !== 'string') return String(entry || '');
				try {
					const payload = JSON.parse(entry);
					return typeof payload?.message === 'string' ? payload.message : entry;
				} catch {
					return entry;
				}
			})
			.filter(line => typeof line === 'string' && line.trim());
		return lines.length ? lines.join('\n').replace(/<br\s*\/?>/gi, '\n') : null;
	} catch {
		return raw.trim().replace(/<br\s*\/?>/gi, '\n');
	}
}

function extractOverlayErrorMessage(error: unknown, fallback = 'Unable to create event.') {
	if (!error) return fallback;
	if (typeof error === 'string' && error.trim()) return error;

	const maybe = error as Record<string, unknown> & {
		response?: Record<string, unknown>;
	};
	const serverMessage =
		parseOverlayServerMessages(maybe.response?._server_messages) ||
		parseOverlayServerMessages(maybe._server_messages) ||
		parseOverlayServerMessages(maybe.response?._messages) ||
		parseOverlayServerMessages(maybe._messages);
	if (serverMessage) return serverMessage;

	const candidates = [
		maybe.response?.message,
		maybe.message,
		maybe.response?.statusText,
		maybe.response?.exception,
		maybe.exception,
		maybe.response?.exc,
		maybe.exc,
	];
	for (const candidate of candidates) {
		if (typeof candidate === 'string' && candidate.trim()) {
			return candidate;
		}
		if (
			candidate &&
			typeof candidate === 'object' &&
			'message' in candidate &&
			typeof (candidate as Record<string, unknown>).message === 'string' &&
			(candidate as Record<string, unknown>).message
		) {
			return String((candidate as Record<string, unknown>).message);
		}
	}

	return fallback;
}

function normalizeOverlayErrorCode(value: unknown): string | null {
	if (typeof value !== 'string') return null;
	const normalized = value.trim();
	return normalized || null;
}

function extractOverlayErrorCode(
	error: unknown,
	message: string | null = typeof error === 'string' ? error : null
) {
	let fallbackCode: string | null = null;
	if (error && typeof error === 'object') {
		const maybe = error as Record<string, unknown> & {
			response?: Record<string, unknown>;
		};
		const responseMessage = maybe.response?.message;
		const candidates = [
			maybe.code,
			maybe.excType,
			maybe.exc_type,
			maybe.response?.exc_type,
			maybe.response?.excType,
			typeof responseMessage === 'object' && responseMessage
				? (responseMessage as Record<string, unknown>).code
				: null,
		];
		for (const candidate of candidates) {
			const code = normalizeOverlayErrorCode(candidate);
			if (!code) continue;
			if (code === 'ValidationError' || code === 'frappe.exceptions.ValidationError') {
				fallbackCode = code;
				continue;
			}
			return code;
		}
	}

	const effectiveMessage =
		typeof message === 'string' ? message : extractOverlayErrorMessage(error, '');
	if (effectiveMessage.startsWith('Student availability conflict')) {
		return 'StudentAvailabilityConflictError';
	}
	if (
		effectiveMessage.startsWith('Location ') &&
		effectiveMessage.includes(' is already booked')
	) {
		return 'LocationConflictError';
	}
	return fallbackCode;
}

function clearErrorState() {
	errorMessage.value = null;
	errorCode.value = null;
}

function setErrorState(message: string | null, code: string | null = null) {
	if (!message) {
		clearErrorState();
		return;
	}
	errorMessage.value = message;
	errorCode.value = code;
}

function resetSlotSuggestions() {
	if (applyingSlotResponse) return;
	slotSearchPerformed.value = false;
	slotSuggestions.value = [];
	fallbackSlotSuggestions.value = [];
	slotNotes.value = [];
}

function resetRoomSuggestions() {
	roomSearchPerformed.value = false;
	roomSuggestions.value = [];
	roomNotes.value = [];
}

function resetAttendeeSearchState() {
	attendeeSearchQuery.value = '';
	attendeeSearchLoading.value = false;
	attendeeSearchResults.value = [];
	attendeeSearchNotes.value = [];
	attendeePanelMessage.value = null;
}

function resetOverlayState() {
	clearErrorState();
	options.value = null;
	resetAttendeeSearchState();
	selectedAttendees.value = [];
	selectedAttendeeKinds.value = [];
	lockedTeamAttendeeUsers.value = [];
	teamHydrating.value = false;
	teamHydratedFor.value = null;
	resetSlotSuggestions();
	resetRoomSuggestions();
}

function initializeForms() {
	const defaults = options.value?.defaults;
	const today = dateInputWithOffsetDays(0);
	const endOfSearchWindow = dateInputWithOffsetDays(5);
	const startTime = defaults?.day_start_time || timeInputWithOffset(0);
	const duration = String(defaults?.duration_minutes || 60);
	const computedEnd = addMinutesToTime(startTime, Number.parseInt(duration, 10) || 60);
	const endTime = computedEnd || defaults?.day_end_time || timeInputWithOffset(60);
	const hostSchool =
		props.prefillSchool || defaults?.school || options.value?.schools?.[0]?.value || '';

	meetingForm.meeting_name = '';
	meetingForm.school = hostSchool;
	meetingForm.team = props.prefillTeam || '';
	meetingForm.date = today;
	meetingForm.start_time = startTime;
	meetingForm.end_time = endTime;
	meetingForm.date_from = today;
	meetingForm.date_to = endOfSearchWindow;
	meetingForm.day_start_time = defaults?.day_start_time || startTime;
	meetingForm.day_end_time = defaults?.day_end_time || endTime;
	meetingForm.duration_minutes = duration;
	meetingForm.location = '';
	meetingForm.location_type = '';
	meetingForm.meeting_category = '';
	meetingForm.virtual_meeting_link = '';
	meetingForm.agenda = '';
	meetingForm.meeting_format = 'in_person';

	schoolEventForm.subject = '';
	schoolEventForm.school = hostSchool;
	schoolEventForm.starts_on = `${today}T${startTime}`;
	schoolEventForm.ends_on = `${today}T${endTime}`;
	schoolEventForm.audience_type = options.value?.audience_types?.[0] || '';
	schoolEventForm.event_category = options.value?.school_event_categories?.[0] || '';
	schoolEventForm.all_day = false;
	schoolEventForm.location = '';
	schoolEventForm.description = '';
	schoolEventForm.audience_team = props.prefillTeam || '';
	schoolEventForm.audience_student_group = '';
	schoolEventForm.include_guardians = false;
	schoolEventForm.include_students = false;
	schoolEventForm.publish_announcement = false;
	schoolEventForm.announcement_message = '';

	const availableKinds = (options.value?.attendee_kinds || []).map(option => option.value);
	selectedAttendeeKinds.value = availableKinds.includes('employee')
		? ['employee']
		: availableKinds.slice(0, 1);
}

function initializeActiveType() {
	const requested = props.eventType || null;
	const canMeeting = hasMeetingAccess.value;
	const canSchoolEvent = hasSchoolEventAccess.value;

	if (requested && (requested === 'meeting' ? canMeeting : canSchoolEvent)) {
		activeType.value = requested;
		return;
	}
	if (canMeeting) {
		activeType.value = 'meeting';
		return;
	}
	if (canSchoolEvent) {
		activeType.value = 'school_event';
	}
}

function setMeetingFormat(nextFormat: MeetingFormat) {
	meetingForm.meeting_format = nextFormat;
	clearErrorState();
	if (nextFormat === 'virtual') {
		meetingForm.location = '';
		resetRoomSuggestions();
	}
}

function setActiveType(nextType: string) {
	const safeType = nextType === 'school_event' ? 'school_event' : 'meeting';
	const allowed = safeType === 'meeting' ? hasMeetingAccess.value : hasSchoolEventAccess.value;
	if (!allowed || !canSwitchType.value) return;
	activeType.value = safeType;
	clearErrorState();
}

function updateMeetingField(field: keyof typeof meetingForm, value: unknown) {
	if (field === 'meeting_format') {
		setMeetingFormat((String(value || '').trim() as MeetingFormat) || 'in_person');
		return;
	}
	(meetingForm as Record<string, string>)[field] = String(value || '').trim();
	clearErrorState();
	if (field === 'team') {
		attendeePanelMessage.value = null;
	}
}

function updateSchoolEventField(field: keyof typeof schoolEventForm, value: unknown) {
	(schoolEventForm as Record<string, unknown>)[field] = String(value || '').trim();
	if (field === 'audience_type') {
		if (schoolEventForm.audience_type !== 'Employees in Team') {
			schoolEventForm.audience_team = '';
		}
		if (schoolEventForm.audience_type !== 'Students in Student Group') {
			schoolEventForm.audience_student_group = '';
		}
		if (!['All Students', 'Students in Student Group'].includes(schoolEventForm.audience_type)) {
			schoolEventForm.include_guardians = false;
		}
		if (!['All Guardians', 'All Employees'].includes(schoolEventForm.audience_type)) {
			schoolEventForm.include_students = false;
		}
	}
	clearErrorState();
}

watch(
	() => canPublishAnnouncement.value,
	canPublish => {
		if (!canPublish) {
			schoolEventForm.publish_announcement = false;
		}
	}
);

function updateAttendeeSearchQuery(value: unknown) {
	attendeeSearchQuery.value = String(value || '').trimStart();
	clearErrorState();
}

function attendeeKindLabel(kind: MeetingAttendeeKind) {
	switch (kind) {
		case 'employee':
			return __('Employee');
		case 'student':
			return __('Student');
		case 'guardian':
			return __('Guardian');
		default:
			return kind;
	}
}

function isAttendeeKindSelected(kind: MeetingAttendeeKind) {
	return selectedAttendeeKinds.value.includes(kind);
}

function toggleNonEmployeeInviteScope(kind: MeetingAttendeeKind) {
	if (kind === 'employee') return;
	if (isAttendeeKindSelected(kind)) {
		selectedAttendeeKinds.value = selectedAttendeeKinds.value.filter(value => value !== kind);
		return;
	}
	const next = new Set(selectedAttendeeKinds.value);
	if (employeeAttendeeKindOption.value) {
		next.add('employee');
	}
	next.add(kind);
	selectedAttendeeKinds.value = Array.from(next);
}

function isSelectedAttendee(userId: string) {
	return selectedAttendees.value.some(attendee => attendee.value === userId);
}

function isLockedTeamAttendee(userId: string) {
	return lockedTeamAttendeeUsers.value.includes(userId);
}

function mergeSelectedAttendees(attendees: MeetingAttendee[]) {
	if (!attendees.length) return 0;

	const existing = new Set(selectedAttendees.value.map(attendee => attendee.value));
	const next = [...selectedAttendees.value];
	let added = 0;

	for (const attendee of attendees) {
		if (!attendee.value || existing.has(attendee.value)) continue;
		existing.add(attendee.value);
		next.push(attendee);
		added += 1;
	}

	selectedAttendees.value = next;
	return added;
}

function applyLockedTeamAttendees(attendees: MeetingAttendee[]) {
	const lockedUsers = attendees.map(attendee => attendee.value).filter(Boolean);
	const lockedUserSet = new Set(lockedUsers);
	const unlockedExtras = selectedAttendees.value.filter(
		attendee => !lockedTeamAttendeeUsers.value.includes(attendee.value)
	);
	selectedAttendees.value = [
		...attendees,
		...unlockedExtras.filter(attendee => !lockedUserSet.has(attendee.value)),
	];
	lockedTeamAttendeeUsers.value = lockedUsers;
}

function addAttendee(attendee: MeetingAttendee) {
	clearErrorState();
	const added = mergeSelectedAttendees([attendee]);
	attendeePanelMessage.value = added
		? __('{0} added to the meeting.', [attendee.label])
		: __('{0} is already in the attendee list.', [attendee.label]);
}

function removeAttendee(userId: string) {
	if (isLockedTeamAttendee(userId)) {
		attendeePanelMessage.value = __('Team attendees are locked by the current entry context.');
		return;
	}
	clearErrorState();
	selectedAttendees.value = selectedAttendees.value.filter(attendee => attendee.value !== userId);
	attendeePanelMessage.value = null;
}

async function runAttendeeSearch() {
	const query = attendeeSearchQuery.value.trim();
	if (!props.open || activeType.value !== 'meeting' || query.length < 2) {
		attendeeSearchLoading.value = false;
		attendeeSearchResults.value = [];
		attendeeSearchNotes.value = [];
		return;
	}

	const requestSeq = ++attendeeSearchRequestSeq;
	attendeeSearchLoading.value = true;

	try {
		const response = await searchMeetingAttendees({
			query,
			attendee_kinds: selectedAttendeeKinds.value,
			limit: 12,
		});
		if (requestSeq !== attendeeSearchRequestSeq) return;
		attendeeSearchResults.value = response.results || [];
		attendeeSearchNotes.value = response.notes || [];
	} catch (error) {
		if (requestSeq !== attendeeSearchRequestSeq) return;
		attendeeSearchResults.value = [];
		attendeeSearchNotes.value = [];
		setErrorState(extractOverlayErrorMessage(error, 'Unable to search for meeting attendees.'));
	} finally {
		if (requestSeq === attendeeSearchRequestSeq) {
			attendeeSearchLoading.value = false;
		}
	}
}

async function addTeamAttendees(optionsArg?: { auto?: boolean }) {
	if (teamHydrating.value) return;
	if (!meetingForm.team) {
		setErrorState(__('Choose a team before loading team attendees.'));
		return;
	}
	if (optionsArg?.auto && teamHydratedFor.value === meetingForm.team) return;

	const requestedTeam = meetingForm.team;
	teamHydrating.value = true;
	clearErrorState();

	try {
		const response = await getMeetingTeamAttendees({ team: requestedTeam });
		if (meetingForm.team !== requestedTeam) return;
		const teamMembers = response.results || [];

		if (effectiveMeetingMode.value === 'team') {
			applyLockedTeamAttendees(teamMembers);
			attendeePanelMessage.value = teamMembers.length
				? teamMembers.length === 1
					? __('{0} team attendee loaded.', [teamMembers.length])
					: __('{0} team attendees loaded.', [teamMembers.length])
				: __('The selected team has no active users to invite.');
		} else {
			const added = mergeSelectedAttendees(teamMembers);
			attendeePanelMessage.value = !teamMembers.length
				? __('The selected team has no active users to invite.')
				: added
					? added === 1
						? __('Added {0} team attendee.', [added])
						: __('Added {0} team attendees.', [added])
					: __('All team members are already in the attendee list.');
		}

		teamHydratedFor.value = requestedTeam;
		if (!optionsArg?.auto && attendeeSearchQuery.value.trim().length >= 2) {
			void runAttendeeSearch();
		}
	} catch (error) {
		setErrorState(extractOverlayErrorMessage(error, 'Unable to load team attendees.'));
	} finally {
		teamHydrating.value = false;
	}
}

function validateCommonTimeRequest() {
	if (!selectedAttendees.value.length) {
		return __('Add at least one attendee before asking for common times.');
	}
	if (showRoomAssistant.value && !meetingForm.school) {
		return __(
			'Host school is required before ranking common times that include room availability.'
		);
	}
	if (!meetingForm.date_from || !meetingForm.date_to) {
		return __('Search start and end dates are required.');
	}
	if (!meetingForm.day_start_time || !meetingForm.day_end_time) {
		return __('Earliest start and latest end are required.');
	}

	const duration = coerceDurationMinutes(meetingForm.duration_minutes);
	if (!duration) {
		return __('Duration must be between 15 and 240 minutes.');
	}

	const start = parseDateTime(`${meetingForm.date_from}T${meetingForm.day_start_time}`);
	const end = parseDateTime(`${meetingForm.date_from}T${meetingForm.day_end_time}`);
	if (!start || !end || end <= start) {
		return __('Latest end must be later than earliest start.');
	}

	const from = parseDateTime(`${meetingForm.date_from}T00:00`);
	const to = parseDateTime(`${meetingForm.date_to}T00:00`);
	if (!from || !to || to < from) {
		return __('Search end date must be on or after search start date.');
	}

	const rangeMs = to.getTime() - from.getTime();
	const rangeDays = Math.floor(rangeMs / (24 * 60 * 60 * 1000)) + 1;
	if (rangeDays > 14) {
		return __('Search window cannot exceed 14 days.');
	}

	return null;
}

function validateRoomRequest() {
	if (meetingForm.meeting_format === 'virtual') {
		return __('Virtual meetings do not require a room.');
	}
	if (!meetingForm.school) return __('Host school is required before suggesting rooms.');
	if (!meetingForm.date) return __('Meeting date is required before suggesting rooms.');
	if (!meetingForm.start_time || !meetingForm.end_time) {
		return __('Start and end times are required before suggesting rooms.');
	}

	const start = parseDateTime(`${meetingForm.date}T${meetingForm.start_time}`);
	const end = parseDateTime(`${meetingForm.date}T${meetingForm.end_time}`);
	if (!start || !end || end <= start) {
		return __('Meeting end time must be later than the start time before suggesting rooms.');
	}

	return null;
}

function validateMeeting() {
	if (!meetingForm.meeting_name) return __('Meeting name is required.');
	if (!meetingForm.school) return __('Host school is required.');
	if (!selectedAttendees.value.length) {
		return __('Add at least one attendee before creating the meeting.');
	}
	if (inviteScopeMismatchMessage.value) return inviteScopeMismatchMessage.value;
	if (!meetingForm.date) return __('Meeting date is required.');
	if (!meetingForm.start_time || !meetingForm.end_time) {
		return __('Start and end times are required.');
	}

	const start = parseDateTime(`${meetingForm.date}T${meetingForm.start_time}`);
	const end = parseDateTime(`${meetingForm.date}T${meetingForm.end_time}`);
	if (!start || !end) return __('Meeting date/time is invalid.');
	if (end <= start) return __('Meeting end time must be later than start time.');
	return null;
}

function validateSchoolEvent() {
	if (!schoolEventForm.subject) return __('Event subject is required.');
	if (!schoolEventForm.school) return __('School is required.');
	if (!schoolEventForm.starts_on || !schoolEventForm.ends_on) {
		return __('Start and end datetime are required.');
	}
	if (!schoolEventForm.audience_type) return __('Audience type is required.');

	const start = parseDateTime(schoolEventForm.starts_on);
	const end = parseDateTime(schoolEventForm.ends_on);
	if (!start || !end) return __('School event datetime is invalid.');
	if (end <= start) return __('School event end datetime must be later than start.');

	if (schoolEventForm.audience_type === 'Employees in Team' && !schoolEventForm.audience_team) {
		return __('Audience team is required for this audience type.');
	}
	if (
		schoolEventForm.audience_type === 'Students in Student Group' &&
		!schoolEventForm.audience_student_group
	) {
		return __('Audience student group is required for this audience type.');
	}
	if (schoolEventForm.publish_announcement) {
		if (!canPublishAnnouncement.value) {
			return (
				publishAnnouncementBlockedReason.value ||
				__('Announcement publishing is not available for this event.')
			);
		}
		if (!schoolEventForm.announcement_message.trim() && !schoolEventForm.description.trim()) {
			return __(
				'Add an announcement message or event description before publishing the announcement.'
			);
		}
	}

	return null;
}

async function findCommonTimes() {
	if (slotLoading.value) return;

	const validationError = validateCommonTimeRequest();
	if (validationError) {
		setErrorState(validationError);
		return;
	}
	clearErrorState();

	const duration = coerceDurationMinutes(meetingForm.duration_minutes);
	if (!duration) {
		setErrorState(__('Duration must be between 15 and 240 minutes.'));
		return;
	}

	slotLoading.value = true;
	slotSearchPerformed.value = true;
	const requestSeq = ++slotRequestSeq;

	try {
		const response = await suggestMeetingSlots({
			attendees: selectedAttendeeInputs.value,
			duration_minutes: duration,
			date_from: meetingForm.date_from,
			date_to: meetingForm.date_to,
			day_start_time: meetingForm.day_start_time,
			day_end_time: meetingForm.day_end_time,
			school: showRoomAssistant.value ? meetingForm.school || null : null,
			location_type: showRoomAssistant.value ? meetingForm.location_type || null : null,
			require_room: showRoomAssistant.value,
		});

		if (requestSeq !== slotRequestSeq) return;

		applyingSlotResponse = true;
		try {
			meetingForm.duration_minutes = String(response.duration_minutes || duration);
			slotSuggestions.value = response.slots || [];
			fallbackSlotSuggestions.value = response.fallback_slots || [];
			slotNotes.value = response.notes || [];
			slotSearchPerformed.value = true;
			if (
				!slotSuggestions.value.length &&
				!fallbackSlotSuggestions.value.length &&
				!slotNotes.value.length
			) {
				slotNotes.value = ['No common times were returned for the selected window.'];
			}
			await nextTick();
		} finally {
			applyingSlotResponse = false;
		}
	} catch (error) {
		if (requestSeq !== slotRequestSeq) return;
		setErrorState(extractOverlayErrorMessage(error, 'Unable to rank common meeting times.'));
	} finally {
		if (requestSeq === slotRequestSeq) {
			slotLoading.value = false;
		}
	}
}

function slotDisplayLabel(slot: MeetingSlotSuggestion) {
	return (
		slot.label ||
		formatHumanDateTimeFields(slot.date, slot.start_time, {
			includeWeekday: true,
			includeYear: false,
		})
	);
}

function slotRoomSummary(slot: MeetingSlotSuggestion) {
	if (!slot.suggested_room) return '';
	const roomCount = slot.available_room_count || 0;
	const roomCountLabel =
		roomCount > 1
			? __(' · {0} rooms free', [roomCount])
			: roomCount === 1
				? __(' · 1 room free')
				: '';
	return __('Best room: {0}{1}', [slot.suggested_room.label, roomCountLabel]);
}

function fallbackRoomSummary(slot: MeetingSlotSuggestion) {
	if (slot.suggested_room) {
		return slotRoomSummary(slot);
	}
	return 'No free room for this slot in the selected school scope.';
}

async function applySuggestedSlot(slot: MeetingSlotSuggestion) {
	clearErrorState();
	meetingForm.date = slot.date;
	meetingForm.start_time = slot.start_time;
	meetingForm.end_time = slot.end_time;
	if (showRoomAssistant.value) {
		meetingForm.location = slot.suggested_room?.value || '';
	}

	const startMinutes = parseTimeToMinutes(slot.start_time);
	const endMinutes = parseTimeToMinutes(slot.end_time);
	if (startMinutes !== null && endMinutes !== null && endMinutes > startMinutes) {
		meetingForm.duration_minutes = String(endMinutes - startMinutes);
	}

	resetRoomSuggestions();
	if (showRoomAssistant.value) {
		await findRoomSuggestions();
	}
}

async function findRoomSuggestions() {
	if (roomLoading.value) return;

	const validationError = validateRoomRequest();
	if (validationError) {
		setErrorState(validationError);
		return;
	}
	clearErrorState();

	roomLoading.value = true;
	roomSearchPerformed.value = true;
	const requestSeq = ++roomRequestSeq;

	try {
		const response = await suggestMeetingRooms({
			school: meetingForm.school,
			date: meetingForm.date,
			start_time: meetingForm.start_time,
			end_time: meetingForm.end_time,
			location_type: meetingForm.location_type || null,
			capacity_needed: roomCapacityTarget.value,
			limit: 8,
		});

		if (requestSeq !== roomRequestSeq) return;

		roomSuggestions.value = response.rooms || [];
		roomNotes.value = response.notes || [];
		if (!roomSuggestions.value.length && !roomNotes.value.length) {
			roomNotes.value = ['No free rooms matched the selected slot.'];
		}
	} catch (error) {
		if (requestSeq !== roomRequestSeq) return;
		setErrorState(extractOverlayErrorMessage(error, 'Unable to suggest meeting rooms.'));
	} finally {
		if (requestSeq === roomRequestSeq) {
			roomLoading.value = false;
		}
	}
}

function applySuggestedRoom(room: MeetingRoomSuggestion) {
	clearErrorState();
	meetingForm.location = room.value;
	if (room.location_type) {
		meetingForm.location_type = room.location_type;
	}
}

async function recoverFromStudentConflict() {
	if (slotLoading.value) return;
	clearErrorState();
	await nextTick();
	commonTimesSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	await findCommonTimes();
}

async function recoverFromRoomConflict() {
	if (roomLoading.value) return;
	clearErrorState();
	await nextTick();
	roomSuggestionsSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	await findRoomSuggestions();
}

async function loadOptions() {
	optionsLoading.value = true;
	clearErrorState();

	try {
		const payload = await getEventQuickCreateOptions();
		options.value = payload;
		initializeActiveType();
		initializeForms();

		if (!payload.can_create_meeting && !payload.can_create_school_event) {
			setErrorState(__('You do not have permission to create meetings or school events.'));
			return;
		}

		if (effectiveMeetingMode.value === 'team' && meetingForm.team) {
			await addTeamAttendees({ auto: true });
		}
	} catch (error) {
		setErrorState(extractOverlayErrorMessage(error, 'Unable to load create-event options.'));
	} finally {
		optionsLoading.value = false;
	}
}

async function submit() {
	if (submitting.value) return;

	const validationError =
		activeType.value === 'meeting' ? validateMeeting() : validateSchoolEvent();
	if (validationError) {
		setErrorState(validationError);
		return;
	}
	clearErrorState();

	submitting.value = true;
	const clientRequestId = makeClientRequestId();

	try {
		let result: Record<string, unknown>;
		if (activeType.value === 'meeting') {
			result = await createMeetingQuick({
				client_request_id: clientRequestId,
				meeting_name: meetingForm.meeting_name,
				school: meetingForm.school || null,
				date: meetingForm.date,
				start_time: meetingForm.start_time,
				end_time: meetingForm.end_time,
				team: effectiveMeetingMode.value === 'team' ? meetingForm.team || null : null,
				location: meetingForm.location || null,
				meeting_category: meetingForm.meeting_category || null,
				virtual_meeting_link: meetingForm.virtual_meeting_link || null,
				agenda: meetingForm.agenda || null,
				visibility_scope: effectiveMeetingMode.value === 'team' ? 'Team & Participants' : null,
				participants: selectedAttendeeInputs.value,
				include_students: includeStudentAttendees.value ? 1 : 0,
				include_guardians: includeGuardianAttendees.value ? 1 : 0,
			});
		} else {
			result = await createSchoolEventQuick({
				client_request_id: clientRequestId,
				subject: schoolEventForm.subject,
				school: schoolEventForm.school,
				starts_on: schoolEventForm.starts_on,
				ends_on: schoolEventForm.ends_on,
				audience_type: schoolEventForm.audience_type,
				event_category: schoolEventForm.event_category || null,
				all_day: schoolEventForm.all_day ? 1 : 0,
				location: schoolEventForm.location || null,
				description: schoolEventForm.description || null,
				audience_team: schoolEventForm.audience_team || null,
				audience_student_group: schoolEventForm.audience_student_group || null,
				include_guardians: schoolEventForm.include_guardians ? 1 : 0,
				include_students: schoolEventForm.include_students ? 1 : 0,
				publish_announcement: schoolEventForm.publish_announcement ? 1 : 0,
				announcement_message: schoolEventForm.announcement_message || null,
				custom_participants: null,
			});
		}

		emitClose('programmatic');
		emit('done', result);
	} catch (error) {
		const message = extractOverlayErrorMessage(error, 'Unable to create event.');
		setErrorState(message, extractOverlayErrorCode(error, message));
	} finally {
		submitting.value = false;
	}
}

watch(
	[attendeeSearchQuery, selectedAttendeeKinds, activeType, () => props.open],
	([query, kinds, type, isOpen]) => {
		cleanupTimers();

		if (!isOpen || type !== 'meeting') {
			attendeeSearchResults.value = [];
			attendeeSearchNotes.value = [];
			attendeeSearchLoading.value = false;
			return;
		}

		const trimmedQuery = String(query || '').trim();
		if (!trimmedQuery || trimmedQuery.length < 2 || !(kinds || []).length) {
			attendeeSearchResults.value = [];
			attendeeSearchNotes.value = [];
			attendeeSearchLoading.value = false;
			return;
		}

		attendeeSearchTimer = window.setTimeout(() => {
			void runAttendeeSearch();
		}, 250);
	},
	{ immediate: true }
);

watch(
	() => selectedAttendees.value,
	() => {
		resetSlotSuggestions();
		if (showRoomAssistant.value) {
			resetRoomSuggestions();
		}
	},
	{ deep: true }
);

watch(
	[
		() => meetingForm.date_from,
		() => meetingForm.date_to,
		() => meetingForm.day_start_time,
		() => meetingForm.day_end_time,
		() => meetingForm.duration_minutes,
		() => meetingForm.location_type,
	],
	() => {
		resetSlotSuggestions();
	}
);

watch(
	[() => meetingForm.school, () => meetingForm.meeting_format, () => meetingForm.location_type],
	() => {
		resetSlotSuggestions();
	}
);

watch(
	[
		() => meetingForm.date,
		() => meetingForm.start_time,
		() => meetingForm.end_time,
		() => meetingForm.school,
		() => meetingForm.meeting_format,
		() => meetingForm.location_type,
	],
	() => {
		resetRoomSuggestions();
		if (meetingForm.meeting_format === 'virtual') {
			meetingForm.location = '';
		}
	}
);

watch(
	() => meetingLocationTypeSelectOptions.value,
	optionsList => {
		const allowed = new Set(optionsList.map(option => option.value));
		if (meetingForm.location_type && !allowed.has(meetingForm.location_type)) {
			meetingForm.location_type = '';
		}
	},
	{ deep: true }
);

watch(
	() => meetingLocationSelectOptions.value,
	optionsList => {
		const allowed = new Set(optionsList.map(option => option.value));
		if (meetingForm.location && !allowed.has(meetingForm.location)) {
			meetingForm.location = '';
		}
	},
	{ deep: true }
);

watch(
	() => schoolEventLocationSelectOptions.value,
	optionsList => {
		const allowed = new Set(optionsList.map(option => option.value));
		if (schoolEventForm.location && !allowed.has(schoolEventForm.location)) {
			schoolEventForm.location = '';
		}
	},
	{ deep: true }
);

watch(
	() => meetingForm.team,
	(nextTeam, previousTeam) => {
		if (!props.open) return;
		if (nextTeam === previousTeam) return;
		teamHydratedFor.value = null;

		if (effectiveMeetingMode.value !== 'team') {
			if (nextTeam) {
				void addTeamAttendees({ auto: true });
			}
			return;
		}

		const previousLockedUsers = new Set(lockedTeamAttendeeUsers.value);
		selectedAttendees.value = selectedAttendees.value.filter(
			attendee => !previousLockedUsers.has(attendee.value)
		);
		lockedTeamAttendeeUsers.value = [];

		if (nextTeam) {
			void addTeamAttendees({ auto: true });
		}
	}
);

watch(
	() => props.open,
	isOpen => {
		if (isOpen) {
			resetOverlayState();
			document.addEventListener('keydown', onKeydown, true);
			void loadOptions();
		} else {
			document.removeEventListener('keydown', onKeydown, true);
			cleanupTimers();
		}
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
	cleanupTimers();
});
</script>
