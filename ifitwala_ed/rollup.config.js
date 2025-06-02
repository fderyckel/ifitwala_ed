import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';
import postcss from 'rollup-plugin-postcss';

export default {
  input: 'public/css/input.css',
  output: {
    dir: 'public/dist',
    format: 'esm'
  },
  plugins: [
    postcss({
      plugins: [
        tailwindcss,
        autoprefixer
      ],
      extract: true,
      minimize: true
    })
  ]
};
