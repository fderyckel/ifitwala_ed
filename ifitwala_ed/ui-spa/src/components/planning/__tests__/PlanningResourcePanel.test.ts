import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const { createPlanningReferenceMaterialMock, toastSuccessMock, toastErrorMock } = vi.hoisted(
	() => ({
		createPlanningReferenceMaterialMock: vi.fn(),
		toastSuccessMock: vi.fn(),
		toastErrorMock: vi.fn(),
	})
);

vi.mock('frappe-ui', () => ({
	Button: defineComponent({
		name: 'ButtonStub',
		props: ['disabled', 'loading', 'appearance'],
		emits: ['click'],
		setup(props, { emit, slots }) {
			return () =>
				h(
					'button',
					{
						type: 'button',
						disabled: props.disabled || props.loading,
						onClick: (event: MouseEvent) => emit('click', event),
					},
					slots.default?.()
				);
		},
	}),
	FormControl: defineComponent({
		name: 'FormControlStub',
		props: ['modelValue', 'type', 'options', 'placeholder', 'rows', 'optionLabel', 'optionValue'],
		emits: ['update:modelValue'],
		setup(props, { emit }) {
			return () => {
				if (props.type === 'textarea') {
					return h('textarea', {
						value: props.modelValue || '',
						placeholder: props.placeholder,
						rows: props.rows,
						onInput: (event: Event) =>
							emit('update:modelValue', (event.target as HTMLTextAreaElement).value),
					});
				}
				if (props.type === 'select') {
					return h(
						'select',
						{
							value: props.modelValue || '',
							onChange: (event: Event) =>
								emit('update:modelValue', (event.target as HTMLSelectElement).value),
						},
						(props.options || []).map((option: Record<string, string>) =>
							h(
								'option',
								{
									value: option.value,
								},
								option.label
							)
						)
					);
				}
				return h('input', {
					value: props.modelValue || '',
					placeholder: props.placeholder,
					onInput: (event: Event) =>
						emit('update:modelValue', (event.target as HTMLInputElement).value),
				});
			};
		},
	}),
	toast: {
		success: toastSuccessMock,
		error: toastErrorMock,
	},
}));

vi.mock('@/lib/services/staff/staffTeachingService', () => ({
	createPlanningReferenceMaterial: createPlanningReferenceMaterialMock,
	uploadPlanningMaterialFile: vi.fn(),
	removePlanningMaterial: vi.fn(),
}));

import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountPanel(resources: Array<Record<string, unknown>> = []) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(PlanningResourcePanel, {
					anchorDoctype: 'Unit Plan',
					anchorName: 'UNIT-PLAN-1',
					eyebrow: 'Unit Resources',
					title: 'Shared resources for this unit',
					description: 'Governed materials for the selected unit.',
					emptyMessage: 'No resources yet.',
					blockedMessage: 'Save the unit first.',
					resources,
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

function setInputValue(placeholder: string, value: string) {
	const input = document.querySelector(
		`input[placeholder="${placeholder}"]`
	) as HTMLInputElement | null;
	if (!input) throw new Error(`Missing input ${placeholder}`);
	input.value = value;
	input.dispatchEvent(new Event('input', { bubbles: true }));
}

afterEach(() => {
	createPlanningReferenceMaterialMock.mockReset();
	toastSuccessMock.mockReset();
	toastErrorMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('PlanningResourcePanel', () => {
	it('allows link sharing with a derived title from the URL hostname', async () => {
		createPlanningReferenceMaterialMock.mockResolvedValue({
			placement: 'MAT-PLC-1',
		});

		mountPanel();
		await flushUi();

		const linkModeButton = document.querySelector(
			'button[data-resource-mode="link"]'
		) as HTMLButtonElement | null;
		linkModeButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		setInputValue('https://...', 'https://www.youtube.com/watch?v=abc123');
		await flushUi();

		const submitButton = Array.from(document.querySelectorAll('button')).find(
			button =>
				(button.textContent || '').trim() === 'Add link' &&
				!button.hasAttribute('data-resource-mode')
		) as HTMLButtonElement | undefined;
		if (!submitButton) throw new Error('Missing Add link submit button');

		expect(submitButton.disabled).toBe(false);
		submitButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(createPlanningReferenceMaterialMock).toHaveBeenCalledWith(
			expect.objectContaining({
				anchor_doctype: 'Unit Plan',
				anchor_name: 'UNIT-PLAN-1',
				title: 'youtube.com',
				reference_url: 'https://www.youtube.com/watch?v=abc123',
			})
		);
		expect(toastSuccessMock).toHaveBeenCalledWith('Resource shared successfully.');
	});

	it('prefers preview links for governed file resources and keeps an explicit original action', async () => {
		mountPanel([
			{
				material: 'MAT-1',
				title: 'Unit diagram',
				material_type: 'File',
				preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1',
				open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1',
			},
		]);
		await flushUi();

		const actions = Array.from(document.querySelectorAll('a.if-action'));
		expect(actions).toHaveLength(2);
		expect(actions[0]?.textContent?.trim()).toBe('Preview');
		expect(actions[0]?.getAttribute('href')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1'
		);
		expect(actions[1]?.textContent?.trim()).toBe('Open original');
		expect(actions[1]?.getAttribute('href')).toBe(
			'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1'
		);
	});
});
