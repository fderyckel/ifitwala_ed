import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { closeMock, getLearningStandardPickerMock } = vi.hoisted(() => ({
	closeMock: vi.fn(),
	getLearningStandardPickerMock: vi.fn(),
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
	Button: defineComponent({
		name: 'ButtonStub',
		props: {
			disabled: {
				type: Boolean,
				required: false,
				default: false,
			},
		},
		emits: ['click'],
		setup(props, { emit, slots }) {
			return () =>
				h(
					'button',
					{
						disabled: props.disabled,
						onClick: (event: MouseEvent) => emit('click', event),
					},
					slots.default?.()
				)
		},
	}),
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		setup() {
			return () => h('span')
		},
	}),
}))

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		close: closeMock,
	}),
}))

vi.mock('@/lib/services/staff/staffTeachingService', () => ({
	getLearningStandardPicker: getLearningStandardPickerMock,
}))

import LearningStandardsPickerOverlay from '@/overlays/planning/LearningStandardsPickerOverlay.vue'

const cleanupFns: Array<() => void> = []

async function flushUi(cycles = 2) {
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
				return h(LearningStandardsPickerOverlay, {
					open: true,
					unitPlan: 'UNIT-1',
					unitTitle: 'Unit 1: Personal Narratives',
					unitProgram: 'IB MYP G6',
					programLocked: true,
					existingStandards: [],
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
	getLearningStandardPickerMock.mockReset()
	closeMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('LearningStandardsPickerOverlay', () => {
	it('loads immediately on mount and hides the program selector when the unit program is locked', async () => {
		getLearningStandardPickerMock.mockResolvedValue({
			filters: {
				unit_plan: 'UNIT-1',
				program: 'IB-MYP-G6',
			},
			options: {
				frameworks: ['IB MYP', 'Common Core'],
				programs: ['IB MYP G6'],
				strands: [],
				substrands: [],
				has_blank_substrand: false,
			},
			standards: [],
		})

		mountOverlay()
		await flushUi()

		expect(getLearningStandardPickerMock).toHaveBeenCalledWith({
			unit_plan: 'UNIT-1',
			framework_name: undefined,
			program: undefined,
			strand: undefined,
			substrand: undefined,
			search_text: undefined,
		})
		expect(document.body.textContent || '').toContain('Framework')
		expect(document.body.textContent || '').not.toContain('All programs')
	})

	it('reloads after auto-selecting the only framework so the strand step can appear', async () => {
		getLearningStandardPickerMock
			.mockResolvedValueOnce({
				filters: {
					unit_plan: 'UNIT-1',
					program: 'IB-MYP-G6',
				},
				options: {
					frameworks: ['IB MYP'],
					programs: ['IB MYP G6'],
					strands: [],
					substrands: [],
					has_blank_substrand: false,
				},
				standards: [],
			})
			.mockResolvedValueOnce({
				filters: {
					unit_plan: 'UNIT-1',
					framework_name: 'IB MYP',
					program: 'IB-MYP-G6',
				},
				options: {
					frameworks: ['IB MYP'],
					programs: ['IB MYP G6'],
					strands: ['Identity'],
					substrands: [],
					has_blank_substrand: false,
				},
				standards: [],
			})

		mountOverlay()
		await flushUi(4)

		expect(getLearningStandardPickerMock).toHaveBeenCalledTimes(3)
		expect(getLearningStandardPickerMock).toHaveBeenNthCalledWith(2, {
			unit_plan: 'UNIT-1',
			framework_name: undefined,
			program: 'IB-MYP-G6',
			strand: undefined,
			substrand: undefined,
			search_text: undefined,
		})
		expect(getLearningStandardPickerMock).toHaveBeenNthCalledWith(3, {
			unit_plan: 'UNIT-1',
			framework_name: 'IB MYP',
			program: 'IB-MYP-G6',
			strand: undefined,
			substrand: undefined,
			search_text: undefined,
		})
		expect(document.body.textContent || '').toContain('Strand')
		expect(document.body.textContent || '').toContain('Choose strand')
	})
})
