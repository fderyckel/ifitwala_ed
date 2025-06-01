// postcss.config.js
module.exports = {
  plugins: [
		require('@tailwindcss/postcss')(),
    require('autoprefixer'),
    require('cssnano')({
      preset: 'default',
    }),
  ],
};

