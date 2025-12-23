// ifitwala_ed/ui-spa/tailwind.config.js


import frappeUiPreset from 'frappe-ui/tailwind';
import colors from 'tailwindcss/colors';

const withOpacity = (variable) => ({ opacityValue }) => {
	if (opacityValue === undefined) {
		return `rgb(var(${variable}) / 1)`;
	}
	return `rgb(var(${variable}) / ${opacityValue})`;
};
const wrapUtilities = (plugin) => {
	if (typeof plugin !== 'function') {
		return plugin;
	}

	const wrapped = (api) => {
		const { addUtilities, addComponents } = api;
		const safeAddUtilities = (utilities, options) => {
			if (!utilities || typeof utilities !== 'object') {
				return addUtilities(utilities, options);
			}

			const safe = {};
			const unsafe = {};

			for (const [selector, rules] of Object.entries(utilities)) {
				if (selector.startsWith('.')) {
					safe[selector] = rules;
				} else {
					unsafe[selector] = rules;
				}
			}

			if (Object.keys(safe).length) {
				addUtilities(safe, options);
			}
			if (Object.keys(unsafe).length) {
				addComponents(unsafe, options);
			}
		};

		return plugin({
			...api,
			addUtilities: safeAddUtilities,
		});
	};

	Object.assign(wrapped, plugin);
	return wrapped;
};

const frappeUiPresetSafe = {
	...frappeUiPreset,
	plugins: (frappeUiPreset.plugins || []).map(wrapUtilities),
};

export default {
	presets: [frappeUiPresetSafe],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts}',
		'./node_modules/frappe-ui/src/**/*.{vue,js,ts}',
	],
	safelist: [
		'bg-surface',
		'bg-surface-soft',
		'bg-surface-strong',
	],
	theme: {
		extend: {
			/* 1. Fonts wired to CSS vars (tokens.css) */
			fontFamily: {
				sans: ['var(--font-sans)'],
				serif: ['var(--font-serif)'],
				mono: ['var(--font-mono)'],
			},

			boxShadow: {
				inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
			},
			opacity: { 15: '0.15', 65: '0.65', 85: '0.85' },
			colors: {
				slate: colors.slate,
				ink: withOpacity('--ink-rgb'),
				'slate-token': withOpacity('--slate-rgb'),
				canopy: withOpacity('--canopy-rgb'),
				leaf: withOpacity('--leaf-rgb'),
				moss: withOpacity('--moss-rgb'),
				sky: withOpacity('--sky-rgb'),
				sand: withOpacity('--sand-rgb'),
				clay: withOpacity('--clay-rgb'),
				jacaranda: withOpacity('--jacaranda-rgb'),
				flame: withOpacity('--flame-rgb'),
				border: withOpacity('--border-rgb'),

				surface: withOpacity('--surface-rgb'),
				'surface-soft': withOpacity('--surface-rgb'),
				'surface-strong': withOpacity('--surface-strong-rgb'),
			},
		},
	},
	plugins: [],
};
