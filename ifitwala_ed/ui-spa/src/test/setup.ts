// ifitwala_ed/ui-spa/src/test/setup.ts

import { afterEach, vi } from 'vitest'

class ResizeObserverStub {
	disconnect() {}
	observe() {}
	unobserve() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverStub)

if (typeof window !== 'undefined' && !window.HTMLElement.prototype.scrollIntoView) {
	window.HTMLElement.prototype.scrollIntoView = vi.fn()
}

afterEach(() => {
	const w = window as any
	delete w.__ifit_overlay_state
	delete w.__overlay_debug
	delete w.__overlay_debug_trace
})
