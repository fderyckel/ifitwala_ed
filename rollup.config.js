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

import resolve  from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import { terser } from 'rollup-plugin-terser';
import postcss   from 'rollup-plugin-postcss';
import { createHash } from 'crypto';
import fs from 'fs';
import path from 'path';
import sass from 'sass';

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
const basePlugins = [resolve(), commonjs()];

/* ─── Build matrix ─────────────────────────────────────────────────── */
export default [
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
                plugins: [require('autoprefixer'), require('cssnano')({ preset: 'default' })]
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
                plugins: [require('autoprefixer'), require('cssnano')({ preset: 'default' })]
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
                plugins: [require('autoprefixer'), require('cssnano')({ preset: 'default' })]
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
                  require('cssnano')({ preset: 'default' })
              ],
              preprocessor: (content, id) => {
                  const { css } = sass.renderSync({ file: id, data: content });
                  return Promise.resolve({ code: css.toString() });
              }
          })
      ]
    }
];
