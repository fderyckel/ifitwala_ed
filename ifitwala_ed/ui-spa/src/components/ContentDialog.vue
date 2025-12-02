<!-- ifitwala_ed/ui-spa/src/components/ContentDialog.vue -->
<template>
  <Dialog
    v-model="isOpen"
    :options="{ size: 'xl', title: null }"
  >
    <template #body-content>
      <div class="flex flex-col gap-5">

        <div class="flex items-start justify-between">
          <div class="flex items-start gap-4">

            <div
              v-if="image || imageFallback"
              class="h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center shadow-inner"
            >
              <img
                v-if="image"
                :src="image"
                class="h-full w-full object-cover"
                alt="Context Icon"
              />
              <span
                v-else
                class="text-lg font-semibold text-slate-400"
              >
                {{ imageFallback }}
              </span>
            </div>

            <div class="flex flex-col pt-0.5">
              <h2 class="text-xl font-semibold text-[color:var(--canopy)] leading-tight">
                {{ subtitle }}
              </h2>

              <div class="flex items-center gap-2 mt-1.5">
                <span
                  v-if="badge"
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200"
                >
                  {{ badge }}
                </span>
              </div>
            </div>
          </div>

          <button
            @click="isOpen = false"
            class="group p-2 rounded-full hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-200"
            aria-label="Close"
          >
            <FeatherIcon
              name="x"
              class="h-5 w-5 text-slate-400 group-hover:text-[color:var(--canopy)] transition-colors"
            />
          </button>
        </div>

        <div class="prose prose-sm max-w-none text-[color:var(--ink)] opacity-90 leading-relaxed">
          <div v-html="cleanedContent"></div>
        </div>

        <div class="flex justify-end pt-2 border-t border-slate-100">
          <Button
            variant="solid"
            label="Close"
            @click="isOpen = false"
          />
        </div>

      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed } from 'vue'
import { Dialog, Button, FeatherIcon } from 'frappe-ui'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  // Subtitle is the ONLY title now
  subtitle: {
    type: String,
    default: ''
  },
  content: {
    type: String,
    default: ''
  },
  image: {
    type: String,
    default: ''
  },
  imageFallback: {
    type: String,
    default: ''
  },
  badge: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

/**
 * CLEANER:
 * If the API response body repeats the title (e.g. "New Policy..."),
 * we strip it here so it doesn't look dumb.
 */
const cleanedContent = computed(() => {
  if (!props.content) return '';
  if (!props.subtitle) return props.content;

  // Simple check: if content starts with subtitle, slice it off
  // We use a regex to be case-insensitive and ignore whitespace
  const pattern = new RegExp(`^\\s*${escapeRegExp(props.subtitle)}`, 'i');

  // Note: This logic assumes the content is plain text or simple HTML.
  // If your API returns <p>Subtitle</p>, this might need a stricter parser.
  // For now, this handles the "Text Duplicate" issue.
  return props.content.replace(pattern, '').trim();
})

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
</script>
