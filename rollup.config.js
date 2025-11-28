/**
 * Rollup build – Ifitwala Ed
 *
 * ── Public-facing assets (heavy traffic) ──────────────────────────────
 * website.js  + website.css  → public/website/website.min.{js|css}
 * school.js   + school.css   → public/website/school.min.{js|css}
 *
 * ── Student-portal bundle  (authenticated traffic, cache-busted) ─────
 * index.js (+ imports)       → public/dist/student_portal.<hash>.{js|css}
 *
 * ── Desk-only hierarchy chart (rarely used, lazy-loaded) ─────────────
 * hierarchy_chart.scss       → public/dist/hierarchy_chart.<hash>.css
 */

const path = require('path');
const fs = require('fs');
const resolve = require('@rollup/plugin-node-resolve');
const commonjs = require('@rollup/plugin-commonjs');
const postcss = require('rollup-plugin-postcss');
const terser = require('@rollup/plugin-terser');
const { createHash } = require('crypto');
const copy = require('rollup-plugin-copy');

/* NEW: inline CSS @import (needed for bootstrap-icons.css) */
const postcssImport = require('postcss-import');

// Resolve the app directory regardless of whether rollup runs from bench root
// (/apps/ifitwala_ed) or the package directory (/apps/ifitwala_ed/ifitwala_ed).
const portalEntry = 'public/js/student_portal/index.js';
const candidateAppDirs = [
	__dirname,
	path.join(__dirname, 'ifitwala_ed'),
];
const appDir = candidateAppDirs.find((dir) =>
	fs.existsSync(path.join(dir, portalEntry))
) || candidateAppDirs[0];

const fromApp = (...segments) => path.join(appDir, ...segments);
const dist = fromApp('public/dist');
const websiteSrc = fromApp('public/website');
const portalSrc = fromApp('public/js/student_portal');
const fontsDir = fromApp('public/fonts');

function contentHash(file) {
	return createHash('sha256')
		.update(fs.readFileSync(file))
		.digest('hex')
		.slice(0, 8);
}

const portalHash = contentHash(path.join(portalSrc, 'index.js'));
const websiteJsHash = contentHash(path.join(websiteSrc, 'website.js'));
const websiteCssHash = contentHash(path.join(websiteSrc, 'website.css'));
const schoolJsHash  = contentHash(path.join(websiteSrc, 'school.js'));
const schoolCssHash = contentHash(path.join(websiteSrc, 'school.css'));

const basePlugins = [
	resolve(),
	commonjs(),
];

/* ─── Build matrix ─────────────────────────────────────────────────── */
module.exports = [
	// ── js for full calendar and other utils ──
	{
		input: fromApp("public/js/ifitwala_ed.bundle.js"),
		output: {
			file: `${dist}/ifitwala_ed.bundle.js`,
			format: "iife",
			sourcemap: true,
		},
		plugins: [
			...basePlugins,
			terser(),
		],
	},

	// ── css for full calendar ──
	{
		input: fromApp("public/scss/fullcalendar.scss"),
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${dist}/fullcalendar.bundle.css`,
				minimize: true,
				plugins: [
					require("postcss-import"),
	       	require("autoprefixer")
				],
				preprocessor: async (content, id) => {
					const sass = await import('sass');
					const result = await sass.compileAsync(id);
					return { code: result.css };
				},
			}),
		],
	},

	// ── Bootstrap 5: Student Group + Attendance styles ──
	{
		input: fromApp("public/scss/student_group_cards.scss"),
		output: {
			file: `${dist}/student_group_cards.bundle.css`,
			format: "es"
		},
		plugins: [
			postcss({
				extract: true,
				minimize: true,
				plugins: [
					require("autoprefixer"),
					require("cssnano")({ preset: ["default", { normalizeUnicode: false }] }),
				],
				preprocessor: async (content, id) => {
					const sass = await import('sass');
					const result = await sass.compileAsync(id);
					return { code: result.css };
				},
			}),
			copy({
				targets: [
					{
						src: 'node_modules/bootstrap-icons/font/fonts/*',
						/* CHANGED: put fonts in public/fonts so ../fonts resolves from dist/*.css */
						dest: fontsDir
					},
					{
						src: 'node_modules/bootstrap/dist/js/bootstrap.bundle.min.js',
						dest: dist
					}
				],
				verbose: true,
				hook: 'buildEnd'
			})
		]
	},

	// ── Other desk pages CSS ──
	{
		input: fromApp('public/css/other_desk_pages.css'),
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
			file: `${dist}/website.${websiteJsHash}.bundle.js`,
			format: 'iife',
			sourcemap: true,
		},
		plugins: [
			...basePlugins,
			terser(),
			{
				name: 'alias-stable-website-js',
				writeBundle() {
					const p = dist;
					try { fs.copyFileSync(`${p}/website.${websiteJsHash}.bundle.js`, `${p}/website.bundle.js`); } catch {}
				}
			}
		],
	},

	// ── Website CSS ──
	{
		input: `${websiteSrc}/website.css`,
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${dist}/website.${websiteCssHash}.bundle.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
			{
				name: 'alias-stable-website-css',
				writeBundle() {
					const p = dist;
					try { fs.copyFileSync(`${p}/website.${websiteCssHash}.bundle.css`, `${p}/website.bundle.css`); } catch {}
				}
			}
		],
	},

	// ── School JS ──
	{
		input: `${websiteSrc}/school.js`,
		output: {
			file: `${dist}/school.${schoolJsHash}.bundle.js`,
			format: 'iife',
			sourcemap: true,
		},
		plugins: [
			...basePlugins,
			terser(),
			{
				name: 'alias-stable-school-js',
				writeBundle() {
					const p = dist;
					try { fs.copyFileSync(`${p}/school.${schoolJsHash}.bundle.js`, `${p}/school.bundle.js`); } catch {}
				}
			}
		],
	},

	// ── School CSS ──
	{
		input: `${websiteSrc}/school.css`,
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${dist}/school.${schoolCssHash}.bundle.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
			{
				name: 'alias-stable-school-css',
				writeBundle() {
					const p = dist;
					try { fs.copyFileSync(`${p}/school.${schoolCssHash}.bundle.css`, `${p}/school.bundle.css`); } catch {}
				}
			}
		],
	},

	// ── Student-portal bundle (hashed) ──
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
				plugins: [
					/* NEW: inline @import (bootstrap-icons.css) into the output */
					postcssImport,
					require('autoprefixer')
				],
				preprocessor: async (content, id) => {
					const sass = await import('sass');
					const result = await sass.compileAsync(id);
					return { code: result.css };
				},
			}),
			copy({
				targets: [
					{
						src: 'node_modules/bootstrap-icons/font/fonts/*',
						/* CHANGED: match ../fonts from dist CSS */
						dest: fontsDir
					}
				],
				verbose: true,
				hook: 'writeBundle'
			}),
			...basePlugins,
			terser(),
			{
				// write stable (non-hashed) aliases so templates don't need to chase hashes
				name: 'alias-stable-output',
				writeBundle() {
					const fs = require('fs');
					const p = dist;
					fs.copyFileSync(
						`${p}/student_portal.${portalHash}.bundle.css`,
						`${p}/student_portal.bundle.css`
					);
					fs.copyFileSync(
						`${p}/student_portal.${portalHash}.bundle.js`,
						`${p}/student_portal.bundle.js`
					);
				}
			}
		],
	},

	// ── Hierarchy Chart SCSS → stable min.css ──
	{
		input: fromApp('public/scss/hierarchy_chart.scss'),
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
