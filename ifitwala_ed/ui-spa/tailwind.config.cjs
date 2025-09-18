const frappeUiPreset = require('frappe-ui/src/utils/tailwind.config');

module.exports = {
  presets: [frappeUiPreset],
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: { extend: {} },
  plugins: {
    '@tailwindcss/postcss': {},
    'autoprefixer': {},
  },
};
