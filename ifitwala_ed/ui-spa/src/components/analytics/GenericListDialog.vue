<!-- ifitwala_ed/ui-spa/src/components/analytics/GenericListDialog.vue -->
<!--
  GenericListDialog.vue
  A reusable dialog for displaying list data (e.g. students, logs) in a modal.
  Supports slots for custom item rendering.

  Used by:
  - EnrollmentAnalytics.vue
  - StudentLogAnalytics.vue
-->
<template>
  <Dialog v-model="show" :options="{ size: 'xl', title: null }">
    <template #body-content>
      <div class="flex flex-col h-[80vh]">

        <!-- Header -->
        <div class="px-6 py-5 border-b border-line-soft bg-surface-soft/70 flex items-center justify-between shrink-0">
          <div>
            <h3 class="text-xl font-bold text-ink">{{ title }}</h3>
            <p v-if="subtitle" class="text-sm text-slate-token/70 mt-1">{{ subtitle }}</p>
          </div>
          <button
            @click="show = false"
            class="p-2 rounded-full border border-line-soft bg-surface-soft text-slate-token/60 transition-colors hover:border-jacaranda/40 hover:text-jacaranda"
          >
            <FeatherIcon name="x" class="h-5 w-5" />
          </button>
        </div>

        <!-- Content Area -->
        <div class="flex-1 overflow-y-auto p-0 custom-scrollbar bg-surface-soft/80">
          <div v-if="loading" class="p-10 flex justify-center">
            <FeatherIcon name="loader" class="h-8 w-8 animate-spin text-slate-token/40" />
          </div>

          <div v-else-if="items && items.length > 0" class="divide-y divide-border/60">
            <div
              v-for="(item, index) in items"
              :key="index"
              class="bg-white/90 hover:bg-surface-soft transition-colors"
            >
              <!-- SLOT gives parent full rendering control -->
              <slot name="item" :item="item" :index="index">
                <div class="p-4">{{ item }}</div>
              </slot>
            </div>
          </div>

          <div v-else class="p-10 text-center text-slate-token/50">
            <FeatherIcon name="inbox" class="h-10 w-10 mx-auto mb-3 opacity-50" />
            <p>No items found</p>
          </div>
        </div>

      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Dialog, FeatherIcon } from 'frappe-ui'

const props = defineProps<{
  modelValue: boolean
  title: string
  subtitle?: string
  items: any[]
  loading?: boolean
}>()

const emit = defineEmits(['update:modelValue'])

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})
</script>
