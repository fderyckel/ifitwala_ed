// ifitwala_ed/ui-spa/src/composables/__tests__/useOverlayStack.test.ts

import { describe, expect, it, vi } from 'vitest'

async function loadOverlayStack() {
	vi.resetModules()
	delete (window as any).__ifit_overlay_state
	return import('@/composables/useOverlayStack')
}

describe('useOverlayStack', () => {
	it('opens and closes overlays from the stack', async () => {
		const { useOverlayStack } = await loadOverlayStack()
		const overlay = useOverlayStack()

		const overlayId = overlay.open('student-log-create', { student: 'STU-1' })
		expect(overlay.isOpen.value).toBe(true)
		expect(overlay.topId.value).toBe(overlayId)

		overlay.close(overlayId)
		expect(overlay.isOpen.value).toBe(false)
	})

	it('closeTopIf only closes when id matches current top', async () => {
		const { useOverlayStack } = await loadOverlayStack()
		const overlay = useOverlayStack()

		const first = overlay.open('student-log-create')
		const second = overlay.open('attendance-remark')

		overlay.closeTopIf(first)
		expect(overlay.topId.value).toBe(second)

		overlay.closeTopIf(second)
		expect(overlay.topId.value).toBe(first)
	})

	it('forceRemove removes non-top overlays by id', async () => {
		const { useOverlayStack } = await loadOverlayStack()
		const overlay = useOverlayStack()

		const first = overlay.open('student-log-create')
		overlay.open('attendance-remark')

		overlay.forceRemove(first)
		expect(overlay.stack.value.find((entry) => entry.id === first)).toBeUndefined()
	})
})
