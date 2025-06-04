/**
 * Rollup build – Ifitwala Ed
 *
 * ── Public‑facing assets (heavy traffic) ──────────────────────────────
 * website.js  + website.css  → public/website/website.min.{js|css}
 * school.js   + school.css   → public/website/school.min.{js|css}
 *
 * ── Student‑portal bundle  (authenticated traffic, cache‑busted) ─────
 * index.js (+ imports)       → public/dist/student_portal.<hash>.{js|css}
 *
 * ── Desk‑only hierarchy chart (rarely used, lazy‑loaded) ─────────────
 * hierarchy_chart.scss       → public/dist/hierarchy_chart.<hash>.css
 */


const path = require('path');
const fs = require('fs');
const alias = require('@rollup/plugin-alias');
const resolve = require('@rollup/plugin-node-resolve');
const commonjs = require('@rollup/plugin-commonjs');
const postcss = require('rollup-plugin-postcss');
const terser = require('@rollup/plugin-terser');
const { createHash } = require('crypto');

const projectRootDir = __dirname;
const dist = 'ifitwala_ed/public/dist';
const websiteSrc = 'ifitwala_ed/public/website';
const portalSrc = 'ifitwala_ed/public/js/student_portal';


function contentHash(file) {
	return createHash('sha256')
		.update(fs.readFileSync(file))
		.digest('hex')
		.slice(0, 8);
}

const portalHash = contentHash(path.join(portalSrc, 'index.js'));

const basePlugins = [
	resolve(),
	commonjs(),
	alias({
		entries: [
			{
				find: '@fullcalendar-css',
				replacement: path.resolve(projectRootDir, 'node_modules/@fullcalendar'),
			},
		],
	}),
];

/* ─── Build matrix ─────────────────────────────────────────────────── */
module.exports = [
	// ── Bootstrap 5: Student Group + Attendance styles ──
	{
		input: 'ifitwala_ed/public/css/student_group_cards.css',
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${dist}/student_group_cards.min.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
		],
	},

	// ── Other desk pages CSS ──
	{
		input: 'ifitwala_ed/public/css/other_desk_pages.css',
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${dist}/other_desk_pages.min.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
		],
	},

	// ── Website JS ──
	{
		input: `${websiteSrc}/website.js`,
		output: {
			file: `${websiteSrc}/website.min.js`,
			format: 'iife',
			sourcemap: true,
		},
		plugins: [...basePlugins, terser()],
	},

	// ── Website CSS ──
	{
		input: `${websiteSrc}/website.css`,
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${websiteSrc}/website.min.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
		],
	},

	// ── School JS ──
	{
		input: `${websiteSrc}/school.js`,
		output: {
			file: `${websiteSrc}/school.min.js`,
			format: 'iife',
			sourcemap: true,
		},
		plugins: [...basePlugins, terser()],
	},

	// ── School CSS ──
	{
		input: `${websiteSrc}/school.css`,
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${websiteSrc}/school.min.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
		],
	},

	// ── Student‑portal bundle (hashed) ──
	{
		input: `${portalSrc}/index.js`,
		output: {
			file: `${dist}/student_portal.${portalHash}.bundle.js`,
			format: 'iife',
			sourcemap: true,
		},
		plugins: [
			postcss({
				extract: path.resolve(dist, `student_portal.${portalHash}.bundle.css`),
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
			...basePlugins,
			terser(),
		],
	},

	// ── Hierarchy Chart SCSS → stable min.css ──
	{
		input: 'ifitwala_ed/public/scss/hierarchy_chart.scss',
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${dist}/hierarchy_chart.min.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
				preprocessor: async (content, id) => {
					const sass = await import('sass');
					const result = await sass.compileAsync(id);
					return { code: result.css };
				},
			}),
		],
	},
];
