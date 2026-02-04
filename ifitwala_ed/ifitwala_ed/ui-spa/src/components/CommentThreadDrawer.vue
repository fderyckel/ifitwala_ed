<!-- ifitwala_ed/ui-spa/src/components/CommentThreadDrawer.vue -->
<!--
  CommentThreadDrawer.vue
  Slide-out drawer for viewing and replying to comment threads on generic documents/communications.

  Used by:
  - MorningBriefing.vue (pages/staff/morning_brief)
  - OrgCommunicationArchive.vue (pages/staff)
-->
<template>
  <Transition name="thread-drawer-fade">
    <div
      v-if="open"
      class="fixed inset-0 z-[100] flex justify-end bg-black/20 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div class="w-full max-w-md bg-white h-full shadow-strong flex flex-col">
        <div class="p-4 border-b border-line-soft flex items-center justify-between bg-slate-50">
          <h3 class="font-bold text-lg">{{ title }}</h3>
          <Button icon="x" variant="ghost" @click="emit('close')" />
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <div v-if="loading" class="text-center py-4">
            <LoadingIndicator />
          </div>
          <div v-else-if="!safeRows.length" class="text-center py-8 text-slate-token/60">
            {{ emptyMessage }}
          </div>

          <div v-for="comment in safeRows" :key="comment.name || comment.id || comment.creation" class="flex gap-3">
            <Avatar :label="comment.full_name || comment.user || 'User'" size="md" />
            <div class="flex-1 space-y-1">
              <div class="flex items-center justify-between">
                <span class="font-semibold text-sm">{{ comment.full_name || comment.user || 'User' }}</span>
                <span class="text-xs text-slate-token/50">
                  {{ formatTimestamp(comment.creation) }}
                </span>
              </div>
              <div class="bg-surface-soft rounded-lg rounded-tl-none p-3 text-sm text-ink/90">
                {{ comment.note }}
              </div>
            </div>
          </div>
        </div>

        <div class="p-4 border-t border-line-soft bg-white gap-2 flex flex-col">
          <FormControl
            v-model="commentValue"
            type="textarea"
            :placeholder="placeholder"
            :rows="2"
          />
          <div class="flex justify-end">
            <Button
              variant="solid"
              color="gray"
              :loading="submitLoading"
              :disabled="submitIsDisabled"
              @click="emit('submit')"
            >
              {{ submitLabel }}
            </Button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Avatar, Button, FormControl, LoadingIndicator } from 'frappe-ui'

type ThreadRow = {
  id?: string | number
  name?: string
  full_name?: string
  user?: string
  creation?: string | null
  note?: string
}

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    rows?: ThreadRow[]
    loading?: boolean
    comment?: string
    submitLabel?: string
    submitLoading?: boolean
    submitDisabled?: boolean
    placeholder?: string
    emptyMessage?: string
    formatTimestamp?: (value: string | null | undefined) => string
  }>(),
  {
    title: 'Comments',
    rows: () => [],
    submitLabel: 'Post Comment',
    submitLoading: false,
    placeholder: 'Write a comment...',
    emptyMessage: 'No comments yet. Start the conversation!',
  },
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit'): void
  (e: 'update:comment', value: string): void
}>()

const safeRows = computed(() => props.rows || [])

const commentValue = computed({
  get: () => props.comment ?? '',
  set: (value: string) => emit('update:comment', value),
})

const submitIsDisabled = computed(() => {
  if (props.submitDisabled !== undefined) return props.submitDisabled
  return !commentValue.value.trim()
})

function formatTimestamp(value?: string | null) {
  if (props.formatTimestamp) return props.formatTimestamp(value)
  return value ?? ''
}
</script>

<style scoped>
.thread-drawer-fade-enter-active,
.thread-drawer-fade-leave-active {
  transition: opacity 0.3s ease;
}

.thread-drawer-fade-enter-from,
.thread-drawer-fade-leave-to {
  opacity: 0;
}
</style>
