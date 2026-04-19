// ifitwala_ed/ui-spa/postcss.config.js

const isVitest = process.env.VITEST === 'true';

export default isVitest
	? {
			plugins: {},
		}
	: {
			plugins: {
				'@tailwindcss/postcss': {
					config: './tailwind.config.js',
				},
				autoprefixer: {},
			},
		};
