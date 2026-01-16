// ui-spa/src/composables/useOverlayStack.ts
import { computed, reactive } from 'vue'

export type OverlayType =
  | 'create-task'
  | 'meeting-event'
  | 'school-event'
  | 'class-event'
  | 'org-communication-quick-create'
  | 'student-log-create'
  | 'student-log-follow-up'
  | 'student-log-analytics-expand'
  | 'focus-router'
  | 'class-hub-student-context'
  | 'class-hub-quick-evidence'
  | 'class-hub-quick-cfu'
  | 'class-hub-task-review'

export type OverlayEntry = {
  id: string
  type: OverlayType
  props?: Record<string, any>
  closeOnBackdrop?: boolean
  closeOnEsc?: boolean
}

type OverlayState = {
  stack: OverlayEntry[]
}

// ✅ hard guarantee: one state per browser tab, even if module is bundled twice
function getSingletonState(): OverlayState {
  const w = window as any
  if (w.__ifit_overlay_state) return w.__ifit_overlay_state
  w.__ifit_overlay_state = reactive<OverlayState>({ stack: [] })
  return w.__ifit_overlay_state
}

const state: OverlayState =
  typeof window !== 'undefined' ? getSingletonState() : reactive({ stack: [] })

function uid() {
  return `ov_${Math.random().toString(16).slice(2)}_${Date.now()}`
}

function log(...args: any[]) {
  if ((window as any).__overlay_debug === true) {
    // eslint-disable-next-line no-console
    console.log('[overlay]', ...args)
  }
}

function open(
  type: OverlayType,
  props: Record<string, any> = {},
  opts?: Partial<Pick<OverlayEntry, 'closeOnBackdrop' | 'closeOnEsc'>>
) {
  const entry: OverlayEntry = {
    id: uid(),
    type,
    props,
    closeOnBackdrop: opts?.closeOnBackdrop ?? true,
    closeOnEsc: opts?.closeOnEsc ?? true,
  }
  state.stack.push(entry)
  log('open', entry)
  return entry.id
}

function close(id?: string) {
  if (!id) {
    const removed = state.stack.pop()
    log('close:top', removed?.id)
    return
  }
  const idx = state.stack.findIndex((x) => x.id === id)
  if (idx >= 0) {
    state.stack.splice(idx, 1)
    log('close:id', id)
  } else {
    log('close:miss', id)
  }
}

function closeTop() {
  const removed = state.stack.pop()
  log('closeTop', removed?.id)
}

function closeTopIf(id: string) {
  const t = state.stack[state.stack.length - 1]
  if (t?.id === id) {
    const removed = state.stack.pop()
    log('closeTopIf', removed?.id)
  } else {
    log('closeTopIf:blocked', { id, top: t?.id })
  }
}

/**
 * A+ required: forceRemove()
 * - Removes an entry from the internal stack.
 * - OverlayHost may call this as a LAST resort.
 * - OverlayHost must never mutate state.stack directly.
 */
function forceRemove(id: string) {
  const safeId = String(id || '').trim()
  if (!safeId) return
  const idx = state.stack.findIndex((x) => x.id === safeId)
  if (idx >= 0) {
    state.stack.splice(idx, 1)
    log('forceRemove', safeId)
  } else {
    log('forceRemove:miss', safeId)
  }
}

function replaceTop(
  type: OverlayType,
  props: Record<string, any> = {},
  opts?: Partial<Pick<OverlayEntry, 'closeOnBackdrop' | 'closeOnEsc'>>
) {
  const removed = state.stack.pop()
  log('replaceTop:pop', removed?.id)
  const id = open(type, props, opts)
  log('replaceTop:open', { id, type })
  return id
}

const top = computed(() => state.stack[state.stack.length - 1] ?? null)
const topId = computed(() => top.value?.id ?? null)
const isOpen = computed(() => state.stack.length > 0)

export function useOverlayStack() {
  return {
    state,
    stack: computed(() => state.stack),
    top,
    topId,
    isOpen,
    open,
    close,
    closeTop,
    closeTopIf,
    forceRemove,
    replaceTop,
  }
}
