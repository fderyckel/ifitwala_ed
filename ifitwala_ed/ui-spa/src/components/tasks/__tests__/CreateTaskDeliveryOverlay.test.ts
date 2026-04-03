import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const MISSING_ACTIVE_PLAN_MESSAGE =
	'This class needs an active Class Teaching Plan before assigned work can be created.';

const { routerPushMock, toastCreateMock, closeMock } = vi.hoisted(() => ({
	routerPushMock: vi.fn(),
	toastCreateMock: vi.fn(),
	closeMock: vi.fn(),
}));

vi.mock('@headlessui/vue', () => {
	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as', 'show'],
			setup(props, { slots, attrs }) {
				return () => {
					if (props.show === false) return null;
					return h(props.as && props.as !== 'template' ? props.as : tag, attrs, slots.default?.());
				};
			},
		});

	return {
		Dialog: passthrough('div'),
		DialogPanel: passthrough('div'),
		DialogTitle: passthrough('h2'),
		TransitionChild: passthrough('div'),
		TransitionRoot: passthrough('div'),
	};
});

vi.mock('vue-router', () => ({
	useRouter: () => ({
		push: routerPushMock,
	}),
}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	const createResource = (config: { url: string; onSuccess?: (payload: any) => void; onError?: (error: any) => void }) => {
		if (config.url === 'ifitwala_ed.api.quiz.list_question_banks') {
			return {
				loading: false,
				submit: async () => {
					config.onSuccess?.([]);
					return [];
				},
			};
		}
		if (config.url === 'ifitwala_ed.assessment.task_creation_service.create_task_and_delivery') {
			return {
				loading: false,
				submit: async () => {
					const error = {
						message: '/api/method/ifitwala_ed.assessment.task_creation_service.create_task_and_delivery ValidationError',
						response: {
							_server_messages: JSON.stringify([
								JSON.stringify({ message: MISSING_ACTIVE_PLAN_MESSAGE }),
							]),
						},
					};
					config.onError?.(error);
					throw error;
				},
			};
		}
		return {
			loading: false,
			submit: async () => {
				config.onSuccess?.({ materials: [] });
				return { materials: [] };
			},
		};
	};

	return {
		Button: defineComponent({
			name: 'ButtonStub',
			props: ['disabled', 'loading', 'appearance'],
			emits: ['click'],
			setup(props, { slots, emit }) {
				return () =>
					h(
						'button',
						{
							disabled: props.disabled,
							onClick: (event: MouseEvent) => emit('click', event),
						},
						slots.default?.()
					);
			},
		}),
		FormControl: defineComponent({
			name: 'FormControlStub',
			props: {
				modelValue: {
					type: [String, Number, Boolean],
					required: false,
					default: '',
				},
				type: {
					type: String,
					required: false,
					default: 'text',
				},
				options: {
					type: Array,
					required: false,
					default: () => [],
				},
				optionLabel: {
					type: String,
					required: false,
					default: 'label',
				},
				optionValue: {
					type: String,
					required: false,
					default: 'value',
				},
				placeholder: {
					type: String,
					required: false,
					default: '',
				},
				rows: {
					type: Number,
					required: false,
					default: 3,
				},
				disabled: {
					type: Boolean,
					required: false,
					default: false,
				},
			},
			emits: ['update:modelValue'],
			setup(props, { emit }) {
				return () => {
					if (props.type === 'textarea') {
						return h('textarea', {
							value: props.modelValue ?? '',
							placeholder: props.placeholder,
							rows: props.rows,
							onInput: (event: Event) =>
								emit('update:modelValue', (event.target as HTMLTextAreaElement).value),
						});
					}
					if (props.type === 'select') {
						const options = Array.isArray(props.options) ? props.options : [];
						return h(
							'select',
							{
								value: props.modelValue ?? '',
								disabled: props.disabled,
								onChange: (event: Event) =>
									emit('update:modelValue', (event.target as HTMLSelectElement).value),
							},
							[
								h('option', { value: '' }, props.placeholder || ''),
								...options.map((option: any) =>
									h(
										'option',
										{ value: option?.[props.optionValue] ?? option?.value ?? '' },
										String(option?.[props.optionLabel] ?? option?.label ?? option ?? '')
									)
								),
							]
						);
					}
					return h('input', {
						type: props.type === 'number' ? 'number' : 'text',
						value: props.modelValue ?? '',
						placeholder: props.placeholder,
						disabled: props.disabled,
						onInput: (event: Event) =>
							emit('update:modelValue', (event.target as HTMLInputElement).value),
					});
				};
			},
		}),
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			setup() {
				return () => h('span');
			},
		}),
		createResource,
		toast: {
			create: toastCreateMock,
		},
	};
});

import CreateTaskDeliveryOverlay from '@/components/tasks/CreateTaskDeliveryOverlay.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountOverlay() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(CreateTaskDeliveryOverlay, {
					open: true,
					prefillStudentGroup: 'GRP-1',
					onClose: closeMock,
				});
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

afterEach(() => {
	routerPushMock.mockReset();
	toastCreateMock.mockReset();
	closeMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('CreateTaskDeliveryOverlay', () => {
	it('explains that comments are an additive gradebook option', async () => {
		mountOverlay();
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Allow comment in gradebook?');
		expect(text).toContain('Comments stay separate from points, criteria, or completion.');
	});

	it('turns missing class planning validation into an actionable recovery path', async () => {
		mountOverlay();
		await flushUi();

		const titleInput = document.querySelector('input[placeholder="Assignment title"]') as
			| HTMLInputElement
			| null;
		expect(titleInput).not.toBeNull();
		titleInput!.value = 'Microscope reflection';
		titleInput!.dispatchEvent(new Event('input', { bubbles: true }));
		await flushUi();

		const createButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Create')
		);
		expect(createButton).not.toBeNull();
		createButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Open Class Planning for this class, create or activate the plan');
		expect(text).toContain('Open class planning');

		const recoveryButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Open class planning')
		);
		expect(recoveryButton).not.toBeNull();
		recoveryButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(closeMock).toHaveBeenCalledWith('programmatic');
		expect(routerPushMock).toHaveBeenCalledWith({
			name: 'staff-class-planning',
			params: { studentGroup: 'GRP-1' },
		});
	});
});
