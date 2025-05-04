import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import { terser } from 'rollup-plugin-terser';

export default {
  input: {
    website: 'ifitwala_ed/public/website/website.js',
    school: 'ifitwala_ed/public/website/school.js',
  },
  output: {
    dir: 'ifitwala_ed/public/dist',
    format: 'iife',
    entryFileNames: '[name].bundle.js',
    sourcemap: true,
  },
  plugins: [
    resolve(),
    commonjs(),
    terser(),
  ],
};