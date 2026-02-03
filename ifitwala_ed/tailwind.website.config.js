// ifitwala_ed/tailwind.website.config.js
module.exports = {
	important: '#ifitwala-page-root',
	corePlugins: { preflight: false },
	content: [
		'./website/templates/**/*.html',
		'./website/blocks/**/*.html',
		'./www/**/*.html',
		'./public/website/**/*.js'
	],
	theme: { extend: {} },
	plugins: [],
};
