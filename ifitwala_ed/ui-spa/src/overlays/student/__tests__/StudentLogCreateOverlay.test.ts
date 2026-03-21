import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { overlayCloseMock } = vi.hoisted(() => ({
	overlayCloseMock: vi.fn(),
}))

vi.mock('@headlessui/vue', () => {
	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as'],
			setup(props, { slots }) {
				return () => h(props.as && props.as !== 'template' ? props.as : tag, slots.default?.())
			},
		})

	return {
		Dialog: passthrough('div'),
		DialogPanel: passthrough('div'),
		DialogTitle: passthrough('h2'),
		TransitionChild: passthrough('div'),
		TransitionRoot: passthrough('div'),
	}
})

vi.mock('frappe-ui', () => ({
	Button: defineComponent({
		name: 'ButtonStub',
		props: ['disabled', 'loading'],
		emits: ['click'],
		setup(props, { slots, emit }) {
			return () =>
				h(
					'button',
					{
						disabled: props.disabled,
						onClick: (event: MouseEvent) => emit('click', event),
					},
					[slots.prefix?.(), slots.default?.()]
				)
		},
	}),
	FormControl: defineComponent({
		name: 'FormControlStub',
		setup() {
			return () => h('div')
		},
	}),
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		setup() {
			return () => h('span')
		},
	}),
	Spinner: defineComponent({
		name: 'SpinnerStub',
		setup() {
			return () => h('span')
		},
	}),
}))

vi.mock('@/lib/services/studentLog/studentLogService', () => ({
	createStudentLogService: () => ({
		searchStudents: vi.fn(),
		searchFollowUpUsers: vi.fn(),
		getFormOptions: vi.fn(),
		submitStudentLog: vi.fn(),
		addClarification: vi.fn(),
	}),
}))

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		close: overlayCloseMock,
	}),
}))

import StudentLogCreateOverlay from '@/overlays/student/StudentLogCreateOverlay.vue'

const cleanupFns: Array<() => void> = []

class SpeechRecognitionStub {
	continuous = false
	interimResults = false
	lang = 'en-US'
	onstart: null | (() => void) = null
	onresult: null | ((event: any) => void) = null
	onerror: null | ((event: any) => void) = null
	onend: null | (() => void) = null

	start() {}
	stop() {}
	abort() {}
}

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
				return h(StudentLogCreateOverlay, {
					open: true,
					mode: 'home',
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

function setMicrophonePermission(state: PermissionState) {
	Object.defineProperty(window, 'isSecureContext', {
		configurable: true,
		value: true,
	})

	Object.defineProperty(window.navigator, 'permissions', {
		configurable: true,
		value: {
			query: vi.fn().mockResolvedValue({ state }),
		},
	})
}

afterEach(() => {
	overlayCloseMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
	Object.defineProperty(window, 'SpeechRecognition', {
		configurable: true,
		value: undefined,
	})
	Object.defineProperty(window, 'webkitSpeechRecognition', {
		configurable: true,
		value: undefined,
	})
})

describe('StudentLogCreateOverlay speech dictation', () => {
	it('shows an inline recovery hint when microphone permission is denied', async () => {
		Object.defineProperty(window, 'SpeechRecognition', {
			configurable: true,
			value: SpeechRecognitionStub,
		})
		setMicrophonePermission('denied')

		mountOverlay()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Microphone access is blocked for this site.')
		expect(text).toContain('Allow microphone access in your browser settings')
	})

	it('turns a not-allowed speech error into an actionable inline error', async () => {
		class NotAllowedSpeechRecognitionStub extends SpeechRecognitionStub {
			override start() {
				this.onerror?.({ error: 'not-allowed' })
				this.onend?.()
			}
		}

		Object.defineProperty(window, 'SpeechRecognition', {
			configurable: true,
			value: NotAllowedSpeechRecognitionStub,
		})
		setMicrophonePermission('granted')

		mountOverlay()
		await flushUi()

		const dictateButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Dictate')
		)
		dictateButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Something went wrong')
		expect(text).toContain('Microphone access is blocked for this site.')
		expect(text).toContain('Allow microphone access in your browser settings')
	})
})
