// ifitwala_ed/ui-spa/src/test/setup.ts

import { afterEach } from 'vitest'

afterEach(() => {
	const w = window as any
	delete w.__ifit_overlay_state
	delete w.__overlay_debug
	delete w.__overlay_debug_trace
})
