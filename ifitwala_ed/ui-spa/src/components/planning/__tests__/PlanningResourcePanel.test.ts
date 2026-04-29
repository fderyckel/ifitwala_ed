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

function buildPlanningAttachment(overrides: Record<string, unknown> = {}) {
	return {
		id: 'MAT-1',
		surface: 'planning.material',
		item_id: 'MAT-1',
		owner_doctype: 'Supporting Material',
		owner_name: 'MAT-1',
		file_id: 'FILE-1',
		display_name: 'Resource',
		kind: 'other',
		preview_mode: 'icon_only',
		...overrides,
	};
}

function mountPanel(
	resources: Array<Record<string, unknown>> = [],
	props: Record<string, unknown> = {}
) {
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
					...props,
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
				attachment: buildPlanningAttachment({
					item_id: 'MAT-1',
					display_name: 'Unit diagram',
					kind: 'other',
					preview_mode: 'icon_only',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1',
				}),
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

	it('renders an inline image preview when attachment preview mode is enabled', async () => {
		mountPanel(
			[
				{
					material: 'MAT-IMG-1',
					title: 'Cell structure diagram',
					material_type: 'File',
					file_name: 'diagram.webp',
					attachment: buildPlanningAttachment({
						item_id: 'MAT-IMG-1',
						display_name: 'Cell structure diagram',
						kind: 'image',
						extension: 'webp',
						preview_mode: 'thumbnail_image',
						thumbnail_url:
							'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-IMG-1',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-1',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-IMG-1',
					}),
				},
			],
			{
				enableAttachmentPreview: true,
			}
		);
		await flushUi();

		const previewSurface = document.querySelector('[data-resource-preview-kind="image"]');
		expect(previewSurface).not.toBeNull();
		const img = previewSurface?.querySelector('img');
		expect(img?.getAttribute('src')).toBe(
			'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-IMG-1'
		);
		expect(previewSurface?.textContent || '').toContain('Image preview');
	});

	it('renders image resources from preview_url when no thumbnail_url is available', async () => {
		mountPanel(
			[
				{
					material: 'MAT-IMG-2',
					title: 'Class map',
					material_type: 'File',
					file_name: 'class-map.png',
					attachment: buildPlanningAttachment({
						item_id: 'MAT-IMG-2',
						display_name: 'Class map',
						kind: 'image',
						extension: 'png',
						preview_mode: 'icon_only',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-2',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-IMG-2',
					}),
				},
			],
			{
				enableAttachmentPreview: true,
			}
		);
		await flushUi();

		const imagePreview = document.querySelector('[data-resource-preview-kind="image"] img');
		expect(imagePreview?.getAttribute('src')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-2'
		);
		expect(document.body.textContent || '').toContain('Preview');
		expect(document.body.textContent || '').toContain('Open original');
	});

	it('retries the governed preview inline when the image thumbnail fails to load', async () => {
		mountPanel(
			[
				{
					material: 'MAT-IMG-3',
					title: 'Lab setup photo',
					material_type: 'File',
					file_name: 'lab-setup.webp',
					attachment: buildPlanningAttachment({
						item_id: 'MAT-IMG-3',
						display_name: 'Lab setup photo',
						kind: 'image',
						extension: 'webp',
						preview_mode: 'thumbnail_image',
						thumbnail_url:
							'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-IMG-3',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-3',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-IMG-3',
					}),
				},
			],
			{
				enableAttachmentPreview: true,
			}
		);
		await flushUi();

		const imagePreview = document.querySelector(
			'[data-resource-preview-kind="image"] img'
		) as HTMLImageElement | null;
		expect(imagePreview).not.toBeNull();

		imagePreview?.dispatchEvent(new Event('error'));
		await flushUi();

		const retriedImage = document.querySelector(
			'[data-resource-preview-kind="image"] img'
		) as HTMLImageElement | null;
		expect(retriedImage?.getAttribute('src')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-3'
		);
		expect(document.body.textContent || '').toContain('Open original');
	});

	it('renders a compact pdf preview tile when attachment preview mode is enabled', async () => {
		mountPanel(
			[
				{
					material: 'MAT-PDF-1',
					title: 'Lab handout',
					material_type: 'File',
					file_name: 'handout.pdf',
					attachment: buildPlanningAttachment({
						item_id: 'MAT-PDF-1',
						display_name: 'Lab handout',
						kind: 'pdf',
						extension: 'pdf',
						preview_mode: 'pdf_embed',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-PDF-1',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-PDF-1',
					}),
				},
			],
			{
				enableAttachmentPreview: true,
			}
		);
		await flushUi();

		const previewSurface = document.querySelector('[data-resource-preview-kind="pdf"]');
		expect(previewSurface).not.toBeNull();
		expect(previewSurface?.getAttribute('href')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-PDF-1'
		);
		expect(previewSurface?.querySelector('img')?.getAttribute('src')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-PDF-1'
		);
		expect(previewSurface?.textContent || '').toContain('PDF preview');
		expect(previewSurface?.textContent || '').toContain('PDF');
	});
});
