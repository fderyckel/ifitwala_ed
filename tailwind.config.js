
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './ifitwala_ed/public/**/*.{js,html}',
    './ifitwala_ed/templates/**/*.html',
    './ifitwala_ed/**/*.py',
    './frappe/**/*.{html,js}', // in case you use custom Frappe templates
  ],
  theme: {
    extend: {
      colors: {
        ifitwala: {
          green: '#2e7d32',
          light: '#a5d6a7',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),     // handles filters/searches better
    require('@tailwindcss/typography') // optional for better content rendering
  ],
};
