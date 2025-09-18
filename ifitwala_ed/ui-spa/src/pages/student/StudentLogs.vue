<template>
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
                      <span>{{ new Date(selectedLog.date).toDateString() }}</span>
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
                  <button type="button" class="inline-flex w-full justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600" @click="isModalOpen = false">
                    Close
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'

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
  // Support both {message: ...} and payload-direct shapes
  return (resp && typeof resp === 'object' && 'message' in resp) ? resp.message : resp
}

async function fetchLogs() {
  try {
    const resp = await call('ifitwala_ed.api.student_log.get_student_logs', {
      start: start.value,
      page_length: PAGE_LENGTH
    })
    const rows = unwrap(resp) || []
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
    const resp = await call('ifitwala_ed.api.student_log.get_student_log_detail', {
      log_name: log.name
    })
    const full = unwrap(resp)
    if (full && typeof full === 'object') {
      selectedLog.value = full
      // mark as read in list
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
