<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/pages/students/StudentLogs.vue -->

<template>
  <div class="p-4 sm:p-6 lg:p-8">
    <div class="mb-6">
      <h1 class="type-h1">Student Logs</h1>
      <p class="type-meta mt-1">Notes shared with you by staff.</p>
    </div>

    <!-- Initial loading -->
    <div v-if="initialLoading" class="py-10 text-center type-meta">
      Loading logs…
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!logs.length"
      class="py-10 border border-dashed rounded-lg text-center type-meta bg-white"
    >
      No logs yet.
    </div>

    <!-- List -->
    <div v-else class="bg-white border rounded-lg divide-y">
      <button
        v-for="log in logs"
        :key="log.name"
        type="button"
        class="w-full text-left p-4 hover:bg-gray-50 transition border-l-4"
        :style="{ borderColor: colorFor(log.log_type) }"
        @click="openLogDetail(log)"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="type-meta">
              <span class="inline-flex items-center gap-2 type-body-strong text-ink">
                <span
                  class="inline-block w-2.5 h-2.5 rounded-full"
                  :style="{ backgroundColor: colorFor(log.log_type) }"
                />
                {{ log.log_type }}
              </span>
              <span class="mx-2 text-ink/30">•</span>
              <span>{{ formatDate(log.date) }}</span>
              <span
                v-if="formatTime(log.time)"
                class="ml-2 align-[0.5px] type-caption text-ink/70 bg-surface-soft border border-line-soft rounded px-1.5 py-0.5 tabular-nums"
              >
                {{ formatTime(log.time) }}
              </span>
            </p>
            <p class="type-meta">By {{ log.author_name }}</p>

            <p v-if="log.preview" class="mt-2 type-body text-ink/80 break-words">
              {{ log.preview }}
            </p>
          </div>

          <div class="ml-3">
            <span
              v-if="log.is_unread"
              class="inline-flex items-center px-2 py-0.5 rounded-full type-badge-label bg-[var(--jacaranda)]/10 text-[var(--jacaranda)]"
              >New</span
            >
          </div>
        </div>

        <div v-if="log.follow_up_status" class="mt-2">
          <span
            class="inline-flex items-center px-2 py-0.5 rounded type-caption"
            :style="statusStyles(log.follow_up_status)"
          >
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
        class="inline-flex items-center px-4 py-2 type-button-label rounded-md bg-[var(--leaf)] text-white hover:bg-[var(--leaf)]/90 disabled:opacity-60"
      >
        <span v-if="!moreLoading">Load more</span>
        <span v-else>Loading…</span>
      </button>
    </div>

    <!-- Modal -->
    <TransitionRoot as="template" :show="isModalOpen">
      <Dialog as="div" class="if-overlay" :initialFocus="initialFocus" @close="isModalOpen = false">
        <TransitionChild
          as="template"
          enter="if-overlay__fade-enter"
          enter-from="if-overlay__fade-from"
          enter-to="if-overlay__fade-to"
          leave="if-overlay__fade-leave"
          leave-from="if-overlay__fade-to"
          leave-to="if-overlay__fade-from"
        >
          <div class="if-overlay__backdrop" />
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
            <DialogPanel class="if-overlay__panel if-overlay__panel--compact">
              <button
                ref="initialFocus"
                type="button"
                class="sr-only"
                aria-hidden="true"
                tabindex="0"
                @click="isModalOpen = false"
              >
                Close
              </button>
              <div class="if-overlay__body">
                <div v-if="selectedLog">
                  <DialogTitle as="h3" class="type-h3">
                    {{ selectedLog.log_type }}
                  </DialogTitle>

                  <div class="mt-2">
                    <div class="type-meta space-x-4">
                      <span>{{ formatDate(selectedLog.date) }}</span>
                      <span>By: {{ selectedLog.author_name }}</span>
                    </div>
                    <hr class="my-4 border-[rgb(var(--border-rgb)/0.7)]" />

                    <div v-if="modalLoading" class="text-center py-8">
                      <p class="type-body text-ink/70">Loading details...</p>
                    </div>
                    <div v-else class="prose prose-sm max-w-none text-ink/80" v-html="selectedLog.log" />
                  </div>
                </div>
              </div>

              <div class="if-overlay__footer">
                <button
                  type="button"
                  class="inline-flex w-full justify-center rounded-lg bg-[var(--leaf)] px-3 py-2 type-button-label text-white shadow-sm hover:bg-[var(--leaf)]/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--leaf)]"
                  @click="isModalOpen = false"
                >
                  Close
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
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
const initialFocus = ref(null)

function unwrap(resp) {
  return resp && typeof resp === 'object' && 'message' in resp ? resp.message : resp
}

// --- Color helpers (elegant, consistent with tokens) ---------------------------------
const PALETTE = [
  'var(--sky)',       // sky
  'var(--leaf)',      // leaf
  'var(--moss)',      // moss
  'var(--jacaranda)', // jacaranda
  'var(--bamboo)',    // (fallback/custom?) - let's stick to knowns
  'var(--sand)',      // sand
  'var(--flame)',     // flame
  'var(--clay)',      // clay
  'var(--canopy)',    // canopy
]

function hashStr(s) {
  let h = 5381
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h) ^ s.charCodeAt(i)
  return Math.abs(h)
}
function colorFor(key) {
  const idx = hashStr(String(key || '')) % PALETTE.length
  return PALETTE[idx]
}
function statusStyles(status) {
  const s = String(status || '').toLowerCase()
  if (s.includes('overdue') || s.includes('escalated'))
    return { backgroundColor: 'rgb(var(--flame-rgb) / 0.15)', color: 'rgb(var(--flame-rgb))' }
  if (s.includes('pending') || s.includes('open'))
    return { backgroundColor: 'rgb(var(--sand-rgb))', color: 'rgb(var(--clay-rgb))' }
  // default -> completed/closed
  return { backgroundColor: 'rgb(var(--leaf-rgb) / 0.15)', color: 'rgb(var(--leaf-rgb))' }
}

// --- Formatting ---------------------------------------------------------------
function formatDate(d) {
  try {
    return new Date(d).toDateString()
  } catch {
    return d
  }
}
function formatTime(t) {
  // Accepts 'HH:MM:SS' or 'HH:MM' (returns 'HH:MM')
  if (!t) return ''
  const [hh = '', mm = ''] = String(t).split(':')
  const H = hh.toString().padStart(2, '0')
  const M = mm.toString().padStart(2, '0')
  return `${H}:${M}`
}

// --- Data fetching (GET, no CSRF) --------------------------------------------
async function fetchLogs() {
  try {
    const qs = new URLSearchParams({
      start: String(start.value),
      page_length: String(PAGE_LENGTH),
    }).toString()

    const r = await fetch(
      `/api/method/ifitwala_ed.api.student_log.get_student_logs?${qs}`,
      { credentials: 'include' }
    )
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const json = await r.json()
    const rows = unwrap(json) || []
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
    const r = await fetch(
      `/api/method/ifitwala_ed.api.student_log.get_student_log_detail?${q}`,
      { credentials: 'include' }
    )
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
