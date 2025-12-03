<!-- ifitwala_ed/ui-spa/src/components/analytics/SideDrawerList.vue -->
<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="open" class="fixed inset-0 z-40 bg-slate-900/40" @click="emitClose"></div>
    </transition>
    <transition name="slide">
      <aside
        v-if="open"
        class="fixed right-0 top-0 z-50 flex h-full w-full max-w-xl flex-col border-l border-slate-200 bg-white shadow-xl"
      >
        <header class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div>
            <p class="text-xs uppercase tracking-wide text-slate-500">{{ entityLabel }}</p>
            <h3 class="text-lg font-semibold text-slate-800">{{ title }}</h3>
          </div>
          <button class="text-slate-500 hover:text-slate-700" @click="emitClose">X</button>
        </header>
        <section class="flex-1 overflow-y-auto px-4 py-3">
          <slot name="filters" />
          <div v-if="loading" class="py-6 text-center text-slate-500">Loading...</div>
          <div v-else-if="!rows.length" class="py-6 text-center text-slate-400 text-sm">No records for this slice.</div>
          <ul v-else class="divide-y divide-slate-100">
            <li v-for="row in rows" :key="row.id || row.name" class="py-3">
              <slot name="row" :row="row">
                <div class="flex flex-col">
                  <span class="font-medium text-slate-800">{{ row.name || row.title }}</span>
                  <span class="text-xs text-slate-500">{{ row.subtitle }}</span>
                </div>
              </slot>
            </li>
          </ul>
        </section>
        <footer class="flex items-center justify-between border-t border-slate-200 px-4 py-3">
          <slot name="actions" />
          <button
            v-if="onLoadMore"
            class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            @click="onLoadMore"
          >
            Load more
          </button>
        </footer>
      </aside>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type EntityType = 'student' | 'guardian'

const props = defineProps<{
  open: boolean
  title: string
  entity: EntityType
  rows: any[]
  loading?: boolean
  onLoadMore?: () => void
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const entityLabel = computed(() =>
  props.entity === 'student' ? 'Students' : 'Guardians'
)

function emitClose() {
  emit('close')
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
