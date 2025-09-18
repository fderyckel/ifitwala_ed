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
import { ref, onMounted } from 'vue';
import { call } from 'frappe-ui';
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue';

const PAGE_LENGTH = 20;

const logs = ref([]);
const selectedLog = ref(null);
const isModalOpen = ref(false);
const hasMore = ref(true);
const start = ref(0);

const initialLoading = ref(true);
const moreLoading = ref(false);
const modalLoading = ref(false);

const fetchLogs = async () => {
  try {
    const newLogs = await call({
      method: 'ifitwala_ed.api.student_log.get_student_logs',
      args: {
        start: start.value,
        page_length: PAGE_LENGTH,
      },
    });

    if (newLogs.message.length < PAGE_LENGTH) {
      hasMore.value = false;
    }

    logs.value.push(...newLogs.message);
    start.value += PAGE_LENGTH;
  } catch (error) {
    console.error("Failed to fetch student logs:", error);
  }
};

const openLogDetail = async (log) => {
  selectedLog.value = log; // Set preliminary data
  isModalOpen.value = true;
  modalLoading.value = true;

  try {
    const response = await call({
      method: 'ifitwala_ed.api.student_log.get_student_log_detail',
      args: { log_name: log.name },
    });
    selectedLog.value = response.message; // Overwrite with full data
    
    // Update the list item to remove the 'New' badge reactively
    const logInList = logs.value.find(l => l.name === log.name);
    if (logInList) {
      logInList.is_unread = false;
    }

  } catch (error) {
    console.error("Failed to fetch log detail:", error);
    // Optionally close modal and show an error message
    isModalOpen.value = false;
  } finally {
    modalLoading.value = false;
  }
};

const loadMoreLogs = async () => {
  moreLoading.value = true;
  await fetchLogs();
  moreLoading.value = false;
};

onMounted(async () => {
  await fetchLogs();
  initialLoading.value = false;
});
</script>