/** @type {import('tailwindcss').Config} */
module.exports = {
	content: [
		"./ifitwala_ed/public/js/**/*.js",               // only JS where Tailwind classes are likely used
		"./ifitwala_ed/public/css/**/*.css",             // any raw CSS using @apply or custom Tailwind
		"./ifitwala_ed/templates/**/*.html",             // standard Jinja templates
		"./ifitwala_ed/www/**/*.html",                   // custom public pages
		'./ifitwala_ed/schedule/page/**/*.{js,html}'
	],
	safelist: [
  	// grid + spacing
    'grid', 'grid-cols-1', 'sm:grid-cols-2', 'md:grid-cols-3',
    'xl:grid-cols-5', 'gap-6', 'px-4', 'mt-4',
    // card + text
    'bg-white', 'rounded-xl', 'p-4', 'text-center', 'shadow',
    'hover:-translate-y-1', 'transition', 'duration-200',
    'text-lg', 'font-semibold', 'text-gray-800',
    'text-sm', 'text-gray-500',
    // avatar
    'rounded-full', 'object-cover', 'bg-neutral-100'
  ],
	plugins: [
		require('@tailwindcss/forms'),     // handles filters/searches better
		require('@tailwindcss/typography') // optional for better content rendering
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
};
