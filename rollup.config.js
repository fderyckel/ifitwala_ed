// rollup.config.js
/**
 * Rollup build – Ifitwala Ed
 *
 * ── Public-facing assets (heavy traffic) ──────────────────────────────
 * website.js + website.css → public/js/ifitwala_site.*.bundle.js + public/css/ifitwala_site.*.bundle.css
 *
 */

const path = require('path');
const fs = require('fs');
const resolve = require('@rollup/plugin-node-resolve');
const commonjs = require('@rollup/plugin-commonjs');
const postcss = require('rollup-plugin-postcss');
const terser = require('@rollup/plugin-terser');
const { createHash } = require('crypto');
const tailwind = require('@tailwindcss/postcss');

// Resolve the app directory regardless of whether rollup runs from bench root
// (/apps/ifitwala_ed) or the package directory (/apps/ifitwala_ed/ifitwala_ed).
const appEntry = 'public/js/ifitwala_ed.entry.js';
const candidateAppDirs = [
	__dirname,
	path.join(__dirname, 'ifitwala_ed'),
];
const appDir = candidateAppDirs.find((dir) =>
	fs.existsSync(path.join(dir, appEntry))
) || candidateAppDirs[0];

const fromApp = (...segments) => path.join(appDir, ...segments);
const jsDest = fromApp('public/js');
const cssDest = fromApp('public/css');
const websiteSrc = fromApp('public/website');

function contentHash(file) {
	return createHash('sha256')
		.update(fs.readFileSync(file))
		.digest('hex')
		.slice(0, 8);
}

function cleanupOldWebsiteBundles(dir, currentFileName, matcher) {
	if (!fs.existsSync(dir)) return;
	const files = fs.readdirSync(dir);
	for (const file of files) {
		if (!matcher.test(file)) continue;
		if (file === currentFileName) continue;
		try {
			fs.unlinkSync(path.join(dir, file));
		} catch {}
	}
}

function cleanupMatchingBundles(dir, matcher) {
	if (!fs.existsSync(dir)) return;
	const files = fs.readdirSync(dir);
	for (const file of files) {
		if (!matcher.test(file)) continue;
		try {
			fs.unlinkSync(path.join(dir, file));
		} catch {}
	}
}

const websiteJsHash = contentHash(path.join(websiteSrc, 'website.js'));
const websiteCssHash = contentHash(path.join(websiteSrc, 'website.css'));

const basePlugins = [
	resolve(),
	commonjs(),
];

/* ─── Build matrix ─────────────────────────────────────────────────── */
module.exports = [
	// ── js for full calendar and other utils ──
	{
		input: fromApp("public/js/ifitwala_ed.entry.js"),
		output: {
			file: `${jsDest}/ifitwala_ed.bundle.js`,
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
				extract: `${cssDest}/fullcalendar.bundle.css`,
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

	// ── Other desk pages CSS ──
	{
		input: fromApp('public/css/other_desk_pages.css'),
		output: { dir: '.' },
		plugins: [
			postcss({
				extract: `${cssDest}/other_desk_pages.min.css`,
				minimize: true,
				plugins: [require('autoprefixer')],
			}),
		],
	},

	// ── Website JS ──
	{
		input: `${websiteSrc}/website.js`,
		output: {
			file: `${jsDest}/ifitwala_site.${websiteJsHash}.bundle.js`,
			format: 'iife',
			sourcemap: true,
		},
		plugins: [
			...basePlugins,
			terser(),
			{
				name: 'alias-stable-website-js',
				writeBundle() {
					const p = jsDest;
					const current = `ifitwala_site.${websiteJsHash}.bundle.js`;
					cleanupOldWebsiteBundles(p, current, /^ifitwala_site\.[a-f0-9]{8}\.bundle\.js$/);
					cleanupMatchingBundles(p, /^website\.[a-f0-9]{8}\.bundle\.js$/);
					cleanupMatchingBundles(p, /^website\.bundle\.js$/);
					try { fs.copyFileSync(`${p}/${current}`, `${p}/ifitwala_site.bundle.js`); } catch {}
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
				extract: `${cssDest}/ifitwala_site.${websiteCssHash}.bundle.css`,
				minimize: true,
				plugins: [
					tailwind({ config: path.join(appDir, 'tailwind.website.config.js') }),
					require('autoprefixer')
				],
			}),
			{
				name: 'alias-stable-website-css',
				writeBundle() {
					const p = cssDest;
					const current = `ifitwala_site.${websiteCssHash}.bundle.css`;
					cleanupOldWebsiteBundles(p, current, /^ifitwala_site\.[a-f0-9]{8}\.bundle\.css$/);
					cleanupMatchingBundles(p, /^website\.[a-f0-9]{8}\.bundle\.css$/);
					cleanupMatchingBundles(p, /^website\.bundle\.css$/);
					try { fs.copyFileSync(`${p}/${current}`, `${p}/ifitwala_site.bundle.css`); } catch {}
				}
			}
		],
	},


];
