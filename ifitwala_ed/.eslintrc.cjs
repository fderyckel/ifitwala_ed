/* eslint-env node */
module.exports = {
	root: true,
	// For Desk JS, keep sourceType "script". For SPA (Vue) the override below flips to "module".
	parserOptions: { ecmaVersion: 2021, sourceType: "script" },
	env: { browser: true, es2021: true, jquery: true },
	extends: ["eslint:recommended", "plugin:prettier/recommended"],
	plugins: ["prettier"],
	globals: {
		frappe: "readonly",
		__: "readonly",
		cur_frm: "readonly",
		cur_dialog: "readonly",
		locals: "readonly",
		wn: "readonly" // legacy in a few places
	},
	rules: {
		// keep code modern but compatible with Desk
		"no-var": "warn",
		"prefer-const": "warn",
		eqeqeq: ["error", "smart"],
		indent: ["error", "tab"],
		quotes: ["error", "single", { avoidEscape: true }],
		semi: ["error", "always"],
		"prettier/prettier": "error"
	},
	overrides: [
		// Vue SPA folders (if you have a /frontend or /ui folder)
		{
			files: ["frontend/**/*.{js,vue}", "ui/**/*.{js,vue}"],
			parserOptions: { sourceType: "module" },
			env: { browser: true, es2021: true },
			extends: ["eslint:recommended", "plugin:vue/vue3-recommended", "plugin:prettier/recommended"],
			plugins: ["vue", "prettier"]
		},
		// Node build scripts
		{
			files: ["**/*.config.{js,cjs,mjs}", "scripts/**/*.js", "rollup*.js", "vite*.{js,ts}"],
			env: { node: true },
			parserOptions: { sourceType: "script" }
		}
	]
};
