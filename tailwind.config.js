
module.exports = {
	important: '.desk-tw', 
	content: [
		"./ifitwala_ed/public/js/**/*.js",               // only JS where Tailwind classes are likely used
		"./ifitwala_ed/public/css/**/*.css",             // any raw CSS using @apply or custom Tailwind
		"./ifitwala_ed/templates/**/*.html",             // standard Jinja templates
		"./ifitwala_ed/www/**/*.html",                   // custom public pages
		'./ifitwala_ed/schedule/page/student_group_cards/**/*.{js,html}'
	],
	safelist: [
		'bg-blue-600',
		'text-white',
		'px-5',
		'py-2',
		'rounded',
		'hover:bg-blue-700',
		'transition',
		'mt-6',
		'flex',
		'justify-center',
		'text-center',
		'text-2xl',
		'font-semibold',
		'text-gray-800',
		'text-sm',
		'text-gray-500',
		'rounded-xl',
		'shadow',
		'duration-200',
		'hover:-translate-y-1'
	], 
	plugins: [
		require('@tailwindcss/forms'),     // handles filters/searches better
		require('@tailwindcss/typography') // optional for better content rendering
	],
	theme: {
    extend: {},
  },
};
