// ifitwala_ed/tailwind.config.js
module.exports = {
	prefix: 'tw-',
  important: '.desk-tw',
  corePlugins: { preflight: false },
	content: [
		"./ifitwala_ed/public/js/**/*.js",
		"./ifitwala_ed/public/css/**/*.css",
		"./ifitwala_ed/templates/**/*.html",
		"./ifitwala_ed/www/**/*.html",
		"./ifitwala_ed/schedule/page/**/*.{js,html}"
	],
	safelist: [
		'bg-blue-600',
		'text-white',
		'px-5',
		'py-2',
		'rounded',
		'hover:bg-blue-700',
		'transition'
	],
	theme: { extend: {} },
	plugins: [
		require('@tailwindcss/forms')({ strategy: 'class' }), 
		require('@tailwindcss/typography')({ className: 'tw-prose' })
	],
};
