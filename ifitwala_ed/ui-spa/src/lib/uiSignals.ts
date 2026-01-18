// ui-spa/src/lib/uiSignals.ts
/**
 * UI Signals (SPA)
 * --------------------------------------------------------------
 * Purpose:
 * - A tiny in-app pub/sub bus for UI invalidation + lightweight cross-surface signals.
 * - This is the integration point between:
 *     (a) workflow completion (UI Services / overlays)
 *     (b) surfaces that own refreshing (pages like StaffHome)
 *
 * A+ contract alignment:
 * - Overlays close immediately on success.
 * - UI Services (or workflow components) emit signals like "focus:invalidate".
 * - Pages listen and refresh what they own.
 *
 * Non-goals:
 * - Not a workflow engine.
 * - Not a global state store.
 * - Not a replacement for caching layers.
 *
 * Design notes:
 * - Works without window/document (SSR-safe).
 * - Handlers are kept in-memory; callers must unsubscribe on unmount.
 * - Emit is best-effort: one bad handler must not break others.
 */

/** Known signal names (extend intentionally) */
export const SIGNAL_FOCUS_INVALIDATE = 'focus:invalidate' as const
export const SIGNAL_STUDENT_LOG_INVALIDATE = 'student_log:invalidate' as const
export const SIGNAL_CALENDAR_INVALIDATE = 'calendar:invalidate' as const
export const SIGNAL_STUDENT_LOG_DASHBOARD_INVALIDATE = 'student_log_dashboard:invalidate' as const
export const SIGNAL_STUDENT_LOG_RECENT_LOGS_INVALIDATE = 'student_log_recent_logs:invalidate' as const
export const SIGNAL_STUDENT_LOG_FILTER_META_INVALIDATE = 'student_log_filter_meta:invalidate' as const
export const SIGNAL_ORG_COMMUNICATION_INVALIDATE = 'org_communication:invalidate' as const
export const SIGNAL_ATTENDANCE_INVALIDATE = 'attendance:invalidate' as const

/**
 * Optional: standard toast signal (only if/when you centralize toasts later).
 * For now, you can ignore it.
 */
export const SIGNAL_TOAST_SHOW = 'toast:show' as const

/** Union of known signals (recommended). */
export type UiSignalName =
	| typeof SIGNAL_FOCUS_INVALIDATE
	| typeof SIGNAL_STUDENT_LOG_INVALIDATE
	| typeof SIGNAL_CALENDAR_INVALIDATE
	| typeof SIGNAL_STUDENT_LOG_DASHBOARD_INVALIDATE
	| typeof SIGNAL_STUDENT_LOG_RECENT_LOGS_INVALIDATE
	| typeof SIGNAL_STUDENT_LOG_FILTER_META_INVALIDATE
	| typeof SIGNAL_ORG_COMMUNICATION_INVALIDATE
	| typeof SIGNAL_TOAST_SHOW
	| typeof SIGNAL_ATTENDANCE_INVALIDATE
	| (string & {}) // allow custom names while keeping known ones typed

export type UiSignalHandler<TPayload = unknown> = (payload?: TPayload) => void

type HandlerSet = Set<UiSignalHandler<unknown>>

/**
 * Internal store:
 * Map<signalName, Set<handler>>
 */
const handlers: Map<string, HandlerSet> = new Map()

/**
 * Subscribe to a signal.
 *
 * Rule (A+):
 * - Prefer uiSignals.subscribe() in application code.
 * - on/off are internal primitives; exporting them invites leaks.
 * - Caller must keep a stable handler reference to unsubscribe later.
 */
function on<TPayload = unknown>(name: UiSignalName, handler: UiSignalHandler<TPayload>) {
	if (!name || typeof handler !== 'function') return

	const key = String(name)
	const set = handlers.get(key) ?? new Set()
	set.add(handler as UiSignalHandler<unknown>)
	handlers.set(key, set)
}

/**
 * Unsubscribe from a signal.
 */
function off<TPayload = unknown>(name: UiSignalName, handler: UiSignalHandler<TPayload>) {
	if (!name || typeof handler !== 'function') return

	const key = String(name)
	const set = handlers.get(key)
	if (!set) return

	set.delete(handler as UiSignalHandler<unknown>)
	if (set.size === 0) handlers.delete(key)
}

/**
 * Emit a signal (best-effort).
 *
 * Contract:
 * - Emitting must never throw (one failing handler must not break the others).
 */
function emit<TPayload = unknown>(name: UiSignalName, payload?: TPayload) {
	if (!name) return

	const key = String(name)
	const set = handlers.get(key)
	if (!set || set.size === 0) return

	// Copy before iterating: lets handlers unsubscribe safely during emit.
	const snapshot = Array.from(set)
	for (const fn of snapshot) {
		try {
			;(fn as UiSignalHandler<TPayload>)(payload)
		} catch (err) {
			// Best-effort: don't break emit. Keep the error visible in console.
			// Avoid toast here (signals are infra; surfaces decide how to report).
			// eslint-disable-next-line no-console
			console.error('[uiSignals] handler failed', { name: key, err })
		}
	}
}

/**
 * Convenience: subscribe and return an unsubscribe function.
 * Useful when the handler is declared inline in a setup() block.
 *
 * A+ rule:
 * - uiSignals.on() MUST NOT be used if you expect an unsubscribe function.
 * - Use uiSignals.subscribe() instead.
 */
function subscribe<TPayload = unknown>(name: UiSignalName, handler: UiSignalHandler<TPayload>) {
	on(name, handler)
	return () => off(name, handler)
}

/**
 * Optional helper: clear all handlers (tests / hot-reload safety).
 * Do not use in application code.
 */
function _clearAllForTests() {
	handlers.clear()
}

export const uiSignals = {
	emit,
	subscribe,
	_clearAllForTests,
} as const
