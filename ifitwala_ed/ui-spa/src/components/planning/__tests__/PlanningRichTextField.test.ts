import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const { textEditorProps, updateSpy } = vi.hoisted(() => ({
	textEditorProps: [] as Array<{ content?: string }>,
	updateSpy: vi.fn(),
}));

vi.mock('frappe-ui', () => ({
	TextEditor: defineComponent({
		name: 'TextEditorStub',
		props: ['content'],
		emits: ['change'],
		setup(props, { emit }) {
			textEditorProps.push(props as { content?: string });
			return () =>
				h(
					'button',
					{
						type: 'button',
						'data-testid': 'text-editor',
						'data-content': props.content || '',
						onClick: () => emit('change', '<p><br></p>'),
					},
					props.content || ''
				);
		},
	}),
}));

import PlanningRichTextField from '@/components/planning/PlanningRichTextField.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
}

function mountField(props: Record<string, unknown>) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(PlanningRichTextField, {
					...props,
					'onUpdate:modelValue': updateSpy,
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
	textEditorProps.length = 0;
	updateSpy.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('PlanningRichTextField', () => {
	it('feeds the editor a safe empty document when the model is blank', async () => {
		mountField({
			modelValue: '',
			editable: true,
		});
		await flushUi();

		expect(document.querySelector('[data-testid="text-editor"]')?.getAttribute('data-content')).toBe(
			'<p></p>'
		);
	});

	it('normalizes empty editor output back to an empty string', async () => {
		mountField({
			modelValue: '<p>Lesson notes</p>',
			editable: true,
		});
		await flushUi();

		document
			.querySelector('[data-testid="text-editor"]')
			?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(updateSpy).toHaveBeenCalledWith('');
	});
});
