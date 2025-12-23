// ifitwala_ed/ui-spa/postcss.config.js

export default {
  plugins: {
    'postcss-import': {},
    '@tailwindcss/postcss': {
      config: './tailwind.config.js',
    },
    autoprefixer: {},
  },
};
