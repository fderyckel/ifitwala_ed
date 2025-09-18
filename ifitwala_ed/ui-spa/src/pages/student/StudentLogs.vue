<template>
	<div class="p-4 sm:p-6 lg:p-8">
		<div class="mb-6">
			<h1 class="text-2xl font-bold text-gray-900">Student Logs</h1>
			<p class="text-gray-500 mt-1">Notes shared with you by staff.</p>
		</div>

		<!-- Initial loading -->
		<div v-if="initialLoading" class="py-10 text-center text-gray-500">
			Loading logs…
		</div>

		<!-- Empty state -->
		<div v-else-if="!logs.length" class="py-10 border border-dashed rounded-lg text-center text-gray-500 bg-white">
			No logs yet.
		</div>

		<!-- List -->
		<div v-else class="bg-white border rounded-lg divide-y">
			<button
				v-for="log in logs"
				:key="log.name"
				type="button"
				class="w-full text-left p-4 hover:bg-gray-50 transition"
				@click="openLogDetail(log)"
			>
				<div class="flex items-start justify-between">
					<div>
						<p class="text-sm text-gray-500">
							<span class="font-medium text-gray-900">{{ log.log_type }}</span>
							• {{ formatDate(log.date) }} {{ formatTime(log.time) }}
						</p>
						<p class="text-sm text-gray-500">By {{ log.author_name }}</p>
					</div>
					<div class="ml-3">
						<span
							v-if="log.is_unread"
							class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
						>New</span>
					</div>
				</div>
				<div v-if="log.follow_up_status" class="mt-2">
					<span class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
						Follow-up: {{ log.follow_up_status }}
					</span>
				</div>
			</button>
		</div>

		<!-- Load more -->
		<div v-if="hasMore" class="mt-4">
			<button
				:disabled="moreLoading"
				@click="loadMoreLogs"
				class="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-60"
			>
				<span v-if="!moreLoading">Load more</span>
				<span v-else>Loading…</span>
			</button>
		</div>

		<!-- Modal -->
		<TransitionRoot as="template" :show="isModalOpen">
			<Dialog as="div" class="relative z-10" @close="isModalOpen = false">
				<TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0" enter-to="opacity-100" leave="ease-in duration-200" leave-from="opacity-100" leave-to="opacity-0">
					<div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
				</TransitionChild>

				<div class="fixed inset-0 z-10 w-screen overflow-y-auto">
					<div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
						<TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="ease-in duration-200" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
							<DialogPanel class="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl sm:p-6">
								<div v-if="selectedLog">
									<DialogTitle as="h3" class="text-lg font-semibold leading-6 text-gray-900">
										{{ selectedLog.log_type }}
									</DialogTitle>
									<div class="mt-2">
										<div class="text-sm text-gray-500 space-x-4">
											<span>{{ formatDate(selectedLog.date) }}</span>
											<span>By: {{ selectedLog.author_name }}</span>
										</div>
										<hr class="my-4" />
										<div v-if="modalLoading" class="text-center py-8">
											<p>Loading details...</p>
										</div>
										<div v-else class="prose max-w-none" v-html="selectedLog.log"></div>
									</div>
								</div>
								<div class="mt-5 sm:mt-6">
									<button
										type="button"
										class="inline-flex w-full justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500"
										@click="isModalOpen = false"
									>
										Close
									</button>
								</div>
							</DialogPanel>
						</TransitionChild>
					</div>
				</div>
			</Dialog>
		</TransitionRoot>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue'

const PAGE_LENGTH = 20

const logs = ref([])
const selectedLog = ref(null)
const isModalOpen = ref(false)
const hasMore = ref(true)
const start = ref(0)

const initialLoading = ref(true)
const moreLoading = ref(false)
const modalLoading = ref(false)

function unwrap(resp) {
	return (resp && typeof resp === 'object' && 'message' in resp) ? resp.message : resp
}

function formatDate(d) {
	try { return new Date(d).toDateString() } catch { return d }
}
function formatTime(t) {
	return t || ''
}

async function fetchLogs() {
	try {
		const qs = new URLSearchParams({
			start: String(start.value),
			page_length: String(PAGE_LENGTH),
		}).toString()

		const r = await fetch(`/api/method/ifitwala_ed.api.student_log.get_student_logs?${qs}`, {
			credentials: 'include',
		})
		if (!r.ok) throw new Error(`HTTP ${r.status}`)
		const json = await r.json()
		const rows = unwrap(json) || []
		console.debug('logs fetched:', rows) // 👈 sanity log
		if (!Array.isArray(rows)) throw new Error('Unexpected logs response')

		logs.value.push(...rows)
		if (rows.length < PAGE_LENGTH) hasMore.value = false
		start.value += PAGE_LENGTH
	} catch (err) {
		console.error('Failed to fetch student logs:', err)
		hasMore.value = false
	}
}

async function openLogDetail(log) {
	selectedLog.value = log
	isModalOpen.value = true
	modalLoading.value = true
	try {
		const q = new URLSearchParams({ log_name: log.name }).toString()
		const r = await fetch(`/api/method/ifitwala_ed.api.student_log.get_student_log_detail?${q}`, {
			credentials: 'include',
		})
		if (!r.ok) throw new Error(`HTTP ${r.status}`)
		const json = await r.json()
		const full = unwrap(json)
		if (full && typeof full === 'object') {
			selectedLog.value = full
			const row = logs.value.find(l => l.name === log.name)
			if (row) row.is_unread = false
		}
	} catch (err) {
		console.error('Failed to fetch log detail:', err)
		isModalOpen.value = false
	} finally {
		modalLoading.value = false
	}
}

async function loadMoreLogs() {
	moreLoading.value = true
	await fetchLogs()
	moreLoading.value = false
}

onMounted(async () => {
	await fetchLogs()
	initialLoading.value = false
})
</script>
