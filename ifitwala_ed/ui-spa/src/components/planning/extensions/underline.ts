import { Mark, mergeAttributes } from '@tiptap/core';

export interface PlanningUnderlineOptions {
	HTMLAttributes: Record<string, unknown>;
}

declare module '@tiptap/core' {
	interface Commands<ReturnType> {
		underline: {
			setUnderline: () => ReturnType;
			toggleUnderline: () => ReturnType;
			unsetUnderline: () => ReturnType;
		};
	}
}

export const PlanningUnderline = Mark.create<PlanningUnderlineOptions>({
	name: 'underline',

	addOptions() {
		return {
			HTMLAttributes: {},
		};
	},

	parseHTML() {
		return [
			{ tag: 'u' },
			{
				style: 'text-decoration',
				consuming: false,
				getAttrs: value => (String(value || '').includes('underline') ? {} : false),
			},
			{
				style: 'text-decoration-line',
				consuming: false,
				getAttrs: value => (String(value || '').includes('underline') ? {} : false),
			},
		];
	},

	renderHTML({ HTMLAttributes }) {
		return ['u', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes), 0];
	},

	addCommands() {
		return {
			setUnderline:
				() =>
				({ commands }) =>
					commands.setMark(this.name),
			toggleUnderline:
				() =>
				({ commands }) =>
					commands.toggleMark(this.name),
			unsetUnderline:
				() =>
				({ commands }) =>
					commands.unsetMark(this.name),
		};
	},

	addKeyboardShortcuts() {
		return {
			'Mod-u': () => this.editor.commands.toggleUnderline(),
			'Mod-U': () => this.editor.commands.toggleUnderline(),
		};
	},
});

export default PlanningUnderline;
