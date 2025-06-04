// ifitwala_ed/tailwind.config.js
module.exports = {
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
		'tw-bg-blue-600',
		'tw-text-white',
		'tw-px-5',
		'tw-py-2',
		'tw-rounded',
		'tw-hover:bg-blue-700',
		'tw-transition'
	],
	theme: { extend: {} },
	plugins: [
		require('@tailwindcss/forms')({ strategy: 'class' }), 
		require('@tailwindcss/typography')({ className: 'tw-prose' })
	],
};
