import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import { terser } from 'rollup-plugin-terser';

export default {
  input: {
    website: 'public/website/website.js',
    home: 'public/website/home.js'
  },
  output: {
    dir: 'public/dist',
    format: 'iife',
    entryFileNames: '[name].bundle.js',
    sourcemap: true
  },
  plugins: [
    resolve(),
    commonjs(),
    terser()
  ],
  external: [
    'bootstrap' // Let it load via CDN or external script fallback
  ]
};
