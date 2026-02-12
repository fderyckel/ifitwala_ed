<!-- ifitwala_ed/ui-spa/src/components/portfolio/PortfolioFeedSurface.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">{{ portalLabel }}</p>
					<h1 class="type-h1 text-ink">{{ title }}</h1>
					<p class="type-body text-ink/70">{{ subtitle }}</p>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<button type="button" class="if-action" :disabled="loading" @click="refreshFeed">Refresh</button>
					<button
						v-if="canExport"
						type="button"
						class="if-action"
						:disabled="exportingPortfolio"
						@click="onExportPortfolio"
					>
						{{ exportingPortfolio ? 'Exporting…' : 'Export Portfolio PDF' }}
					</button>
					<button
						v-if="canExport"
						type="button"
						class="if-action"
						:disabled="exportingReflection"
						@click="onExportReflection"
					>
						{{ exportingReflection ? 'Exporting…' : 'Export Reflection PDF' }}
					</button>
				</div>
			</div>
		</header>

		<section class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">Feed Filters</h2>
			<div class="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
				<label class="flex flex-col gap-1">
					<span class="type-label">From</span>
					<input v-model="filters.dateFrom" type="date" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink" />
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">To</span>
					<input v-model="filters.dateTo" type="date" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink" />
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Academic Year</span>
					<input
						v-model="filters.academicYear"
						type="text"
						placeholder="e.g. AY-2026-2027"
						class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
					/>
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Program Enrollment</span>
					<input
						v-model="filters.programEnrollment"
						type="text"
						placeholder="Program Enrollment ID"
						class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
					/>
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Tags</span>
					<input
						v-model="filters.tagIdsCsv"
						type="text"
						placeholder="Comma-separated Tag Taxonomy IDs"
						class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
					/>
				</label>
				<label v-if="actor === 'guardian'" class="flex flex-col gap-1">
					<span class="type-label">Child</span>
					<select v-model="filters.guardianStudent" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink">
						<option value="">All linked children</option>
						<option v-for="child in guardianChildren" :key="child.student" :value="child.student">
							{{ child.full_name || child.student }}
						</option>
					</select>
				</label>
				<label v-else-if="actor === 'staff'" class="flex flex-col gap-1">
					<span class="type-label">Students</span>
					<input
						v-model="filters.staffStudentCsv"
						type="text"
						placeholder="Comma-separated Student IDs"
						class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
					/>
				</label>
				<label v-if="actor !== 'guardian'" class="flex items-center gap-2 pt-7">
					<input v-model="filters.showShowcaseOnly" type="checkbox" class="rounded border-line-soft" />
					<span class="type-caption text-ink/80">Show showcase-approved items only</span>
				</label>
			</div>
			<div class="mt-4 flex flex-wrap gap-2">
				<button type="button" class="if-action" :disabled="loading" @click="applyFilters">Apply filters</button>
				<button type="button" class="if-action" :disabled="loading" @click="resetFilters">Reset</button>
			</div>
		</section>

		<section v-if="shareControlsEnabled" class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">External Share Link</h2>
			<p class="mb-3 type-caption text-ink/70">Showcase-only, tokenized link with expiry and optional email gate.</p>
			<div class="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
				<label class="flex flex-col gap-1">
					<span class="type-label">Portfolio</span>
					<select v-model="shareForm.portfolio" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink">
						<option value="">Select portfolio</option>
						<option v-for="portfolio in availablePortfolioIds" :key="portfolio" :value="portfolio">
							{{ portfolio }}
						</option>
					</select>
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Expires On</span>
					<input v-model="shareForm.expiresOn" type="date" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink" />
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Viewer Email (Optional)</span>
					<input
						v-model="shareForm.viewerEmail"
						type="email"
						placeholder="family@example.com"
						class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
					/>
				</label>
				<label class="flex items-center gap-2 pt-7">
					<input v-model="shareForm.allowDownload" type="checkbox" class="rounded border-line-soft" />
					<span class="type-caption text-ink/80">Allow download</span>
				</label>
			</div>
			<div class="mt-4 flex flex-wrap items-center gap-2">
				<button type="button" class="if-action" :disabled="creatingShareLink" @click="onCreateShareLink">
					{{ creatingShareLink ? 'Creating…' : 'Create Share Link' }}
				</button>
				<p v-if="shareLink" class="type-caption text-ink/80">
					Share URL: <a class="text-jacaranda underline" :href="shareLink.share_url" target="_blank" rel="noopener">{{ shareLink.share_url }}</a>
				</p>
			</div>
		</section>

		<section v-if="canMutate" class="card-surface p-5">
			<h2 class="mb-3 type-h3 text-ink">New Reflection Entry</h2>
			<p class="mb-3 type-caption text-ink/70">Reflections stay in the student stream and can be promoted into portfolio evidence.</p>
			<div class="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
				<label class="flex flex-col gap-1">
					<span class="type-label">Student</span>
					<input
						v-model="reflectionForm.student"
						type="text"
						:readonly="actor === 'student' && !!reflectionForm.student"
						placeholder="Student ID"
						class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
					/>
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Date</span>
					<input v-model="reflectionForm.entryDate" type="date" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink" />
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Type</span>
					<select v-model="reflectionForm.entryType" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink">
						<option>Journal</option>
						<option>Reflection</option>
						<option>Goal Check-in</option>
						<option>Advisory</option>
						<option>Activity</option>
						<option>Program</option>
						<option>Course</option>
					</select>
				</label>
				<label class="flex flex-col gap-1">
					<span class="type-label">Visibility</span>
					<select v-model="reflectionForm.visibility" class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink">
						<option>Private</option>
						<option>Teacher</option>
						<option>Portfolio</option>
					</select>
				</label>
			</div>
			<label class="mt-3 flex flex-col gap-1">
				<span class="type-label">Reflection</span>
				<textarea
					v-model="reflectionForm.body"
					rows="4"
					placeholder="Write your reflection..."
					class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
				/>
			</label>
			<p v-if="reflectionError" class="mt-2 type-caption text-flame" role="alert">{{ reflectionError }}</p>
			<div class="mt-3 flex items-center gap-2">
				<button type="button" class="if-action" :disabled="creatingReflection" @click="onCreateReflection">
					{{ creatingReflection ? 'Saving…' : 'Create Reflection' }}
				</button>
			</div>
		</section>

		<section class="card-surface p-5">
			<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
				<h2 class="type-h3 text-ink">Portfolio + Reflection Feed</h2>
				<p class="type-caption text-ink/60">
					Portfolio: {{ portfolioFeed.items.length }} · Reflections: {{ reflectionFeed.items.length }}
				</p>
			</div>
			<div
				v-if="isStaff && moderationQueueItems.length"
				class="mb-3 rounded-xl border border-line-soft bg-surface-soft p-3"
			>
				<div class="flex flex-wrap items-center justify-between gap-2">
					<p class="type-body-strong text-ink">
						Moderation Queue: {{ moderationQueueItems.length }} pending on this page
					</p>
					<p class="type-caption text-ink/70">{{ selectedModerationCount }} selected</p>
				</div>
				<div class="mt-2 flex flex-wrap gap-2">
					<button type="button" class="if-action" :disabled="moderationBusy" @click="selectPendingForModeration">
						Select all pending
					</button>
					<button type="button" class="if-action" :disabled="moderationBusy" @click="clearModerationSelection">
						Clear selection
					</button>
					<button type="button" class="if-action" :disabled="moderationBusy" @click="onBatchModerate('approve')">
						Approve selected
					</button>
					<button type="button" class="if-action" :disabled="moderationBusy" @click="onBatchModerate('return_for_edit')">
						Return selected
					</button>
					<button type="button" class="if-action" :disabled="moderationBusy" @click="onBatchModerate('hide')">
						Hide selected
					</button>
				</div>
				<p v-if="moderationError" class="mt-2 type-caption text-flame" role="alert">{{ moderationError }}</p>
			</div>

			<p v-if="loading" class="type-body text-ink/70">Loading feed...</p>
			<div v-else-if="loadError" class="rounded-lg border border-line-soft bg-white p-3">
				<p class="type-body-strong text-flame">Could not load portfolio feed.</p>
				<p class="type-caption text-ink/70">{{ loadError }}</p>
			</div>
			<div v-else-if="!combinedRows.length" class="rounded-lg border border-line-soft bg-white p-3">
				<p class="type-body text-ink/70">No feed items match these filters.</p>
			</div>
			<div v-else class="space-y-3">
				<article
					v-for="row in combinedRows"
					:key="row.key"
					class="rounded-xl border border-line-soft bg-white p-4"
				>
					<template v-if="row.kind === 'portfolio'">
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-caption text-ink/60">
									Portfolio · {{ row.item.item_type }} · {{ row.item.student_name }}
									<span v-if="row.item.evidence_date">· {{ row.item.evidence_date }}</span>
								</p>
								<p class="type-body-strong text-ink">{{ row.item.caption || row.item.item_type }}</p>
								<p v-if="row.item.reflection_summary" class="mt-1 type-caption text-ink/80">{{ row.item.reflection_summary }}</p>
								<p class="mt-1 type-caption text-ink/60">Moderation: {{ row.item.moderation_state }}</p>
							</div>
							<div class="flex flex-wrap items-center gap-2">
								<label
									v-if="isStaff && canBatchModerateItem(row.item)"
									class="inline-flex items-center gap-2 rounded-full border border-line-soft bg-white px-2 py-1"
								>
									<input
										type="checkbox"
										class="rounded border-line-soft"
										:checked="Boolean(moderationSelection[row.item.item_name])"
										@change="onToggleModerationSelection(row.item.item_name, $event)"
									/>
									<span class="type-caption text-ink/70">Queue</span>
								</label>
								<span
									class="rounded-full px-2 py-1 type-badge-label"
									:class="row.item.is_showcase ? 'bg-leaf/20 text-leaf' : 'bg-surface-soft text-ink/70'"
								>
									{{ row.item.is_showcase ? 'Showcase' : 'Internal' }}
								</span>
								<button
									v-if="canMutate"
									type="button"
									class="if-action"
									:disabled="Boolean(showcaseBusy[row.item.item_name])"
									@click="onToggleShowcase(row.item.item_name, row.item.is_showcase)"
								>
									{{ row.item.is_showcase ? 'Remove Showcase' : 'Mark Showcase' }}
								</button>
							</div>
						</div>
						<p v-if="row.item.evidence?.text_preview" class="mt-2 type-caption text-ink/80">{{ row.item.evidence.text_preview }}</p>
						<p v-if="row.item.evidence?.link_url" class="mt-2 type-caption">
							<a class="text-jacaranda underline" :href="row.item.evidence.link_url" target="_blank" rel="noopener">Open evidence link</a>
						</p>
						<p v-if="row.item.evidence?.file_url" class="mt-2 type-caption">
							<a class="text-jacaranda underline" :href="row.item.evidence.file_url" target="_blank" rel="noopener">Download {{ row.item.evidence.file_name || 'artefact' }}</a>
						</p>

						<div v-if="row.item.tags.length" class="mt-2 flex flex-wrap gap-2">
							<span v-for="tag in row.item.tags" :key="tag.name || `${tag.tag_taxonomy}-${tag.tagged_by_id}`" class="rounded-full bg-surface-soft px-2 py-1 type-badge-label text-ink/80">
								{{ tag.title }}
								<span class="text-ink/50">· {{ tag.tagged_by_type }}</span>
								<button
									v-if="canMutate && tag.name"
									type="button"
									class="ml-1 text-flame"
									:title="`Remove ${tag.title}`"
									@click="onRemoveTag(tag.name)"
								>
									×
								</button>
							</span>
						</div>

						<div v-if="canMutate" class="mt-3 flex flex-wrap items-center gap-2">
							<input
								v-model="tagDraft[row.item.item_name]"
								type="text"
								placeholder="Tag Taxonomy ID"
								class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
							/>
							<button type="button" class="if-action" :disabled="Boolean(tagBusy[row.item.item_name])" @click="onAddTag(row.item.item_name)">
								Add Tag
							</button>
						</div>
					</template>

					<template v-else>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-caption text-ink/60">
									Reflection · {{ row.item.student }}
									<span v-if="row.item.entry_date">· {{ row.item.entry_date }}</span>
								</p>
								<p class="type-body-strong text-ink">{{ row.item.entry_type || 'Reflection' }}</p>
								<p class="mt-1 type-caption text-ink/70">Visibility: {{ row.item.visibility || 'Teacher' }}</p>
								<p class="mt-1 type-caption text-ink/60">Moderation: {{ row.item.moderation_state || 'Draft' }}</p>
							</div>
							<div>
								<button
									v-if="canMutate"
									type="button"
									class="if-action"
									:disabled="Boolean(addToPortfolioBusy[row.item.name])"
									@click="onAddReflectionToPortfolio(row.item)"
								>
									Add to Portfolio
								</button>
							</div>
						</div>
						<p class="mt-2 type-caption text-ink/80">{{ row.item.body_preview || '' }}</p>
					</template>
				</article>
			</div>

			<div v-if="hasPaging" class="mt-4 flex items-center justify-between">
				<button type="button" class="if-action" :disabled="loading || page <= 1" @click="goPrev">Previous</button>
				<p class="type-caption text-ink/70">Page {{ page }} of {{ totalPages }}</p>
				<button type="button" class="if-action" :disabled="loading || page >= totalPages" @click="goNext">Next</button>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { toast } from 'frappe-ui'

import { getGuardianHomeSnapshot } from '@/lib/services/guardianHome/guardianHomeService'
import {
	addPortfolioItem,
	applyEvidenceTag,
	createPortfolioShareLink,
	createReflectionEntry,
	exportPortfolioPdf,
	exportReflectionPdf,
	getPortfolioFeed,
	listReflectionEntries,
	moderatePortfolioItems,
	removeEvidenceTag,
	setShowcaseState,
} from '@/lib/services/portfolio/portfolioService'

import type { PortfolioFeedItem, Request as GetPortfolioFeedRequest, Response as GetPortfolioFeedResponse } from '@/types/contracts/portfolio/get_portfolio_feed'
import type { ReflectionEntryRow, Request as ListReflectionEntriesRequest, Response as ListReflectionEntriesResponse } from '@/types/contracts/portfolio/list_reflection_entries'
import type { ModerationAction } from '@/types/contracts/portfolio/moderate_portfolio_items'
import type { ChildRef } from '@/types/contracts/guardian/get_guardian_home_snapshot'

type Actor = 'student' | 'guardian' | 'staff'
type FeedRow =
	| { key: string; date: string; kind: 'portfolio'; item: PortfolioFeedItem }
	| { key: string; date: string; kind: 'reflection'; item: ReflectionEntryRow }

const props = withDefaults(
	defineProps<{
		actor: Actor
		title?: string
		subtitle?: string
	}>(),
	{
		title: 'Portfolio Feed',
		subtitle: 'Annual evidence lens with universal reflections and low-friction sharing.',
	}
)

const actor = computed<Actor>(() => props.actor)
const title = computed(() => props.title)
const subtitle = computed(() => props.subtitle)
const portalLabel = computed(() => {
	if (actor.value === 'student') return 'Student Portfolio'
	if (actor.value === 'guardian') return 'Guardian Showcase'
	return 'Staff Portfolio Review'
})

const canMutate = computed(() => actor.value !== 'guardian')
const canExport = computed(() => actor.value !== 'guardian')
const shareControlsEnabled = computed(() => actor.value !== 'guardian')
const isStaff = computed(() => actor.value === 'staff')

const loading = ref(false)
const loadError = ref('')
const page = ref(1)
const pageLength = ref(20)

const portfolioFeed = ref<GetPortfolioFeedResponse>({ items: [], total: 0, page: 1, page_length: 20 })
const reflectionFeed = ref<ListReflectionEntriesResponse>({ items: [], total: 0, page: 1, page_length: 20 })

const filters = reactive({
	dateFrom: '',
	dateTo: '',
	academicYear: '',
	programEnrollment: '',
	tagIdsCsv: '',
	guardianStudent: '',
	staffStudentCsv: '',
	showShowcaseOnly: false,
})

const guardianChildren = ref<ChildRef[]>([])

const shareForm = reactive({
	portfolio: '',
	expiresOn: addDaysIso(30),
	viewerEmail: '',
	allowDownload: false,
})
const creatingShareLink = ref(false)
const shareLink = ref<{ share_url: string } | null>(null)

const reflectionForm = reactive({
	student: '',
	entryDate: todayIso(),
	entryType: 'Reflection',
	visibility: 'Teacher',
	body: '',
})
const reflectionError = ref('')
const creatingReflection = ref(false)

const exportingPortfolio = ref(false)
const exportingReflection = ref(false)

const showcaseBusy = ref<Record<string, boolean>>({})
const tagBusy = ref<Record<string, boolean>>({})
const tagDraft = ref<Record<string, string>>({})
const addToPortfolioBusy = ref<Record<string, boolean>>({})
const moderationSelection = ref<Record<string, boolean>>({})
const moderationBusy = ref(false)
const moderationError = ref('')

const combinedRows = computed<FeedRow[]>(() => {
	const portfolioRows: FeedRow[] = (portfolioFeed.value.items || []).map((item) => ({
		key: `portfolio:${item.item_name}`,
		date: normalizeDate(item.evidence_date),
		kind: 'portfolio',
		item,
	}))

	if (actor.value === 'guardian') {
		return portfolioRows.sort((a, b) => b.date.localeCompare(a.date))
	}

	const reflectionRows: FeedRow[] = (reflectionFeed.value.items || []).map((item) => ({
		key: `reflection:${item.name}`,
		date: normalizeDate(item.entry_date),
		kind: 'reflection',
		item,
	}))

	return [...portfolioRows, ...reflectionRows].sort((a, b) => b.date.localeCompare(a.date))
})

const availablePortfolioIds = computed(() => {
	const set = new Set<string>()
	for (const row of portfolioFeed.value.items || []) {
		if (row.portfolio) set.add(row.portfolio)
	}
	return Array.from(set)
})

const totalPages = computed(() => {
	const portfolioTotal = Number(portfolioFeed.value.total || 0)
	const reflectionTotal = actor.value === 'guardian' ? 0 : Number(reflectionFeed.value.total || 0)
	const total = Math.max(portfolioTotal, reflectionTotal)
	return Math.max(1, Math.ceil(total / pageLength.value))
})

const hasPaging = computed(() => totalPages.value > 1)
const moderationQueueItems = computed(() =>
	(portfolioFeed.value.items || []).filter((item) => canBatchModerateItem(item))
)
const selectedModerationNames = computed(() =>
	moderationQueueItems.value
		.filter((item) => Boolean(moderationSelection.value[item.item_name]))
		.map((item) => item.item_name)
)
const selectedModerationCount = computed(() => selectedModerationNames.value.length)

function todayIso(): string {
	const now = new Date()
	const year = now.getFullYear()
	const month = `${now.getMonth() + 1}`.padStart(2, '0')
	const day = `${now.getDate()}`.padStart(2, '0')
	return `${year}-${month}-${day}`
}

function addDaysIso(days: number): string {
	const d = new Date()
	d.setDate(d.getDate() + days)
	const year = d.getFullYear()
	const month = `${d.getMonth() + 1}`.padStart(2, '0')
	const day = `${d.getDate()}`.padStart(2, '0')
	return `${year}-${month}-${day}`
}

function normalizeDate(value?: string | null): string {
	if (!value) return ''
	return String(value)
}

function canBatchModerateItem(item: PortfolioFeedItem): boolean {
	if (!item.is_showcase) return false
	return item.moderation_state === 'Submitted for Review' || item.moderation_state === 'Returned for Edit'
}

function parseCsv(value: string): string[] {
	return value
		.split(',')
		.map((entry) => entry.trim())
		.filter(Boolean)
}

function resolvedStudentIds(): string[] {
	if (actor.value === 'guardian') {
		return filters.guardianStudent ? [filters.guardianStudent] : []
	}
	if (actor.value === 'staff') {
		return parseCsv(filters.staffStudentCsv)
	}
	return []
}

function buildPortfolioFilterPayload(): GetPortfolioFeedRequest {
	return {
		date_from: filters.dateFrom || undefined,
		date_to: filters.dateTo || undefined,
		student_ids: resolvedStudentIds(),
		program_enrollment: filters.programEnrollment || undefined,
		academic_year: filters.academicYear || undefined,
		tag_ids: parseCsv(filters.tagIdsCsv),
		show_showcase_only: actor.value === 'guardian' || filters.showShowcaseOnly ? 1 : 0,
		page: page.value,
		page_length: pageLength.value,
	}
}

function buildReflectionFilterPayload(): ListReflectionEntriesRequest {
	return {
		date_from: filters.dateFrom || undefined,
		date_to: filters.dateTo || undefined,
		student_ids: resolvedStudentIds(),
		program_enrollment: filters.programEnrollment || undefined,
		academic_year: filters.academicYear || undefined,
		page: page.value,
		page_length: pageLength.value,
	}
}

function syncDerivedDefaults() {
	if (!shareForm.portfolio && availablePortfolioIds.value.length === 1) {
		shareForm.portfolio = availablePortfolioIds.value[0]
	}
	if (shareForm.portfolio && !availablePortfolioIds.value.includes(shareForm.portfolio)) {
		shareForm.portfolio = availablePortfolioIds.value[0] || ''
	}

	const scopedStudents = Array.isArray(portfolioFeed.value.scope_students) ? portfolioFeed.value.scope_students : []
	const students = Array.from(
		new Set([...scopedStudents, ...portfolioFeed.value.items.map((row) => row.student)].filter(Boolean))
	)
	if (actor.value === 'student' && !reflectionForm.student && students.length === 1) {
		reflectionForm.student = students[0]
	}
	if (actor.value === 'staff' && !reflectionForm.student) {
		const filtered = resolvedStudentIds()
		if (filtered.length === 1) reflectionForm.student = filtered[0]
	}
}

function pruneModerationSelection() {
	const allowed = new Set(moderationQueueItems.value.map((item) => item.item_name))
	const next: Record<string, boolean> = {}
	for (const [itemName, checked] of Object.entries(moderationSelection.value)) {
		if (checked && allowed.has(itemName)) {
			next[itemName] = true
		}
	}
	moderationSelection.value = next
}

function messageForError(error: unknown, fallback: string): string {
	if (error instanceof Error) return error.message || fallback
	if (typeof error === 'string') return error || fallback
	return fallback
}

async function loadGuardianChildren() {
	if (actor.value !== 'guardian') return
	try {
		const snapshot = await getGuardianHomeSnapshot({ school_days: 1 })
		guardianChildren.value = snapshot.family.children || []
	} catch (error) {
		guardianChildren.value = []
		toast.error(messageForError(error, 'Could not load linked children for filters.'))
	}
}

async function loadFeed() {
	loading.value = true
	loadError.value = ''
	try {
		const portfolioPromise = getPortfolioFeed(buildPortfolioFilterPayload())
		const reflectionPromise = actor.value === 'guardian'
			? Promise.resolve<ListReflectionEntriesResponse>({ items: [], total: 0, page: 1, page_length: pageLength.value })
			: listReflectionEntries(buildReflectionFilterPayload())

		const [portfolioData, reflectionData] = await Promise.all([portfolioPromise, reflectionPromise])
		portfolioFeed.value = portfolioData
		reflectionFeed.value = reflectionData
		syncDerivedDefaults()
		pruneModerationSelection()
	} catch (error) {
		loadError.value = messageForError(error, 'Unknown error')
	} finally {
		loading.value = false
	}
}

async function refreshFeed() {
	await loadFeed()
}

async function applyFilters() {
	page.value = 1
	await loadFeed()
}

async function resetFilters() {
	filters.dateFrom = ''
	filters.dateTo = ''
	filters.academicYear = ''
	filters.programEnrollment = ''
	filters.tagIdsCsv = ''
	filters.guardianStudent = ''
	filters.staffStudentCsv = ''
	filters.showShowcaseOnly = false
	page.value = 1
	await loadFeed()
}

async function goPrev() {
	if (page.value <= 1) return
	page.value -= 1
	await loadFeed()
}

async function goNext() {
	if (page.value >= totalPages.value) return
	page.value += 1
	await loadFeed()
}

async function onToggleShowcase(itemName: string, current: boolean) {
	showcaseBusy.value[itemName] = true
	try {
		await setShowcaseState({ item_name: itemName, is_showcase: current ? 0 : 1 })
		toast.success(current ? 'Removed from showcase.' : 'Submitted to showcase moderation queue.')
		await loadFeed()
	} catch (error) {
		toast.error(messageForError(error, 'Could not update showcase state.'))
	} finally {
		showcaseBusy.value[itemName] = false
	}
}

function onToggleModerationSelection(itemName: string, event: Event) {
	const checked = (event.target as HTMLInputElement | null)?.checked === true
	moderationSelection.value = {
		...moderationSelection.value,
		[itemName]: checked,
	}
}

function selectPendingForModeration() {
	const next: Record<string, boolean> = {}
	for (const item of moderationQueueItems.value) {
		next[item.item_name] = true
	}
	moderationSelection.value = next
	moderationError.value = ''
}

function clearModerationSelection() {
	moderationSelection.value = {}
	moderationError.value = ''
}

async function onBatchModerate(action: ModerationAction) {
	const itemNames = selectedModerationNames.value
	if (!itemNames.length) {
		moderationError.value = 'Select at least one pending showcase item for moderation.'
		toast.error(moderationError.value)
		return
	}

	moderationBusy.value = true
	moderationError.value = ''
	try {
		const response = await moderatePortfolioItems({
			action,
			item_names: itemNames,
		})
		const failed = (response.results || []).filter((row) => !row.ok)
		if (failed.length) {
			const firstError = failed[0]?.error || 'Some items could not be moderated.'
			moderationError.value = `Updated ${response.updated} item(s). ${failed.length} item(s) failed. ${firstError}`
			toast.error(moderationError.value)
		} else {
			toast.success(`Updated ${response.updated} showcase item(s).`)
		}
		clearModerationSelection()
		await loadFeed()
	} catch (error) {
		const message = messageForError(error, 'Could not run batch moderation.')
		moderationError.value = message
		toast.error(message)
	} finally {
		moderationBusy.value = false
	}
}

async function onAddTag(itemName: string) {
	const tagTaxonomy = (tagDraft.value[itemName] || '').trim()
	if (!tagTaxonomy) {
		toast.error('Enter a Tag Taxonomy ID before adding a tag.')
		return
	}

	tagBusy.value[itemName] = true
	try {
		await applyEvidenceTag({
			target_doctype: 'Student Portfolio Item',
			target_name: itemName,
			tag_taxonomy: tagTaxonomy,
			scope: 'portfolio',
		})
		tagDraft.value[itemName] = ''
		toast.success('Tag added.')
		await loadFeed()
	} catch (error) {
		toast.error(messageForError(error, 'Could not add tag.'))
	} finally {
		tagBusy.value[itemName] = false
	}
}

async function onRemoveTag(name: string) {
	try {
		await removeEvidenceTag({ name })
		toast.success('Tag removed.')
		await loadFeed()
	} catch (error) {
		toast.error(messageForError(error, 'Could not remove tag.'))
	}
}

async function onAddReflectionToPortfolio(reflection: ReflectionEntryRow) {
	addToPortfolioBusy.value[reflection.name] = true
	try {
		await addPortfolioItem({
			student: reflection.student,
			academic_year: reflection.academic_year,
			school: reflection.school,
			item_type: 'Student Reflection Entry',
			student_reflection_entry: reflection.name,
			is_showcase: 0,
		})
		toast.success('Reflection added to annual portfolio.')
		await loadFeed()
	} catch (error) {
		toast.error(messageForError(error, 'Could not add reflection to portfolio.'))
	} finally {
		addToPortfolioBusy.value[reflection.name] = false
	}
}

async function onCreateReflection() {
	reflectionError.value = ''
	const student = reflectionForm.student.trim()
	const body = reflectionForm.body.trim()
	if (!student) {
		reflectionError.value = 'Student is required.'
		toast.error('Student is required before creating a reflection.')
		return
	}
	if (!body) {
		reflectionError.value = 'Reflection body is required.'
		toast.error('Write a reflection body before submitting.')
		return
	}

	creatingReflection.value = true
	try {
		await createReflectionEntry({
			student,
			academic_year: filters.academicYear || undefined,
			entry_date: reflectionForm.entryDate,
			entry_type: reflectionForm.entryType,
			visibility: reflectionForm.visibility,
			body,
			program_enrollment: filters.programEnrollment || undefined,
		})
		reflectionForm.body = ''
		reflectionError.value = ''
		toast.success('Reflection created.')
		await loadFeed()
	} catch (error) {
		const message = messageForError(error, 'Could not create reflection entry.')
		reflectionError.value = message
		toast.error(message)
	} finally {
		creatingReflection.value = false
	}
}

async function onCreateShareLink() {
	const portfolio = shareForm.portfolio.trim()
	if (!portfolio) {
		toast.error('Select a portfolio before creating a share link.')
		return
	}
	if (!shareForm.expiresOn) {
		toast.error('Expiry date is required.')
		return
	}

	creatingShareLink.value = true
	try {
		const response = await createPortfolioShareLink({
			portfolio,
			expires_on: shareForm.expiresOn,
			allowed_viewer_email: shareForm.viewerEmail || undefined,
			allow_download: shareForm.allowDownload ? 1 : 0,
		})
		shareLink.value = { share_url: response.share_url }
		toast.success('Share link created.')
	} catch (error) {
		toast.error(messageForError(error, 'Could not create share link.'))
	} finally {
		creatingShareLink.value = false
	}
}

async function onExportPortfolio() {
	exportingPortfolio.value = true
	try {
		const response = await exportPortfolioPdf(buildPortfolioFilterPayload())
		if (response.file_url) {
			window.open(response.file_url, '_blank', 'noopener')
		}
		toast.success(`Portfolio PDF ready: ${response.file_name}`)
	} catch (error) {
		toast.error(messageForError(error, 'Could not export portfolio PDF.'))
	} finally {
		exportingPortfolio.value = false
	}
}

async function onExportReflection() {
	exportingReflection.value = true
	try {
		const response = await exportReflectionPdf(buildReflectionFilterPayload())
		if (response.file_url) {
			window.open(response.file_url, '_blank', 'noopener')
		}
		toast.success(`Reflection PDF ready: ${response.file_name}`)
	} catch (error) {
		toast.error(messageForError(error, 'Could not export reflection PDF.'))
	} finally {
		exportingReflection.value = false
	}
}

onMounted(async () => {
	await loadGuardianChildren()
	await loadFeed()
})
</script>
