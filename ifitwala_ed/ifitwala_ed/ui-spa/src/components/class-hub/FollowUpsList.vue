<!-- ifitwala_ed/ui-spa/src/components/class-hub/FollowUpsList.vue -->
<!--
  FollowUpsList.vue
  A list of pending follow-up items for the teacher in the Class Hub.

  Used by:
  - ClassHub.vue
-->
<template>
  <section class="space-y-3">
    <p class="type-overline text-slate-token/70">My Follow-ups</p>
    <div class="space-y-2">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="w-full rounded-xl border border-slate-200 bg-white/90 px-4 py-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda/60"
        @click="$emit('open', item)"
      >
        <span class="type-body-strong text-ink">{{ item.label }}</span>
      </button>
      <div v-if="!items.length" class="rounded-xl border border-dashed border-slate-200 bg-white/80 px-4 py-3">
        <p class="type-caption text-slate-token/70">No follow-ups queued.</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ClassHubBundle } from '@/types/classHub'

defineProps<{
  items: ClassHubBundle['follow_up_items']
}>()

defineEmits<{
  (e: 'open', item: ClassHubBundle['follow_up_items'][number]): void
}>()
</script>
