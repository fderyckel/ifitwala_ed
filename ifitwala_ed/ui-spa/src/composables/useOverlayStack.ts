// ui-spa/src/composables/useOverlayStack.ts
import { computed, reactive } from 'vue'

export type OverlayType =
  | 'create-task'
  | 'meeting-event'
  | 'school-event'
  | 'class-event'

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

const state: OverlayState = reactive({
  stack: [],
})

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
    replaceTop,
  }
}
