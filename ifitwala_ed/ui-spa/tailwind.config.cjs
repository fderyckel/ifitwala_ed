module.exports = {
	presets: [require('frappe-ui/src/utils/tailwind.config')],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts}'
	],
	theme: {
		extend: {}
	},
	plugins: []
}
