
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
		"./ifitwala_ed/public/js/**/*.js",               // only JS where Tailwind classes are likely used
		"./ifitwala_ed/public/css/**/*.css",             // any raw CSS using @apply or custom Tailwind
		"./ifitwala_ed/templates/**/*.html",             // standard Jinja templates
		"./ifitwala_ed/www/**/*.html",                   // custom public pages
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
