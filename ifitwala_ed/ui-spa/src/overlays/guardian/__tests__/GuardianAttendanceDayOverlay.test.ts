import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { clearSelectionMock, closeEventMock } = vi.hoisted(() => ({
	clearSelectionMock: vi.fn(),
	closeEventMock: vi.fn(),
}))

function passthroughComponent(name: string, tag = 'div') {
	return defineComponent({
		name,
		inheritAttrs: false,
		props: {
			as: {
				type: String,
				required: false,
				default: tag,
			},
			show: {
				type: Boolean,
				required: false,
				default: true,
			},
		},
		emits: ['after-leave'],
		setup(props, { attrs, emit, slots }) {
			return () => {
				if (props.show === false) {
					emit('after-leave')
					return null
				}
				if (props.as === 'template') {
					return slots.default?.()
				}
				return h(props.as || tag, attrs, slots.default?.())
			}
		},
	})
}

vi.mock('@headlessui/vue', () => ({
	Dialog: passthroughComponent('Dialog'),
	DialogPanel: passthroughComponent('DialogPanel'),
	DialogTitle: passthroughComponent('DialogTitle', 'h2'),
	TransitionChild: passthroughComponent('TransitionChild'),
	TransitionRoot: passthroughComponent('TransitionRoot'),
}))

vi.mock('frappe-ui', () => ({
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		props: {
			name: {
				type: String,
				required: false,
				default: '',
			},
		},
		setup(props) {
			return () => h('span', { 'data-feather-icon': props.name })
		},
	}),
}))

import GuardianAttendanceDayOverlay from '@/overlays/guardian/GuardianAttendanceDayOverlay.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountOverlay() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianAttendanceDayOverlay, {
					open: true,
					overlayId: 'ov_guardian_attendance_day',
					studentName: 'Amina Example',
					day: {
						date: '2026-03-12',
						state: 'late',
						details: [
							{
								attendance: 'ATT-1',
								time: '08:15',
								attendance_code: 'L',
								attendance_code_name: 'Late',
								whole_day: false,
								course: 'Math',
								location: 'Room 201',
								remark: 'Late bus',
							},
						],
					},
					clearSelection: clearSelectionMock,
					onClose: closeEventMock,
				})
			},
		})
	)

	app.mount(host)
	cleanupFns.push(() => {
		app.unmount()
		host.remove()
	})
}

afterEach(() => {
	clearSelectionMock.mockReset()
	closeEventMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('GuardianAttendanceDayOverlay', () => {
	it('renders the selected attendance detail inside a compact overlay', async () => {
		mountOverlay()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Amina Example')
		expect(text).toContain('attendance detail(s)')
		expect(text).toContain('Late or tardy')
		expect(text).toContain('Late bus')
		expect(text).toContain('Math')
		expect(text).toContain('Room 201')
	})

	it('emits a programmatic close and clears the selected cell state', async () => {
		mountOverlay()
		await flushUi()

		const closeButton = document.querySelector('[aria-label="Close attendance detail"]') as
			| HTMLButtonElement
			| null
		expect(closeButton).not.toBeNull()

		closeButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))

		expect(clearSelectionMock).toHaveBeenCalledTimes(1)
		expect(closeEventMock).toHaveBeenCalledWith('programmatic')
	})

	it('closes when the user clicks outside the dialog panel', async () => {
		mountOverlay()
		await flushUi()

		const wrap = document.querySelector('.if-overlay__wrap') as HTMLDivElement | null
		expect(wrap).not.toBeNull()

		wrap?.dispatchEvent(new MouseEvent('click', { bubbles: true }))

		expect(clearSelectionMock).toHaveBeenCalledTimes(1)
		expect(closeEventMock).toHaveBeenCalledWith('backdrop')
	})
})
