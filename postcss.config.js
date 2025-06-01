// postcss.config.js  (v4-compatible)
module.exports = {
  plugins: [
    require('@tailwindcss/postcss')({        // <-- v4 PostCSS plugin
      config: './tailwind.config.js'         // picks up your colours etc.
    }),
    require('autoprefixer'),
  ]
};