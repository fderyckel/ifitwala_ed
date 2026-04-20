import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianCalendarOverlayMock, overlayOpenMock, overlayCloseMock } = vi.hoisted(() => ({
	getGuardianCalendarOverlayMock: vi.fn(),
	overlayOpenMock: vi.fn(),
	overlayCloseMock: vi.fn(),
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
		setup(props, { attrs, slots }) {
			return () => {
				if (props.show === false) {
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

vi.mock('@/lib/services/guardianCalendar/guardianCalendarService', () => ({
	getGuardianCalendarOverlay: getGuardianCalendarOverlayMock,
}))

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
		close: overlayCloseMock,
	}),
}))

import GuardianCalendarOverlay from '@/overlays/guardian/GuardianCalendarOverlay.vue'

const cleanupFns: Array<() => void> = []

function buildPayload() {
	return {
		meta: {
			generated_at: '2026-04-20T09:00:00',
			timezone: 'Asia/Bangkok',
			month_start: '2026-04-01',
			month_end: '2026-04-30',
			filters: {
				student: null,
				school: null,
				include_holidays: true,
				include_school_events: true,
			},
		},
		family: {
			children: [
				{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
				{ student: 'STU-2', full_name: 'Noah Example', school: 'School Two' },
			],
		},
		filter_options: {
			students: [
				{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
				{ student: 'STU-2', full_name: 'Noah Example', school: 'School Two' },
			],
			schools: [
				{ school: 'School One', label: 'School One' },
				{ school: 'School Two', label: 'School Two' },
			],
		},
		summary: {
			holiday_count: 1,
			school_event_count: 1,
		},
		items: [
			{
				item_id: 'holiday::CAL-1::2026-04-01',
				kind: 'holiday',
				title: 'Songkran Break',
				start: '2026-04-01',
				end: '2026-04-01',
				all_day: true,
				color: '#dc2626',
				school: 'School One',
				matched_children: [
					{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
				],
				description: 'School closed.',
				event_category: null,
				open_target: null,
			},
			{
				item_id: 'event::EVENT-1',
				kind: 'school_event',
				title: 'Parent Conference',
				start: '2026-04-01T09:00:00',
				end: '2026-04-01T11:00:00',
				all_day: false,
				color: '#2563eb',
				school: 'School One',
				matched_children: [
					{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
				],
				description: 'Meet teachers in person.',
				event_category: 'Meeting',
				open_target: { type: 'school-event', name: 'EVENT-1' },
			},
		],
	}
}

async function flushUi(cycles = 3) {
	for (let index = 0; index < cycles; index += 1) {
		await Promise.resolve()
		await nextTick()
	}
}

function mountOverlay(props: Record<string, unknown> = {}) {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianCalendarOverlay, {
					open: true,
					overlayId: 'ov_guardian_calendar',
					initialMonthStart: '2026-04-15',
					...props,
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
	getGuardianCalendarOverlayMock.mockReset()
	overlayOpenMock.mockReset()
	overlayCloseMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('GuardianCalendarOverlay', () => {
	it('loads the monthly guardian calendar payload on mount', async () => {
		getGuardianCalendarOverlayMock.mockResolvedValue(buildPayload())

		mountOverlay()
		await flushUi()

		expect(getGuardianCalendarOverlayMock).toHaveBeenCalledWith({
			month_start: '2026-04-01',
			student: undefined,
			school: undefined,
			include_holidays: 1,
			include_school_events: 1,
		})

		const text = document.body.textContent || ''
		expect(text).toContain('School Calendar')
		expect(text).toContain('Songkran Break')
		expect(text).toContain('Parent Conference')
	})

	it('locks the school filter to the selected child and refetches in child scope', async () => {
		getGuardianCalendarOverlayMock.mockResolvedValue(buildPayload())

		mountOverlay()
		await flushUi()

		const selects = Array.from(document.querySelectorAll('select'))
		expect(selects.length).toBeGreaterThanOrEqual(2)

		const childSelect = selects[0] as HTMLSelectElement
		childSelect.value = 'STU-1'
		childSelect.dispatchEvent(new Event('change', { bubbles: true }))
		await flushUi()

		expect(getGuardianCalendarOverlayMock).toHaveBeenLastCalledWith({
			month_start: '2026-04-01',
			student: 'STU-1',
			school: 'School One',
			include_holidays: 1,
			include_school_events: 1,
		})

		const schoolSelect = selects[1] as HTMLSelectElement
		expect(schoolSelect.disabled).toBe(true)
		expect(document.body.textContent || '').toContain('School is fixed to School One')
	})

	it('opens the existing school-event detail overlay from the day agenda', async () => {
		getGuardianCalendarOverlayMock.mockResolvedValue(buildPayload())

		mountOverlay()
		await flushUi()

		const dayButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Parent Conference')
		)
		expect(dayButton).toBeTruthy()

		dayButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		const viewDetailsButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('View details')
		)
		expect(viewDetailsButton).toBeTruthy()

		viewDetailsButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))

		expect(overlayOpenMock).toHaveBeenCalledWith('school-event', { event: 'EVENT-1' })
	})
})
