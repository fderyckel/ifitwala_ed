// postcss.config.js  (v4-compatible)
module.exports = {
  plugins: [
    require('@tailwindcss/postcss')({ config: './tailwind.config.js'}),
    require('autoprefixer'),
  ]
};