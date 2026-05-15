const { defineConfig } = require("cypress");

module.exports = defineConfig({
	video: false,
	defaultCommandTimeout: 10000,
	requestTimeout: 10000,
	responseTimeout: 15000,
	e2e: {
		baseUrl: "http://127.0.0.1:8000",
		specPattern: "cypress/e2e/**/*.cy.js",
		supportFile: "cypress/support/e2e.js",
	},
});
