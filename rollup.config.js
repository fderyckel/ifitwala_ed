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

import path from 'path';
import fs from 'fs';
import alias from '@rollup/plugin-alias';
import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import postcss from 'rollup-plugin-postcss';
import { terser } from 'rollup-plugin-terser';
import { createHash } from 'crypto';


const projectRootDir = path.resolve(__dirname);

/* ─── Paths ────────────────────────────────────────────────────────── */
const dist       = 'ifitwala_ed/public/dist';
const websiteSrc = 'ifitwala_ed/public/website';
const portalSrc  = 'ifitwala_ed/public/js/student_portal';

/* ─── Helper – content hash for long‑lived bundles ─────────────────── */
function contentHash(file) {
	return createHash('sha256')
		.update(fs.readFileSync(file))
		.digest('hex')
		.slice(0, 8);
}
const portalHash = contentHash(path.join(portalSrc, 'index.js'));

/* ─── Common plugins ───────────────────────────────────────────────── */
const basePlugins = [ 
	resolve(),
	commonjs(),
	alias({
		entries: [
			{ find: '@fullcalendar-css', replacement: path.resolve(projectRootDir, 'node_modules/@fullcalendar') }
		]
	})
];

/* ─── Build matrix ─────────────────────────────────────────────────── */
export default [
	/* ── Desk bundle (shared by all staff-facing pages) ─────────────── */
	{
		input: "ifitwala_ed/public/js/ifitwala_ed.bundle.js",   // source
		output: {
			file: `${dist}/ifitwala_ed.bundle.js`,                
			format: "iife",
			sourcemap: true
		}, 
		plugins: [
			...basePlugins,
			postcss({
				extract: `${dist}/ifitwala_ed.bundle.css`,   
				minimize: true,
			}),
			terser()
		]
	},
	/* ── Other desk pages (CSS only, no JS) ─────────────────────────── */
	{
		input: "ifitwala_ed/public/css/other_desk_pages.css",
		output: { dir: "." },
		plugins: [
			postcss({
				extract: `${dist}/other_desk_pages.min.css`,
				minimize: true,
			})
		]
	},	
	/* ── Website JS ── */
	{
		input: `${websiteSrc}/website.js`,
		output: {
			file: `${websiteSrc}/website.min.js`,
			format: 'iife',
			sourcemap: true
		},
		plugins: [...basePlugins, terser()]
	},

	/* ── Website CSS ── */
	{
		input: `${websiteSrc}/website.css`,
		output: { dir: '.' },   // no JS output – CSS only
		plugins: [
			postcss({
				extract: `${websiteSrc}/website.min.css`,
				minimize: true,
				plugins: [require('autoprefixer'), 
				]
			})
		]
	},

	/* ── School JS ── */
	{
		input: `${websiteSrc}/school.js`,
		output: {
			file: `${websiteSrc}/school.min.js`,
			format: 'iife',
			sourcemap: true
		},
		plugins: [...basePlugins, terser()]
	},

	/* ── School CSS ── */
	{
		input: `${websiteSrc}/school.css`,
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${websiteSrc}/school.min.css`,
				minimize: true,
				plugins: [require('autoprefixer'), 
				]
			})
		]
	},

	/* ── Student‑portal bundle (JS + extracted CSS) ── */
	{
		input: `${portalSrc}/index.js`,
		output: {
			file: `${dist}/student_portal.${portalHash}.bundle.js`,
			format: 'iife',
			sourcemap: true
		},
		plugins: [
			...basePlugins,
			terser(),
			postcss({
				extract: `${dist}/student_portal.${portalHash}.bundle.css`,
				minimize: true,
				plugins: [
					require('autoprefixer'), 
				]
			})
		]
	},
	/* ── Hierarchy chart (SCSS → minified CSS, stable filename) ── */
	{
		input: 'ifitwala_ed/public/scss/hierarchy_chart.scss',
		output: { dir: '.' },          // CSS‑only job, no JS
		plugins: [
			postcss({
				extract: `${dist}/hierarchy_chart.min.css`,   // << stable name
				minimize: true,
				plugins: [
					require('autoprefixer'),
				],
				preprocessor: async (content, id) => {
					const sass = await import('sass');
					const result = await sass.compileAsync(id);
					return { code: result.css };
				}
			})
		]
	}, 
];
