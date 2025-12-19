<template>
  <div class="staff-shell space-y-6">
    <!-- Header -->
    <header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="type-h1">Announcement Archive</h1>
        <p class="type-meta text-slate-token/70">
          All communications visible to you across your organisation
        </p>
      </div>

      <!-- Date Range Toggles -->
      <div class="flex items-center gap-1 rounded-lg bg-surface-soft p-1">
        <button
          v-for="range in DATE_RANGES"
          :key="range.value"
          @click="filters.date_range = range.value"
          class="px-3 py-1.5 text-xs font-medium rounded-md transition-all"
          :class="
            filters.date_range === range.value
              ? 'bg-white text-ink shadow-sm'
              : 'text-slate-token/60 hover:text-ink hover:bg-white/50'
          "
        >
          {{ range.label }}
        </button>
      </div>
    </header>

    <!-- Filters Bar -->
    <div class="analytics-filters flex flex-wrap items-center gap-3 rounded-xl border border-line-soft bg-surface-glass p-3 shadow-soft">
      <div class="analytics-filters__title text-sm font-semibold text-ink mr-2">
        Filters
      </div>

      <!-- Organization -->
      <FormControl
        v-if="organizationOptions.length > 0"
        type="select"
        :options="organizationOptions"
        v-model="filters.organization"
        class="w-40"
      />

      <!-- School -->
      <FormControl
        v-if="schoolOptions.length > 0"
        type="select"
        :options="schoolOptions"
        v-model="filters.school"
        class="w-40"
      />

      <!-- Team -->
      <FormControl
        v-if="myTeam"
        type="select"
        :options="teamOptions"
        v-model="filters.team"
        class="w-40"
      />

      <!-- Student Group -->
      <FormControl
        v-if="studentGroupOptions.length > 1"
        type="select"
        :options="studentGroupOptions"
        v-model="filters.student_group"
        class="w-40"
      />

       <!-- Interaction Toggle -->
      <label class="flex items-center gap-2 cursor-pointer text-sm text-ink select-none px-2">
        <input type="checkbox" v-model="filters.only_with_interactions" class="rounded border-slate-300 text-jacaranda focus:ring-jacaranda" />
        <span>With interactions</span>
      </label>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-6 items-start h-[calc(100vh-14rem)]">

      <!-- LEFT LIST -->
      <div class="flex flex-col h-full bg-white rounded-xl border border-line-soft shadow-soft overflow-hidden">
        <div class="flex-1 overflow-y-auto p-4 space-y-2">

          <div v-if="orgCommFeed.loading && !feedItems.length" class="py-12 text-center text-slate-token/60">
             <LoadingIndicator />
          </div>

          <div v-else-if="!feedItems.length" class="py-12 text-center">
            <p class="type-h3 text-slate-token/40">No announcements found</p>
            <p class="text-sm text-slate-token/60 mt-1">Try adjusting your filters</p>
          </div>

          <div
            v-for="item in feedItems"
            :key="item.name"
            @click="selectItem(item)"
            class="group relative flex gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all border border-transparent hover:border-line-soft hover:bg-surface-soft hover:shadow-sm"
            :class="selectedComm?.name === item.name ? 'bg-surface-soft ring-1 ring-jacaranda/40' : ''"
          >
            <!-- Priority Indicator -->
            <div
              class="absolute left-0 top-3 bottom-3 w-1 rounded-r-full"
              :class="getPriorityClass(item.priority)"
            ></div>

             <div class="flex-1 pl-3 min-w-0">
               <div class="flex items-start justify-between gap-2">
                 <h3 class="text-sm font-semibold text-ink line-clamp-1 group-hover:text-jacaranda transition-colors">
                   {{ item.title }}
                 </h3>
                 <span class="shrink-0 text-[10px] font-medium uppercase tracking-wider text-slate-token/50 bg-slate-100 px-1.5 py-0.5 rounded">
                   {{ item.status }}
                 </span>
               </div>

               <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-token/60">
                 <span class="inline-flex items-center gap-1">
                   <FeatherIcon name="calendar" class="h-3 w-3" />
                   {{ formatDate(item.publish_from) }}
                 </span>
                 <span>•</span>
                 <span class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-token/70">
                   {{ item.communication_type }}
                 </span>
                 <span v-if="item.portal_surface !== 'Everywhere'" class="bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded">
                    {{ item.portal_surface }}
                 </span>
               </div>

               <p class="mt-2 text-xs text-slate-token/80 line-clamp-2 leading-relaxed">
                 {{ item.snippet }}
               </p>

               <div class="mt-3 flex items-center gap-4">
                 <div class="flex items-center gap-1.5 text-xs text-slate-token/60">
                    <FeatherIcon name="users" class="h-3 w-3" />
                    <span class="truncate max-w-[150px]">{{ item.audience_label }}</span>
                 </div>

                 <!-- Interaction Summary -->
                 <div class="flex items-center gap-3 ml-auto">
                    <div v-if="getInteractionFor(item).self" class="text-xs text-jacaranda font-medium flex items-center gap-1">
                      <FeatherIcon name="check-circle" class="h-3 w-3" />
                      You: {{ getInteractionFor(item).self?.intent_type || 'Responded' }}
                    </div>
                    <div class="flex items-center gap-1 text-xs text-slate-token/50 bg-slate-50 px-2 py-1 rounded">
                       <span>👍 {{ getInteractionStats(item).acks }}</span>
                       <span class="border-l border-slate-200 h-3 mx-1"></span>
                       <span>💬 {{ getInteractionStats(item).comments }}</span>
                    </div>
                 </div>
               </div>
             </div>
          </div>

           <!-- Load More -->
          <div v-if="hasMore" class="pt-2">
            <Button
              variant="subtle"
              class="w-full text-xs"
              :loading="orgCommFeed.loading"
              @click="loadMore"
            >
              Load More
            </Button>
          </div>

        </div>
      </div>

      <!-- RIGHT DETAIL -->
      <div class="h-full bg-white rounded-xl border border-line-soft shadow-soft overflow-hidden flex flex-col relative">
        <div v-if="!selectedComm" class="flex flex-col items-center justify-center h-full text-center p-8 text-slate-token/40">
           <FeatherIcon name="inbox" class="h-10 w-10 mb-3 opacity-50" />
           <p class="type-h3">Select an announcement</p>
           <p class="text-sm mt-1">Click on an item from the list to view details</p>
        </div>

        <div v-else class="flex flex-col h-full">
           <!-- Detail Header -->
           <div class="p-6 border-b border-line-soft bg-slate-50/50">
             <div class="flex flex-col gap-4">


                <div class="flex items-start justify-between gap-4">
                   <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2 mb-2">
                    <Badge :color="getPriorityColor(selectedComm.priority)" size="sm">
                       {{ selectedComm.priority }}
                    </Badge>
                     <span class="text-xs text-slate-token/50">•</span>
                    <span class="text-xs font-medium text-slate-token/70">
                      {{ selectedComm.communication_type }}
                    </span>
                   </div>
                   <h2 class="text-xl font-bold text-ink leading-tight">
                     {{ selectedComm.title }}
                   </h2>
                </div>
              </div>
            </div>

             <div class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-token/70">
                <div class="flex items-center gap-2">
                   <FeatherIcon name="calendar" class="h-4 w-4 text-slate-token/50" />
                   <span>{{ formatDate(selectedComm.publish_from, 'DD MMMM YYYY') }}</span>
                   <span v-if="selectedComm.publish_to" class="text-slate-token/40">→ {{ formatDate(selectedComm.publish_to, 'DD MMM') }}</span>
                </div>
                <div class="flex items-center gap-2">
                   <FeatherIcon name="users" class="h-4 w-4 text-slate-token/50" />
                   <span>{{ selectedComm.audience_label }}</span>
                </div>
             </div>
           </div>

           <!-- Content -->
           <div class="flex-1 overflow-y-auto p-6 text-sm text-ink leading-relaxed prose prose-slate max-w-none">
              <div v-if="fullContent.loading" class="py-10 text-center"><LoadingIndicator /></div>
              <div v-else v-html="fullContent.data?.message || selectedComm.snippet"></div>
           </div>

           <!-- Interactions Footer -->
           <div class="p-4 border-t border-line-soft bg-white z-10 sticky bottom-0">
              <div class="flex items-center justify-between gap-4">

                 <div class="flex gap-2">
                    <Button
                      :variant="getInteractionFor(selectedComm).self ? 'solid' : 'subtle'"
                      :color="getInteractionFor(selectedComm).self ? 'gray' : 'gray'"
                      class="gap-2"
                      @click="acknowledge(selectedComm)"
                      :loading="interactionAction.loading"
                      :disabled="!canInteract(selectedComm)"
                    >
                      <FeatherIcon name="thumbs-up" class="h-4 w-4" />
                      <span>
                        {{ getInteractionFor(selectedComm).self ? 'Acknowledged' : 'Acknowledge' }}
                      </span>
                      <Badge variant="outline" class="bg-white/50 ml-1">
                        {{ getInteractionStats(selectedComm).acks }}
                      </Badge>
                    </Button>

                    <Button
                      variant="subtle"
                      color="gray"
                      class="gap-2"
                      @click="openThread(selectedComm)"
                      :disabled="!selectedComm.allow_public_thread"
                    >
                      <FeatherIcon name="message-square" class="h-4 w-4" />
                      Comments
                      <Badge variant="outline" class="bg-white/50 ml-1">
                        {{ getInteractionStats(selectedComm).comments }}
                      </Badge>
                    </Button>
                 </div>

                 <div v-if="getInteractionFor(selectedComm).self" class="text-xs text-jacaranda font-medium">
                    You responded: {{ getInteractionFor(selectedComm).self?.intent_type }}
                 </div>

              </div>
           </div>
        </div>
      </div>

    </div>

    <!-- Thread Drawer (Reusing SideDrawerList-like or creating a simple drawer)
         User said: "Reuse your existing SideDrawerList component exactly as in MorningBrief."
         However, MorningBrief uses a specific drawer logic. I should check if I can just use a generic drawer for now or if I need to import that component.
         Since I can't easily see usage of SideDrawerList (it was for logs?),
         I will implement a sleek side drawer here for the thread.
    -->
    <Transition name="slide-verify">
      <div v-if="showThreadDrawer" class="fixed inset-0 z-[100] flex justify-end bg-black/20 backdrop-blur-sm" @click.self="showThreadDrawer = false">
        <div class="w-full max-w-md bg-white h-full shadow-strong flex flex-col">
            <div class="p-4 border-b border-line-soft flex items-center justify-between bg-slate-50">
               <h3 class="font-bold text-lg">Comments</h3>
               <Button icon="x" variant="ghost" @click="showThreadDrawer = false" />
            </div>

            <div class="flex-1 overflow-y-auto p-4 space-y-4">
               <div v-if="threadResource.loading" class="text-center py-4"><LoadingIndicator /></div>
               <div v-else-if="!threadResource.data?.length" class="text-center py-8 text-slate-token/60">
                 No comments yet. Start the conversation!
               </div>

               <div v-for="comment in threadResource.data || []" :key="comment.name" class="flex gap-3">
                  <Avatar :label="comment.full_name" size="md" />
                  <div class="flex-1 space-y-1">
                     <div class="flex items-center justify-between">
                        <span class="font-semibold text-sm">{{ comment.full_name }}</span>
                        <span class="text-xs text-slate-token/50">{{ formatDate(comment.creation, 'DD MMM HH:mm') }}</span>
                     </div>
                     <div class="bg-surface-soft rounded-lg rounded-tl-none p-3 text-sm text-ink/90">
                        {{ comment.note }}
                     </div>
                  </div>
               </div>
            </div>

            <div class="p-4 border-t border-line-soft bg-white gap-2 flex flex-col">
                <FormControl
                    type="textarea"
                    placeholder="Write a comment..."
                    v-model="newComment"
                    :rows="2"
                 />
                 <div class="flex justify-end">
                    <Button
                        variant="solid"
                        color="gray"
                        :loading="interactionAction.loading"
                        @click="submitComment"
                        :disabled="!newComment.trim()"
                    >
                        Post Comment
                    </Button>
                 </div>
            </div>
        </div>
      </div>
    </Transition>

  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Avatar, Badge, Button, FeatherIcon, FormControl, LoadingIndicator, createResource } from 'frappe-ui'
import { type ArchiveFilters, type OrgCommunicationListItem, type InteractionSummary } from '@/types/orgCommunication'

const PAGE_LENGTH = 30

const DATE_RANGES = [
  { label: 'Last 7 Days', value: '7d' },
  { label: 'Last 30 Days', value: '30d' },
  { label: 'Last 90 Days', value: '90d' },
  { label: 'YTD', value: 'year' },
  { label: 'All Time', value: 'all' },
] as const

const filters = ref<ArchiveFilters>({
	search: '',
	status: 'PublishedOrArchived',
	priority: 'All',
	portal_surface: 'All',
	communication_type: 'All',
	date_range: '90d',
	only_with_interactions: false,
	team: null,
	student_group: null,
	school: null,
	organization: null,
})

const selectedComm = ref<OrgCommunicationListItem | null>(null)
const showThreadDrawer = ref(false)
const newComment = ref('')
const initialized = ref(false)

const start = ref(0)
const feedItems = ref<OrgCommunicationListItem[]>([])
const hasMore = ref(false)
const interactionSummaries = ref<Record<string, InteractionSummary>>({})

// User Context for Filters
const myTeam = ref<string | null>(null)
const myStudentGroups = ref<Array<{ label: string; value: string }>>([])
const orgChoices = ref<Array<{ label: string; value: string }>>([])
const schoolChoices = ref<Array<{ label: string; value: string; organization?: string | null }>>([])

const organizationOptions = computed(() => [
	{ label: 'All organisations', value: null },
	...orgChoices.value,
])

const schoolOptions = computed(() => {
	const org = filters.value.organization
	const scoped = org
		? schoolChoices.value.filter((s) => s.organization === org)
		: schoolChoices.value
	return [{ label: 'All schools', value: null }, ...scoped]
})

const teamOptions = computed(() => {
	const opts = [{ label: 'All teams', value: null }]
	if (myTeam.value) {
		opts.push({ label: myTeam.value, value: myTeam.value })
	}
	return opts
})

const studentGroupOptions = computed(() => [{ label: 'All groups', value: null }, ...myStudentGroups.value])

let reloadTimer: number | undefined
function queueReload() {
	window.clearTimeout(reloadTimer)
	reloadTimer = window.setTimeout(() => {
		loadFeed(true)
	}, 350)
}

const archiveContext = createResource({
	url: 'ifitwala_ed.api.org_communication_archive.get_archive_context',
	method: 'POST',
	auto: true,
	onSuccess(data) {
		if (!data) return

		myTeam.value = data.my_team || null
		myStudentGroups.value = (data.my_groups || []).map((g: string) => ({
			label: g,
			value: g,
		}))

		orgChoices.value = (data.organizations || []).map((o: any) => ({
			label: o.organization_name || o.name,
			value: o.name,
		}))

		schoolChoices.value = (data.schools || []).map((s: any) => ({
			label: s.school_name || s.name,
			value: s.name,
			organization: s.organization || null,
		}))

		if (data.defaults) {
			filters.value.organization = data.defaults.organization || null
			filters.value.school = data.defaults.school || null
			filters.value.team = data.defaults.team || null
		}

		initialized.value = true
		loadFeed(true)
	},
})

const orgCommFeed = createResource<{
	items: OrgCommunicationListItem[]
	total_count: number
	has_more: boolean
	start: number
	page_length: number
}>({
	url: 'ifitwala_ed.api.org_communication_archive.get_org_communication_feed',
	method: 'POST',
	params: () => ({
		filters: filters.value,
		start: start.value,
		page_length: PAGE_LENGTH,
	}),
	auto: false,
})

const interactionSummaryResource = createResource<Record<string, InteractionSummary>>({
	url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_org_comm_interaction_summary',
	method: 'POST',
	auto: false,
	onSuccess(data) {
		if (data) {
			interactionSummaries.value = { ...interactionSummaries.value, ...data }
		}
	},
})

const fullContent = createResource({
	url: 'ifitwala_ed.api.org_communication_archive.get_org_communication_item',
	method: 'POST',
	auto: false,
})

const threadResource = createResource({
	url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.get_communication_thread',
	method: 'POST',
	auto: false,
})

const interactionAction = createResource({
	url: 'ifitwala_ed.setup.doctype.communication_interaction.communication_interaction.upsert_communication_interaction',
	method: 'POST',
	auto: false,
})

watch(
	filters,
	() => {
		if (!initialized.value) return
		selectedComm.value = null
		queueReload()
	},
	{ deep: true },
)

watch(
	() => filters.value.organization,
	(newOrg, oldOrg) => {
		// During initial load, archiveContext sets defaults; don't thrash filters.
		if (!initialized.value) return

		// School: only clear if current school is not valid in the newly scoped options.
		// (We keep it if it still belongs to the selected org.)
		const allowedSchools = schoolOptions.value.map((o) => o.value)
		if (filters.value.school && !allowedSchools.includes(filters.value.school)) {
			filters.value.school = null
		}

		// Team: DO NOT clear.
		// In this UI, teamOptions is always [All teams] + [My team], so it's always valid.
		// Clearing it here is a classic "why did my filter change?" foot-gun.

		// Student group: safest to clear on org change (groups are org/school-scoped in reality).
		// You can later refine to only clear if invalid once you return scoped groups from server.
		if (oldOrg !== undefined && newOrg !== oldOrg) {
			filters.value.student_group = null
		}
	},
)


watch(
	schoolOptions,
	(options) => {
		const allowed = options.map((o) => o.value)
		if (filters.value.school && !allowed.includes(filters.value.school)) {
			filters.value.school = null
		}
	},
)

function selectItem(item: OrgCommunicationListItem) {
	selectedComm.value = item
	fullContent.submit({ name: item.name })
}

async function loadFeed(reset = false) {
	if (!initialized.value) return

	if (reset) {
		start.value = 0
		feedItems.value = []
		hasMore.value = false
		interactionSummaries.value = {}
		selectedComm.value = null
	}

	const payload = ((await orgCommFeed.fetch()) as any) || {}
	const items = payload.items || []

	feedItems.value = reset ? items : [...feedItems.value, ...items]
	hasMore.value = !!payload.has_more

	const responseStart = typeof payload.start === 'number' ? payload.start : start.value
	start.value = responseStart + items.length

	if (items.length) {
		interactionSummaryResource.submit({ comm_names: items.map((i: OrgCommunicationListItem) => i.name) })
	}

	if (!selectedComm.value && feedItems.value.length) {
		selectItem(feedItems.value[0])
	}
}

function loadMore() {
	if (orgCommFeed.loading || !hasMore.value) return
	loadFeed(false)
}

function getInteractionFor(item: OrgCommunicationListItem): InteractionSummary {
	if (!item) return { counts: {}, self: null }
	return interactionSummaries.value[item.name] ?? { counts: {}, self: null }
}

function getInteractionStats(item: OrgCommunicationListItem) {
	const summary = getInteractionFor(item)
	const acks = summary.counts['Acknowledged'] || 0
	const comments = (summary.counts['Comment'] || 0) + (summary.counts['Question'] || 0)
	return { acks, comments }
}

function canInteract(item: OrgCommunicationListItem) {
	return item.interaction_mode !== 'None'
}

function refreshSummary(names: string[]) {
	if (!names.length) return
	interactionSummaryResource.submit({ comm_names: names })
}

function acknowledge(item: OrgCommunicationListItem) {
	interactionAction.submit(
		{
			org_communication: item.name,
			intent_type: 'Acknowledged',
			surface: 'Portal Feed',
		},
		{
			onSuccess: () => refreshSummary([item.name]),
		},
	)
}

function openThread(item: OrgCommunicationListItem) {
	selectedComm.value = item
	showThreadDrawer.value = true
	threadResource.submit({ org_communication: item.name })
}

function submitComment() {
	if (!selectedComm.value || !newComment.value.trim()) return

	interactionAction.submit(
		{
			org_communication: selectedComm.value.name,
			intent_type: 'Comment',
			note: newComment.value,
			surface: 'Portal Feed',
		},
		{
			onSuccess: () => {
				newComment.value = ''
				threadResource.reload()
				refreshSummary([selectedComm.value!.name])
			},
		},
	)
}

function formatDate(date: string | null, fmt = 'DD MMM') {
	if (!date) return ''
	const d = new Date(date)
	if (isNaN(d.getTime())) return ''

	if (fmt === 'DD MMM') {
		return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
	}
	if (fmt === 'DD MMMM YYYY') {
		return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' })
	}
	if (fmt === 'DD MMM HH:mm') {
		return d.toLocaleDateString('en-GB', {
			day: '2-digit',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit',
			hour12: false,
		})
	}

	return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

function getPriorityClass(priority: string) {
	switch (priority) {
		case 'Critical':
			return 'bg-flame'
		case 'High':
			return 'bg-jacaranda'
		case 'Normal':
			return 'bg-blue-400'
		case 'Low':
			return 'bg-slate-300'
		default:
			return 'bg-slate-200'
	}
}

function getPriorityColor(priority: string) {
	switch (priority) {
		case 'Critical':
			return 'red'
		case 'High':
			return 'purple'
		case 'Normal':
			return 'blue'
		default:
			return 'gray'
	}
}

</script>

<style scoped>
/* Scoped styles/overrides if needed */
.slide-verify-enter-active,
.slide-verify-leave-active {
  transition: opacity 0.3s ease;
}

.slide-verify-enter-from,
.slide-verify-leave-to {
  opacity: 0;
}
</style>
