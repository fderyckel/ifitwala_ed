import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { overlayCloseMock, searchStudentsMock, searchFollowUpUsersMock, getFormOptionsMock, submitStudentLogMock, addClarificationMock } = vi.hoisted(() => ({
	overlayCloseMock: vi.fn(),
	searchStudentsMock: vi.fn(),
	searchFollowUpUsersMock: vi.fn(),
	getFormOptionsMock: vi.fn(),
	submitStudentLogMock: vi.fn(),
	addClarificationMock: vi.fn(),
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
		searchStudents: searchStudentsMock,
		searchFollowUpUsers: searchFollowUpUsersMock,
		getFormOptions: getFormOptionsMock,
		submitStudentLog: submitStudentLogMock,
		addClarification: addClarificationMock,
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
	return mountOverlayWithProps({
		open: true,
		mode: 'home',
	})
}

function mountOverlayWithProps(props: Record<string, unknown>) {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StudentLogCreateOverlay, props)
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
	searchStudentsMock.mockReset()
	searchFollowUpUsersMock.mockReset()
	getFormOptionsMock.mockReset()
	submitStudentLogMock.mockReset()
	addClarificationMock.mockReset()
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

describe('StudentLogCreateOverlay form controls', () => {
	it('renders native select controls with loaded options in attendance mode', async () => {
		getFormOptionsMock.mockResolvedValue({
			log_types: [{ value: 'NOTE', label: 'Note' }],
			next_steps: [{ value: 'CALL_HOME', label: 'Call home', role: 'Teacher' }],
			student_school: 'SCH-001',
			allowed_next_step_schools: ['SCH-001'],
		})

		mountOverlayWithProps({
			open: true,
			mode: 'attendance',
			student: {
				id: 'STU-001',
				label: 'Jo',
			},
		})
		await flushUi()

		const selects = Array.from(document.querySelectorAll('select'))
		expect(selects).toHaveLength(1)
		expect(selects[0]?.textContent || '').toContain('Note')

		const followUpCheckbox = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(input =>
			(input.parentElement?.textContent || '').includes('Needs follow-up')
		) as HTMLInputElement | undefined
		followUpCheckbox?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		const followUpSelects = Array.from(document.querySelectorAll('select'))
		expect(followUpSelects).toHaveLength(2)
		expect(followUpSelects[1]?.textContent || '').toContain('Call home')
	})

	it('keeps visibility toggles in the dedicated responsive grid', async () => {
		mountOverlay()
		await flushUi()

		const visibilityLabel = Array.from(document.querySelectorAll('p')).find(node =>
			(node.textContent || '').trim() === 'Visibility'
		)
		const visibilityGrid = visibilityLabel
			?.parentElement
			?.querySelector('.student-log-create__visibility-grid') as HTMLDivElement | null

		expect(visibilityGrid).not.toBeNull()
		expect(visibilityGrid?.className || '').toContain('min-[480px]:grid-cols-2')
		expect(visibilityGrid?.textContent || '').toContain('Visible to student')
		expect(visibilityGrid?.textContent || '').toContain('Visible to parents')
	})

	it('uses shared overlay surfaces and button primitives in review mode', async () => {
		getFormOptionsMock.mockResolvedValue({
			log_types: [{ value: 'NOTE', label: 'Note' }],
			next_steps: [],
			student_school: 'SCH-001',
			allowed_next_step_schools: ['SCH-001'],
		})

		mountOverlayWithProps({
			open: true,
			mode: 'attendance',
			student: {
				id: 'STU-001',
				label: 'Jo',
			},
		})
		await flushUi()

		const logTypeSelect = document.querySelector('select') as HTMLSelectElement | null
		expect(logTypeSelect).not.toBeNull()
		if (!logTypeSelect) return

		logTypeSelect.value = 'NOTE'
		logTypeSelect.dispatchEvent(new Event('change', { bubbles: true }))

		const noteInput = document.querySelector('textarea') as HTMLTextAreaElement | null
		expect(noteInput).not.toBeNull()
		if (!noteInput) return

		noteInput.value = 'Observed a clear attendance-related concern.'
		noteInput.dispatchEvent(new Event('input', { bubbles: true }))
		await flushUi()

		const reviewButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Review & submit')
		)
		reviewButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		const reviewCard = document.querySelector('.student-log-create__review-card') as HTMLDivElement | null
		expect(reviewCard).not.toBeNull()
		expect(reviewCard?.className || '').toContain('card-panel')

		const sharedSurfaces = reviewCard?.querySelectorAll('.card-surface') || []
		expect(sharedSurfaces.length).toBeGreaterThanOrEqual(3)

		const editButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Go back and edit')
		)
		expect(editButton?.className || '').toContain('if-button')
		expect(editButton?.className || '').toContain('if-button--secondary')

		const submitButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Confirm & submit')
		)
		expect(submitButton?.className || '').toContain('if-button')
		expect(submitButton?.className || '').toContain('if-button--primary')
	})
})
