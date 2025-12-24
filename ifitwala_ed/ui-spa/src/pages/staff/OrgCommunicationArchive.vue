<!-- ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue -->
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
    <div class="analytics-filters ifit-filters flex flex-wrap items-center gap-3 rounded-xl border border-line-soft bg-surface-glass p-3 shadow-soft">
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
				v-if="hasTeamFilter"
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
        <input type="checkbox" v-model="filters.only_with_interactions" class="rounded border-slate-300 text-jacaranda" />
        <span>With interactions</span>
      </label>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-6 items-start h-[calc(100vh-14rem)]">

      <!-- LEFT LIST -->
      <div class="flex flex-col h-full bg-surface-glass rounded-2xl border border-line-soft shadow-soft overflow-hidden">
        <div class="flex-1 overflow-y-auto p-4 space-y-2 bg-sand/20">

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
      <div class="h-full bg-surface-glass rounded-2xl border border-line-soft shadow-soft overflow-hidden flex flex-col relative">
        <div v-if="!selectedComm" class="flex flex-col items-center justify-center h-full text-center p-8 text-slate-token/40">
           <FeatherIcon name="inbox" class="h-10 w-10 mb-3 opacity-50" />
           <p class="type-h3">Select an announcement</p>
           <p class="text-sm mt-1">Click on an item from the list to view details</p>
        </div>

        <div v-else class="flex flex-col h-full">
           <!-- Detail Header -->
           <div class="p-6 border-b border-line-soft bg-surface-soft/70">
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
           <div class="flex-1 overflow-y-auto p-6 text-sm text-ink leading-relaxed">
              <div class="prose prose-slate max-w-none bg-white/80 rounded-2xl border border-line-soft shadow-soft p-6">
                <div v-if="fullContent.loading" class="py-10 text-center"><LoadingIndicator /></div>
                <div v-else v-html="fullContent.data?.message || selectedComm.snippet"></div>
              </div>
           </div>

           <!-- Interactions Footer -->
           <div class="p-4 border-t border-line-soft bg-surface-soft/80 z-10 sticky bottom-0">
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

    <CommentThreadDrawer
      :open="showThreadDrawer"
      title="Comments"
      :rows="threadResource.data || []"
      :loading="threadResource.loading"
      v-model:comment="newComment"
      :submit-loading="interactionAction.loading"
      :format-timestamp="(value) => formatDate(value, 'DD MMM HH:mm')"
      @close="showThreadDrawer = false"
      @submit="submitComment"
    />

  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Badge, Button, FeatherIcon, FormControl, LoadingIndicator, createResource } from 'frappe-ui'
import { type ArchiveFilters, type OrgCommunicationListItem, type InteractionSummary } from '@/types/orgCommunication'
import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue'

const PAGE_LENGTH = 30

const DATE_RANGES = [
  { label: 'Last 7 Days', value: '7d' },
  { label: 'Last 30 Days', value: '30d' },
  { label: 'Last 90 Days', value: '90d' },
  { label: 'YTD', value: 'year' },
  { label: 'All Time', value: 'all' },
] as const

const filters = ref<ArchiveFilters>({
	search_text: '',
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
const hasTeamFilter = computed(() => myTeams.value.length > 0)
const myTeams = ref<Array<{ label: string; value: string }>>([])
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

const teamOptions = computed(() => [
	{ label: 'All teams', value: null },
	...myTeams.value,
])


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

		myTeams.value = Array.isArray(data.my_teams) ? data.my_teams : []


		// Student Groups:
		// - Old shape: string[]
		// - New shape: Array<{ label: string; value: string; ... }>
		const rawGroups = data.my_groups || []
		const normalizedGroups: Array<{ label: string; value: string }> = []

		for (const g of rawGroups) {
			// Old shape
			if (typeof g === 'string') {
				const v = g.trim()
				if (v) normalizedGroups.push({ label: v, value: v })
				continue
			}

			// New shape (must have a real value)
			if (g && typeof g === 'object') {
				const v = typeof g.value === 'string' ? g.value.trim() : ''
				if (!v) continue

				const l = typeof g.label === 'string' ? g.label.trim() : ''
				normalizedGroups.push({ label: l || v, value: v })
			}
		}

		// De-dupe by value (safety)
		const seen = new Set<string>()
		myStudentGroups.value = normalizedGroups.filter((x) => {
			if (!x.value || seen.has(x.value)) return false
			seen.add(x.value)
			return true
		})

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
			filters.value.team = data.defaults?.team || null
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
		filters: normalizeArchiveFilters(filters.value),
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

/**
 * MUTUAL EXCLUSION: Team ↔ Student Group
 * - If team becomes non-null → student_group = null
 * - If student_group becomes non-null → team = null
 *
 * Guard with `if (val)` so selecting "All" (null) doesn't wipe the other filter.
 */
watch(
	() => filters.value.team,
	(val) => {
		if (!initialized.value) return
		if (val) {
			filters.value.student_group = null
		}
	},
)

watch(
	() => filters.value.student_group,
	(val) => {
		if (!initialized.value) return
		if (val) {
			filters.value.team = null
		}
	},
)

/**
 * ORGANIZATION CHANGE
 * Rule: If organization changes → set school = null, team = null, student_group = null
 *
 * We do it strictly (your rule), and we do it only when org actually changes.
 * Note: This will also trigger the school watcher, but that's fine.
 */
watch(
	() => filters.value.organization,
	(newOrg, oldOrg) => {
		if (!initialized.value) return
		if (newOrg === oldOrg) return

		filters.value.school = null
		filters.value.team = null
		filters.value.student_group = null
	},
)

/**
 * SCHOOL CHANGE
 * Rule: If school changes → set team = null and student_group = null (safety)
 *
 * Do it only when school actually changes.
 */
watch(
	() => filters.value.school,
	(newSchool, oldSchool) => {
		if (!initialized.value) return
		if (newSchool === oldSchool) return

		filters.value.team = null
		filters.value.student_group = null
	},
)

/**
 * VALIDITY GUARD (keep)
 * If schoolOptions changes (because org scope changes, or context loaded),
 * ensure current school is still selectable.
 *
 * With the strict org-change rule above, this will *usually* be redundant,
 * but it's still a good safety net (and harmless).
 */
watch(
	schoolOptions,
	(options) => {
		const allowed = options.map((o) => o.value)
		if (filters.value.school && !allowed.includes(filters.value.school)) {
			filters.value.school = null
		}
	},
	{ deep: true },
)

function normalizeArchiveFilters(f: ArchiveFilters): ArchiveFilters {
	const cleanLink = (v: any) => {
		if (!v) return null
		if (typeof v === 'string') return v.trim() || null
		if (typeof v === 'object' && typeof v.value === 'string') return v.value.trim() || null
		return null
	}

	return {
		...f,
		search_text: typeof f.search_text === 'string' ? (f.search_text.trim() || null) : null,
		team: cleanLink((f as any).team),
		student_group: cleanLink((f as any).student_group),
		school: cleanLink((f as any).school),
		organization: cleanLink((f as any).organization),
	}
}



function selectItem(item: OrgCommunicationListItem) {
	if (!item?.name) return
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

	const payload =
		((await orgCommFeed.submit({
			filters: normalizeArchiveFilters(filters.value),
			start: start.value,
			page_length: PAGE_LENGTH,
		})) as any) || {}

	const items = payload.items || []

	feedItems.value = reset ? items : [...feedItems.value, ...items]
	hasMore.value = !!payload.has_more

	const responseStart = typeof payload.start === 'number' ? payload.start : start.value
	start.value = responseStart + items.length

	if (items.length) {
		const commNames = items
			.map((i: OrgCommunicationListItem) => i?.name)
			.filter((name): name is string => typeof name === 'string' && !!name.trim())

		if (commNames.length) {
			interactionSummaryResource.submit({ comm_names: commNames })
		}
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
	const commNames = names.filter((name) => typeof name === 'string' && !!name.trim())
	if (!commNames.length) return
	interactionSummaryResource.submit({ comm_names: commNames })
}

function acknowledge(item: OrgCommunicationListItem) {
	if (!item?.name) return
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
	if (!item?.name) return
	selectedComm.value = item
	showThreadDrawer.value = true
	threadResource.submit({ org_communication: item.name })
}

function submitComment() {
	if (!selectedComm.value?.name || !newComment.value.trim()) return

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
