// ui-spa/src/composables/useOverlayStack.ts
import { computed, reactive } from 'vue'

export type OverlayType =
  | 'create-task'
  | 'meeting-event'
  | 'school-event'
  | 'class-event'
  | 'org-communication-quick-create'
  | 'attendance-remark'
  | 'student-log-create'
  | 'student-log-follow-up'
  | 'student-log-analytics-expand'
  | 'org-chart-person'
  | 'staff-policy-signature-campaign'
  | 'focus-router'
  | 'class-hub-student-context'
  | 'class-hub-quick-evidence'
  | 'class-hub-quick-cfu'
  | 'class-hub-task-review'
  | 'admissions-health'
  | 'admissions-document-upload'
  | 'admissions-policy-ack'
  | 'admissions-submit'

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
  if ((window as any).__overlay_debug_trace === true) {
    // Always-visible stack, not a collapsed trace
    // eslint-disable-next-line no-console
    console.error(
      '[overlay] close() CALLED',
      { id, stackSize: state.stack.length, stack: state.stack.map((x) => ({ id: x.id, type: x.type })) },
      new Error('overlay.close() callsite')
    )
  }

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


function forceRemove(id: string) {
  const safeId = String(id || '').trim()
  if (!safeId) return

  if ((window as any).__overlay_debug_trace === true) {
    // eslint-disable-next-line no-console
    console.groupCollapsed('[overlay] forceRemove()', { id: safeId, stackSize: state.stack.length })
    // eslint-disable-next-line no-console
    console.log('stack(before)=', state.stack.map((x) => ({ id: x.id, type: x.type })))
    // eslint-disable-next-line no-console
    console.trace('forceRemove() callsite')
    // eslint-disable-next-line no-console
    console.groupEnd()
  }

  const idx = state.stack.findIndex((x) => x.id === safeId)
  if (idx >= 0) {
    state.stack.splice(idx, 1)
    log('forceRemove:id', safeId)
  } else {
    log('forceRemove:miss', safeId)
  }
}

function closeTop() {
  if ((window as any).__overlay_debug_trace === true) {
    // eslint-disable-next-line no-console
    console.groupCollapsed('[overlay] closeTop()', { stackSize: state.stack.length })
    // eslint-disable-next-line no-console
    console.log('stack(before)=', state.stack.map((x) => ({ id: x.id, type: x.type })))
    // eslint-disable-next-line no-console
    console.trace('closeTop() callsite')
    // eslint-disable-next-line no-console
    console.groupEnd()
  }

  const removed = state.stack.pop()
  log('closeTop', removed?.id)
}

function closeTopIf(id: string) {
  if ((window as any).__overlay_debug_trace === true) {
    // eslint-disable-next-line no-console
    console.groupCollapsed('[overlay] closeTopIf()', { id, stackSize: state.stack.length })
    // eslint-disable-next-line no-console
    console.log('stack(before)=', state.stack.map((x) => ({ id: x.id, type: x.type })))
    // eslint-disable-next-line no-console
    console.trace('closeTopIf() callsite')
    // eslint-disable-next-line no-console
    console.groupEnd()
  }

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
    forceRemove,
    closeTop,
    closeTopIf,
    replaceTop,
  }
}
