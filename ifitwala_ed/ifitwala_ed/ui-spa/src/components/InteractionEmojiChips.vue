<!-- ifitwala_ed/ui-spa/src/components/InteractionEmojiChips.vue -->
<!--
  InteractionEmojiChips.vue
  Displays reaction counts (like, love, etc.) as clickable chips.
  Handles visual state for active/inactive reactions.

  Used by:
  - ContentDialog.vue
  - MorningBriefing.vue
-->
<template>
  <div class="flex flex-wrap items-center gap-2">
    <button
      v-for="chip in chips"
      :key="chip.code"
      type="button"
      class="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition"
      :class="chipClass(chip.code)"
      :disabled="readonly || !onReact"
      @click="handleClick(chip.code)"
    >
      <span class="text-[12px] leading-none">{{ chip.emoji }}</span>
      <span class="text-[10px] font-mono" :class="countClass(chip.code)">
        {{ counts[chip.code] ?? 0 }}
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InteractionSummary } from '@/types/morning_brief'
import type { InteractionIntentType, ReactionCode } from '@/types/interactions'
import { getInteractionStats } from '@/utils/interactionStats'

const props = withDefaults(
  defineProps<{
    interaction: InteractionSummary
    readonly?: boolean
    onReact?: (code: ReactionCode) => void
  }>(),
  {
    readonly: true,
  }
)

const chips = [
  { code: 'like' as const, emoji: '👍' },
  { code: 'thank' as const, emoji: '🙏' },
  { code: 'heart' as const, emoji: '❤️' },
  { code: 'smile' as const, emoji: '😊' },
  { code: 'applause' as const, emoji: '👏' },
  { code: 'question' as const, emoji: '❓' },
]

const INTENT_TO_REACTION: Partial<Record<InteractionIntentType, ReactionCode>> = {
  Acknowledged: 'like',
  Appreciated: 'thank',
  Support: 'heart',
  Positive: 'smile',
  Celebration: 'applause',
  Question: 'question',
  Concern: 'concern',
}

const stats = computed(() => getInteractionStats(props.interaction))
const counts = computed(() => stats.value.reaction_counts)

const activeCode = computed<ReactionCode | null>(() => {
  const self = props.interaction?.self
  const direct = (self?.reaction_code || null) as ReactionCode | null
  if (direct) return direct
  const intent = (self?.intent_type || null) as InteractionIntentType | null
  if (!intent) return null
  return INTENT_TO_REACTION[intent] || null
})

function isActive(code: ReactionCode): boolean {
  // Only highlight codes we actually render
  return activeCode.value === code
}

function chipClass(code: ReactionCode): string {
  if (isActive(code)) {
    return 'border-jacaranda/60 bg-jacaranda/10 text-ink shadow-sm ring-1 ring-jacaranda/20'
  }
  return 'border-border/60 bg-white/70 text-slate-token/80 hover:bg-surface-soft hover:border-jacaranda/30'
}

function countClass(code: ReactionCode): string {
  return isActive(code) ? 'text-ink/70' : 'text-slate-token/60'
}

function handleClick(code: ReactionCode) {
  if (props.readonly || !props.onReact) return
  props.onReact(code)
}
</script>
