/* eslint-env node */
module.exports = {
  root: true,
  // Default for standard Frappe files (CommonJS)
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
    wn: "readonly"
  },
  rules: {
    "no-var": "warn",
    "prefer-const": "warn",
    eqeqeq: ["error", "smart"],
    // REMOVED "indent" rule because it fights with Prettier
    quotes: ["error", "single", { avoidEscape: true }],
    semi: ["error", "always"],
    "prettier/prettier": "error"
  },
  overrides: [
    // 1. Vue SPA & Modern Configs (The Fix is Here!)
    {
      // We explicitly point to your actual SPA folder
      files: ["ifitwala_ed/ui-spa/**/*.{js,ts,vue}"],
      parserOptions: { sourceType: "module" },
      env: { browser: true, es2021: true, node: true },
      extends: ["eslint:recommended", "plugin:vue/vue3-recommended", "plugin:prettier/recommended"],
      plugins: ["vue", "prettier"]
    },

    // 2. Standard Node Scripts (e.g. root config files)
    {
      files: ["**/*.config.{js,cjs,mjs}", "scripts/**/*.js", "rollup*.js", "vite*.{js,ts}"],
      // Keep ignoring the SPA folder so it doesn't get forced into "script" mode
      excludedFiles: ["ifitwala_ed/ui-spa/**/*"],
      env: { node: true },
      parserOptions: { sourceType: "script" }
    }
  ]
};
