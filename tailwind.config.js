module.exports = {
	important: '.desk-tw', 
	content: [
		"./ifitwala_ed/public/js/**/*.js",               // only JS where Tailwind classes are likely used
		"./ifitwala_ed/public/css/**/*.css",             // any raw CSS using @apply or custom Tailwind
		"./ifitwala_ed/templates/**/*.html",             // standard Jinja templates
		"./ifitwala_ed/www/**/*.html",                   // custom public pages
		'./ifitwala_ed/schedule/page/**/*.{js,html}'
	],
	safelist: [ 
		{ pattern: /.*/ } 
  ],
	plugins: [
		require('@tailwindcss/forms'),     // handles filters/searches better
		require('@tailwindcss/typography') // optional for better content rendering
	],
	theme: {
    extend: {},
  },
};
