import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import { terser } from 'rollup-plugin-terser';

export default [
  {
    input: 'ifitwala_ed/public/website/website.js',
    output: {
      file: 'ifitwala_ed/public/dist/website.bundle.js',
      format: 'iife',
      sourcemap: true,
    },
    plugins: [resolve(), commonjs(), terser()],
  },
  {
    input: 'ifitwala_ed/public/website/school.js',
    output: {
      file: 'ifitwala_ed/public/dist/school.bundle.js',
      format: 'iife',
      sourcemap: true,
    },
    plugins: [resolve(), commonjs(), terser()],
  },
];
