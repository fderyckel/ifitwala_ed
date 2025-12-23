// ifitwala_ed/ui-spa/tailwind.config.js


import frappeUiPreset from 'frappe-ui/tailwind';
import colors from 'tailwindcss/colors';

const withAlpha = (variable) => `rgb(var(${variable}) / <alpha-value>)`;

export default {
	presets: [frappeUiPreset],
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
				ink: withAlpha('--ink-rgb'),
				'slate-token': withAlpha('--slate-rgb'),
				canopy: withAlpha('--canopy-rgb'),
				leaf: withAlpha('--leaf-rgb'),
				moss: withAlpha('--moss-rgb'),
				sky: withAlpha('--sky-rgb'),
				sand: withAlpha('--sand-rgb'),
				clay: withAlpha('--clay-rgb'),
				jacaranda: withAlpha('--jacaranda-rgb'),
				flame: withAlpha('--flame-rgb'),
				border: withAlpha('--border-rgb'),

				surface: withAlpha('--surface-rgb'),
				'surface-soft': withAlpha('--surface-rgb'),
				'surface-strong': withAlpha('--surface-strong-rgb'),
			},
		},
	},
	plugins: [],
};
